# Roadmap

## Objective

Ship a reliable, reproducible public accounts data pipeline in staged milestones, starting small and expanding coverage only after validation gates are met.

## Milestones

## M0 - Project foundation (current)

**Deliverables**

- Documentation baseline (scope, roadmap, sources, schema, architecture, quality, contribution workflows).
- Initial repository conventions for `source-data/`, `output-data/`, and `src/`.

**Acceptance criteria**

- Core docs exist and are internally consistent.
- Team/agents can identify next implementation tasks without additional context.

## M1 - Ingestion MVP

**Deliverables**

- Minimal ingest pipeline for initial jurisdictions.
- Repeatable run command(s) for local execution.
- Raw source files organized by jurisdiction and version/date.

**Acceptance criteria**

- End-to-end ingest works for agreed initial jurisdictions.
- Ingest is idempotent for unchanged inputs.
- Source provenance metadata is captured.

## M2 - Normalization and schema enforcement

**Deliverables**

- Canonical transformation layer aligned to `docs/DATA_SCHEMA.md`.
- Schema validation checks as part of pipeline runs.
- Initial output datasets in `output-data/`.

**Acceptance criteria**

- Required fields are populated and typed correctly.
- Normalized outputs are reproducible from raw sources.
- Validation failures are explicit and actionable.

## M3 - Data quality and reconciliation checks

**Deliverables**

- Quality checks from `docs/DATA_QUALITY.md` implemented.
- Basic reconciliation checks (for example, subtotal/total consistency where applicable).
- Run report summarizing pass/fail by jurisdiction.

**Acceptance criteria**

- Agreed quality thresholds pass for supported jurisdictions.
- Failures block publication until resolved or explicitly waived with documented reason.

## M4 - Coverage expansion

**Deliverables**

- Onboarding workflow for adding new jurisdictions quickly.
- Expanded province/municipality support.
- Updated source registry and caveat tracking.

**Acceptance criteria**

- New jurisdictions can be added with documented, repeatable steps.
- Existing coverage remains stable (no regressions in schema/quality checks).

## Prioritized backlog

1. Confirm first 3-5 jurisdictions for MVP.
2. Lock canonical schema v0.1.
3. Implement ingest adapters for MVP jurisdictions.
4. Build transform + validation modules.
5. Add run reporting and quality gating.
6. Expand jurisdiction coverage.

## Definition of done for roadmap tasks

A roadmap task is done when:

- code and docs are updated together,
- reproducible run steps are documented,
- relevant validations/tests pass, and
- output impact is described in the PR/commit message.
