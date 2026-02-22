# Pipeline Architecture

## Architecture goals

- Reproducible end-to-end runs.
- Clear separation of ingest, transform, and validation responsibilities.
- Traceability from outputs back to source documents.
- Transparent documentation of transformation assumptions.
- Easy onboarding of new jurisdictions by adding scoped adapters.

## Proposed stages

1. **Source discovery**
   - Read active entries from `docs/DATA_SOURCES.md` (or a machine-readable derivative).
   - Resolve official and/or mirror URLs and expected artifacts.

2. **Ingestion**
   - Download/capture source artifacts.
   - Store immutable raw files under `source-data/<jurisdiction>/...`.
   - Record source metadata (timestamp, hash, URL, retrieval status).

3. **Parsing**
   - Extract structured records from raw files (PDF tables, spreadsheets, CSV, etc.).
   - Preserve original labels and references (page/table metadata).

4. **Normalization**
   - Map source fields and labels to canonical schema in `docs/DATA_SCHEMA.md`.
   - Normalize units, fiscal year format, and common naming conventions.
   - For v0.1, produce summary-level spending totals by category.

5. **Validation and quality checks**
   - Enforce schema constraints.
   - Execute data quality checks from `docs/DATA_QUALITY.md`.
   - Produce run-level pass/warn/fail summary.

6. **Publishing**
   - Write normalized outputs to `output-data/`.
   - Emit run metadata (pipeline version, source set, validation results).

## Proposed code organization

```text
src/
  ingest/
    adapters/
  parse/
  normalize/
  validate/
  publish/
  common/
```

Adapter logic should be isolated per source/jurisdiction so failures and updates are localized.

## Interface contracts between stages

- Ingest outputs immutable artifacts + metadata.
- Parse outputs structured records with source references.
- Normalize outputs canonical summary records that match schema.
- Validate outputs explicit check results and failure reasons.
- Publish writes datasets and run manifests.

## Idempotency and reruns

- Re-running unchanged source inputs should not produce different outputs.
- Source hashes should be used to detect unchanged artifacts.
- Failed stages should be rerunnable without manual cleanup whenever possible.

## Observability and run artifacts

Each pipeline run should produce:

- run ID and timestamp,
- source list used,
- counts by stage (fetched, parsed, normalized, rejected),
- validation/quality summary,
- output artifact locations.

## Extension strategy

To add a new jurisdiction:

1. add/verify source registry entry,
2. implement or configure source adapter,
3. map to canonical schema,
4. add/adjust quality checks if needed,
5. run end-to-end and record caveats.
