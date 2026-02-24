# Source Documents Guide

## Purpose

`source-docs/` is the source-of-truth inventory for upstream public accounts documents used by this repository.

This directory contains:

- `manifest.yaml` - machine-readable document inventory,
- `manifest.schema.json` - validation contract for the manifest,
- downloaded source files organized by jurisdiction.

## Source of truth policy

- Use `source-docs/manifest.yaml` as the canonical registry of source documents.
- Do not duplicate source registries in other markdown files.
- Every source artifact tracked in this repository should have a corresponding manifest entry.

## Official and mirror policy

- Official government publication URLs are preferred.
- Mirror/archive URLs are allowed (and often necessary) when official links move or historical continuity is at risk.
- If a mirror is used, document both official and mirror details in manifest fields when available, and explain caveats in `notes`.

## Manifest conventions

For each `documents[]` entry:

- `id` should be stable and lower-kebab-case.
- `level` must match one of: `federal`, `provincial`, `municipal`.
- `jurisdiction` values should use consistent naming/casing.
- `doc.fiscal_year` should use the normalized range format where possible (`YYYY-YYYY`).
- `storage.relpath` should match the tracked file path under `source-docs/`.
- `source.retrieved_at` should capture when the source was obtained.

## Lifecycle states

Suggested use of `status`:

- `planned` - target source identified but not yet downloaded
- `downloaded` - source stored locally and registered
- `parsed` - extraction pipeline has produced structured outputs
- `verified` - extraction/normalization checks reviewed and accepted

## Adding a new source document

1. Add the document file under the appropriate `source-docs/<level>/...` folder.
2. Add a corresponding entry to `manifest.yaml`.
3. Validate shape/fields against `manifest.schema.json`.
4. Add notes for caveats, especially if source links are unstable or mirrored.
5. If extraction is performed, link outputs in `output-data/raw-tables/` or downstream parsed datasets.
