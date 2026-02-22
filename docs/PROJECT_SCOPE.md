# Project Scope

## Purpose

Define what this repository is responsible for delivering, what is intentionally out of scope, and the minimum criteria for saying a jurisdiction is "supported."

This repository is a data foundation for a downstream web app that presents a "tax receipt" style view of what taxes fund.

## In scope

This project is in scope to:

- ingest official public accounts source materials from Canadian government entities,
- parse/transform source content into structured records,
- normalize fields into a canonical schema,
- publish cleaned outputs to a stable output location, and
- run quality checks that verify structural and accounting consistency.

For the first release, normalized outputs are summary-level spending totals by category.

## Target coverage (phased)

- **MVP required:** Federal (Canada), Ontario, Toronto.
- **Optional early-support track:** Saskatchewan and Regina.
- **Later expansion:** additional provinces/municipalities after MVP quality gates pass.

Coverage should expand only when the previous set is reproducible and passes quality gates.

## Data domains in scope

The pipeline should prioritize commonly published public accounts concepts such as:

- spending/expenditure totals by category (first release priority),
- revenues,
- assets/liabilities, and
- net debt/net financial position.

Exact inclusion per jurisdiction depends on source availability and reliable extraction.

## Out of scope (current phase)

- Forecasting and predictive modeling.
- Policy or performance scoring.
- Reconciliation against private/non-official datasets.
- Manual one-off analysis notebooks as primary deliverables.
- Any transformation that obscures source provenance.

## Definition of "cleaned and consistent"

For this repository, cleaned and consistent means:

1. required schema fields are present and typed correctly,
2. naming conventions are standardized across jurisdictions,
3. currency and fiscal period are explicit and normalized,
4. missing/unknown values are represented consistently, and
5. each output record carries provenance metadata linking to its source,
6. transformation assumptions are documented in output metadata.

## Definition of "jurisdiction supported"

A jurisdiction is considered supported when all conditions are met:

1. Source entry is registered in `docs/DATA_SOURCES.md`.
2. Ingestion/transformation pipeline runs without manual edits.
3. Output validates against `docs/DATA_SCHEMA.md`.
4. Quality checks in `docs/DATA_QUALITY.md` pass.
5. Run instructions and caveats are documented.

## Scope change process

If scope needs to change:

1. propose change in an issue/PR,
2. update this document and related schema/quality docs together,
3. record the reasoning in commit/PR notes for future contributors and agents.
