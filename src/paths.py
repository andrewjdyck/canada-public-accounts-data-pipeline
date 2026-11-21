"""Repository paths shared by every pipeline script.

Layers (see README):
  data/bronze  source documents exactly as published + source-docs-manifest.yaml
  data/silver  values extracted from bronze, labels kept verbatim (no categories)
  data/gold    categorised, validated, cross-jurisdiction data and reconciliations
  config/      hand-written specs: extraction specs, taxonomy, mappings
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

DATA = REPO / "data"
BRONZE = DATA / "bronze"
SILVER = DATA / "silver"
GOLD = DATA / "gold"

MANIFEST = BRONZE / "source-docs-manifest.yaml"
MANIFEST_SCHEMA = BRONZE / "source-docs-manifest.schema.json"

CONFIG = REPO / "config"
EXTRACTION_SPECS = CONFIG / "extraction"
EXTRACTION_SCHEMA = CONFIG / "extraction.schema.json"
TAXONOMY = CONFIG / "taxonomy"
MAPPINGS = CONFIG / "mappings"


def rel(path: Path) -> str:
    """Path relative to the repo root, for log messages and provenance fields."""
    try:
        return str(Path(path).resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def load_manifest(validate: bool = True) -> dict:
    import json

    import yaml

    manifest = yaml.safe_load(MANIFEST.read_text())
    if validate:
        import jsonschema

        schema = json.loads(MANIFEST_SCHEMA.read_text())
        errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(manifest), key=lambda e: list(e.path))
        if errors:
            for e in errors:
                print(f"manifest error at {list(e.path)}: {e.message}", file=sys.stderr)
            raise SystemExit(f"{rel(MANIFEST)} failed schema validation ({len(errors)} errors)")
    return manifest


def manifest_doc(doc_id: str, manifest: dict | None = None) -> dict:
    manifest = manifest or load_manifest()
    for doc in manifest["documents"]:
        if doc["id"] == doc_id:
            return doc
    raise SystemExit(f"document id {doc_id!r} not in {rel(MANIFEST)}")


def doc_path(doc: dict) -> Path:
    return BRONZE / doc["storage"]["relpath"]
