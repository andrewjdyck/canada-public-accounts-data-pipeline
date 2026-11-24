"""
Build the can-tax-receipt output file: data/gold/spending-shares/<fiscal-year>.yaml.

Each rate is the share of a government's expense going to one *service* (README "Principles",
docs/federal-design.md). Services are defined in config/taxonomy/services.csv.

Federal: rolled up from data/gold/federal-leaves.csv. Leaves treated as service, financing
  or unidentified are in the shares. Pass-throughs to provinces, unidentified transfers to
  municipalities and Indigenous governments, and pollution pricing returns are left out of
  numerator and denominator and listed in _meta.excludedFromShares.
Provinces: rolled up from data/gold/public-accounts-facts.csv (function_breakdown tables).
  Each line's COFOG concept maps to a service; lines listed in
  config/output/category-overrides.csv go to Municipal Transfers instead (whole line, or a
  carve-out of a detail-schedule row). Denominator = the statement's total expense.

Rates are rounded to 4 decimals; the rounding residual goes to the largest category so each
government's rates sum to exactly 1. Categories with no money are omitted.

Writes:
  data/gold/spending-shares/<fy>.yaml          the contract file
  data/gold/spending-shares/<fy>-amounts.csv   the dollars behind every rate, and the exclusions
Then validates the file and exits non-zero on failure.

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
from services import service_for, service_names  # noqa: E402

DECIMALS = 4
EXCLUSION_LABELS = {
    "pass_through_provinces": ("Transfers to provinces and territories",
                               "Pass-through: counted where the service is delivered, in provincial shares"),
    "other_municipal_indigenous_transfers": ("Other municipal / Indigenous transfers",
                                             "Transfers to municipalities and Indigenous governments or organizations not yet tied to a service"),
    "pollution_pricing_returns": ("Pollution pricing proceeds returned",
                                  "Not tax-funded and not a service: proceeds returned to people and businesses"),
}


def git_version() -> str:
    try:
        return subprocess.run(["git", "describe", "--tags", "--always", "--dirty"], cwd=REPO, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return "unversioned"


def order() -> list[str]:
    return [r["service_id"] for r in read_csv(TAXONOMY / "services.csv")]


def rates_for(amounts: dict[str, float]) -> dict[str, float]:
    total = sum(amounts.values())
    rates = {k: round(v / total, DECIMALS) for k, v in amounts.items()}
    largest = max(amounts, key=amounts.get)
    rates[largest] = round(rates[largest] + (1 - sum(rates.values())), DECIMALS)
    return rates


def categories(amounts: dict[str, float], names: dict[str, str]) -> tuple[list[dict], dict[str, float]]:
    nonzero = {k: v for k, v in amounts.items() if round(v) != 0}
    rates = rates_for(nonzero)
    return [{"name": names[s], "rate": rates[s]} for s in order() if s in nonzero], rates


def doc_meta(doc: dict, pages, notes: str) -> dict:
    return {
        "source": doc["doc"]["title"],
        "sourceUrl": doc["source"]["url"],
        "sourceDate": doc["doc"]["fiscal_year"][:4] + "-" + doc["doc"]["fiscal_year"][-2:],
        "dataQuality": "actual",
        "documentId": doc["id"],
        "pages": sorted({int(p) for p in pages if str(p).strip()}),
        "verified": False,
        "extractionNotes": notes,
    }


def build_federal(cfg: dict, manifest: dict, names: dict[str, str], amounts_out: list[dict]) -> dict:
    fed = cfg["federal"]
    doc = manifest_doc(fed["doc_id"], manifest)
    leaves = [r for r in read_csv(GOLD / "federal-leaves.csv") if r["fiscal_year"] == cfg["fiscal_year_key"]]
    amounts, excluded, pages = defaultdict(float), defaultdict(float), []
    for r in leaves:
        pages.append(r["page"])
        if r["in_shares"] == "True":
            amounts[r["service_id"]] += float(r["amount_cad"])
        else:
            excluded[r["treatment"]] += float(r["amount_cad"])
    cats, rates = categories(amounts, names)
    denominator = sum(amounts.values())
    gross = denominator + sum(excluded.values())
    for s, v in amounts.items():
        amounts_out.append({"level": "federal", "jurisdiction": "Federal", "category": names[s], "amount_cad": round(v),
                            "denominator_cad": round(denominator), "rate": rates.get(s, ""), "in_shares": True})
    for t, v in excluded.items():
        amounts_out.append({"level": "federal", "jurisdiction": "Federal", "category": EXCLUSION_LABELS[t][0],
                            "amount_cad": round(v), "denominator_cad": round(denominator), "rate": "", "in_shares": False})
    meta = doc_meta(doc, pages, (
        f"Shares of federal expense by service. Total expenses ${gross / 1e9:,.1f}B; ${sum(excluded.values()) / 1e9:,.1f}B is "
        f"excluded (see excludedFromShares), leaving ${denominator / 1e9:,.1f}B. Built from Volume I Table 3.6 (ministry x payment "
        "type) split into program leaves (data/gold/federal-leaves.csv, design in docs/federal-design.md). Net actuarial losses "
        "are allocated to ministries by operating expense. Ministry 'other transfers' not yet split by program (Volume II) take "
        "the ministry's default service, or Unidentified where the ministry funds several services."))
    meta["excludedFromShares"] = [{"name": EXCLUSION_LABELS[t][0], "amountCad": round(v), "reason": EXCLUSION_LABELS[t][1]}
                                  for t, v in sorted(excluded.items(), key=lambda x: -x[1])]
    return {"_meta": meta, "categories": cats}


def stated_total(doc_id: str, fy: str, basis: str) -> float:
    spec = yaml.safe_load((EXTRACTION_SPECS / f"{doc_id}.yaml").read_text())
    table = next(t for t in spec["tables"] if t["role"] == "function_breakdown")
    for r in read_csv(SILVER / "public-accounts" / doc_id / f"{table['table_id']}.csv"):
        if r["row_kind"] == "total" and r["column_kind"] == "detail" and r["fiscal_year"] == fy and r["basis"] == basis:
            return float(r["amount"]) * float(r["scale"])
    raise SystemExit(f"{doc_id}: no stated total for {fy} {basis}")


def build_provinces(cfg: dict, manifest: dict, names: dict[str, str], amounts_out: list[dict]) -> dict:
    juris_names = {r["code"]: r["name_en"] for r in read_csv(TAXONOMY / "jurisdictions.csv")}
    override_rows = read_csv(CONFIG / "output" / "category-overrides.csv")
    whole = {(r["jurisdiction"], r["table_id"], r["source_label"]): r for r in override_rows if not r["carve_table"]}
    carves: dict[tuple, list[dict]] = defaultdict(list)
    for r in override_rows:
        if r["carve_table"]:
            carves[(r["jurisdiction"], r["table_id"], r["source_label"])].append(r)
    fy, basis = cfg["fiscal_year_key"], cfg["basis"]

    by_juris: dict[str, dict] = defaultdict(lambda: {"amounts": defaultdict(float), "pages": set(), "doc": None,
                                                     "lines": defaultdict(list), "unallocated": set()})
    used = set()
    for f in read_csv(GOLD / "public-accounts-facts.csv"):
        if f["level"] != "provincial" or f["role"] != "function_breakdown" or f["fiscal_year"] != fy or f["basis"] != basis:
            continue
        j = by_juris[f["jurisdiction"]]
        key = (f["jurisdiction"], f["table_id"], f["source_label"])
        if key in whole:
            sid = "municipal_transfers"
            used.add(key)
        else:
            sid = service_for(f["function_id"])
        if f["function_id"] == "_unallocated":
            j["unallocated"].add(f["source_label"])
        j["amounts"][sid] += float(f["amount_cad"])
        j["pages"].add(f["page"])
        j["doc"] = f["doc_id"]
        j["lines"][sid].append(f["source_label"])
        for c in carves.get(key, []):
            carve_doc = c["carve_doc_id"] or f["doc_id"]
            cell = next((r for r in read_csv(SILVER / "public-accounts" / carve_doc / f"{c['carve_table']}.csv")
                         if r["row_label"] == c["carve_row"] and r["fiscal_year"] == fy and r["basis"] == basis
                         and (not c["carve_column"] or r["column_id"] == c["carve_column"])), None)
            if cell is None:
                raise SystemExit(f"carve-out {carve_doc} / {c['carve_table']} / {c['carve_row']} not found for {fy} {basis}")
            moved = float(cell["amount"]) * float(cell["scale"]) * float(f["weight"])
            j["amounts"][sid] -= moved
            j["amounts"]["municipal_transfers"] += moved
            if carve_doc == f["doc_id"]:
                j["pages"].add(cell["page"])
            j["lines"]["municipal_transfers"].append(f"{c['carve_row']} (from {f['source_label']})")
            used.add(key)
    unused = (set(whole) | set(carves)) - used
    if unused:
        raise SystemExit(f"category-overrides.csv rows match no source line: {sorted(unused)}")

    out = {}
    for code in sorted(by_juris, key=lambda c: juris_names[c]):
        j = by_juris[code]
        doc = manifest_doc(j["doc"], manifest)
        total = sum(j["amounts"].values())
        stated = stated_total(j["doc"], fy, basis)
        if abs(total - stated) > 5e6:
            raise SystemExit(f"{code}: service amounts {total:,.0f} do not add to the stated total {stated:,.0f}")
        cats, rates = categories(j["amounts"], names)
        for s, v in j["amounts"].items():
            if round(v):
                amounts_out.append({"level": "provincial", "jurisdiction": juris_names[code], "category": names[s],
                                    "amount_cad": round(v), "denominator_cad": round(total), "rate": rates.get(s, ""),
                                    "in_shares": True, "source_lines": "; ".join(sorted(set(j["lines"][s])))})
        muni = [r for r in override_rows if r["jurisdiction"] == code]
        label = lambda r: r["carve_row"] + f" (from {r['source_label']})" if r["carve_table"] else r["source_label"]  # noqa: E731
        muni_note = ("Municipal Transfers = " + "; ".join(f"{label(r)}: {r['notes']}" if r["notes"] else label(r) for r in muni) + "."
                     if muni else "No transfers to municipalities of unknown use are reported separately; transfers with a known "
                                  "purpose are in that service.")
        notes = (f"Shares of total expense (${total / 1e9:,.2f}B) by service, consolidated summary financial statements, "
                 f"FY{cfg['fiscalYear']} actual. Lines mapped to services via COFOG (config/mappings/{code.lower()}.csv, "
                 f"config/taxonomy/services.csv). {muni_note}")
        if j["unallocated"]:
            notes += " Unidentified = lines the statement does not split by service: " + "; ".join(sorted(j["unallocated"])) + "."
        out[juris_names[code]] = {"_meta": doc_meta(doc, j["pages"], notes), "categories": cats}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pipeline-version", default=None, help="Git tag being released (default: git describe)")
    args = parser.parse_args()

    cfg = yaml.safe_load((CONFIG / "output" / "spending-shares.yaml").read_text())
    manifest = load_manifest()
    names = service_names()
    amounts: list[dict] = []
    data = {
        "schemaVersion": cfg["schemaVersion"],
        "dataset": cfg["dataset"],
        "pipelineVersion": args.pipeline_version or git_version(),
        "generatedAt": dt.date.today().isoformat(),
        "fiscalYear": cfg["fiscalYear"],
        "federal": build_federal(cfg, manifest, names, amounts),
        "provincial": build_provinces(cfg, manifest, names, amounts),
    }
    out_dir = GOLD / "spending-shares"
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{cfg['fiscalYear']}.yaml"
    header = (f"# Spending shares by service, FY{cfg['fiscalYear']}. Generated by src/publish/build_spending_shares.py; do not edit.\n"
              "# rate = share of that government's expense spent on the service (README 'Principles'; docs/federal-design.md).\n")
    dest.write_text(header + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=160))
    write_csv(out_dir / f"{cfg['fiscalYear']}-amounts.csv", amounts,
              ["level", "jurisdiction", "category", "amount_cad", "denominator_cad", "rate", "in_shares", "source_lines"])
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
