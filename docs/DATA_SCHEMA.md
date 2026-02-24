# Data Schema

## Purpose

Define data contracts across pipeline layers so outputs are reproducible and traceable from published summaries back to source documents.

## Data layers

## Layer 0 - Source document registry

- Files: `source-docs/manifest.yaml`, `source-docs/manifest.schema.json`
- Contract: one manifest entry per source document with jurisdiction, source URL, storage path, and metadata.

## Layer 1 - Raw extracted tables

- Files: `output-data/raw-tables/<pdf_stem>/page-XXXX/table-YY.csv`
- Manifest: `output-data/raw-tables/<pdf_stem>.manifest.jsonl`
- Row grain: one detected table from one page.

Manifest record fields:

| Field | Type | Description |
|---|---|---|
| `pdf_path` | string | source PDF path |
| `pdf_stem` | string | source PDF stem name |
| `page_number` | int | 1-based page number |
| `table_index` | int | 1-based table index on page |
| `bbox` | array[float] | detected table bounding box |
| `nrows` | int | extracted row count |
| `ncols` | int | extracted max column count |
| `csv_path` | string | output CSV path |

## Layer 2 - Parsed canonical tables

Current examples live under `parsed-data/*.example.csv` and represent intended canonical structure.

### `entities`

| Field | Type | Required |
|---|---|---|
| `entity_id` | string | yes |
| `parent_entity_id` | string | no |
| `level` | string | yes |
| `name` | string | yes |
| `entity_type` | string | yes |

### `statements`

| Field | Type | Required |
|---|---|---|
| `statement_id` | string | yes |
| `entity_id` | string | yes |
| `statement_type` | string | yes |
| `consolidation_scope` | string | yes |
| `fiscal_year` | string | yes |
| `source_doc_id` | string | yes |

### `line_items`

| Field | Type | Required |
|---|---|---|
| `statement_id` | string | yes |
| `account_code` | string | no |
| `account_name` | string | yes |
| `category` | string | yes |
| `subcategory` | string | no |
| `amount` | decimal | yes |

### `account_mapping`

| Field | Type | Required |
|---|---|---|
| `source_account_name` | string | yes |
| `standard_account` | string | yes |
| `level` | string | yes |

## Layer 3 - Published summary outputs (v0.1 target)

First release target is summary-level spending data for the tax-receipt experience.

Proposed table: `public_accounts_summary_totals`  
Grain: one row per `(jurisdiction_code, fiscal_year, spending_category)`

| Field | Type | Required | Description |
|---|---|---|---|
| `record_id` | string | yes | deterministic record key |
| `jurisdiction_type` | string | yes | `federal`, `provincial`, `municipal` |
| `jurisdiction_code` | string | yes | for example `can`, `on`, `tor` |
| `jurisdiction_name` | string | yes | display name |
| `fiscal_year` | string | yes | normalized fiscal period |
| `spending_category` | string | yes | canonical category |
| `spending_category_source` | string | yes | source label before mapping |
| `amount_reported` | decimal | yes | value in source units |
| `reporting_unit` | string | yes | dollars/thousands/millions |
| `amount_normalized_cad` | decimal | yes | normalized CAD dollars |
| `normalization_factor` | decimal | yes | conversion multiplier |
| `currency` | string | yes | expected `CAD` |
| `source_id` | string | yes | manifest document ID |
| `source_page_ref` | string | no | page/table location |
| `transformation_assumptions` | string | yes | mapping assumptions |
| `pipeline_version` | string | yes | producing version |
| `quality_status` | string | yes | `pass`, `warn`, `fail` |

## Conventions

- Strings are UTF-8 and trimmed.
- Decimal fields should not use floating-point binary types.
- Missing values are explicit null/empty policy, not ad hoc placeholders.
- IDs should be deterministic where possible.

## Versioning policy

- Schema changes are documented in this file.
- Additive changes are preferred.
- Breaking changes require:
  1. version bump,
  2. migration note,
  3. related README/docs updates.
