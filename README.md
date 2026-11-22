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
| gold | `data/gold/spending-shares/<fy>.yaml` | `src/publish/build_spending_shares.py` | **The can-tax-receipt output file** (validated), plus `<fy>-amounts.csv` with the dollars behind each rate |

| Config | Purpose |
|---|---|
| `config/extraction/<doc_id>.yaml` | Which pages and tables to read, the column meanings, units, and the checks the numbers must pass (schema: `config/extraction.schema.json`) |
| `config/mappings/<jurisdiction>.csv` | The "spread": each source line maps to a concept, with weights for splits ([README](config/mappings/README.md)) |
| `config/taxonomy/` | COFOG concepts, object concepts, app category rollups, StatCan components, jurisdictions ([README](config/taxonomy/README.md)) |
| `config/reconciling-items.csv` | Known reasons public accounts and StatCan differ |
| `config/output/` | Output contract settings: category order, federal rules, municipal-transfer overrides, and this repo's copy of the output schema |

## Running it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
make all PY=.venv/bin/python        # fetch, extract, clean, reconcile, publish
```

Or step by step:

```bash
.venv/bin/python src/fetch/fetch_sources.py            # bronze: download missing, verify sha256
.venv/bin/python src/extract/extract_statement_tables.py --all
.venv/bin/python src/extract/extract_statcan.py         # silver
.venv/bin/python src/clean/clean_statcan_cofog.py
.venv/bin/python src/clean/build_public_accounts_facts.py   # gold
.venv/bin/python src/reconcile/reconcile_cofog.py
.venv/bin/python src/publish/build_spending_shares.py   # output file for the app
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
- Silver and gold: **all 11 jurisdictions.** Each has an expense-by-function (or ministry) table and an amortization source; Ontario also has the sector-by-expense-type matrix. Every extraction check and every mapping check passes.
- Reconciliation against StatCan covers all 11 for FY2024-25. See [docs/reconciliation-review.md](docs/reconciliation-review.md) for the analysis.
- Extraction uses pdfplumber word positions plus the spec (`method: pdfplumber_words`). Per-table options cover layout quirks: `drop_chars` (BC, MB dot leaders), `merge_split_digits` (AB, MB, NS), `space_thousands` (QC), `ignore_unaligned_numbers` (NB, QC note columns), and row `sign` and `memo`. The LLM extractor planned in PLAN.md A4 is not built yet.
- Mappings are first-pass by ministry name; see each row's `confidence`. The federal mapping still puts all of Finance in general public services.

## StatCan COFOG reconciliation: what we found

Full analysis: [docs/reconciliation-review.md](docs/reconciliation-review.md). In short, for FY2024-25:

- **Amortization is the first bridge.** StatCan excludes it; once it is removed, ON, PE, AB and BC agree with StatCan within 3%.
- NS, NB, MB and NL are 5–10% higher in the public accounts (lead: health authorities and school boards consolidated at full expense). SK and QC are 12–15% lower (open; for Quebec, refundable tax credits are ruled out).
- Categories don't line up even where totals do. Education is higher and Social protection lower in the public accounts in most large provinces. Long-term care is a strong lead (Ontario's Health gap is $3,297M; its Long-Term Care ministry is $3,276M), and child care inside education ministries is another.
- Federally, StatCan files the Canada Health Transfer under Health. The federal mapping needs Finance split by transfer.
- Provincial COFOG is division-level only and lags a year, so it works as a check, not as the app's source.
