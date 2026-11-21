"""
Reconcile public-accounts expense against StatCan CCOFOG, by COFOG division.

For each jurisdiction and fiscal year present in both gold files:
  public accounts  data/gold/public-accounts-facts.csv, function_breakdown tables, actual basis
  StatCan          data/gold/statcan-cofog.csv, table 10-10-0024-01, component
                   provincial_territorial (provinces) or federal (Canada), division level

Columns written per division:
  pa_expense               public accounts expense mapped to the division
  pa_amortization          amortization in that division, from the sector-by-object schedule
                           (only where a sector maps to one division; the rest is reported
                           on the _unallocated row)
  pa_expense_ex_amort      pa_expense - pa_amortization: the like-for-like figure, because
                           StatCan excludes consumption of fixed capital
  statcan                  StatCan provincial_territorial (or federal) expense
  gap / gap_pct            pa_expense_ex_amort - statcan, and as a share of statcan

The TOTAL row also gets context columns: StatCan's hospital, school board and
university/college components (not consolidated, so not additive; see
config/reconciling-items.csv).

Outputs:
  data/gold/reconciliation/cofog-by-division.csv
  data/gold/reconciliation/summary.md

Usage:
  python src/reconcile/reconcile_cofog.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clean.common import cofog, read_csv, write_csv  # noqa: E402
from paths import CONFIG, GOLD, rel  # noqa: E402

FIELDS = ["jurisdiction", "fiscal_year", "pa_basis", "division", "division_name", "pa_expense", "pa_amortization",
          "pa_expense_ex_amort", "statcan", "gap", "gap_pct", "statcan_health_institutions", "statcan_school_boards",
          "statcan_universities_colleges", "statcan_status"]
CONTEXT = {"health_social_institutions": "statcan_health_institutions", "school_boards": "statcan_school_boards",
           "universities_colleges": "statcan_universities_colleges"}
M = 1_000_000


def main() -> int:
    facts_path, statcan_path = GOLD / "public-accounts-facts.csv", GOLD / "statcan-cofog.csv"
    for p in (facts_path, statcan_path):
        if not p.exists():
            raise SystemExit(f"{rel(p)} missing: run the clean step first")
    names = {k: v["name"] for k, v in cofog().items() if v["level"] == "division"}
    names["_unallocated"] = "Unallocated (spans several functions)"

    pa = defaultdict(float)
    amort_by_fn = defaultdict(float)  # from sector x object schedules
    amort_total = defaultdict(float)  # from object-only tables (no function split)
    basis = {}
    for f in read_csv(facts_path):
        if f["basis"] not in ("actual", "actual_restated"):
            continue
        key = (f["jurisdiction"], f["fiscal_year"])
        amount = float(f["amount_cad"])
        if f["role"] == "function_breakdown":
            pa[key + (f["function_division"],)] += amount
            basis[key] = f["basis"]
        elif f["object_id"] == "amortization" and f["role"] == "function_by_object":
            amort_by_fn[key + (f["function_division"],)] += amount
        elif f["object_id"] == "amortization" and f["role"] == "object_breakdown":
            amort_total[key] += amount
    # Use the function split where a jurisdiction publishes one; otherwise the whole
    # amortization total sits on the _unallocated row and only adjusts the TOTAL.
    amort = defaultdict(float, amort_by_fn)
    for key, v in amort_total.items():
        if not any(k[:2] == key for k in amort_by_fn):
            amort[key + ("_unallocated",)] += v

    sc = defaultdict(float)
    ctx = defaultdict(float)
    status = defaultdict(set)
    for r in read_csv(statcan_path):
        if r["statcan_product_id"] != "10100024" or r["concept_level"] != "division" or r["amount_cad"] == "":
            continue
        comp = r["component_id"]
        if comp in CONTEXT:
            # Context components are matched on StatCan's reference year (school boards report on
            # a school year ending Aug 31, so their fiscal year label differs from the province's).
            ctx[(r["jurisdiction"], r["ref_year"], CONTEXT[comp])] += float(r["amount_cad"])
            continue
        key = (r["jurisdiction"], r["fiscal_year"])
        if key not in basis:
            continue
        if comp == ("federal" if r["jurisdiction"] == "CA" else "provincial_territorial"):
            sc[key + (r["concept_id"],)] += float(r["amount_cad"])
            status[key].add(r["status"] or "final")

    out = []
    for key in sorted(basis):
        if not any(k[:2] == key for k in sc):
            print(f"SKIP {key[0]} {key[1]}: no StatCan data for this year (latest StatCan year may lag)")
            continue
        divisions = sorted({k[2] for k in list(pa) + list(sc) + list(amort) if k[:2] == key},
                           key=lambda d: (d.startswith("_"), d))
        tot = defaultdict(float)
        for d in divisions:
            row = {"pa_expense": pa[key + (d,)], "pa_amortization": amort[key + (d,)], "statcan": sc[key + (d,)]}
            row["pa_expense_ex_amort"] = row["pa_expense"] - row["pa_amortization"]
            for k, v in row.items():
                tot[k] += v
            out.append(dict(jurisdiction=key[0], fiscal_year=key[1], pa_basis=basis[key], division=d,
                            division_name=names.get(d, d), **row))
        total = dict(jurisdiction=key[0], fiscal_year=key[1], pa_basis=basis[key], division="TOTAL",
                     division_name="Total expense", **tot, statcan_status="/".join(sorted(status[key])))
        for col in CONTEXT.values():
            total[col] = ctx[(key[0], key[1][:4], col)]
        out.append(total)

    for r in out:
        r["gap"] = r["pa_expense_ex_amort"] - r["statcan"]
        r["gap_pct"] = round(r["gap"] / r["statcan"], 4) if r["statcan"] else ""
        for k in FIELDS:
            if k != "gap_pct" and isinstance(r.get(k), float):
                r[k] = round(r[k])
    dest = GOLD / "reconciliation" / "cofog-by-division.csv"
    write_csv(dest, out, FIELDS)
    write_summary(out)
    print(f"OK   {len(out)} rows -> {rel(dest)}")
    return 0


def fmt(v) -> str:
    return "" if v in ("", None) else f"{v / M:,.0f}"


def write_summary(rows: list[dict]) -> None:
    items = read_csv(CONFIG / "reconciling-items.csv")
    lines = ["# Reconciliation: public accounts vs StatCan CCOFOG", "",
             "Generated by `src/reconcile/reconcile_cofog.py`. Amounts in $ millions. StatCan = table 10-10-0024-01, "
             "provincial and territorial governments component (federal government for Canada).", "",
             "`PA ex amort.` removes amortization of tangible capital assets, which StatCan excludes. "
             "Gap = PA ex amort. - StatCan.", ""]
    for key in sorted({(r["jurisdiction"], r["fiscal_year"]) for r in rows}):
        sub = [r for r in rows if (r["jurisdiction"], r["fiscal_year"]) == key]
        tot = next(r for r in sub if r["division"] == "TOTAL")
        lines += [f"## {key[0]} {key[1]} (public accounts basis: {tot['pa_basis']}; StatCan status: {tot['statcan_status']})", "",
                  "| Division | PA expense | PA amortization | PA ex amort. | StatCan | Gap | Gap % |",
                  "|---|--:|--:|--:|--:|--:|--:|"]
        for r in sub:
            pct = "" if r["gap_pct"] == "" else f"{r['gap_pct']:+.1%}"
            name = f"**{r['division_name']}**" if r["division"] == "TOTAL" else f"{r['division']} {r['division_name']}"
            lines.append(f"| {name} | {fmt(r['pa_expense'])} | {fmt(r['pa_amortization'])} | {fmt(r['pa_expense_ex_amort'])} "
                         f"| {fmt(r['statcan'])} | {fmt(r['gap'])} | {pct} |")
        lines += ["", "StatCan components outside government proper (not consolidated, shown for context only): "
                  f"health and social service institutions {fmt(tot['statcan_health_institutions'])}, "
                  f"school boards {fmt(tot['statcan_school_boards'])} (school year ending Aug 31 of the reference year), "
                  f"universities and colleges {fmt(tot['statcan_universities_colleges'])}.", ""]
    lines += ["## Known reconciling items", "", "From `config/reconciling-items.csv`:", ""]
    lines += [f"- **{i['item_id']}** ({i['direction']}): {i['description']}" for i in items]
    dest = GOLD / "reconciliation" / "summary.md"
    dest.write_text("\n".join(lines) + "\n")
    print(f"OK   summary -> {rel(dest)}")


if __name__ == "__main__":
    sys.exit(main())
