# canada-public-accounts-data-pipeline

**What are Canadians buying with their taxes?** This repository uses the public accounts that federal and provincial governments already publish to work out which goods and services government spending delivers to citizens: health care, schooling, income support, roads, policing and so on.

Plenty of reporting already covers *who* spends public money (which ministry, which order of government) and *how much* they spend. This project focuses on *what is delivered*. Every dollar is classified by the service it pays for, not by the organisation that spends or passes it on.

Its first consumer is [can-tax-receipt](https://github.com/andrewjdyck/can-tax-receipt) (MyTaxReceipt.ca), which shows each taxpayer what their taxes bought. See [PLAN.md](./PLAN.md) for the MVP and task list.

## Principles

These rules decide every classification choice in the pipeline:

1. **Classify by what is delivered, not who spends it.** Categories are services and goods (health care, education, income support, transportation, ...), anchored to the international Classification of the Functions of Government (COFOG). Ministry and department names are only evidence of what was delivered.
2. **Follow pass-through money to the service it pays for.** A transfer from one government to another is not a service. Count it once, where the service is delivered and in that service's category, not as spending by the government that passed it on.
   - The Canada Health Transfer, Canada Social Transfer, equalization and other federal transfers to provinces and territories are **excluded from federal shares** (numerator and denominator). They reappear as health, education and social services in provincial spending.
   - A provincial transfer to a municipality or agency whose purpose is known (transit, social housing, hospitals) is counted **in that service's category**.
3. **Name the gap when the service can't be identified.** A transfer whose end use the published reports don't reveal, such as an unconditional grant to municipalities, is kept as its own transparent category (e.g. Municipal Transfers) rather than guessed into a service. As better sources are found, these amounts should move into service categories. They are a measure of what isn't yet known, not a destination.
4. **Use what governments already publish.** Every figure comes from audited public accounts (or, for detail, the governments' own supplementary volumes) and traces to a document, page and printed line. Statistics Canada's COFOG tables are used to check the work, not as the source.
5. **Show the judgment calls.** Each mapping from a printed line to a service carries a confidence level and a note. Where the published detail forces a compromise (a line that mixes services, a total that can't be split), it is stated in the output's `extractionNotes`.

## Data layers

```
data/
  1_bronze/ source documents exactly as published, plus source-docs-manifest.yaml describing each
  2_silver/ values extracted from bronze in long format, labels verbatim, no categories
  3_gold/   categorised, validated, cross-jurisdiction data; reconciliation against StatCan
config/     hand-written specs that drive each step (never rewritten by scripts)
src/        one folder per step: fetch -> extract -> clean -> reconcile
```

| Layer | Path | Written by | Contents |
|---|---|---|---|
| bronze | `data/1_bronze/{federal,provincial,municipal}/...` | `src/fetch/fetch_sources.py` | Public accounts PDFs |
| bronze | `data/1_bronze/statcan/<product_id>/` | `src/fetch/fetch_sources.py` | StatCan full-table CSV zips (COFOG) |
| bronze | `data/1_bronze/source-docs-manifest.yaml` | by hand + `fetch_sources.py --record` | URL, retrieval date, sha256, status of every source |
| silver | `data/2_silver/public-accounts/<doc_id>/<table_id>.csv` | `src/extract/extract_statement_tables.py` | One row per printed amount, with page, row label, column, fiscal year, basis; plus `checks.csv` and `lineage.json` |
| silver | `data/2_silver/statcan/<product_id>.csv` | `src/extract/extract_statcan.py` | StatCan rows, labels as published |
| gold | `data/3_gold/public-accounts-facts.csv` | `src/clean/build_public_accounts_facts.py` | Each amount mapped to a function (COFOG) and, where the source has it, an object (salaries, transfers, amortization, ...) |
| gold | `data/3_gold/spending-shares-preview.csv` | `src/clean/build_public_accounts_facts.py` | Shares by app category (preview of the PLAN.md output contract) |
| gold | `data/3_gold/statcan-cofog.csv` | `src/clean/clean_statcan_cofog.py` | StatCan COFOG with the same jurisdiction, fiscal-year and concept ids |
| gold | `data/3_gold/reconciliation/` | `src/reconcile/reconcile_cofog.py` | Public accounts vs StatCan by COFOG division, plus `summary.md` |
| gold | `data/3_gold/validation/` | clean step | Mapping and total checks |
| gold | `data/3_gold/federal-leaves.csv` | `src/clean/build_federal_leaves.py` | Every federal dollar as one leaf of the Table 3.6 grid (ministry × payment type), with its treatment (service, financing, unidentified, or excluded pass-through) and service ([design](docs/federal-design.md)) |
| gold | `data/3_gold/spending-shares/<fy>.yaml` | `src/publish/build_spending_shares.py` | **The can-tax-receipt output file** (validated), plus `<fy>-amounts.csv` with the dollars behind each rate |

| Config | Purpose |
|---|---|
| `config/extraction/<doc_id>.yaml` | Which pages and tables to read, the column meanings, units, and the checks the numbers must pass (schema: `config/extraction.schema.json`) |
| `config/mappings/<jurisdiction>.csv` | The "spread": each source line maps to a concept, with weights for splits ([README](config/mappings/README.md)) |
| `config/taxonomy/` | COFOG concepts, object concepts, app category rollups, StatCan components, jurisdictions ([README](config/taxonomy/README.md)) |
| `config/reconciling-items.csv` | Known reasons public accounts and StatCan differ |
| `config/taxonomy/services.csv` | **The service categories** (COFOG → service). Review map: [docs/cofog-to-services.md](docs/cofog-to-services.md) |
| `config/federal/` | Federal leaves (`leaves.csv`) and each ministry's default treatment and service by payment type (`ministry-services.csv`) |
| `config/output/` | Output contract settings, provincial Municipal Transfers overrides, and this repo's copy of the output schema |

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

1. Add the document to `data/1_bronze/source-docs-manifest.yaml`, then run `fetch_sources.py --record`.
2. Find the expense-by-function and expense-by-object tables (`src/extract/find_text.py`, `scan_tables.py`, `inspect_pdf.py`).
3. Write `config/extraction/<doc_id>.yaml`, using Ontario's as the template. Include the checks: rows add to totals, and schedules agree with the statement.
4. Write `config/mappings/<code>.csv`. The clean step lists any unmapped line.
5. Run `make all`. If StatCan has the same fiscal year, the jurisdiction appears in the reconciliation.

## Current state

_As of 2026-11-24._

- **Output:** `data/3_gold/spending-shares/2025-26.yaml` gives shares **by service** for federal and all 10 provinces (validated). Federal shares exclude transfers to provinces and territories ($110.4B), unidentified transfers to municipalities and Indigenous governments ($45.8B) and pollution pricing returns ($4.3B); these are listed in `_meta.excludedFromShares` and kept in `data/3_gold/federal-leaves.csv`.
- **Federal:** built from the Volume I Table 3.6 grid ([design](docs/federal-design.md)). Major transfers are split exactly into programs. "Other transfers" use ministry defaults until **Volume II 2025-26** is in bronze. It can't be downloaded by script (the server sends an incomplete certificate chain), so download it by browser to `data/1_bronze/federal/ca/2026-vol2-eng.pdf`. Volume II is what will move Indigenous Services and housing/infrastructure transfers out of the excluded group and into services.
- **Provinces:** all 10 extracted and mapped COFOG → service. Quebec uses its by-portfolio Appendix 2. Municipal Transfers holds only provincial transfers to municipalities of unknown use.
- **Checks:** every extraction check, mapping check and leaf-sum check passes. Reconciliation against StatCan covers all 11 for FY2024-25 ([analysis](docs/reconciliation-review.md)).
- Extraction uses pdfplumber word positions plus per-table specs. The LLM extractor planned in PLAN.md A4 is not built yet.

## StatCan COFOG reconciliation: what we found

Full analysis: [docs/reconciliation-review.md](docs/reconciliation-review.md). In short, for FY2024-25:

- **Amortization is the first bridge.** StatCan excludes it; once it is removed, ON, PE, AB and BC agree with StatCan within 3%.
- NS, NB, MB and NL are 5–10% higher in the public accounts (lead: health authorities and school boards consolidated at full expense). SK and QC are 12–15% lower (open; for Quebec, refundable tax credits are ruled out).
- Categories don't line up even where totals do. Education is higher and Social protection lower in the public accounts in most large provinces. Long-term care is a strong lead (Ontario's Health gap is $3,297M; its Long-Term Care ministry is $3,276M), and child care inside education ministries is another.
- Federally, StatCan files the Canada Health Transfer under Health. The federal mapping needs Finance split by transfer.
- Provincial COFOG is division-level only and lags a year, so it works as a check, not as the app's source.
