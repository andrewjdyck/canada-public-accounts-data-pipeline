# Project Scope

## Purpose

Define what this repository is responsible for delivering, what is intentionally out of scope, and the minimum criteria for saying a jurisdiction is "supported."

## In scope

This project is in scope to:

- ingest official public accounts source materials from Canadian government entities,
- parse/transform source content into structured records,
- normalize fields into a canonical schema,
- publish cleaned outputs to a stable output location, and
- run quality checks that verify structural and accounting consistency.

## Target coverage (phased)

- **Federal:** Government of Canada public accounts artifacts.
- **Provincial:** Province-level public accounts (starting with a small initial subset).
- **Municipal:** City-level public accounts for selected municipalities (expanding iteratively).

Coverage should expand only when the previous set is reproducible and passes quality gates.

## Data domains in scope

The pipeline should prioritize commonly published public accounts concepts such as:

- revenues,
- expenses/expenditures,
- assets/liabilities,
- net debt/net financial position, and
- segment/program-level line items where available.

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
5. each output record carries provenance metadata linking to its source.

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
