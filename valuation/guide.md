# Valuation methodology

## v1.1 method selection

Start with value basis, objective, as-of date, entity perimeter and currency. Select approaches based on business model, commercial maturity and evidence—not on the ability to generate a number.

| Method | Suitable when | Required checks / disqualifiers |
|---|---|---|
| EV/revenue | Revenue observable and peers genuinely comparable | Recognised revenue, matching period and currency, comparable growth/margins/model, positive multiple; unsuitable for GMV/bookings |
| EV/EBITDA | Sustainable positive normalised EBITDA | Normalisation reconciliation, comparable capital intensity and accounting, EV not equity multiple |
| Net assets | Asset-backed or liquidation context | Current realisable asset and liability values; book values may not be fair values |
| DCF | Defensible free cash flow forecast and discount assumptions | Full-horizon drivers, reinvestment, tax, WACC, terminal growth below discount rate, sensitivity, cash/debt bridge |
| VC / milestone | Early venture with explicit exit scenarios | Exit assumptions, dilution, time, risk, target return; not a verified market price |
| Precedent transactions | Comparable terms actually known | Date, control premium, deal structure, geography, enterprise/equity basis, disclosed price |
| Probability-adjusted valuation | R&D / regulatory milestones | Evidence-based conditional probabilities and cost/timing dependencies; no false precision |

Initial deterministic implementation supports EV/revenue, EV/EBITDA, net-assets equity and EV-to-equity bridge. A range requires low/base/high assumptions and sensitivity; each bound must be recomputed from traceable operands. The validator checks numerical results and declared basis, not appropriateness of a comparable. Any unsupported approach may be described qualitatively, but do not represent a numerical result as validated by this kit. If private data or comparables are absent, report not estimable and the specific missing evidence. Preserve asking price separately. Never give a fairness opinion or personalised investment recommendation.

## v1.2 FCFF discounted cash flow

The v1.2 model supports a nominal, unlevered enterprise DCF on a named downside, base or upside case. It requires operating-stage evidence from early revenue onward and excludes lending from the modeled perimeter. An eligible forecast has at least two complete annual periods grouped from the linked monthly FCFF through the last year. The last year needs positive, normalised FCFF and a defensible steady state for reinvestment, risk and perpetual growth. Link the DCF to independent A/B evidence and explain case selection, operating maturity, terminal cash conversion and comparability of cost-of-capital inputs. Terminal growth and the cost of equity each require independent A/B support. Keep operating cash flows, discount rates and terminal growth in the same nominal currency context.

- WACC = cost of equity × (1 − debt weight) + pre-tax debt cost × (1 − marginal tax rate) × debt weight. Use target market-value capital weights and document the rationale. The formula supports debt and common equity. The debt weight is in [0, 1), the tax rate is in [0, 1], equity cost is positive, and debt cost is positive when debt has positive weight.
- Sum twelve monthly FCFF amounts for each explicit year. Discount each year-end cash flow by (1 + WACC) to the power of its year number.
- Terminal value at the last year-end = final annual FCFF × (1 + growth) ÷ (WACC − growth). WACC must be positive and terminal growth greater than −100% and lower than WACC in every sensitivity cell.
- Enterprise value of operations = present value of explicit FCFF plus present value of terminal value. Equity value = enterprise value + excess nonoperating cash − interest-bearing debt + net other noncash equity bridge adjustments. Source every bridge line at the cutoff, including supported zero adjustments. Cash must be part of unrestricted opening cash and exclude liquidity needed to run the business.
- Supply low and high assumptions that strictly bracket base WACC and terminal growth. The 3×3 sensitivity recalculates enterprise and equity values using the same cash flows and bridge. Each cell is conditional on that scenario. A separate presentation of a valuation range requires an explicitly supported range of assumptions.

The v1.2 validator also retains the v1.1 multiple and bridge methods with stronger quantity, stage and period checks. EV multiples use observed full-year recognised revenue or normalised EBITDA and an independently supported comparable-multiple assumption. The denominator and multiple use the same reference window. Standalone EV bridges and net-assets calculations use analysis-date operands with independent evidence for enterprise value or realisable assets and settlement liabilities. Use the v1.2 unavailable status and link the exact gap when a method lacks eligible inputs.

For the FCFF, WACC and terminal-value convention, see [Aswath Damodaran's valuation notes](https://pages.stern.nyu.edu/adamodar/pdfiles/eqnotes/dcfallA.pdf).
