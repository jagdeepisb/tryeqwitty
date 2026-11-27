# Benchmarks
These are fictional structural/arithmetical fixtures, not company research. Sparse manufacturing: applicable factors unknown, zero assessed, no runway or valuation. Reported SaaS: gross margin 0.6 and runway 6 months from synthetic reported inputs, one partially assessed factor, qualified decision. Negative tests mutate fixtures to catch unsupported verification, missing factor, false zero, wrong calculation, wrong currency, assumed observed inputs, unresolved challenge and broken valuation range. Extend with real permissioned or synthetic adversarial datasets with known financial statements and independent research answer keys. Cross-agent trials should use identical documents, frozen date, search budget/depth, blind scoring and record claim accuracy, arithmetic, coverage, missed material risks, calibration and cost/time. No cross-agent performance claim until such trials are run.

Conflicting revenue: synthetic deck claims 100,000 versus independent fixture 80,000. Preserve dispute, withhold gross margin and qualify decision. Arbitrary illustrative 2×/3×/4× multiples on 80,000 yield 160,000/240,000/320,000 enterprise scenario values, not a market valuation. All fixture commit fields are zero sentinels; real runs must use the reviewed Git commit.


Use [acceptance-rubric.md](acceptance-rubric.md) for future independent cross-agent adjudication. The known-answer formula test covers all implemented calculator IDs. These tests establish deterministic arithmetic on synthetic operands only; no factual benchmark performance is claimed.

## v1.2 deterministic fixtures

| Fixture | Known answers |
|---|---|
| [Linked financial model](financial-model-v1.2.json) | First round price: USD 2; proceeds: USD 50; shares: 100 before the round, 150 after. Second round price: USD 3; total shares: 170 after. Downside capital gap: USD 300; runway: 4 completed months. In the base case the first round reduces the capital gap from USD 60 to USD 10 and increases runway from 12 to 22 months. Upside runway is at least 24 months. Base annual FCFF: USD 120 in each year. WACC: 10%; terminal growth: 2%; terminal value: USD 1,530; EV: USD 1,472.73; equity value: USD 1,442.73, rounded to cents. |
| [Sparse manufacturing](financial-sparse-v1.2.json) | No input qualifies for a numerical cash, dilution or valuation result. Model components, runway and the multiple-based valuation emit null and reference their missing information. |

The unit tests verify all nine DCF sensitivity cells and all new scalar formulas independently. Adversarial mutations cover unsupported stages and business models, unresolved sources, wrong units and cutoff dates, incompatible terms and financing paths, null handling and the existing report renderer.

## v1.3 report fixtures

The complete fixture exercises a disputed claim, a partially known competitor comparison, cash and dilution schedules, and DCF sensitivity. The sparse fixture exercises qualified decisions, unavailable results and named missing-information links. CI renders real PDFs, checks the reference HTML and CSVs, verifies the embedded brand fonts and link destinations, and compares every numeric exhibit to the validated results. [Complete bundle](report-complete-v1.3.json) · [Sparse bundle](report-sparse-v1.3.json) · [Reference outputs](../report-kit/README.md)

## v1.4 adaptive research fixtures

| Case | Differentiation and known result |
|---|---|
| [Early-revenue SaaS valuation](research-early-saas-v1.4.json) | Prioritises subscription economics and valuation eligibility. Eight planned questions yield two completed, two partial, three blocked and one deferred. Five captured evidence records represent four originating sources. The pricing dispute remains open and the valuation is unavailable. |
| [Manufacturing pilot fundraising](research-pilot-manufacturing-v1.4.json) | Prioritises pilot conditions, production readiness, capex and funding. Eight questions yield one completed, two partial, four blocked and one deferred. Independent inspection corroborates the scoped pilot. Cash and operating records remain open. |

Both cases use frozen synthetic documents and disclose zero web searches. Tests cover stage changes within a model, hybrid routes, exact priorities, shared attempts, false completion, duplicate origins, prerequisite cycles and priority-matched information requests. These cases test the contract under fixed conditions. [Cross-agent evaluation rubric](acceptance-rubric.md)
