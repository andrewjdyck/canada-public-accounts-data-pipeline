# Agent Development Guide

## Why this file exists

This repository is intended to be actively developed by both humans and AI coding agents. This guide defines expectations so agent work is reliable, reviewable, and aligned with project goals.

## Project objective (agent-facing)

Build a reproducible pipeline that converts Canadian public accounts source materials into standardized, high-quality, traceable datasets.

For v0.1, prioritize summary-level spending outputs that can power a "tax receipt" web app while keeping source and transformation assumptions explicit.

## Source of truth documents

Before making changes, agents should read:

1. `README.md`
2. `docs/PROJECT_SCOPE.md`
3. `docs/ROADMAP.md`
4. `docs/DATA_SCHEMA.md`
5. `docs/DATA_QUALITY.md`
6. `docs/DATA_SOURCES.md`

If implementation conflicts with docs, update docs and code in the same change.

## Agent task priorities

1. Preserve correctness and traceability.
2. Keep changes small and scoped.
3. Prefer deterministic logic over brittle heuristics.
4. Add or update validation checks when behavior changes.
5. Document assumptions explicitly.

## Guardrails

- Do not fabricate source data, URLs, or validation results.
- Do not overwrite or mutate raw source files in place.
- Do not introduce schema-breaking changes without updating `docs/DATA_SCHEMA.md`.
- Do not bypass failed quality checks without recording a clear caveat.
- Do not use mirror sources without documenting official URL and mirror provenance.

## Implementation conventions

- Prefer modular adapters by jurisdiction/source.
- Keep parsing logic separate from normalization logic.
- Use explicit naming for jurisdiction and fiscal period handling.
- Store reproducibility metadata (hashes, timestamps, pipeline version).

## Definition of done (agent tasks)

An agent task should be considered done when:

- changes align with scope and roadmap,
- docs are updated if behavior/contracts changed,
- relevant checks pass,
- commit messages clearly describe the change and why it was needed.

## Preferred commit style

Use concise, descriptive messages such as:

- `docs: define canonical schema v0.1`
- `ingest(on): add parser for FY2024 public accounts workbook`
- `quality: enforce unique record_id validation`
