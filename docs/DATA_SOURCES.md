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

## Registry schema

Each source entry should contain:

- `source_id`: stable unique ID (for example, `prov_on_public_accounts`).
- `jurisdiction_type`: `federal` | `provincial` | `municipal`.
- `jurisdiction_code`: short code (for example, `can`, `on`, `yvr`).
- `publisher`: organization publishing the source.
- `dataset_name`: official name of publication.
- `source_url`: canonical URL.
- `file_format`: `pdf` | `xlsx` | `csv` | `api` | other.
- `coverage_start` / `coverage_end`: fiscal years covered.
- `update_cadence`: annual, quarterly, ad hoc, etc.
- `license_notes`: usage restrictions/notes.
- `ingest_method`: parser/adapter approach.
- `status`: `candidate` | `active` | `deprecated`.
- `last_verified_utc`: last verification timestamp.
- `known_caveats`: parsing limitations or content gaps.

## Initial registry (seed placeholders)

These entries are placeholders to guide implementation and should be replaced with verified source details.

| source_id | jurisdiction_type | jurisdiction_code | publisher | dataset_name | source_url | file_format | update_cadence | status | known_caveats |
|---|---|---|---|---|---|---|---|---|---|
| federal_public_accounts_tbd | federal | can | TBD | Public Accounts (TBD) | TBD | TBD | annual (expected) | candidate | Source URL and format not yet confirmed |
| provincial_bc_public_accounts_tbd | provincial | bc | TBD | Public Accounts BC (TBD) | TBD | TBD | annual (expected) | candidate | Needs official URL verification |
| provincial_ab_public_accounts_tbd | provincial | ab | TBD | Public Accounts AB (TBD) | TBD | TBD | annual (expected) | candidate | Needs official URL verification |
| provincial_sk_public_accounts_tbd | provincial | sk | TBD | Public Accounts SK (TBD) | TBD | TBD | annual (expected) | candidate | Needs official URL verification |
| provincial_on_public_accounts_tbd | provincial | on | TBD | Public Accounts ON (TBD) | TBD | TBD | annual (expected) | candidate | Needs official URL verification |
| municipal_yvr_public_accounts_tbd | municipal | yvr | TBD | Municipal Financial Statements (TBD) | TBD | TBD | annual (expected) | candidate | Define exact municipality entity/source |
| municipal_yyc_public_accounts_tbd | municipal | yyc | TBD | Municipal Financial Statements (TBD) | TBD | TBD | annual (expected) | candidate | Define exact municipality entity/source |
| municipal_yqr_public_accounts_tbd | municipal | yqr | TBD | Municipal Financial Statements (TBD) | TBD | TBD | annual (expected) | candidate | Define exact municipality entity/source |
| municipal_yyz_public_accounts_tbd | municipal | yyz | TBD | Municipal Financial Statements (TBD) | TBD | TBD | annual (expected) | candidate | Define exact municipality entity/source |

## Source verification checklist

- [ ] URL resolves and document is accessible.
- [ ] Publication is official and attributable.
- [ ] Fiscal year labeling is clear.
- [ ] License/usage constraints reviewed.
- [ ] Parser strategy selected and documented.
