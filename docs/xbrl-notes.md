# XBRL notes (future publishing format)

This repo’s goal is to convert Canadian public accounts (often PDF tables) into **consistent, comparable** datasets across:

- Federal
- Provincial
- Municipal

## What XBRL can help with

XBRL (and related specs like iXBRL) are useful when you want:

- **A shared taxonomy**: standardized concepts like “Tax revenue”, “Transfer payments”, “Old Age Security”, etc.
- **Machine-readable facts**: each numeric value is published as a “fact” with explicit dimensions.
- **Comparable reporting**: different issuers can publish the same concept with consistent identifiers.

## Practical approach for this project

Instead of trying to force raw PDF tables directly into XBRL, a robust pipeline usually looks like:

1. **Extract** (per source PDF):
   - Raw tables to CSV with provenance (pdf, page, bounding box).
   - Extracted page text for locating headings/sections.
2. **Normalize** into internal “fact tables”:
   - `entity` (Government of Canada / Province of X / City of Y)
   - `fiscal_year`
   - `statement` / `schedule`
   - `concept` (canonical internal id)
   - `amount`
   - `currency`
   - optional dimensions: `program`, `ministry`, `standard_object`, `fund`, etc.
3. **Publish**:
   - Primary open data formats (CSV/Parquet) plus data dictionary and lineage.
   - Optionally **export to XBRL** using a taxonomy mapping layer.

## What’s hard / needs decisions

- **Taxonomy design**: pick a base taxonomy (or define your own) and decide how granular concepts should be.
- **Dimensionality**: public accounts often slice the same totals by different “axes” (ministry, standard object, vote, etc.).
- **Versioning**: concepts change year-to-year; you need stable IDs and mapping tables.

## Deliverables that make XBRL feasible later

Even if XBRL export is a later step, the project should produce:

- **Canonical concept registry** (e.g. `concepts.csv`):
  - `concept_id`, `label_en`, `label_fr`, `definition`, `unit`, `sign`, `notes`
- **Mapping tables** from each source table row label to canonical concept:
  - `source_label` → `concept_id` (+ regex rules, manual overrides)
- **Dataset packaging metadata** (e.g. frictionless datapackage or similar), including:
  - provenance, update cadence, and validation rules


