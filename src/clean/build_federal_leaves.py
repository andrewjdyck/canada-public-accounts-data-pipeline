"""
Federal expense grid (Volume I Table 3.6) -> data/gold/federal-leaves.csv.

Design: docs/federal-design.md. Every federal dollar lands in exactly one leaf, and every
leaf has a treatment:
  service | financing | unidentified                       -> in the shares
  pass_through_provinces | other_municipal_indigenous_transfers
  | pollution_pricing_returns                               -> kept here, excluded from shares

How a cell (ministry x payment type) becomes leaves:
  major_transfers / other_transfers: named leaves in config/federal/leaves.csv (amounts from
      silver cells, or fixed amounts quoted from the notes); a leaf with no amount source takes
      the residual of the cell. Other transfers without a residual leaf fall back to the
      ministry default in config/federal/ministry-services.csv.
      (Volume II program lines will add leaves here once 2026-vol2-eng.pdf is in bronze.)
  other_expenses: ministry default service.
  public_debt_charges: financing / Debt Charges.
  Net actuarial losses (one row in the grid): allocated to ministries in proportion to their
      other expenses (proxy for personnel cost), then treated like that ministry's operations.

Checks (exit non-zero, nothing written, on failure):
  - every grid ministry has defaults; every leaves.csv row is used
  - leaves add to their cell, cells to the grid total, and the grid total to total expenses
  - negative residual leaves are allowed (printed cells can be negative) but reported

Usage:
  python src/clean/build_federal_leaves.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clean.common import read_csv, write_csv  # noqa: E402
from paths import CONFIG, GOLD, SILVER, rel  # noqa: E402
from services import service_names  # noqa: E402

DOC = "fed-canada-public-accounts-2025-26-vol1"
YEARS = {"2025_26": ("2025-2026", "actual"), "2024_25": ("2024-2025", "actual_restated")}
CELLS = ["major_transfers", "other_transfers", "other_expenses", "public_debt_charges"]
EXCLUDED = {"pass_through_provinces", "other_municipal_indigenous_transfers", "pollution_pricing_returns"}
TREATMENTS = EXCLUDED | {"service", "financing", "unidentified"}
FIELDS = ["fiscal_year", "basis", "ministry", "cell_type", "leaf", "recipient", "treatment", "service_id", "service_name",
          "amount_cad", "in_shares", "source", "page", "confidence", "notes"]
TOL = 2_000_000  # printed in millions


def main() -> int:
    names = service_names()
    silver = SILVER / "public-accounts" / DOC
    grid_rows = read_csv(silver / "table-3-6-grid.csv")
    other = {}
    for f in silver.glob("*.csv"):
        if f.name not in ("checks.csv", "table-3-6-grid.csv"):
            for r in read_csv(f):
                other[(r["table_id"], r["row_label"], r["column_id"])] = r
    leaves_cfg = read_csv(CONFIG / "federal" / "leaves.csv")
    defaults = {(r["ministry"], r["cell_type"]): r for r in read_csv(CONFIG / "federal" / "ministry-services.csv")}
    errors, out, used = [], [], set()

    for suffix, (fy, basis) in YEARS.items():
        grid = defaultdict(dict)
        pages = {}
        for r in grid_rows:
            if r["fiscal_year"] != fy:
                continue
            ctype = r["column_id"][: -len("_" + suffix)]
            grid[r["row_label"]][ctype] = float(r["amount"]) * float(r["scale"])
            pages[r["row_label"], ctype] = r["page"]
        total = grid["Total expenses"]["total"]
        ministries = [m for m, c in grid.items() if m not in ("Total expenses", "Net actuarial losses",
                                                               "Total expenses, excluding net actuarial losses")]

        def leaf(m, ctype, name, amount, treatment, service_id, recipient, source, page, confidence, notes):
            if treatment not in TREATMENTS:
                errors.append(f"{m} / {ctype} / {name}: unknown treatment {treatment!r}")
            if treatment == "service" and service_id not in names:
                errors.append(f"{m} / {ctype} / {name}: unknown service {service_id!r}")
            sid = "debt_charges" if treatment == "financing" else ("unidentified" if treatment == "unidentified" else service_id)
            out.append({"fiscal_year": fy, "basis": basis, "ministry": m, "cell_type": ctype, "leaf": name,
                        "recipient": recipient, "treatment": treatment, "service_id": sid if treatment not in EXCLUDED else "",
                        "service_name": names.get(sid, "") if treatment not in EXCLUDED else "",
                        "amount_cad": round(amount), "in_shares": treatment not in EXCLUDED, "source": source, "page": page,
                        "confidence": confidence, "notes": notes})

        def default(m, ctype, amount, name, source, page):
            d = defaults.get((m, ctype))
            if d is None:
                errors.append(f"no default in config/federal/ministry-services.csv for {m} / {ctype}")
                return
            leaf(m, ctype, name, amount, d["treatment"], d["service_id"], "", source, page, d["confidence"], d["notes"])

        # Net actuarial losses: allocate by operating expense
        actuarial = grid["Net actuarial losses"].get("other_expenses", 0.0)
        ops_base = {m: grid[m].get("other_expenses", 0.0) for m in ministries if grid[m].get("other_expenses", 0.0) > 0}
        ops_total = sum(ops_base.values())

        for m in ministries:
            for ctype in CELLS:
                cell = grid[m].get(ctype, 0.0)
                page = pages.get((m, ctype), "")
                src = f"{DOC}/table-3-6-grid"
                if ctype == "public_debt_charges":
                    if cell:
                        leaf(m, ctype, "Public debt charges", cell, "financing", "debt_charges", "lenders", src, page, "high", "")
                    continue
                if ctype == "other_expenses":
                    if cell:
                        default(m, ctype, cell, "Operations", src, page)
                    continue
                named = [c for c in leaves_cfg if c["ministry"] == m and c["cell_type"] == ctype]
                remaining = cell
                residual_cfg = None
                for c in named:
                    used.add(id(c))
                    if c["amount_table"]:
                        ref = other.get((c["amount_table"], c["amount_row"], f"actual_{suffix}"))
                        if ref is None:
                            errors.append(f"{fy}: leaf source {c['amount_table']} / {c['amount_row']} not found")
                            continue
                        amount, lpage = float(ref["amount"]) * float(ref["scale"]), ref["page"]
                    elif c["amount_fixed_millions"]:
                        if suffix != "2025_26":
                            continue  # quoted amounts are for 2025-26; earlier years leave them in the residual
                        amount, lpage = float(c["amount_fixed_millions"]) * 1e6, c["page"]
                    else:
                        residual_cfg = c
                        continue
                    remaining -= amount
                    leaf(m, ctype, c["leaf"], amount, c["treatment"], c["service_id"], c["recipient"],
                         f"{DOC}/{c['amount_table'] or 'note text'}", lpage, c["confidence"], c["notes"])
                if named and abs(remaining) <= TOL and residual_cfg is None:
                    continue
                if not named and cell == 0:
                    continue
                if named and remaining < -TOL:
                    # Allowed (e.g. a negative 'other major transfers' adjustment), but worth seeing.
                    print(f"WARN  {fy}: {m} / {ctype}: residual is negative ({remaining / 1e6:,.0f}M)")
                if residual_cfg is not None:
                    leaf(m, ctype, residual_cfg["leaf"], remaining, residual_cfg["treatment"], residual_cfg["service_id"],
                         residual_cfg["recipient"], f"{src} (residual)", page, residual_cfg["confidence"], residual_cfg["notes"])
                elif ctype == "major_transfers":
                    errors.append(f"{fy}: {m} has major transfers of {remaining / 1e6:,.0f}M with no leaf in config/federal/leaves.csv")
                else:
                    default(m, ctype, remaining, "Other transfer payments (not yet split by program)", f"{src} (residual)", page)
            if m in ops_base and actuarial:
                share = actuarial * ops_base[m] / ops_total
                default(m, "other_expenses", share, "Net actuarial losses (allocated by operating expense)",
                        f"{DOC}/table-3-6-grid (allocation)", pages.get(("Net actuarial losses", "other_expenses"), ""))

        got = sum(r["amount_cad"] for r in out if r["fiscal_year"] == fy)
        if abs(got - total) > TOL * 5:
            errors.append(f"{fy}: leaves add to {got / 1e6:,.0f}M, grid total is {total / 1e6:,.0f}M")

    unused = [c["leaf"] for c in leaves_cfg if id(c) not in used]
    if unused:
        errors.append(f"leaves.csv rows matched no cell: {unused}")
    for e in errors:
        print(f"ERROR {e}")
    if errors:
        return 1
    dest = GOLD / "federal-leaves.csv"
    write_csv(dest, out, FIELDS)
    for fy in sorted({r["fiscal_year"] for r in out}):
        rows = [r for r in out if r["fiscal_year"] == fy]
        by_t = defaultdict(float)
        for r in rows:
            by_t[r["treatment"]] += r["amount_cad"]
        print(f"OK   {fy}: {len(rows)} leaves, total {sum(by_t.values()) / 1e6:,.0f}M; "
              + ", ".join(f"{t} {v / 1e6:,.0f}M" for t, v in sorted(by_t.items())))
    print(f"OK   -> {rel(dest)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
