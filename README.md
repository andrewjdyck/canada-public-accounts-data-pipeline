# canada-public-accounts-data-pipeline

A repository for building a reproducible pipeline that converts Canadian public accounts sources into cleaned, comparable datasets across federal, provincial, and municipal governments.

## Mission

Public accounts are published by different governments in inconsistent formats (mostly PDFs, with varying labels and fiscal conventions). This project aims to:

1. collect and catalog source documents with clear provenance,
2. extract structured data from those sources reproducibly,
3. normalize data into canonical formats for comparison, and
4. publish outputs that are transparent about assumptions and transformations.

## Audience and product context

- **Primary audience today:** the project author/developer.
- **Near-term audience:** public users and contributors after first release.
- **Downstream product:** a web app that shows a "tax receipt" view of taxes paid and services funded.

To support that use case responsibly, source choices, transformations, and assumptions must be explicit and auditable.

## Current status

The repository now includes:

- source document inventory + schema under `source-docs/`,
- early PDF extraction tooling in `src/pa_pdf/`,
- extracted raw table outputs in `output-data/raw-tables/`,
- manually generated summary estimates in `output-data/manually-generated/`,
- draft parsed-data examples in `parsed-data/`,
- planning and standards documentation in `docs/`.

## Repository structure

```text
root/
  README.md
  AGENTS.md
  CONTRIBUTING.md
  docs/
    ROADMAP.md
    DATA_SCHEMA.md
    DATA_QUALITY.md
    PIPELINE_ARCHITECTURE.md
    xbrl-notes.md
  source-docs/
    README.md
    manifest.yaml
    manifest.schema.json
    federal/
    provincial/
    municipal/
  parsed-data/
    *.example.csv
  output-data/
    raw-tables/
    manually-generated/
  src/
    pa_pdf/
```

## Development priorities

- **MVP jurisdictions:** Federal (Canada), Ontario, Toronto.
- **Optional early-support track:** Saskatchewan and Regina.
- **First release granularity:** summary-level spending categories.

See [docs/ROADMAP.md](docs/ROADMAP.md) for milestones and acceptance criteria.

## Working with PDFs (tables inside Public Accounts)

Most public accounts are published as PDFs with embedded tables. Typical flow:

1. inspect extractability (embedded text, detectable tables),
2. extract tables to CSV with per-table provenance,
3. normalize into canonical structures,
4. validate and publish.

### Quick commands (conda env `dev`)

These scripts only require `pdfplumber`.

Inspect a PDF:

```bash
CONDA_NO_PLUGINS=true conda run -n dev python src/pa_pdf/inspect_pdf.py --pdf source-docs/federal/ca/2025-vol2-eng.pdf --pages 1-5 --sample-page 1
```

Scan for pages with detectable tables:

```bash
CONDA_NO_PLUGINS=true conda run -n dev python src/pa_pdf/scan_tables.py --pdf source-docs/federal/ca/2025-vol2-eng.pdf --start 1 --end 50
```

Extract tables to CSV + manifest:

```bash
CONDA_NO_PLUGINS=true conda run -n dev python src/pa_pdf/extract_tables.py --pdf source-docs/federal/ca/2025-vol2-eng.pdf --out output-data/raw-tables --pages 1-50
```

Find text pattern in PDF:

```bash
CONDA_NO_PLUGINS=true conda run -n dev python src/pa_pdf/find_text.py --pdf source-docs/federal/ca/2025-vol2-eng.pdf --pattern "Table\\s+2" --ignore-case
```

## Documentation map

- [Roadmap](docs/ROADMAP.md)
- [Canonical data schema](docs/DATA_SCHEMA.md)
- [Data quality framework](docs/DATA_QUALITY.md)
- [Pipeline architecture](docs/PIPELINE_ARCHITECTURE.md)
- [Source document manifest guide](source-docs/README.md)
- [XBRL notes](docs/xbrl-notes.md)
- [Agent guide](AGENTS.md)
- [Contributing guide](CONTRIBUTING.md)

## Working principles

- **Reproducibility first:** same inputs should produce same outputs.
- **Traceability first:** outputs should map back to source documents/pages.
- **Transparency first:** assumptions and caveats are documented.
- **Incremental delivery:** expand coverage in small validated steps.
