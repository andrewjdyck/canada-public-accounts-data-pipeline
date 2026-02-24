# Data Quality Framework

## Purpose

Define minimum checks required before data is considered reliable enough for downstream use (especially public-facing tax-receipt summaries).

## Quality dimensions

- **Completeness** - required fields are present.
- **Validity** - values match schema/type expectations.
- **Consistency** - conventions are stable across jurisdictions and runs.
- **Traceability** - outputs can be linked back to source docs/pages.
- **Reconciliation** - mapped totals align with reported totals where available.

## Layered checks

## 1) Source-manifest checks (Layer 0)

- `source-docs/manifest.yaml` conforms to `source-docs/manifest.schema.json`.
- Every `storage.relpath` points to an existing tracked file.
- `doc.fiscal_year` and jurisdiction fields follow agreed formatting conventions.

## 2) Raw extraction checks (Layer 1)

- Every JSONL manifest row has required fields (`pdf_path`, `page_number`, `table_index`, `csv_path`, etc.).
- Referenced CSV files exist.
- Manifest `nrows` and `ncols` align with actual CSV content.
- Duplicate `(pdf_stem, page_number, table_index)` records are not allowed.

## 3) Parsed canonical checks (Layer 2)

- Required columns exist for each canonical table (`entities`, `statements`, `line_items`, `account_mapping`).
- Row widths are consistent with headers.
- Key references are valid:
  - `statements.entity_id` exists in `entities`
  - `line_items.statement_id` exists in `statements`
- Numeric fields (`amount`) parse as numeric values.

## 4) Published summary checks (Layer 3)

- Required fields in `public_accounts_summary_totals` are populated.
- `record_id` is unique within a release snapshot.
- `amount_reported`, `normalization_factor`, and `amount_normalized_cad` are numeric.
- `transformation_assumptions` is populated (`none` allowed when truly none).

## 5) Reconciliation checks

Where source tables provide totals:

- Sum of mapped category totals should approximate reported totals within tolerance.
- Significant unexplained variance is flagged.

## Severity model

- **fail** - publication blocked
- **warn** - publication allowed only with explicit caveat
- **info** - diagnostic output only

## Suggested initial thresholds

- Required-field null rate: **0.0%** for publishable datasets.
- Duplicate `record_id` rate: **0.0%**.
- Reconciliation tolerance: **<= 0.5%** warn, **> 0.5%** fail (unless documented waiver).

## Handling failures

1. Mark run as failed.
2. Capture failing rows/check IDs.
3. Block publication unless an explicit waiver is documented.
4. Record root cause and remediation plan.
