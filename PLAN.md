# MVP Execution Plan

This repository is a **data producer**. Its job is to publish a consistent, versioned, well-documented dataset of government spending shares. It contains no application code.

The first consumer is [can-tax-receipt](https://github.com/andrewjdyck/can-tax-receipt) (MyTaxReceipt.ca), a web app in a **separate repository**. Wherever this plan says "the app", it means that external consumer. The app fetches a tagged release of this repo's output and owns everything downstream: UI, tax rates, deployment, and its own build-time checks (see that repo's `PLAN.md`). This repo owns the spending data, its accuracy, and the published file format. Nothing here depends on the app's code.

_Created: 2026-11-13_

---

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
- Publish to: `output-data/spending-shares/<fiscal-year>.yaml`, plus a git tag (and ideally a GitHub release asset) that consumers fetch. The app's sync script is one such consumer.

---

## Tasks

Status: ⬜ not started · 🔄 in progress · ✅ done

### A. Spending-share extraction (moved from the app plan)

| Task | Status | Details |
|------|--------|---------|
| A1 Source documents | 🔄 | **Progress (2026-11-14):** all 11 jurisdictions have FY2025-26 sources with sha256 recorded. Ten are downloaded by `src/pa_pdf/fetch_sources.py`. PEI was downloaded by browser, because its site blocks scripts; its direct PDF URL still needs recording. Still open: whether PDFs stay in git. <br>**Original task:** Add federal + all 10 provinces to `source-docs/manifest.yaml` with URL, fiscal year, retrieval date and sha256. Use the latest published year for each. Prefer the consolidated "expense by function/ministry" statement in each jurisdiction's summary financial statements. Decide whether PDFs stay in git or are downloaded by script. |
| A2 Category taxonomy | ⬜ | Define one provincial category set and one federal set. Write a mapping file per jurisdiction from source line items to categories, replacing the `*.mapping.example.yaml` files. Suggested sets: <br>• Provincial: Healthcare, Education, Social Services, Transportation, Debt Charges, Other. <br>• Federal: Elderly Benefits, Transfers to Provinces, Children's Benefits, Employment Insurance, Defence, Debt Charges, Indigenous Services, Other. |
| A3 Locate tables | ⬜ | Use the existing `find_text` / `scan_tables` scripts to find the candidate pages in each document. Record the page numbers in the manifest. |
| A4 LLM extraction | ⬜ | For each located table, an LLM returns structured rows (line item, amount, units, page). Validate them against a schema. Check that the rows add up to the total stated in the document. Store the raw output with the model, prompt version and page reference. |
| A5 Ontario as reference | ⬜ | Run Ontario first and compare against the earlier hand extraction (see "Ontario reference" below). |
| A6 Accuracy check | ⬜ | Hand-check extracted values against the source for every jurisdiction, or for a documented sample. Record the accuracy figure, every correction made, and whether each was an extraction or a mapping error. |
| A7 Publish | ⬜ | Write `output-data/spending-shares/<fiscal-year>.yaml` in the contract format. Validate it with the app's rules. Tag a version. |
| A8 README | ⬜ | Document the workflow, how to rerun it, the accuracy result and known limitations. Remove the `output-data/manually-generated/` placeholders. |

### B. Supporting work

| Task | Status | Details |
|------|--------|---------|
| B1 Reproducible environment | ✅ | `requirements.txt` with pinned direct dependencies; install into `.venv`. Original task: Pin dependencies (`requirements.txt` or `pyproject.toml`) rather than relying on a local conda env. Keep API keys in env vars. |
| B2 Output validation | ⬜ | Keep a copy of the output schema in this repo and validate against it before tagging: shares sum to 1, exactly 10 provinces, and `_meta` complete. The rules should match the checks the app applies on its side (its `lib/data-files.ts`), so a release never breaks the consumer. |
| B3 Folder structure | ⬜ | Move the provincial mapping files to a consistent layout per jurisdiction, matching `source-docs/`. |

### Notes

- Quebec publishes its public accounts in English as well as French; use the English edition if the tables match.
- Federal transfers to provinces (Canada Health Transfer, Canada Social Transfer, equalization) appear again in provincial spending. Document this rather than adjust for it.
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
B1 → A1 → A2 → A3 → A4 + A5 (Ontario first) → A4 (remaining 10) → A6 → B2 → A7 → A8
```

## Rough Effort

| Workstream | Effort |
|------------|--------|
| A. Extraction (11 jurisdictions) | 18–24 h |
| B. Supporting work | 2–3 h |

**Total:** ~20–27 hours
