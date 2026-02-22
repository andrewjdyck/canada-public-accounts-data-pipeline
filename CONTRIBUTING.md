# Contributing

Thanks for contributing to this project.

## Contribution goals

Contributions should improve one or more of the following:

- source coverage,
- data quality,
- schema consistency,
- reproducibility and maintainability.

## Development workflow

1. Pick or open an issue describing the change.
2. Confirm the change aligns with `docs/PROJECT_SCOPE.md` and `docs/ROADMAP.md`.
3. Implement in small commits.
4. Update docs alongside code when contracts/behavior change.
5. Run validations/checks relevant to the change.
6. Submit for review with a clear summary and known caveats.

## Repository conventions

- `source-data/` is for immutable/raw source artifacts.
- `output-data/` is for normalized outputs and run artifacts.
- `src/` contains ingestion, parsing, normalization, validation, and publish logic.
- `docs/` contains scope/contracts/operational guidance.

## Documentation expectations

If you change any of the following, update docs in the same change:

- source inventory -> update `docs/DATA_SOURCES.md`
- output contract -> update `docs/DATA_SCHEMA.md`
- quality thresholds/checks -> update `docs/DATA_QUALITY.md`
- implementation milestones -> update `docs/ROADMAP.md`

## Code quality expectations

- Keep changes focused and easy to review.
- Prefer deterministic parsing/transform logic.
- Add tests/checks where feasible.
- Preserve provenance metadata in output records.

## Pull request checklist

- [ ] Scope and motivation are clear.
- [ ] Docs updated if required.
- [ ] Validation/checks executed and results included.
- [ ] Known limitations or caveats documented.
- [ ] No unrelated cleanup bundled into the same change.
