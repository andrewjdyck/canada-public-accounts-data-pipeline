"""
StatCan CCOFOG tables (silver) -> data/3_gold/statcan-cofog.csv.

Adds the pipeline's ids to every StatCan value so it can be joined to public-accounts facts:
  - jurisdiction code (config/taxonomy/jurisdictions.csv)
  - component_id and fiscal_year (config/taxonomy/statcan-components.csv; StatCan's
    reference year is the fiscal year ending closest to Dec 31, so 2024 = FY2024-25
    for federal and provincial governments)
  - concept_id from the CCOFOG code in brackets ([7073] -> 07.3), checked against
    config/taxonomy/cofog.csv
  - amount_cad in dollars (StatCan publishes millions)

Usage:
  python src/clean/clean_statcan_cofog.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clean.common import cofog, read_csv, write_csv  # noqa: E402
from paths import GOLD, SILVER, TAXONOMY, load_manifest, rel  # noqa: E402

LABEL = re.compile(r"^(?P<name>.*) \[(?P<codes>[\d, ]+)\]$")
SCALE = {"units": 1, "thousands": 1_000, "millions": 1_000_000, "billions": 1_000_000_000}
FIELDS = ["doc_id", "statcan_product_id", "ref_year", "fiscal_year", "jurisdiction", "geo", "component_id",
          "concept_id", "concept_level", "concept_name", "amount_cad", "status", "vector"]


def concept_of(codes: str) -> str:
    return "+".join(c if len(c) == 2 else f"{c[:2]}.{c[2:]}" for c in (x.strip()[1:] for x in codes.split(",")))


def fiscal_year(rule: str, year: int) -> str:
    return {"apr_mar": f"{year}-{year + 1}", "sep_aug": f"{year - 1}-{year}", "calendar": f"{year}"}[rule]


def main() -> int:
    concepts = cofog()
    geos = {r["statcan_geo"]: r["code"] for r in read_csv(TAXONOMY / "jurisdictions.csv")}
    components = {r["component"]: r for r in read_csv(TAXONOMY / "statcan-components.csv")}
    out, problems = [], set()
    for doc in load_manifest()["documents"]:
        if "cofog" not in doc.get("tags", []):
            continue
        pid = doc["source"]["statcan_product_id"]
        src = SILVER / "statcan" / f"{pid}.csv"
        rows = read_csv(src)
        label_col = next(c for c in rows[0] if "CCOFOG" in c)
        for r in rows:
            m = LABEL.match(r[label_col])
            comp = components.get(r["Public sector components"])
            if not m or comp is None or r["GEO"] not in geos:
                problems.add(f"unmapped StatCan label: {r[label_col]!r} / {r['Public sector components']!r} / {r['GEO']!r}")
                continue
            cid = concept_of(m["codes"])
            if cid not in concepts:
                problems.add(f"concept {cid} ({m['name']}) not in config/taxonomy/cofog.csv")
                continue
            year = int(r["REF_DATE"])
            value = r["VALUE"]
            out.append({
                "doc_id": doc["id"], "statcan_product_id": pid, "ref_year": year,
                "fiscal_year": fiscal_year(comp["fiscal_year_rule"], year), "jurisdiction": geos[r["GEO"]],
                "geo": r["GEO"], "component_id": comp["component_id"], "concept_id": cid,
                "concept_level": concepts[cid]["level"], "concept_name": concepts[cid]["name"],
                "amount_cad": "" if value == "" else int(round(float(value) * SCALE[r["SCALAR_FACTOR"]])),
                "status": r["STATUS"] or r["SYMBOL"], "vector": r["VECTOR"],
            })
    for p in sorted(problems):
        print(f"ERROR {p}")
    if problems:
        return 1
    dest = GOLD / "statcan-cofog.csv"
    write_csv(dest, out, FIELDS)
    print(f"OK   {len(out):,} rows -> {rel(dest)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
