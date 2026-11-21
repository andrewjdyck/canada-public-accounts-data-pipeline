# canada-public-accounts-data-pipeline

A repository with cleaned and consistent public accounts data for Canadian government entities: federal, provincial, and municipal.

Its first consumer is [can-tax-receipt](https://github.com/andrewjdyck/can-tax-receipt) (MyTaxReceipt.ca), which needs each government's spending broken down by category. See [PLAN.md](./PLAN.md) for the MVP and task list.

## Data layers

```
data/
  bronze/   source documents exactly as published, plus source-docs-manifest.yaml describing each
  silver/   values extracted from bronze in long format, labels verbatim, no categories
  gold/     categorised, validated, cross-jurisdiction data; reconciliation against StatCan
config/     hand-written specs that drive each step (never rewritten by scripts)
src/        one folder per step: fetch -> extract -> clean -> reconcile
```

| Layer | Path | Written by | Contents |
|---|---|---|---|
| bronze | `data/bronze/{federal,provincial,municipal}/...` | `src/fetch/fetch_sources.py` | Public accounts PDFs |
| bronze | `data/bronze/statcan/<product_id>/` | `src/fetch/fetch_sources.py` | StatCan full-table CSV zips (COFOG) |
| bronze | `data/bronze/source-docs-manifest.yaml` | by hand + `fetch_sources.py --record` | URL, retrieval date, sha256, status of every source |
| silver | `data/silver/public-accounts/<doc_id>/<table_id>.csv` | `src/extract/extract_statement_tables.py` | One row per printed amount, with page, row label, column, fiscal year, basis; plus `checks.csv` and `lineage.json` |
| silver | `data/silver/statcan/<product_id>.csv` | `src/extract/extract_statcan.py` | StatCan rows, labels as published |
| gold | `data/gold/public-accounts-facts.csv` | `src/clean/build_public_accounts_facts.py` | Each amount mapped to a function (COFOG) and, where the source has it, an object (salaries, transfers, amortization, ...) |
| gold | `data/gold/spending-shares-preview.csv` | `src/clean/build_public_accounts_facts.py` | Shares by app category (preview of the PLAN.md output contract) |
| gold | `data/gold/statcan-cofog.csv` | `src/clean/clean_statcan_cofog.py` | StatCan COFOG with the same jurisdiction, fiscal-year and concept ids |
| gold | `data/gold/reconciliation/` | `src/reconcile/reconcile_cofog.py` | Public accounts vs StatCan by COFOG division, plus `summary.md` |
| gold | `data/gold/validation/` | clean step | Mapping and total checks |

| Config | Purpose |
|---|---|
| `config/extraction/<doc_id>.yaml` | Which pages and tables to read, the column meanings, units, and the checks the numbers must pass (schema: `config/extraction.schema.json`) |
| `config/mappings/<jurisdiction>.csv` | The "spread": each source line maps to a concept, with weights for splits ([README](config/mappings/README.md)) |
| `config/taxonomy/` | COFOG concepts, object concepts, app category rollups, StatCan components, jurisdictions ([README](config/taxonomy/README.md)) |
| `config/reconciling-items.csv` | Known reasons public accounts and StatCan differ |

## Running it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
make all PY=.venv/bin/python        # fetch, extract, clean, reconcile
```

Or step by step:

```bash
.venv/bin/python src/fetch/fetch_sources.py            # bronze: download missing, verify sha256
.venv/bin/python src/extract/extract_statement_tables.py --all
.venv/bin/python src/extract/extract_statcan.py         # silver
.venv/bin/python src/clean/clean_statcan_cofog.py
.venv/bin/python src/clean/build_public_accounts_facts.py   # gold
.venv/bin/python src/reconcile/reconcile_cofog.py
```

Each step exits non-zero if its checks fail, so bad numbers never reach gold. To check for a newer StatCan release: `fetch_sources.py --only statcan-cofog-by-component --refresh --record`.

### Adding a jurisdiction

1. Add the document to `data/bronze/source-docs-manifest.yaml`, then run `fetch_sources.py --record`.
2. Find the expense-by-function and expense-by-object tables (`src/extract/find_text.py`, `scan_tables.py`, `inspect_pdf.py`).
3. Write `config/extraction/<doc_id>.yaml`, using Ontario's as the template. Include the checks: rows add to totals, and schedules agree with the statement.
4. Write `config/mappings/<code>.csv`. The clean step lists any unmapped line.
5. Run `make all`. If StatCan has the same fiscal year, the jurisdiction appears in the reconciliation.

## Current state

_As of 2026-11-21._

- Bronze: FY2025-26 public accounts for federal plus all 10 provinces, StatCan tables 10-10-0024-01 and 10-10-0005-01.
- Silver and gold: **Ontario only** so far. Three tables (Statement of Operations, Schedule 3 sector by expense type, Schedule 4 by ministry) for 2025-26, plus the restated 2024-25 comparatives. All 62 extraction checks and 5 mapping checks pass.
- Extraction uses pdfplumber word positions plus the spec (`method: pdfplumber_words`). The LLM extractor planned in PLAN.md A4 is not built yet; it would be another `method`, writing the same silver format.

## StatCan COFOG reconciliation: what we found

StatCan's latest COFOG year is 2024 (= FY2024-25, preliminary). The public accounts comparison uses the restated 2024-25 column of the 2025-26 statements. See `data/gold/reconciliation/summary.md` for the full table.

- **Totals reconcile once amortization is removed.** Ontario FY2024-25: public accounts $226,035M − amortization $8,347M = $217,688M, vs StatCan provincial government $217,667M (a $21M gap). StatCan CCOFOG excludes consumption of fixed capital (table footnote 2).
- **Divisions don't line up.** Education is +$14.7B in the public accounts and Social protection −$16.0B, offsetting each other. Health is +$3.3B, almost exactly the Long-Term Care ministry ($3,276M), which suggests StatCan files long-term care under Social protection (10.2 Old age). Child care inside the Education ministry is another likely piece. These are hypotheses: provincial data stops at division level, so they can't be confirmed from the table itself.
- **Provincial COFOG is division-level only** (10 categories). Groups such as hospital services exist only for federal and municipal governments, so StatCan can't supply the health subcategories the app wants.
- **StatCan's provincial component is government proper.** Hospitals, school boards and universities/colleges are separate, unconsolidated components. Adding them double-counts provincial grants.

The likely reasons it didn't reconcile when you first tried were, in order: amortization at the total level, then classification at the division level.
