# Data Sources Registry

## Purpose

Maintain a single source-of-truth inventory of upstream public accounts sources, including URLs, formats, update cadence, and caveats.

This file should be updated whenever a source is added, replaced, or deprecated.

## Source intake policy

Before adding a source, confirm:

1. it is an official or clearly attributable publication,
2. usage/licensing allows ingestion and transformation,
3. expected update cadence is understood, and
4. source format and parsing strategy are documented.

## Official + mirror policy

- Official government sources are preferred whenever available.
- Mirrors/archives are allowed when:
  1. the official document has moved or become unavailable, or
  2. historical continuity is better preserved via archival copy.
- Mirror usage must be explicit in the registry (never implicit).
- When possible, keep both:
  - the official publication URL, and
  - a repository-tracked or externally stable archived copy reference.

## Registry schema

Each source entry should contain:

- `source_id`: stable unique ID (for example, `prov_on_public_accounts`).
- `jurisdiction_type`: `federal` | `provincial` | `municipal`.
- `jurisdiction_code`: short code (for example, `can`, `on`, `tor`).
- `publisher`: organization publishing the source.
- `dataset_name`: official name of publication.
- `source_url`: primary URL used by the pipeline for retrieval.
- `official_source_url`: official publication URL (even if retrieval uses mirror URL).
- `source_tier`: `official` | `mirror` | `official+mirror`.
- `mirror_url`: mirror/archive URL when used.
- `file_format`: `pdf` | `xlsx` | `csv` | `api` | other.
- `coverage_start` / `coverage_end`: fiscal years covered.
- `update_cadence`: annual, quarterly, ad hoc, etc.
- `license_notes`: usage restrictions/notes.
- `ingest_method`: parser/adapter approach.
- `status`: `candidate` | `active` | `deprecated`.
- `last_verified_utc`: last verification timestamp.
- `archived_copy_path`: local or stable path to archived copy when retained.
- `known_caveats`: parsing limitations or content gaps.

## Initial registry (seed placeholders)

These entries are placeholders to guide implementation and should be replaced with verified source details.

| source_id | jurisdiction_type | jurisdiction_code | publisher | dataset_name | source_url | official_source_url | source_tier | mirror_url | file_format | update_cadence | archived_copy_path | status | known_caveats |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| federal_public_accounts_tbd | federal | can | TBD | Public Accounts of Canada (TBD) | TBD | TBD | official+mirror (planned) | TBD | TBD | annual (expected) | source-data/federal/... | candidate | Confirm official pages and retention approach |
| provincial_on_public_accounts_tbd | provincial | on | TBD | Public Accounts of Ontario (TBD) | TBD | TBD | official+mirror (planned) | TBD | TBD | annual (expected) | source-data/provincial/on/... | candidate | Confirm exact ministry publication channel |
| municipal_toronto_financials_tbd | municipal | tor | TBD | City of Toronto financial statements (TBD) | TBD | TBD | official+mirror (planned) | TBD | TBD | annual (expected) | source-data/municipal/toronto/... | candidate | Confirm dataset granularity and category mapping |
| provincial_sk_public_accounts_tbd | provincial | sk | TBD | Public Accounts of Saskatchewan (TBD) | TBD | TBD | official+mirror (planned) | TBD | TBD | annual (expected) | source-data/provincial/sk/... | candidate | Optional early-support track |
| municipal_regina_financials_tbd | municipal | reg | TBD | City of Regina financial statements (TBD) | TBD | TBD | official+mirror (planned) | TBD | TBD | annual (expected) | source-data/municipal/regina/... | candidate | Optional early-support track |

## Source verification checklist

- [ ] URL resolves and document is accessible.
- [ ] Publication is official and attributable.
- [ ] If mirror is used, official URL and mirror URL are both documented.
- [ ] Fiscal year labeling is clear.
- [ ] License/usage constraints reviewed.
- [ ] Archived copy location recorded (when retained).
- [ ] Parser strategy selected and documented.
