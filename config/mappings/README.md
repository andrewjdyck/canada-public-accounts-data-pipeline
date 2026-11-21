# Mappings: the "spread" from source lines to concepts

One CSV per jurisdiction (`<code>.csv`, lowercase). Each row maps one printed source line to a concept.

| Column | Meaning |
|---|---|
| `table_id` | Table in `config/extraction/<doc_id>.yaml` |
| `dimension` | `function` (maps to `config/taxonomy/cofog.csv` or `_unallocated`) or `object` (maps to `objects.csv`) |
| `source_label` | The row label (or, for sector-by-object tables, the `sector` column dimension) exactly as in the spec |
| `concept_id` | Target concept |
| `weight` | Share of the line going to this concept. Split a line by giving it several rows; the weights must sum to 1 |
| `valid_from` / `valid_to` | Fiscal years the row applies to (blank `valid_to` = still valid). Lets ministries be renamed or reorganised without losing history |
| `method` | `manual`, or how a split was estimated (e.g. `estimates_2024_25`) |
| `confidence` | `high` / `medium` / `low`: how cleanly the line fits the concept |

`src/clean/build_public_accounts_facts.py` fails if any source line is unmapped, if weights don't sum to 1, or if mapped totals don't equal the stated total.
