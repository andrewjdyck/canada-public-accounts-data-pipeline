# Roadmap

## Objective

Ship a reliable, reproducible public-accounts data pipeline that can feed a downstream tax-receipt web app with transparent, auditable spending summaries.

## Coverage targets

- **MVP required:** Federal (Canada), Ontario, Toronto
- **Optional early-support track:** Saskatchewan and Regina

## Current baseline (already present)

- `source-docs/manifest.yaml` + `source-docs/manifest.schema.json`
- PDF tooling in `src/pa_pdf/`:
  - `inspect_pdf.py`
  - `scan_tables.py`
  - `find_text.py`
  - `extract_tables.py`
- Example extracted tables + JSONL manifests in `output-data/raw-tables/`
- Draft examples in `parsed-data/`
- Manual summary estimates in `output-data/manually-generated/`

## Milestones

## M0 - Foundation and extraction baseline (in progress)

**Deliverables**

- Source-document manifest and schema
- Repeatable PDF inspection/extraction scripts
- Documentation baseline for schema, quality, and architecture

**Acceptance criteria**

- Source artifacts are cataloged in manifest
- Extraction scripts run repeatably for at least one source PDF
- Raw extraction outputs include per-table provenance

## M1 - Parsed canonical datasets (next)

**Deliverables**

- Canonical parsed tables for entities, statements, line items, and mapping
- Stable mapping patterns for first jurisdictions
- Data dictionary aligned with `docs/DATA_SCHEMA.md`

**Acceptance criteria**

- Parsed outputs are reproducible from raw extracted tables
- Required canonical fields are populated for MVP jurisdictions
- Mapping assumptions are documented

## M2 - Summary-level publishable outputs (v0.1 release target)

**Deliverables**

- Summary spending-category outputs per jurisdiction/fiscal year
- Provenance + assumptions metadata
- Basic quality report and release notes

**Acceptance criteria**

- Summary outputs are generated for required MVP jurisdictions
- Quality checks in `docs/DATA_QUALITY.md` pass (or waived with rationale)
- Output structure matches `docs/DATA_SCHEMA.md`

## M3 - Quality hardening and onboarding workflow

**Deliverables**

- Automated schema/quality validations
- Standard process for adding new source docs and mappings
- Clear contributor and agent runbook

**Acceptance criteria**

- Validation failures are explicit and actionable
- New jurisdiction onboarding is documented and repeatable
- No regressions in previously supported datasets

## M4 - Coverage expansion and taxonomy maturity

**Deliverables**

- Additional provincial/municipal support
- Improved concept taxonomy and cross-jurisdiction mapping consistency
- Better packaging for public release consumers

**Acceptance criteria**

- Expanded coverage without breaking existing contracts
- Mapping/versioning changes documented
- Consumers can trace outputs to source material and assumptions

## Prioritized next actions

1. Bring Ontario and Toronto source manifests/docs into `source-docs/`
2. Stabilize parsed-data table contracts from examples to production-ready format
3. Implement first end-to-end transformation from raw tables to summary totals
4. Add quality checks for manifest validity, parsed-table integrity, and summary totals
5. Publish first reproducible MVP snapshot

## Definition of done

A roadmap task is done when:

- docs and code are updated together,
- run instructions are reproducible,
- relevant validation checks pass, and
- caveats/assumptions are explicitly documented.
