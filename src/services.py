"""Map a COFOG concept id to a service id (config/taxonomy/services.csv), longest prefix first."""

from __future__ import annotations

import csv
from functools import lru_cache

from paths import TAXONOMY


@lru_cache(maxsize=1)
def _prefixes() -> list[tuple[str, str]]:
    with (TAXONOMY / "services.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = [(p.strip(), r["service_id"]) for r in rows for p in r["cofog_prefixes"].split(";") if p.strip()]
    return sorted(out, key=lambda x: -len(x[0]))


def service_for(concept_id: str) -> str:
    for prefix, sid in _prefixes():
        if concept_id == prefix or concept_id.startswith(prefix + ".") or concept_id.startswith(prefix + "+"):
            return sid
    raise KeyError(f"no service for COFOG concept {concept_id!r} in config/taxonomy/services.csv")


def service_names() -> dict[str, str]:
    with (TAXONOMY / "services.csv").open(newline="", encoding="utf-8") as f:
        return {r["service_id"]: r["name"] for r in csv.DictReader(f)}
