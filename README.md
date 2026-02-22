# canada-public-accounts-data-pipeline

A repository for building a reproducible data pipeline that produces cleaned, standardized Canadian public accounts data across federal, provincial, and municipal governments.

## Mission

Public accounts are published by many entities in inconsistent formats (PDF, tables, spreadsheets, and different fiscal conventions). This project aims to:

1. collect source public accounts data from Canadian jurisdictions,
2. normalize and clean it into a shared schema, and
3. publish machine-readable outputs suitable for analysis and downstream tooling.

## Current status

This repository is currently in an early scaffold/documentation phase. The folder conventions and documentation define how development should proceed, while pipeline code and data assets are still to be implemented.

## Goals

- Build a repeatable ingestion and transformation pipeline.
- Standardize terminology and fields across jurisdictions.
- Preserve provenance from every output record back to source material.
- Establish quality checks that catch parsing and normalization errors early.
- Make future onboarding easy for both human contributors and AI agents.

## Non-goals (for now)

- Forecasting, policy interpretation, or causal analysis.
- Replacing official government publications.
- Creating opinionated rankings of governments or programs.

## Proposed repository structure

```text
root/
  README.md
  AGENTS.md
  CONTRIBUTING.md
  docs/
    PROJECT_SCOPE.md
    ROADMAP.md
    DATA_SOURCES.md
    DATA_SCHEMA.md
    PIPELINE_ARCHITECTURE.md
    DATA_QUALITY.md
  source-data/
    federal/
    provincial/
      bc/
      ab/
      sk/
      on/
      ...
    municipal/
      yvr/
      yyc/
      yqr/
      yyz/
      ...
  output-data/
    ...
  src/
    ...
```

## Development plan (high level)

1. **Foundation:** define scope, schema, source registry, and quality gates.
2. **Ingestion MVP:** support a small initial set of jurisdictions end-to-end.
3. **Normalization + QA:** enforce schema and validations across all supported inputs.
4. **Coverage expansion:** add more provinces/municipalities with repeatable onboarding.

See [docs/ROADMAP.md](docs/ROADMAP.md) for milestones and acceptance criteria.

## Documentation map

- [Project scope](docs/PROJECT_SCOPE.md)
- [Roadmap](docs/ROADMAP.md)
- [Data sources registry](docs/DATA_SOURCES.md)
- [Canonical data schema](docs/DATA_SCHEMA.md)
- [Pipeline architecture](docs/PIPELINE_ARCHITECTURE.md)
- [Data quality framework](docs/DATA_QUALITY.md)
- [Agent guide](AGENTS.md)
- [Contributing guide](CONTRIBUTING.md)

## Working principles

- **Reproducibility first:** identical inputs should produce identical outputs.
- **Traceability first:** every transformed row should map back to a source file/record.
- **Incremental delivery:** add jurisdictions through small, verifiable iterations.
- **Contract-driven development:** schema and quality checks are treated as core API contracts.

## Getting started (current phase)

1. Read the docs listed above.
2. Align on scope, schema, and first jurisdictions.
3. Implement pipeline modules in `src/` according to the architecture document.
4. Validate outputs against quality checks before expanding coverage.
