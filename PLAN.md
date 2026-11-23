# MVP Execution Plan

This repository is a **data producer**. Its job is to publish a consistent, versioned, well-documented dataset of government spending shares. It contains no application code.

The first consumer is [can-tax-receipt](https://github.com/andrewjdyck/can-tax-receipt) (MyTaxReceipt.ca), a web app in a **separate repository**. Wherever this plan says "the app", it means that external consumer. The app fetches a tagged release of this repo's output and owns everything downstream: UI, tax rates, deployment, and its own build-time checks (see that repo's `PLAN.md`). This repo owns the spending data, its accuracy, and the published file format. Nothing here depends on the app's code.

_Created: 2026-11-13_

---

**Purpose:** show which goods and services citizens receive for their taxes, classified by what is delivered rather than who spends it. See README "Principles".

## MVP Definition

**What it is:** A repeatable pipeline that turns published public accounts documents into spending shares by category for the federal government and all 10 provinces. Every number traces back to a source page, and accuracy is measured.

**The MVP is done when:**

1. **Coverage:** The federal government and all 10 provinces each have spending shares by category from their latest published public accounts (FY2025-26 where available, otherwise FY2024-25).
2. **LLM extraction:** Expense tables are read from the public accounts PDFs by an LLM. Its output is checked against a schema and against the totals stated in each document.
3. **Provenance:** Every figure records its source document (URL, retrieval date, sha256) and page number.
4. **Measured accuracy:** Extracted values are hand-checked against the source. The accuracy figure is published along with every correction made, and whether each was an extraction or a mapping error.
5. **Published output:** A versioned (tagged) `spending-shares` file in the format can-tax-receipt expects, with every jurisdiction marked `dataQuality: actual`.
6. **Documented:** The README explains the workflow, how to rerun it, the accuracy result, and known limitations. This is the source material for the app's "How this was built" page.

**Not in the MVP:** territories, municipal data, multiple fiscal years, full fact-table normalisation for every line item, XBRL mapping.

**Target:** published in time for the app to launch before the spring 2027 tax season.

---

## Output Contract

This repo publishes one file per fiscal year. Consumers such as can-tax-receipt download it from a tagged release. Its format was first written down in the app repo at [`data/schema/spending-shares.md`](https://github.com/andrewjdyck/can-tax-receipt/blob/main/data/schema/spending-shares.md). As the producer, this repo should keep its own copy of the schema and validate against it before each release (B2), so publishing never depends on the app's code. In brief:

```yaml
schemaVersion: 1
dataset: canada-spending-shares
pipelineVersion: "v0.1.0"          # the git tag
generatedAt: "2027-01-15"
fiscalYear: "2025-26"
federal:
  _meta:
    source: "Public Accounts of Canada 2025-26, Volume I"
    sourceUrl: "https://..."
    sourceDate: "2025-26"
    dataQuality: "actual"           # actual | estimate | placeholder
    documentId: "fed-canada-public-accounts-2025-26-vol1"
    pages: [41, 42]
    verified: true
    extractionNotes: "..."
  categories:
    - name: "Elderly Benefits"
      rate: 0.16                    # share of TOTAL spending; categories sum to 1.0
      subcategories:
        - name: "Old Age Security (OAS)"
          rate: 0.12                # also a share of TOTAL spending
provincial:
  Alberta: { _meta: {...}, categories: [...] }
  # ...exactly the 10 provinces, keyed by full English name
```

- The app repo currently holds a placeholder file in this format at `data/pipeline/spending-shares.yaml`. Use it as a worked example.
- Rules this repo enforces before publishing (B2). The app's build applies the same checks independently, so a file that fails here would break the consumer:
  - shares sum to 1;
  - exactly the 10 provinces, no more and no fewer;
  - `schemaVersion` is one consumers support.
- Changing the format (a new `schemaVersion`) is a breaking change for consumers. Coordinate it with the app repo before tagging.
- Publish to: `data/gold/spending-shares/<fiscal-year>.yaml`, plus a git tag (and ideally a GitHub release asset) that consumers fetch. The app's sync script is one such consumer.

---

## Tasks

Status: ⬜ not started · 🔄 in progress · ✅ done

### A. Spending-share extraction (moved from the app plan)

| Task | Status | Details |
|------|--------|---------|
| A1 Source documents | 🔄 | **Progress (2026-11-14):** all 11 jurisdictions have FY2025-26 sources with sha256 recorded. Ten are downloaded by `src/fetch/fetch_sources.py`. PEI was downloaded by browser, because its site blocks scripts; its direct PDF URL still needs recording. **Decision:** source PDFs are committed to git as binary files. They don't change once downloaded, and publisher links break (the Saskatchewan 2024-25 Volume 1 link already returns 404). `fetch_sources.py` checks each committed file's sha256 against the manifest. <br>**Original task:** Add federal + all 10 provinces to `source-docs/manifest.yaml` with URL, fiscal year, retrieval date and sha256. Use the latest published year for each. Prefer the consolidated "expense by function/ministry" statement in each jurisdiction's summary financial statements. Decide whether PDFs stay in git or are downloaded by script. |
| A2 Category taxonomy | 🔄 | **Progress (2026-11-21):** categories are now defined as COFOG concepts (`config/taxonomy/cofog.csv`), rolled up to the app's names in `config/taxonomy/app-categories.csv`. Mappings are long CSVs with weights (`config/mappings/<code>.csv`); all 11 have a first pass. The federal mapping needs Finance and Employment split into groups. <br>**Original task:** Define one provincial category set and one federal set. Write a mapping file per jurisdiction from source line items to categories, replacing the `*.mapping.example.yaml` files. Suggested sets: <br>• Provincial: Healthcare, Education, Social Services, Transportation, Debt Charges, Other. <br>• Federal: Elderly Benefits, Transfers to Provinces, Children's Benefits, Employment Insurance, Defence, Debt Charges, Indigenous Services, Other. <br>**Decided 2026-11-22/23:** classify by what is delivered, not who spends (README "Principles"). Federal transfers to provinces are excluded from federal numerator and denominator (no Transfers to Provinces category). Provincial transfers to municipalities go to the service they fund when that is known; only transfers whose use is unknown stay in a Municipal Transfers category. |
| A3 Locate tables | 🔄 | **Progress (2026-11-21):** table locations live in `config/extraction/<doc_id>.yaml`; all 11 jurisdictions have a function table and an amortization source. Still open: object-by-function schedules beyond Ontario. <br>**Original task:** Use the existing `find_text` / `scan_tables` scripts to find the candidate pages in each document. Record the page numbers in the extraction spec. |
| A4 LLM extraction | 🔄 | **Progress (2026-11-21):** spec-driven extraction with checks is built (`src/extract/extract_statement_tables.py`, `method: pdfplumber_words`), writing long-format silver tables. The LLM extractor would be a second `method` writing the same format, so checks and downstream steps don't change. Needs an Anthropic API key. <br>**Original task:** For each located table, an LLM returns structured rows (line item, amount, units, page). Validate them against a schema. Check that the rows add up to the total stated in the document. Store the raw output with the model, prompt version and page reference. |
| A5 Ontario as reference | 🔄 | **Progress (2026-11-21):** Ontario 2024-25 (restated) gives Healthcare 0.4022, Education 0.2372, Social Services 0.0915, Transportation 0.0321, Debt Charges 0.0669, Other 0.1700, vs the hand extraction's 0.4036 / 0.2306 / 0.0892 / 0.0318 / (in Other) / 0.2448. Differences: Teachers' Pension and Seniors are now mapped to Education and Social Services, debt is separated, and the comparatives are restated. Health subcategories are not split yet. <br>**Original task:** Run Ontario first and compare against the earlier hand extraction (see "Ontario reference" below). |
| A6 Accuracy check | ⬜ | Hand-check extracted values against the source for every jurisdiction, or for a documented sample. Record the accuracy figure, every correction made, and whether each was an extraction or a mapping error. |
| A7 Publish | 🔄 | **Progress (2026-11-22):** `data/gold/spending-shares/2025-26.yaml` is built for federal and all 10 provinces by `src/publish/build_spending_shares.py` (`make publish`), with amounts behind every rate in `2025-26-amounts.csv`. Federal shares exclude transfers to provinces and territories (major transfers plus EI Labour Market Development Agreements) from numerator and denominator. Provinces have a Municipal Transfers category (`config/output/category-overrides.csv`). Still open: `verified: true` after A6, health subcategories, and the git tag. <br>**Original task:** Write `data/gold/spending-shares/<fiscal-year>.yaml` in the contract format. Validate it with the app's rules. Tag a version. |
| A8 README | ⬜ | Document the workflow, how to rerun it, the accuracy result and known limitations. ~~Remove the `output-data/manually-generated/` placeholders.~~ Done 2026-11-21. |

### B. Supporting work

| Task | Status | Details |
|------|--------|---------|
| B1 Reproducible environment | ✅ | `requirements.txt` with pinned direct dependencies; install into `.venv`. Original task: Pin dependencies (`requirements.txt` or `pyproject.toml`) rather than relying on a local conda env. Keep API keys in env vars. |
| B2 Output validation | ✅ | Done 2026-11-22: `config/output/spending-shares.schema.json` + `src/publish/validate_spending_shares.py` check the schema, shares summing to 1, exactly 10 provinces, subcategories within their category, and dataQuality actual. The app repo's `data/schema/spending-shares.md` and `lib/data-files.ts` are not pushed to any branch, so these rules follow this plan's contract; compare once they are. <br>**Original task:** Keep a copy of the output schema in this repo and validate against it before tagging: shares sum to 1, exactly 10 provinces, and `_meta` complete. The rules should match the checks the app applies on its side (its `lib/data-files.ts`), so a release never breaks the consumer. |
| B3 Folder structure | ✅ | Done 2026-11-21: `data/{bronze,silver,gold}`, `config/`, and `src/{fetch,extract,clean,reconcile}`. `parsed-data/` and `output-data/` are removed, and the manifest is renamed `data/bronze/source-docs-manifest.yaml`. |

### C. StatCan COFOG comparison

| Task | Status | Details |
|------|--------|---------|
| C1 Download COFOG | ✅ | StatCan tables 10-10-0024-01 (by government component) and 10-10-0005-01 (consolidated) are in bronze, fetched by `fetch_sources.py` (`download.method: statcan_wds`). `--refresh` picks up new StatCan releases. |
| C2 Comparable format | ✅ | `data/gold/statcan-cofog.csv` has the same jurisdiction codes, fiscal years and COFOG concept ids as `public-accounts-facts.csv`. |
| C3 Reconciliation | 🔄 | All 11 jurisdictions reconciled for FY2024-25 (2026-11-21); analysis in `docs/reconciliation-review.md`. Open: Quebec (−14.8%) and Saskatchewan (−12.6%) perimeter, the long-term care and child care classification tests, and the federal Finance split. |
| C4 Year overlap | 🔄 | StatCan's latest year is 2024 (FY2024-25, preliminary). Use the restated prior-year column in each FY2025-26 document (as for Ontario), so no extra downloads are needed. |

### Notes

- Quebec publishes its public accounts in English as well as French; use the English edition if the tables match.
- Federal transfers to provinces (Canada Health Transfer, Canada Social Transfer, equalization) are pass-throughs: they are excluded from federal shares and counted where the service is delivered (README "Principles", decided 2026-11-22). This replaces the earlier note to document rather than adjust for them.
- Spending is total government spending from all revenue sources. The app applies these shares to income tax only and explains this to users.

### Ontario reference (earlier hand extraction, 2024-25)

This was done by hand in the app repo before the pipeline existed. Use it as the baseline for A5.

- **Source:** [Ontario Public Accounts – Summary Table 9 (Operating and capital), 2024-25](https://www.ontario.ca/page/summary-table-9-operating-and-capital-2024-25), column "Operating and capital expense total including adjustments".
- **Mapping:**
  - Health + Long-Term Care → Healthcare
  - Education + Colleges/Universities → Education
  - Children, Community and Social Services → Social Services
  - Transportation → Transportation
  - everything else → Other
- **Healthcare subcategories:**
  - Long-Term Care ministry is used directly.
  - The Health ministry is split using the [Expenditure Estimates](https://www.ontario.ca/page/expenditure-estimates-ministry-health-2024-25): Health Services ≈ hospitals, OHIP ≈ other.
- **Results (shares of total):**

  | Category | Subcategory | Share |
  |----------|-------------|-------|
  | Healthcare | | 0.4036 |
  | | Hospitals | 0.1957 |
  | | Long-term Care | 0.0185 |
  | | Other Healthcare | 0.1894 |
  | Education | | 0.2306 |
  | | Primary and Secondary | 0.1760 |
  | | Post-secondary | 0.0546 |
  | Social Services | | 0.0892 |
  | Transportation | | 0.0318 |
  | Other | | 0.2448 |

- **Known gap:** debt interest was left in Other. The suggested taxonomy separates Debt Charges.

---

## Suggested Order

```
B1 → A1 → B3 → C1 → C2 → A2/A3/A4 + A5 (Ontario first) → C3 → A2/A3/A4 (remaining 10, each reconciled with C3) → A6 → B2 → A7 → A8
```

## Rough Effort

| Workstream | Effort |
|------------|--------|
| A. Extraction (11 jurisdictions) | 18–24 h |
| B. Supporting work | 2–3 h |

**Total:** ~20–27 hours
