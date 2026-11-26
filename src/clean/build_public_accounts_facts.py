"""
Public-accounts silver tables + mappings -> gold facts and spending shares.

For every document with an extraction spec:
  - function_breakdown tables (expense by ministry): each detail row is mapped to a
    function concept (COFOG) through config/mappings/<jurisdiction>.csv.
  - function_by_object tables (sector x expense type): each cell gets a function concept
    from its sector column and an object concept from its row, which is what lets you
    ask "how much of Health was salaries vs amortization".
  - object_breakdown tables (expense by type only, or just the amortization line of the
    Statement of Change in Net Debt): rows map to object concepts; function_id is "_all".
  - headline tables are not mapped; they are only used by the extraction checks.

Validation (the script exits non-zero and writes nothing to gold if any fail):
  - every source line has a mapping (100% of dollars mapped);
  - weights for each source line sum to 1;
  - every concept id exists in the taxonomy;
  - mapped facts add back to the table's stated total for each fiscal year and basis.

Outputs:
  data/3_gold/public-accounts-facts.csv          one row per mapped amount, with provenance
  data/3_gold/spending-shares-preview.csv        shares by service, every year and basis (function_breakdown tables;
                                               the published federal shares use federal-leaves.csv instead)
  data/3_gold/validation/public-accounts.csv     results of the checks above

Usage:
  python src/clean/build_public_accounts_facts.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clean.common import cofog, division_of, fiscal_year_in, read_csv, write_csv  # noqa: E402
from paths import EXTRACTION_SPECS, GOLD, MAPPINGS, SILVER, TAXONOMY, load_manifest, manifest_doc, rel  # noqa: E402
from services import service_for, service_names  # noqa: E402

FACT_FIELDS = ["jurisdiction", "level", "doc_id", "table_id", "role", "page", "fiscal_year", "basis", "scope",
               "function_id", "function_division", "object_id", "source_label", "source_column", "weight",
               "amount_cad", "mapping_confidence"]
SHARE_FIELDS = ["jurisdiction", "level", "fiscal_year", "basis", "doc_id", "category", "subcategory",
                "amount_cad", "share"]
TOLERANCE_CAD = 5_000_000  # rounding: tables printed in millions can be off by a few million


def mapping_index(rows: list[dict]) -> dict[tuple[str, str, str], list[dict]]:
    idx: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for r in rows:
        idx[(r["table_id"], r["dimension"], r["source_label"])].append(r)
    return idx


def lookup(idx, table_id: str, dimension: str, label: str, fy: str, errors: list[str]) -> list[dict]:
    hits = [m for m in idx.get((table_id, dimension, label), []) if fiscal_year_in(fy, m["valid_from"], m["valid_to"])]
    if not hits:
        errors.append(f"unmapped {dimension}: {table_id} / {label!r} ({fy})")
        return []
    total = sum(float(m["weight"]) for m in hits)
    if abs(total - 1) > 1e-9:
        errors.append(f"weights sum to {total} for {table_id} / {dimension} / {label!r} ({fy})")
    return hits


def main() -> int:
    manifest = load_manifest()
    concepts = cofog()
    objects = {r["object_id"] for r in read_csv(TAXONOMY / "objects.csv")}
    names = service_names()
    facts, checks, errors = [], [], []

    for spec_path in sorted(EXTRACTION_SPECS.glob("*.yaml")):
        spec = yaml.safe_load(spec_path.read_text())
        doc = manifest_doc(spec["doc_id"], manifest)
        juris = doc["jurisdiction"]["province"] or doc["jurisdiction"]["country"]
        level = doc["level"]
        map_path = MAPPINGS / f"{juris.lower()}.csv"
        if not map_path.exists():
            errors.append(f"{rel(map_path)} missing for {doc['id']}")
            continue
        mappings = read_csv(map_path)
        for m in mappings:
            ok = m["concept_id"] in objects if m["dimension"] == "object" else (
                m["concept_id"] in concepts or m["concept_id"] == "_unallocated")
            if not ok:
                errors.append(f"{rel(map_path)}: unknown {m['dimension']} concept {m['concept_id']!r}")
        idx = mapping_index(mappings)

        for table in spec["tables"]:
            role = table["role"]
            if role not in ("function_breakdown", "function_by_object", "object_breakdown"):
                continue
            silver = read_csv(SILVER / "public-accounts" / doc["id"] / f"{table['table_id']}.csv")
            stated: dict[tuple[str, str], float] = {}
            mapped: dict[tuple[str, str], float] = defaultdict(float)
            for c in silver:
                amount = float(c["amount"]) * float(c["scale"])
                key = (c["fiscal_year"], c["basis"])
                is_total_cell = c["row_kind"] == "total" and (
                    c["column_kind"] == "total" if role == "function_by_object" else c["column_kind"] == "detail")
                if is_total_cell:
                    stated[key] = amount
                if c["column_kind"] != "detail" or c["row_kind"] not in ("detail", "adjustment"):
                    continue
                if role != "function_by_object" and c["row_kind"] != "detail":
                    continue
                dims = dict(kv.split("=", 1) for kv in c["column_dims"].split(";") if kv)
                none = [{"concept_id": "", "weight": "1", "confidence": ""}]
                if role == "object_breakdown":  # expense by type only: no function dimension
                    fn_maps = [{"concept_id": "_all", "weight": "1", "confidence": ""}]
                else:
                    fn_label = c["row_label"] if role == "function_breakdown" else dims.get("sector", "")
                    fn_maps = lookup(idx, table["table_id"], "function", fn_label, c["fiscal_year"], errors)
                obj_maps = (none if role == "function_breakdown"
                            else lookup(idx, table["table_id"], "object", c["row_label"], c["fiscal_year"], errors))
                for fm in fn_maps:
                    for om in obj_maps:
                        w = float(fm["weight"]) * float(om["weight"])
                        mapped[key] += amount * w
                        facts.append({
                            "jurisdiction": juris, "level": level, "doc_id": doc["id"], "table_id": table["table_id"],
                            "role": role, "page": c["page"], "fiscal_year": c["fiscal_year"], "basis": c["basis"],
                            "scope": table.get("scope", ""), "function_id": fm["concept_id"],
                            "function_division": division_of(fm["concept_id"]), "object_id": om["concept_id"],
                            "source_label": c["row_label"], "source_column": c["column_id"], "weight": w,
                            "amount_cad": round(amount * w), "mapping_confidence": fm["confidence"] or om["confidence"],
                        })
            for key, total in stated.items():
                got = mapped.get(key, 0.0)
                checks.append({"doc_id": doc["id"], "table_id": table["table_id"], "fiscal_year": key[0], "basis": key[1],
                               "check": "mapped facts = stated total", "computed": round(got), "stated": round(total),
                               "diff": round(got - total), "ok": abs(got - total) <= TOLERANCE_CAD})

    for e in sorted(set(errors)):
        print(f"ERROR {e}")
    bad = [c for c in checks if not c["ok"]]
    for c in bad:
        print(f"FAIL  {c['table_id']} {c['fiscal_year']} {c['basis']}: mapped {c['computed']:,} vs stated {c['stated']:,}")
    write_csv(GOLD / "validation" / "public-accounts.csv", checks,
              ["doc_id", "table_id", "fiscal_year", "basis", "check", "computed", "stated", "diff", "ok"])
    if errors or bad:
        return 1

    write_csv(GOLD / "public-accounts-facts.csv", facts, FACT_FIELDS)

    totals: dict[tuple, float] = defaultdict(float)
    by_cat: dict[tuple, float] = defaultdict(float)
    for f in facts:
        if f["role"] != "function_breakdown" or f["basis"] == "budget":
            continue
        key = (f["jurisdiction"], f["level"], f["fiscal_year"], f["basis"], f["doc_id"])
        cat, sub = names[service_for(f["function_id"])], ""
        totals[key] += f["amount_cad"]
        by_cat[key + (cat, sub)] += f["amount_cad"]
    shares = [dict(zip(SHARE_FIELDS, (*k, round(v), round(v / totals[k[:5]], 4)))) for k, v in sorted(by_cat.items())]
    write_csv(GOLD / "spending-shares-preview.csv", shares, SHARE_FIELDS)
    print(f"OK   {len(facts):,} facts -> {rel(GOLD / 'public-accounts-facts.csv')}")
    print(f"OK   {len(shares)} share rows -> {rel(GOLD / 'spending-shares-preview.csv')}")
    print(f"OK   {len(checks)} total checks passed -> {rel(GOLD / 'validation' / 'public-accounts.csv')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
