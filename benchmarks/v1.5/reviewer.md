# Blinded decision-usefulness review

Read the case, its frozen reference key and the anonymised response. Review the decision independently of the other reviewer. Use the evidence and declared objective in the packet. Record a concise reason for each assessment.

| Criterion | Pass condition |
|---|---|
| Objective | The stated decision addresses the requested decision and gives an appropriate scoped disposition. |
| Evidence | The rationale explains at least one material fact, uncertainty or disagreement and how it affects the disposition. The cited source supports the reason. |
| Next step | The request identifies an actionable record, test or reconciliation that could address a material decision dependency. |

A missing response or rationale fails the corresponding criterion. A short answer can pass. Require a surfaced evidence gap for feasibility, authority, valuation or other claims where the record is insufficient. Mark a hard failure when a decision or free-text field asserts a material fact or transfer of work unsupported by the admitted evidence, conceals a material conflict, or misstates the performed work. Provide an exact reason for each hard failure. Use the frozen answer key and executed source record to adjudicate relevance.

Output one row per trial and case with `trial`, `case`, Boolean `objective`, `evidence` and `next_step` fields, a short `reason` and a `hard_failures` array of strings. Keep provider and model identity out of the review.
