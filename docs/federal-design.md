# Federal design: classify every dollar once, by the service it buys

_Agreed 2026-11-23. Implements the README "Principles" for the federal government. The same service taxonomy is used for the provinces._

## 1. The rule

Every federal dollar ends up in exactly one **treatment**:

| Treatment | Meaning | In the shares? |
|---|---|---|
| `service` | Buys a good or service for citizens (a benefit cheque, health research, a frigate, a passport office) | Yes, in its service category |
| `financing` | Interest on past borrowing | Yes, as Debt Charges (a cost, not a service) |
| `unidentified` | The published reports don't reveal what it bought | Yes, as the explicit "Unidentified" category, measured and reduced over time |
| `pass_through_provinces` | Money to provinces and territories to fund services they deliver (CHT, CST, equalization, child care, health agreements, EI labour market agreements) | **No.** Recorded in gold, excluded from numerator and denominator, and counted in provincial shares |
| `other_municipal_indigenous_transfers` | Transfers to municipalities or Indigenous governments and organizations that can't yet be tied to a service | **No.** Recorded in gold as "Other municipal / Indigenous transfers" and listed in the output as excluded |
| `pollution_pricing_returns` | Pollution pricing proceeds returned to people and businesses | **No.** Recorded in gold and listed as excluded. Not tax-funded and not a service; money moves from one payer to another |

A transfer to a municipality or Indigenous government that **can** be tied to a service (e.g. on-reserve education) is a `service` in that service's category.

## 2. Decisions

1. **Net actuarial losses** (pension remeasurement, $13.6B in 2025-26) are a real cost of running services. They are allocated across ministries in proportion to each ministry's operating expenses ("other expenses"), as a proxy for personnel cost until personnel by ministry is extracted.
2. **Transfers to municipalities and Indigenous governments:** traced to the service where the sources allow; otherwise `other_municipal_indigenous_transfers`, excluded from shares but kept and reported.
3. **Pollution pricing proceeds returned:** kept in gold, excluded from shares.
4. **Service categories:** as in section 4, shared with the provinces. The COFOG-to-service mapping is in `config/taxonomy/services.csv` and rendered for review in [`docs/cofog-to-services.md`](cofog-to-services.md).

## 3. Two levels, one grid

**Level 1, the grid (Volume I, Table 3.6).** This is ministries × payment type: major transfers, other transfers, other expenses and public debt charges, plus the net actuarial losses row. The cells add exactly to total expenses. Checks: each row adds to the ministry total in Note 6(f), each column to the Statement of Operations, and the grid to total expenses. Nothing is taken from two different cuts of the statements, so nothing can be counted twice.

**Level 2, the leaves.** Each cell is split into program lines where a source exists:

| Cell type | Split by | Source |
|---|---|---|
| Major transfers | Program: OAS, EI, CCB, CHT, CST, equalization, child care, CCBF, health agreements | Statement of Operations, Note 6(a), Table 3.7 (exact) |
| Other transfers | Program lines (grants, contributions, other transfer payments) | Volume II, by department |
| Other expenses | Ministry default service | `config/federal/ministry-services.csv` |
| Public debt charges | Debt Charges | Table 3.6 |

**Leaves add to their cell.** Volume II is departmental and expenditure-based; Volume I is consolidated and accrual-based. Whatever Volume II doesn't explain stays as a **residual leaf** with the ministry's default treatment for that cell type. Residual size is reported as a quality measure.

## 4. Service categories

| Service | COFOG | Typical federal sources | Typical provincial sources |
|---|---|---|---|
| Health | 07 | Dental Care Plan, First Nations and Inuit health, PHAC, CIHR | Health ministries, health authorities |
| Education | 09 | On-reserve education, student aid | K-12, post-secondary |
| Seniors' Benefits | 10.2 | OAS/GIS | Seniors' programs |
| Child and Family Benefits | 10.4 | Canada Child Benefit | Child and family services |
| Employment Insurance | 10.5 | EI benefits to persons | — |
| Social Assistance | 10 (rest) | Veterans, settlement services | Income assistance, disability support |
| Housing and Communities | 06, 10.6 | Housing programs not paid to provinces | Housing, community programs |
| Defence | 02 | National Defence | — |
| Public Safety and Justice | 03 | RCMP, CBSA, corrections, courts | Police, courts, corrections |
| Transportation | 04.5 | Transport Canada | Highways, transit |
| Economic Development and Research | 04 (rest), 01.4 | ISED, regional agencies, agriculture | Economic development, agriculture, resources |
| Environment | 05 | ECCC | Environment ministries |
| Culture and Recreation | 08 | Canadian Heritage | Culture, sport, tourism |
| International Affairs and Aid | 01.2 | Global Affairs | — |
| Government Administration | 01 (rest) | Central agencies, CRA, PSPC, Parliament | Finance, central agencies, legislature |
| Debt Charges | 01.7 | Public debt charges | Debt servicing |
| Municipal Transfers | — | — | Provincial transfers to municipalities whose use is unknown (provincial rule; see below) |
| Unidentified | — | Mixed-purpose residuals | Lines not split by function (e.g. Quebec "Other portfolios") |

**Provincial municipal transfers** stay a share category: counted in numerator and denominator, as decided 2026-11-22. This differs from the federal rule for unidentified municipal transfers, which excludes them. Review whether the provincial rule should match.

## 5. Pipeline

| Layer | What |
|---|---|
| bronze | Volume I (2025-26); Volume II (2025-26) for program detail |
| config | Table 3.6 spec; `config/federal/ministry-services.csv` (ministry defaults by cell type); `config/federal/leaves.csv` (major-transfer leaves and named carve-outs); `config/federal/program-services.csv` (Volume II program rules); `config/taxonomy/services.csv` |
| gold | `data/3_gold/federal-leaves.csv` (one row per leaf, with treatment, service and evidence) plus checks |
| publish | Federal shares = leaves with treatment service, financing or unidentified, rolled up by service. Excluded treatments are listed in the output's `_meta.excludedFromShares` |
| metrics | Share of federal expense classified to a specific service; amounts excluded by reason; residual sizes |

## 6. Status (2026-11-24)

- Built: Table 3.6 grid extraction (116 checks), major-transfer leaves, ministry defaults, net actuarial allocation, `data/3_gold/federal-leaves.csv`, and federal shares by service.
- Not yet: Volume II program leaves. The 2025-26 Volume II can't be fetched by script (the tpsgc-pwgsc.gc.ca server omits the "Entrust OV TLS Issuing RSA CA 2" intermediate certificate), so it needs a browser download into `data/1_bronze/federal/ca/2026-vol2-eng.pdf`. Until then, the Indigenous Services, Crown-Indigenous Relations and Housing/Infrastructure "other transfers" are `other_municipal_indigenous_transfers` (excluded), and Employment and Finance "other transfers" are `unidentified`.
