"""
Build the can-tax-receipt output file: data/gold/spending-shares/<fiscal-year>.yaml.

Each rate is a share of that government's total expense (PLAN.md "Output Contract").

Federal (config/output/spending-shares.yaml, `federal`):
  denominator = total expenses - transfers to provinces and territories
  (major transfers to other levels of government + EI Labour Market Development
  Agreements). Those transfers are in neither the numerator nor the denominator.
  Named categories come from cells of the federal statements; "Other" is the remainder.

Provinces:
  amounts come from gold facts (function_breakdown tables, actual basis). A line listed
  in config/output/category-overrides.csv goes to that category (this is how provincial
  transfers to municipalities become their own category); every other line rolls up
  from its COFOG concept through config/taxonomy/app-categories.csv. Denominator = the
  statement's total expense, so municipal transfers are in both numerator and denominator.

Writes:
  data/gold/spending-shares/<fy>.yaml          the contract file
  data/gold/spending-shares/<fy>-amounts.csv   amounts behind every rate, for review
Then validates the file (src/publish/validate_spending_shares.py) and exits non-zero on failure.

Usage:
  python src/publish/build_spending_shares.py [--pipeline-version v0.1.0]
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clean.common import read_csv, write_csv  # noqa: E402
from paths import CONFIG, EXTRACTION_SPECS, GOLD, REPO, SILVER, TAXONOMY, load_manifest, manifest_doc, rel  # noqa: E402
from publish.validate_spending_shares import validate  # noqa: E402

DECIMALS = 4


def git_version() -> str:
    try:
        return subprocess.run(["git", "describe", "--tags", "--always", "--dirty"], cwd=REPO, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return "unversioned"


def round_shares(amounts: dict[str, float], total: float, absorb: str) -> dict[str, float]:
    """Round to DECIMALS and put the rounding residual on `absorb` so rates sum to exactly 1."""
    rates = {k: round(v / total, DECIMALS) for k, v in amounts.items()}
    rates[absorb] = round(rates[absorb] + (1 - sum(rates.values())), DECIMALS)
    return rates


def category_for(concept_id: str, rollups: list[dict]) -> str:
    best = (-2, "Other")
    for r in rollups:
        if r["level"] != "provincial":
            continue
        p = r["concept_prefix"]
        if p == "*" or concept_id == p or concept_id.startswith(p + "."):
            score = -1 if p == "*" else len(p)
            best = max(best, (score, r["category"]))
    return best[1]


def doc_meta(doc: dict, pages: list[int], notes: str) -> dict:
    return {
        "source": doc["doc"]["title"],
        "sourceUrl": doc["source"]["url"],
        "sourceDate": doc["doc"]["fiscal_year"][:4] + "-" + doc["doc"]["fiscal_year"][-2:],
        "dataQuality": "actual",
        "documentId": doc["id"],
        "pages": sorted(set(pages)),
        "verified": False,
        "extractionNotes": notes,
    }


def silver_cells(doc_id: str) -> dict[tuple[str, str, str], dict]:
    cells = {}
    for f in (SILVER / "public-accounts" / doc_id).glob("*.csv"):
        if f.name == "checks.csv":
            continue
        for r in read_csv(f):
            cells[(r["table_id"], r["row_label"], r["column_id"])] = r
    return cells


def build_federal(cfg: dict, manifest: dict, amounts_out: list[dict]) -> dict:
    fed = cfg["federal"]
    doc = manifest_doc(fed["doc_id"], manifest)
    cells = silver_cells(fed["doc_id"])
    col = fed["column"]
    pages: list[int] = []

    def cell(ref: dict) -> float:
        r = cells.get((ref["table"], ref["row"], col))
        if r is None:
            raise SystemExit(f"federal: no silver cell {ref['table']} / {ref['row']} / {col}")
        pages.append(int(r["page"]))
        return float(r["amount"]) * float(r["scale"])

    total = sum(cell(t) for t in fed["total"])
    excluded, adjust = 0.0, defaultdict(float)
    notes = []
    for x in fed["excluded_transfers_to_provinces"]:
        if "table" in x:
            v = cell(x)
            notes.append(f"{x['row']} (${v / 1e6:,.0f}M)")
        else:
            v = x["amount_millions"] * 1e6
            pages.append(x["page"])
            notes.append(f"{x['row']} (${v / 1e6:,.0f}M, p.{x['page']})")
            if x.get("subtract_from"):
                adjust[x["subtract_from"]] -= v
        excluded += v
    denominator = total - excluded

    amounts: dict[str, float] = {}
    for c in fed["categories"]:
        if c.get("remainder"):
            continue
        amounts[c["name"]] = sum(cell(ref) for ref in c["cells"]) + adjust[c["name"]]
    remainder = next(c["name"] for c in fed["categories"] if c.get("remainder"))
    amounts[remainder] = denominator - sum(amounts.values())
    if amounts[remainder] < 0:
        raise SystemExit("federal: named categories exceed the denominator")
    rates = round_shares(amounts, denominator, remainder)
    for name, v in amounts.items():
        amounts_out.append({"level": "federal", "jurisdiction": "Federal", "category": name, "amount_cad": round(v),
                            "denominator_cad": round(denominator), "rate": rates[name]})
    amounts_out.append({"level": "federal", "jurisdiction": "Federal", "category": "(excluded: transfers to provinces)",
                        "amount_cad": round(excluded), "denominator_cad": round(denominator), "rate": ""})
    meta = doc_meta(doc, pages, (
        f"Shares of total federal expense (${total / 1e9:,.1f}B) excluding transfers to provinces and territories "
        f"(${excluded / 1e9:,.1f}B): " + "; ".join(notes) + ". Denominator ${:,.1f}B. ".format(denominator / 1e9)
        + "Defence and Indigenous Services are ministry (segment) totals; Other includes net actuarial losses, "
        "pollution pricing proceeds returned and all other programs. Bilateral transfers to provinces paid outside "
        "the major transfers (e.g. some health and housing agreements) are not separately disclosed in Volume I and stay in Other."))
    return {"_meta": meta, "categories": [{"name": n, "rate": rates[n]} for n in amounts]}


def build_provinces(cfg: dict, manifest: dict, amounts_out: list[dict]) -> dict:
    rollups = read_csv(TAXONOMY / "app-categories.csv")
    override_rows = read_csv(CONFIG / "output" / "category-overrides.csv")
    # Whole-line overrides move a source line to a category; carve-outs move only the amount of
    # a detail-schedule row (carve_table/carve_row) out of the line's category.
    overrides = {(r["jurisdiction"], r["table_id"], r["source_label"]): r for r in override_rows if not r["carve_table"]}
    carves: dict[tuple, list[dict]] = defaultdict(list)
    for r in override_rows:
        if r["carve_table"]:
            carves[(r["jurisdiction"], r["table_id"], r["source_label"])].append(r)
    names = {r["code"]: r["name_en"] for r in read_csv(TAXONOMY / "jurisdictions.csv")}
    order = cfg["provincial"]["categories"]
    fy, basis = cfg["fiscal_year_key"], cfg["basis"]

    by_juris: dict[str, dict] = defaultdict(lambda: {"amounts": defaultdict(float), "pages": set(), "doc": None, "lines": defaultdict(list)})
    used_overrides = set()
    for f in read_csv(GOLD / "public-accounts-facts.csv"):
        if f["level"] != "provincial" or f["role"] != "function_breakdown" or f["fiscal_year"] != fy or f["basis"] != basis:
            continue
        j = by_juris[f["jurisdiction"]]
        key = (f["jurisdiction"], f["table_id"], f["source_label"])
        if key in overrides:
            cat = overrides[key]["category"]
            used_overrides.add(key)
        else:
            cat = category_for(f["function_id"], rollups)
        if cat not in order:
            raise SystemExit(f"{f['jurisdiction']}: category {cat!r} is not in config/output/spending-shares.yaml")
        j["amounts"][cat] += float(f["amount_cad"])
        if f["function_id"] == "_unallocated":
            j.setdefault("unallocated", set()).add(f["source_label"])
        j["pages"].add(int(f["page"]))
        j["doc"] = f["doc_id"]
        j["lines"][cat].append(f["source_label"])
        for c in carves.get(key, []):
            carve_doc = c["carve_doc_id"] or f["doc_id"]
            cell = next((r for r in read_csv(SILVER / "public-accounts" / carve_doc / f"{c['carve_table']}.csv")
                         if r["row_label"] == c["carve_row"] and r["fiscal_year"] == fy and r["basis"] == basis
                         and (not c["carve_column"] or r["column_id"] == c["carve_column"])), None)
            if cell is None:
                raise SystemExit(f"carve-out {carve_doc} / {c['carve_table']} / {c['carve_row']} not found for {fy} {basis}")
            moved = float(cell["amount"]) * float(cell["scale"]) * float(f["weight"])
            j["amounts"][cat] -= moved
            j["amounts"][c["category"]] += moved
            if carve_doc == f["doc_id"]:
                j["pages"].add(int(cell["page"]))
            j["lines"][c["category"]].append(f"{c['carve_row']} (from {f['source_label']})")
            used_overrides.add(key)
    unused = (set(overrides) | set(carves)) - used_overrides
    if unused:
        raise SystemExit(f"category-overrides.csv rows match no source line: {sorted(unused)}")

    out = {}
    for code in sorted(by_juris, key=lambda c: names[c]):
        j = by_juris[code]
        doc = manifest_doc(j["doc"], manifest)
        amounts = {c: j["amounts"].get(c, 0.0) for c in order}
        total = sum(amounts.values())
        stated = stated_total(j["doc"], fy, basis)
        if abs(total - stated) > 5e6:
            raise SystemExit(f"{code}: category amounts {total:,.0f} do not add to the stated total {stated:,.0f}")
        rates = round_shares(amounts, total, "Other")
        for c in order:
            amounts_out.append({"level": "provincial", "jurisdiction": names[code], "category": c, "amount_cad": round(amounts[c]),
                                "denominator_cad": round(total), "rate": rates[c],
                                "source_lines": "; ".join(sorted(set(j["lines"][c])))})
        muni = [r for r in override_rows if r["jurisdiction"] == code]
        label = lambda r: r["carve_row"] + f" (from {r['source_label']})" if r["carve_table"] else r["source_label"]  # noqa: E731
        muni_note = ("Municipal Transfers = " + "; ".join(f"{label(r)}: {r['notes']}" if r["notes"] else label(r) for r in muni)
                     if muni else "Municipal Transfers: not reported as a separate line in this statement, so the rate is 0 and "
                                  "transfers to municipalities stay inside the ministries that pay them.")
        meta = doc_meta(doc, sorted(j["pages"]), (
            f"Shares of total expense (${total / 1e9:,.2f}B), consolidated summary financial statements, FY{cfg['fiscalYear']} actual. "
            f"Lines mapped to categories via COFOG (config/mappings/{code.lower()}.csv). {muni_note}"
            + ("" if not j.get("unallocated") else
               " Other includes lines the statement does not split by function: " + "; ".join(sorted(j["unallocated"])) + ".")))
        out[names[code]] = {"_meta": meta, "categories": [{"name": c, "rate": rates[c]} for c in order]}
    return out


def stated_total(doc_id: str, fy: str, basis: str) -> float:
    spec = yaml.safe_load((EXTRACTION_SPECS / f"{doc_id}.yaml").read_text())
    table = next(t for t in spec["tables"] if t["role"] == "function_breakdown")
    for r in read_csv(SILVER / "public-accounts" / doc_id / f"{table['table_id']}.csv"):
        if r["row_kind"] == "total" and r["fiscal_year"] == fy and r["basis"] == basis:
            return float(r["amount"]) * float(r["scale"])
    raise SystemExit(f"{doc_id}: no stated total for {fy} {basis}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pipeline-version", default=None, help="Git tag being released (default: git describe)")
    args = parser.parse_args()

    cfg = yaml.safe_load((CONFIG / "output" / "spending-shares.yaml").read_text())
    manifest = load_manifest()
    amounts: list[dict] = []
    data = {
        "schemaVersion": cfg["schemaVersion"],
        "dataset": cfg["dataset"],
        "pipelineVersion": args.pipeline_version or git_version(),
        "generatedAt": dt.date.today().isoformat(),
        "fiscalYear": cfg["fiscalYear"],
        "federal": build_federal(cfg, manifest, amounts),
        "provincial": build_provinces(cfg, manifest, amounts),
    }
    out_dir = GOLD / "spending-shares"
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{cfg['fiscalYear']}.yaml"
    header = (f"# Spending shares by category, FY{cfg['fiscalYear']}. Generated by src/publish/build_spending_shares.py; do not edit.\n"
              "# rate = share of that government's total expense (federal excludes transfers to provinces/territories).\n")
    dest.write_text(header + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=160))
    write_csv(out_dir / f"{cfg['fiscalYear']}-amounts.csv", amounts,
              ["level", "jurisdiction", "category", "amount_cad", "denominator_cad", "rate", "source_lines"])
    errors = validate(dest)
    for e in errors:
        print(f"INVALID {e}")
    if errors:
        return 1
    print(f"OK   {rel(dest)} (valid)")
    print(f"OK   {rel(out_dir / (cfg['fiscalYear'] + '-amounts.csv'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
