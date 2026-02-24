# Pipeline Architecture

## Architecture goals

- Reproducible processing from source documents to publishable outputs
- Strong provenance between each output and its source page/table
- Clear separation between extraction, parsing/mapping, and publishing
- Practical onboarding path for new jurisdictions

## Current implemented flow

## Stage A - Source registry

- Source documents are tracked in `source-docs/manifest.yaml`
- Registry shape is defined by `source-docs/manifest.schema.json`
- Artifacts are stored under `source-docs/<level>/...`

## Stage B - PDF analysis and extraction

Current scripts under `src/pa_pdf/`:

- `inspect_pdf.py` - check text/table extractability
- `scan_tables.py` - find pages likely containing tables
- `find_text.py` - locate schedules/labels via regex text search
- `extract_tables.py` - extract detected tables to CSV + JSONL manifest

Outputs:

- CSV tables in `output-data/raw-tables/<pdf_stem>/page-XXXX/table-YY.csv`
- Extraction manifest in `output-data/raw-tables/<pdf_stem>.manifest.jsonl`

## Planned next flow

## Stage C - Canonical parsing/mapping

- Convert extracted raw tables into canonical parsed tables in `parsed-data/`
- Normalize labels/accounts using mapping rules
- Keep explicit source references for every parsed record

## Stage D - Summary publish outputs

- Produce summary-level spending outputs for the tax-receipt use case
- Include assumptions and provenance metadata
- Publish to stable dataset paths under `output-data/`

## Stage E - Validation and release

- Apply checks defined in `docs/DATA_QUALITY.md`
- Emit run summaries and caveat notes
- Mark datasets ready for downstream app use

## Recommended code expansion

```text
src/
  pa_pdf/              # current extraction tooling
  parse/               # next: canonical parsing
  normalize/           # next: category and unit normalization
  validate/            # next: quality checks
  publish/             # next: release packaging
```

## Idempotency expectations

- Re-running extraction on unchanged source docs should produce stable outputs.
- Manifest/document IDs should be stable over time.
- Pipeline steps should be restartable without manual cleanup.
