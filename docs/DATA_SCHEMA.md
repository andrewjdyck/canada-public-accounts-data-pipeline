# Canonical Data Schema

## Purpose

Define the normalized output contract so all jurisdictions can be compared consistently and downstream users can rely on stable fields.

## Output datasets (v0.1 draft)

The initial schema assumes one primary normalized table:

- `public_accounts_line_items`

Future versions may add derived aggregates and metadata tables, but should preserve backward compatibility where feasible.

## `public_accounts_line_items` fields

| Field | Type | Required | Description |
|---|---|---|---|
| `record_id` | string | yes | Stable unique record identifier |
| `jurisdiction_type` | string | yes | `federal`, `provincial`, or `municipal` |
| `jurisdiction_code` | string | yes | Canonical short code (for example `can`, `on`) |
| `fiscal_year` | string | yes | Fiscal year label (for example `2024-2025`) |
| `statement_section` | string | yes | High-level section (`revenue`, `expense`, `asset`, `liability`, etc.) |
| `line_item_code` | string | no | Optional source or mapped account code |
| `line_item_name` | string | yes | Standardized line item name |
| `line_item_name_source` | string | yes | Original source label prior to normalization |
| `amount` | decimal | yes | Numeric amount in stated currency units |
| `currency` | string | yes | ISO-like code (`CAD` expected in most cases) |
| `unit` | string | yes | Unit basis (`dollars`, `thousands`, `millions`) |
| `value_sign` | string | yes | `positive`, `negative`, or `as_reported` |
| `source_id` | string | yes | Link to `docs/DATA_SOURCES.md` source entry |
| `source_document_url` | string | yes | URL or path to exact source document |
| `source_document_hash` | string | no | Optional hash for reproducibility/integrity |
| `source_page_ref` | string | no | Source page/table reference for traceability |
| `ingested_at_utc` | datetime | yes | Ingestion timestamp in UTC |
| `pipeline_version` | string | yes | Pipeline/schema version used to produce the record |
| `quality_status` | string | yes | `pass`, `warn`, or `fail` at record/run level |

## Field conventions

- Strings are UTF-8 and trimmed.
- Monetary values are decimal (not floating point binary).
- Nulls are explicit; empty strings should be avoided for missing values.
- `fiscal_year` format must be consistent across outputs.
- `record_id` should be deterministic for identical source inputs.

## Enumerations (initial)

- `jurisdiction_type`: `federal`, `provincial`, `municipal`
- `quality_status`: `pass`, `warn`, `fail`
- `value_sign`: `positive`, `negative`, `as_reported`

## Output format and partitioning (initial proposal)

- Preferred storage: Parquet for machine use, optional CSV extracts for review.
- Suggested partition keys: `jurisdiction_type`, `jurisdiction_code`, `fiscal_year`.

## Versioning policy

- Schema versions follow semantic intent (`v0.1`, `v0.2`, `v1.0`).
- Additive field changes are preferred.
- Breaking changes require:
  1. version bump,
  2. migration note,
  3. documentation update in this file and README.

## Validation requirements

At minimum, each run should validate:

1. required fields are present,
2. required enums contain only allowed values,
3. amounts are numeric and unit/currency are populated,
4. provenance fields exist for each record.
