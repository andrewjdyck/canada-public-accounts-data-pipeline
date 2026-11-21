"""Helpers shared by the clean and reconcile steps."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import TAXONOMY  # noqa: E402


def read_csv(path: Path) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def cofog() -> dict[str, dict]:
    return {r["concept_id"]: r for r in read_csv(TAXONOMY / "cofog.csv")}


def division_of(concept_id: str) -> str:
    """'07.3' -> '07'; '01.5+01.6+01.8' -> '01'; '_unallocated' stays as is."""
    return concept_id if concept_id.startswith("_") else concept_id[:2]


def fiscal_year_in(fy: str, valid_from: str, valid_to: str) -> bool:
    start = int(fy[:4])
    return (not valid_from or start >= int(valid_from[:4])) and (not valid_to or start <= int(valid_to[:4]))
