# Financial diligence and formula library v1.1
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
