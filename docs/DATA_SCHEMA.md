# Canonical Data Schema

## Purpose

Define the normalized output contract so jurisdictions can be compared consistently and downstream users can audit data sources, transformations, and assumptions.

## Release scope

For the first release, output granularity is **summary level**, not line-item level.

- Primary v0.1 table: `public_accounts_summary_totals`
- Grain: one row per `(jurisdiction, fiscal_year, spending_category)`

Line-item detail can be added in later schema versions once summary outputs are stable.

## `public_accounts_summary_totals` fields (v0.1)

| Field | Type | Required | Description |
|---|---|---|---|
| `record_id` | string | yes | Deterministic unique record identifier |
| `jurisdiction_type` | string | yes | `federal`, `provincial`, or `municipal` |
| `jurisdiction_code` | string | yes | Canonical code (for example `can`, `on`, `tor`) |
| `jurisdiction_name` | string | yes | Human-readable jurisdiction name |
| `fiscal_year` | string | yes | Fiscal year label (for example `2024-2025`) |
| `spending_category` | string | yes | Standardized spending category name |
| `spending_category_source` | string | yes | Original source category label before mapping |
| `amount_reported` | decimal | yes | Amount as represented in source units |
| `reporting_unit` | string | yes | `dollars`, `thousands`, `millions`, etc. |
| `amount_normalized_cad` | decimal | yes | Amount normalized to CAD dollars for comparability |
| `normalization_factor` | decimal | yes | Multiplier used to convert source units to dollars |
| `currency` | string | yes | Currency code (`CAD` expected in most cases) |
| `source_id` | string | yes | Link to `docs/DATA_SOURCES.md` source entry |
| `source_document_url` | string | yes | URL/path of specific source artifact used |
| `source_page_ref` | string | no | Optional page/table reference in source document |
| `transformation_assumptions` | string | yes | Assumptions used in category mapping or aggregation |
| `ingested_at_utc` | datetime | yes | Ingestion timestamp in UTC |
| `pipeline_version` | string | yes | Pipeline/schema version used for this record |
| `quality_status` | string | yes | `pass`, `warn`, or `fail` |

## Spending category taxonomy (v0.1 draft)

Initial categories should be lightweight and easy to map:

- health
- education
- social_services
- infrastructure_transport
- public_safety
- debt_servicing
- general_government
- other

Taxonomy refinements are expected in later versions.

## Field conventions

- Strings are UTF-8 and trimmed.
- Monetary fields use decimal (not binary float).
- Nulls are explicit; empty strings are avoided for missing values.
- `record_id` must be deterministic for identical source inputs.
- `amount_reported` preserves source representation.
- `amount_normalized_cad` provides cross-jurisdiction comparability.

## Enumerations (initial)

- `jurisdiction_type`: `federal`, `provincial`, `municipal`
- `quality_status`: `pass`, `warn`, `fail`

## Output format and partitioning (initial proposal)

- Preferred storage: Parquet for machine use, optional CSV extract for review.
- Suggested partition keys: `jurisdiction_type`, `jurisdiction_code`, `fiscal_year`.

## Versioning policy

- Schema versions follow semantic intent (`v0.1`, `v0.2`, `v1.0`).
- Additive changes are preferred.
- Breaking changes require:
  1. version bump,
  2. migration note,
  3. documentation updates in this file and README.

## Validation requirements

At minimum, each run should validate:

1. required fields are present and typed correctly,
2. `amount_reported`, `normalization_factor`, and `amount_normalized_cad` are numeric,
3. provenance fields exist for each record,
4. `transformation_assumptions` is populated (use `none` when not needed).
