# Financial diligence and formula library

## v1.1 formula library

The calculator uses Decimal and accepts typed operands with unit, entity, period and basis. Rates are ratios (0.25 = 25%), not whole percentages; money amounts must be in the same currency and base units; months are explicit. No FX conversion is implicit. Inputs are observed company-reported/independent figures or explicitly labelled assumptions. Observed metrics must use observed inputs only. Scenario metrics must disclose assumptions. The calculator rejects missing operands, zero/negative required denominators and incompatible units/entity/period. Growth permits two distinct comparable periods with an explicit rationale; independently check equal duration and consistent definition. Runway is a simple cash/net monthly burn estimate, not a cash-flow forecast, and not applicable to non-positive burn.

| Formula ID | Definition |
|---|---|
| revenue_growth | (current revenue / prior revenue) − 1 |
| gross_margin | (revenue − COGS) / revenue |
| contribution_margin | (revenue − variable costs) / revenue |
| ebitda_margin | EBITDA / revenue |
| cac | acquisition spend / acquired customers |
| cac_payback | acquisition cost / monthly contribution per acquired customer |
| nrr | (opening recurring revenue + expansion − contraction − churn) / opening recurring revenue |
| grr | (opening recurring revenue − contraction − churn) / opening recurring revenue |
| take_rate | recognised marketplace revenue / GMV |
| utilisation | used capacity / available capacity |
| inventory_turns | annual COGS / average inventory |
| runway | unrestricted cash / positive monthly net burn |
| current_ratio | current assets / current liabilities |
| net_debt | interest-bearing debt − unrestricted cash |
| balance_sheet_gap | assets − liabilities − equity |
| cash_flow_gap | closing cash − opening cash − operating cash flow − investing cash flow − financing cash flow |

Reconciliation checklist: compare deck and model, actual vs forecast, revenue gross/net, P&L to balance sheet and cash flow, cap table vs financing terms, full horizon, working capital and tax. Explicitly classify every mismatch. A zero balance-sheet gap is a limited arithmetic check, not assurance. FX, consolidation, lease treatment, restricted cash and irregular periods require separate documented work. LTV, cohorts, debt covenant, risk-adjusted lending metrics and complex scenario cash flows require bespoke formulas with sourced inputs; they are not implemented in this initial calculator. Do not invent them merely to fill a section.

## v1.2 typed inputs and eligibility

Use the v1.2 schema and the [complete synthetic bundle](../benchmarks/financial-model-v1.2.json) for structure. The rules above describe the original v1.1 mode. For v1.2, declare one currency and accounting basis in `financial_model`. Use the profile's legal entity as the common measurement perimeter. Document consolidation, local GAAP and any reconciliations in scope. Supported bases are `ifrs`, `us_gaap`, `local_gaap` and `management_accrual`. Supply money in base currency units, proportions as decimal ratios (0.25 = 25%), counts and shares as whole units, and hours as measured. Supply a date (`YYYY-MM-DD`) for point-in-time amounts or inclusive dates (`YYYY-MM-DD/YYYY-MM-DD`) for flows and cohort windows. Use actual days for day ratios and a complete 12 months for annual metrics.

Each v1.2 input has a semantic `quantity`, a matching `unit`, currency for money, an entity, an accounting basis, a period, a source rationale and at least one registered evidence ID. Use `claim_ids` to link relevant claims when present. Locate each value or assumption in its supporting sources. An observed amount must come from a historical source and its period must end by the analysis date. Company-origin evidence retains its reported status. Forecasts, conditional financing and valuation rates use assumption inputs even when extracted from company materials. Scalar metrics use one basis throughout. Opening balances and the DCF bridge use dated observations, while cash projections and valuation results carry the scenario basis. Unresolved critical challenges on a used component, round, result, input, claim or source block the dependent calculation.

Use `unavailable` and specific `gap_ids` for a requested but unsupported calculation. Unavailable scalar rows require `value: null`. Unavailable model components take a rationale and gap IDs, and emit a null value. Omitting an optional model component leaves it outside the calculation request. Record an explicit sourced zero when a line really is zero. A scenario month requires all six drivers, and an empty `round_ids` explicitly records that no linked primary proceeds are scheduled.

| v1.2 formula ID | Calculation and period | Eligibility |
|---|---|---|
| `saas_arr` | Contracted recurring MRR × 12 at the measurement date | SaaS from early revenue. Exclude one-off services, usage without a recurring commitment and bookings. |
| `saas_logo_churn` | Customers lost from the opening cohort ÷ opening customers across the same window | SaaS from early revenue. Exclude customers acquired during the window. |
| `marketplace_match_rate` | Matched eligible requests ÷ eligible requests in the same market and period | Marketplace from pilot. Count unique requests once. |
| `manufacturing_first_pass_yield` | Good units on first pass ÷ units processed on first pass | Manufacturing from pilot. Use the same process perimeter and exclude reworked units from the numerator. |
| `manufacturing_cash_conversion_days` | Inclusive days × (average inventory ÷ COGS + average trade receivables ÷ credit sales − average trade payables ÷ credit purchases) | Manufacturing from early revenue. Same window and positive COGS and credit denominators. A negative cycle can occur. |
| `lending_net_charge_off_rate` | (Gross charge-offs − recoveries) ÷ average gross loan principal over 12 months | Lending from pilot with a positive matching loan book. Recoveries can exceed charge-offs. |
| `lending_par30` | Outstanding principal on loans more than 30 days past due ÷ gross outstanding principal at the measurement date | Lending from pilot. Use the entire outstanding balance of each affected loan and the same loan book. |
| `consumer_repeat_purchase_rate` | Repeat buyers ÷ eligible opening cohort buyers over a common observation window | Consumer from early revenue. Provide a consistent repeat and eligibility definition. |
| `services_billable_utilisation` | Billable hours ÷ available delivery hours over the same window | Services from pilot, within the declared hours capacity. |

For v1.2 scalar rows, `finance_metrics.py` lists exact quantities and units for each named operand. The retained formulas add business-model and period checks. NRR and GRR require SaaS cohort data from early revenue. Take rate requires marketplace fees and matched GMV from early revenue. Utilisation requires manufacturing from pilot. Annual inventory turns require manufacturing from early revenue. Growth uses non-overlapping comparable periods. Base business P&L metrics require operating evidence. Biotech, deeptech and other profiles can use common cash, financing and financial metrics where the required context exists.

### Linked cash flow, capital and runway

Every case uses the same opening unrestricted cash, minimum cash floor and number of months. Enter drivers, financing paths and a rationale for each of downside, base and upside. The first period starts the day after the analysis date. Subsequent bounds use monthly anniversaries of the analysis date, preserving month-end where applicable. Use nonnegative unlevered cash taxes, D&A and capex. Use a signed change in noncash operating working capital, positive when more cash is tied up.

- Operating cash before capex = EBIT − unlevered cash income tax + D&A − change in noncash operating working capital.
- FCFF = operating cash before capex − capex. Pre-round cash flow = FCFF + signed other cash flow. Other cash flow accounts for movements outside FCFF and linked primary proceeds, such as interest, debt principal or other separately evidenced flows.
- Cash flow after linked rounds adds only the primary cash from dated modeled rounds. Each case can include an ordered prefix of future rounds. Financing already reflected in observed cash cannot be added again.
- Closing cash rolls forward from opening cash by each month's net movement. Capital required is the maximum shortfall to the cash floor across opening and month-end balances, calculated before and after linked rounds. This is a minimum cash injection under those modeled flows, before any incremental financing costs.
- Runway is the completed months before the first balance strictly below the cash floor. A starting breach yields zero. If no breach appears, report the modeled months as a lower bound. Month-end schedules do not establish intra-month liquidity.

### Priced primary equity and dilution

Use a dated, fully diluted common-equivalent opening register with each holder and explicitly documented shares, including zeros for future investors. A single unallocated option pool may be included. Roll the rounds in chronological order. Terms on or before the analysis date are observed and later terms are assumptions. Document excluded instruments. If they materially affect ownership and cannot be reconciled to opening as-converted shares, withhold the result. The priced-round calculation covers primary common-equivalent shares, with option pool top-ups applied pre-money. Preference waterfalls, convertible/SAFE pricing, secondary transfers and issuance requiring share rounding need separate analysis.

- Issue price = pre-money equity value ÷ (prior fully diluted shares + pool top-up).
- For each subscription, new shares = primary cash ÷ issue price. The model checks exact whole-share issuance without rounding the issue price.
- Post-money equity value = pre-money equity value + primary cash. Post-close fully diluted shares include the opening positions, pool top-up and new shares.
- Ownership = holder's fully diluted shares ÷ corresponding share total. Ownership change is the after-minus-before share of ownership, including any subscription by that holder. Existing-share dilution = (post-close shares − prior shares) ÷ post-close shares. The round's cash can feed the same scenario month.

For the charge-off definition, see the [FDIC Quarterly Banking Profile glossary](https://www.fdic.gov/quarterly-banking-profile/quarterly-banking-profile-first-quarter-2026.pdf).
