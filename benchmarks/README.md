# Benchmarks
The financial examples are deliberately simplified regression fixtures for arithmetic and missing-data handling. They are not commercially calibrated examples. The separate [November 2026 pilot](v1.5/pilot-results.md) measures repeatability on a fixed set of questions.

| Early contract example | Expected result |
|---|---|
| [Manufacturing intake](sparse-manufacturing.json) | No source records. Runway and enterprise value are unavailable. |
| [Reported SaaS accounts](reported-saas.json) | Reported gross margin of 60% and six months of runway at the stated burn. Cash and revenue quality are partially assessed. |
| [Conflicting revenue](conflicting-revenue.json) | The company reports USD 100,000 and the second sales record gives USD 80,000. Gross margin is withheld. Illustrative multiples of 2, 3 and 4 on the latter amount give scenarios of USD 160,000, 240,000 and 320,000. |

Example bundles use zeroes in the source-commit field. Use the reviewed commit for a company assessment. [Evaluation rubric](acceptance-rubric.md)

## v1.2 deterministic fixtures

| Fixture | Known answers |
|---|---|
| [Linked financial model](financial-model-v1.2.json) | First round price: USD 2; proceeds: USD 50; shares: 100 before the round, 150 after. Second round price: USD 3; total shares: 170 after. Downside capital gap: USD 300; runway: 4 completed months. In the base case the first round reduces the capital gap from USD 60 to USD 10 and increases runway from 12 to 22 months. Upside runway is at least 24 months. Base annual FCFF: USD 120 in each year. WACC: 10%; terminal growth: 2%; terminal value: USD 1,530; EV: USD 1,472.73; equity value: USD 1,442.73, rounded to cents. |
| [Sparse manufacturing](financial-sparse-v1.2.json) | No input qualifies for a numerical cash, dilution or valuation result. Model components, runway and the multiple-based valuation emit null and reference their missing information. |

The unit tests verify all nine DCF sensitivity cells and all new scalar formulas independently. Adversarial mutations cover unsupported stages and business models, unresolved sources, wrong units and cutoff dates, incompatible terms and financing paths, null handling and the existing report renderer.

## v1.3 report fixtures

The complete fixture exercises a disputed claim, a partially known competitor comparison, cash and dilution schedules, and DCF sensitivity. The sparse fixture exercises qualified decisions, unavailable results and named missing-information links. CI renders real PDFs, checks archived HTML integrity, fresh exports and the reference CSVs, verifies the embedded brand fonts and link destinations, and compares every numeric exhibit to the validated results. [Complete bundle](report-complete-v1.3.json) · [Sparse bundle](report-sparse-v1.3.json) · [Reference outputs](../report-kit/README.md)

## v1.4 adaptive research fixtures

| Case | Differentiation and known result |
|---|---|
| [Early-revenue SaaS valuation](research-early-saas-v1.4.json) | Prioritises subscription economics and valuation eligibility. Four questions are partially answered, three are blocked and one is deferred. Neither the ownership question nor the recurring-revenue question is complete. Five captured evidence records represent four originating sources. The pricing dispute remains open and the valuation is unavailable. |
| [Manufacturing pilot fundraising](research-pilot-manufacturing-v1.4.json) | Prioritises pilot conditions, production readiness, capex and funding. Eight questions yield one completed, two partial, four blocked and one deferred. Independent inspection corroborates the scoped pilot. Cash and operating records remain open. |

Both cases use frozen synthetic documents and disclose zero web searches. Tests cover stage changes within a model, hybrid routes, exact priorities, shared attempts, false completion, duplicate origins, prerequisite cycles and priority-matched information requests. These cases test the contract under fixed conditions. [Cross-agent evaluation rubric](acceptance-rubric.md)

## v1.5 Codex repeatability pilot

Six sealed cases cover SaaS, manufacturing, marketplace, lending, deeptech and a public corporate-register check. Six sessions of one Codex configuration produced the submissions. Two other Codex sessions reviewed masked responses. [Methodology and cases](v1.5/README.md) · [Measured pilot](v1.5/pilot-results.md)

## Future evaluation

The existing pilot is a descriptive repeatability baseline. It is not a prospective acceptance test or evidence of model superiority. Follow the [prospective evaluation requirements](prospective-evaluation.md) before making broader performance claims.
