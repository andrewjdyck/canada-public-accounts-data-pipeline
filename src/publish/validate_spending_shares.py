"""
Validate a spending-shares file against this repo's copy of the output contract (PLAN.md B2).

Checks:
  - JSON schema: config/output/spending-shares.schema.json (schemaVersion, _meta complete, rates in [0, 1])
  - category rates sum to 1 for every government (within 1e-9)
  - subcategory rates (also shares of TOTAL spending) sum to no more than their category
  - exactly the 10 provinces, keyed by full English name
  - every government is dataQuality: actual (MVP definition)

Usage:
  python src/publish/validate_spending_shares.py data/3_gold/spending-shares/2025-26.yaml
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CONFIG  # noqa: E402

PROVINCES = {"Newfoundland and Labrador", "Prince Edward Island", "Nova Scotia", "New Brunswick", "Quebec", "Ontario",
             "Manitoba", "Saskatchewan", "Alberta", "British Columbia"}
SUPPORTED_SCHEMA_VERSIONS = {1}


def validate(path: Path) -> list[str]:
    data = yaml.safe_load(Path(path).read_text())
    schema = json.loads((CONFIG / "output" / "spending-shares.schema.json").read_text())
    errors = [f"schema: {list(e.path)}: {e.message}" for e in jsonschema.Draft202012Validator(schema).iter_errors(data)]
    if errors:
        return errors
    if data["schemaVersion"] not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(f"schemaVersion {data['schemaVersion']} not supported")
    got = set(data["provincial"])
    if got != PROVINCES:
        errors.append(f"provinces: missing {sorted(PROVINCES - got)}, unexpected {sorted(got - PROVINCES)}")
    govs = [("federal", data["federal"])] + [(k, v) for k, v in data["provincial"].items()]
    for name, gov in govs:
        total = sum(c["rate"] for c in gov["categories"])
        if abs(total - 1) > 1e-9:
            errors.append(f"{name}: category rates sum to {total}")
        for c in gov["categories"]:
            sub = sum(s["rate"] for s in c.get("subcategories", []))
            if sub > c["rate"] + 1e-9:
                errors.append(f"{name}/{c['name']}: subcategories ({sub}) exceed category ({c['rate']})")
        if gov["_meta"]["dataQuality"] != "actual":
            errors.append(f"{name}: dataQuality is {gov['_meta']['dataQuality']}, MVP requires actual")
    return errors


if __name__ == "__main__":
    errs = validate(Path(sys.argv[1]))
    for e in errs:
        print(f"INVALID {e}")
    print("valid" if not errs else f"{len(errs)} problems")
    sys.exit(1 if errs else 0)
