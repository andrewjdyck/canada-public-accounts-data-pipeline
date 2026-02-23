# canada-public-accounts-data-pipeline

A repository with cleaned and consistent public accounts data for Canadian government entities - federal, provincial, and municipal

## Folder structure

- root
README.md
  - source-data
    - federal
    - provincial
      - bc
      - ab
      - sk
      - on
      - ...
    - municipal
      - yvr
      - yyc
      - yqr
      - yyz
      - ...
  - output-data
    - ...
- src

## Working with PDFs (tables inside Public Accounts)

Most Canadian public accounts are published as PDFs with embedded tables. With a PDF like `source-docs/2025-vol2-eng.pdf`, the typical workflow is:

- **Inspect extractability**: detect whether the PDF has embedded text and whether tables are discoverable programmatically (vs needing OCR).
- **Extract tables**: pull detected tables into `CSV` files with provenance (pdf name, page number, table index, bounding box).
- **Normalize**: map extracted tables into consistent “fact tables” (entity/year/line item/value/units) so federal/provincial/municipal data can be compared.
- **Publish**: ship open formats (CSV/Parquet) plus metadata and (optionally) an XBRL-aligned taxonomy mapping.

### Quick commands (using your conda env `dev`)

These scripts only require `pdfplumber` (no pandas/numpy):

- **Inspect the PDF**:

```bash
CONDA_NO_PLUGINS=true conda run -n dev python src/pa_pdf/inspect_pdf.py --pdf source-docs/2025-vol2-eng.pdf --pages 1-5 --sample-page 1
```

- **Extract tables to CSV + manifest**:

```bash
CONDA_NO_PLUGINS=true conda run -n dev python src/pa_pdf/extract_tables.py --pdf source-docs/2025-vol2-eng.pdf --out output-data/raw-tables --pages 1-50
```

