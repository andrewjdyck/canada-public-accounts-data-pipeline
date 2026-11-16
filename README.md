# canada-public-accounts-data-pipeline

A repository with cleaned and consistent public accounts data for Canadian government entities - federal, provincial, and municipal

Its first consumer is [can-tax-receipt](https://github.com/andrewjdyck/can-tax-receipt) (MyTaxReceipt.ca), which needs each government's spending broken down by category. See [PLAN.md](./PLAN.md) for the MVP and task list.

## Folder structure

```
README.md
PLAN.md
source-docs/            # original public accounts documents + manifest.yaml describing each
  federal/ca/
  provincial/sk/
  municipal/regina-sk/
output-data/
  raw-tables/           # tables extracted from PDFs, with a provenance manifest
  manually-generated/   # hand-written placeholder shares (to be replaced; see PLAN.md)
parsed-data/            # mapping files from source line items to categories (examples so far)
docs/                   # notes (e.g. XBRL)
src/pa_pdf/             # PDF inspection and table-extraction scripts
```

## Current state

_As of 2026-11-13._

- `pdfplumber` scripts to inspect PDFs, find text, scan for tables and extract tables to CSV with a provenance manifest (`src/pa_pdf/`).
- A source manifest (`source-docs/manifest.yaml`) covering:
  - federal Public Accounts Volume II, 2024-25;
  - Saskatchewan Volume 2, 2024-25;
  - City of Regina.
- Raw tables extracted for two pages of the federal PDF only (`output-data/raw-tables/2025-vol2-eng/`).
- Example mapping files (`parsed-data/*.example.*`, `parsed-data/provincial/sk/`, `parsed-data/municipal/regina-sk/`).
- Hand-written placeholder share files in `output-data/manually-generated/`.
- Not built yet:
  - LLM extraction;
  - normalised output;
  - accuracy check;
  - a published file in the format can-tax-receipt uses.

## Working with PDFs (tables inside Public Accounts)

Most Canadian public accounts are published as PDFs with embedded tables. With a PDF like `source-docs/federal/ca/2025-vol2-eng.pdf`, the typical workflow is:

- **Inspect extractability**: detect whether the PDF has embedded text and whether tables are discoverable programmatically (vs needing OCR).
- **Extract tables**: pull detected tables into `CSV` files with provenance (pdf name, page number, table index, bounding box).
- **Normalize**: map extracted tables into consistent “fact tables” (entity/year/line item/value/units) so federal/provincial/municipal data can be compared.
- **Publish**: ship open formats (CSV/Parquet) plus metadata and (optionally) an XBRL-aligned taxonomy mapping.

### Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### Quick commands

- **Download source documents and verify their sha256 against the manifest** (`--record` writes hashes for new entries):

```bash
.venv/bin/python src/pa_pdf/fetch_sources.py
```

- **Inspect the PDF**:

```bash
.venv/bin/python src/pa_pdf/inspect_pdf.py --pdf source-docs/federal/ca/2025-vol2-eng.pdf --pages 1-5 --sample-page 1
```

- **Extract tables to CSV + manifest**:

```bash
.venv/bin/python src/pa_pdf/extract_tables.py --pdf source-docs/federal/ca/2025-vol2-eng.pdf --out output-data/raw-tables --pages 1-50
```
