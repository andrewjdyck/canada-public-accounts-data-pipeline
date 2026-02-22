# Data Quality Framework

## Purpose

Define the minimum quality standards required before normalized outputs are considered publishable.

## Quality dimensions

- **Completeness:** required fields are populated.
- **Validity:** values conform to type, format, and enum constraints.
- **Consistency:** similar concepts are represented consistently across jurisdictions.
- **Reconciliation:** totals/subtotals align where source structure allows.
- **Traceability:** each record can be traced to a source location.

## Required checks (minimum set)

## 1) Schema checks

- Required columns exist.
- Field types conform to `docs/DATA_SCHEMA.md`.
- Enumerated fields only contain allowed values.

## 2) Null and range checks

- No nulls in required fields.
- Amount fields are numeric.
- Unit/currency fields are populated for all monetary rows.
- `transformation_assumptions` is populated (`none` allowed when appropriate).

## 3) Uniqueness checks

- `record_id` is unique within a dataset snapshot.
- No duplicated records across `(jurisdiction_code, fiscal_year, spending_category, source_page_ref)` unless explicitly justified.

## 4) Reconciliation checks

Where source structures provide totals:

- Sum of mapped category totals approximates reported top-level totals within tolerance.
- Significant unexplained variance is flagged as failure.

## 5) Provenance checks

- `source_id`, `source_document_url`, and ingestion metadata present.
- Source page/table references present when technically extractable.

## Severity model

- **fail:** publication blocked.
- **warn:** publication allowed with explicit caveat.
- **info:** diagnostic only.

## Suggested initial thresholds

- Required field null rate: **0.0%** (fail if greater).
- Duplicate `record_id` rate: **0.0%** (fail if greater).
- Reconciliation variance tolerance: **<= 0.5%** (warn), **> 0.5%** (fail), unless source caveat documented.

Thresholds should be adjusted only with documented rationale.

## Handling failures

When checks fail:

1. mark run as failed,
2. capture failing records/check IDs,
3. block output publication unless waived,
4. document root cause and remediation path.

## Run reporting

Each run should emit a quality report including:

- check results by jurisdiction and fiscal year,
- counts of fail/warn/info,
- top failure categories,
- link/path to affected records.
