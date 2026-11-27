# Valuation methodology v1.1
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
