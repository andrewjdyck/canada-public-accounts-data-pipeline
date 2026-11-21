# Taxonomy (hand-written config)

| File | What it is |
|---|---|
| `cofog.csv` | Function concepts. The 10 COFOG divisions and the groups Statistics Canada publishes (CCOFOG). `concept_id` is derived from StatCan's codes: `[7073]` becomes `07.3`. Where StatCan merges several COFOG groups into one "not elsewhere classified" line, the id lists them all (`01.5+01.6+01.8`). Regenerate only if StatCan changes the classification. |
| `objects.csv` | Economic object concepts: what money was spent *on* (salaries, transfers, amortization, ...). Used with the sector-by-object schedules. |
| `app-categories.csv` | Rolls function concepts up to the category names in the can-tax-receipt output contract. Matching is by longest `concept_prefix` (`04.5` beats `04`), and `*` is the fallback. |
| `statcan-components.csv` | StatCan "public sector component" labels, short ids, and how a StatCan reference year maps to a fiscal year. |
| `jurisdictions.csv` | Jurisdiction codes, StatCan GEO names and the full English names the output contract uses as keys. |

Special function concept used in mappings, not in `cofog.csv`:

- `_unallocated`: a source line that spans several functions and can't be split from the document alone, such as Ontario's "Other" sector. It is kept in the totals, so shares still sum to 1, and reported separately in reconciliation.
