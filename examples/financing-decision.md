# Financing decision: Alder Workflow (fictional)

**Question:** Would a proposed USD 400,000 round give a subscription software business enough time to reach its next financing milestone?

This is an illustrative decision note, not a real-company assessment, a benchmark result or an independently reviewed investment opinion. All inputs below are invented for teaching. Amounts are in USD, not thousands.

## Decision

The round would extend the base-case cash-floor runway from 10 to 18 completed months if the proceeds arrive immediately. In a higher-burn case, runway after the round falls to 12 months. A milestone planned for month 15 is therefore exposed to the downside. Before setting the raise size, reconcile unrestricted cash, verify the timing and cost of the milestone, and model a delayed close.

## Illustrative inputs

| Item | Amount | Basis |
|---|---:|---|
| Revenue, trailing 12 months | 1,050,000 | Illustrative recognised subscription revenue |
| Direct costs, same period | 315,000 | Illustrative hosting and delivery costs |
| Contracted monthly recurring revenue, at cutoff | 100,000 | Assumed recurring subscription charges, excluding one-time fees |
| Unrestricted opening cash | 600,000 | Assumed balance |
| Minimum cash floor | 100,000 | Assumed operating reserve |
| Monthly net cash outflow, base | 50,000 | Assumed constant net burn |
| Monthly net cash outflow, downside | 75,000 | Assumed higher net burn |
| Proposed primary equity proceeds | 400,000 | Conditional, assumed immediate close |
| Proposed pre-money equity value | 4,000,000 | Illustrative negotiated terms, not an independent valuation |

Reported gross margin on these hypothetical inputs is 70%: (1,050,000 minus 315,000) divided by 1,050,000. Annualised contracted recurring revenue at cutoff is 1,200,000. This differs from trailing recognised revenue, which covers the previous twelve months.

## Cash implications

Runway is the number of completed months with closing cash at or above the cash floor. With constant outflows, it equals the integer part of (opening cash plus conditional proceeds minus floor) divided by monthly outflow.

| Case | Without financing | With financing | Cash at month 15 after financing |
|---|---:|---:|---:|
| Base | 10 months | 18 months | 250,000 |
| Downside | 6 months | 12 months | -125,000 |

The downside needs an additional 225,000 to maintain the 100,000 floor at month 15, before financing fees or a contingency reserve. The negative closing balance is a mathematical funding gap, not a claim that the company can operate without cash.

At the proposed 4,000,000 pre-money equity value, the 400,000 primary round gives new investors 400,000 / 4,400,000 = 9.09% of post-money equity, assuming no option-pool increase, convertibles, secondary transfers or fees. This is a financing scenario, not a justified valuation.

## Records needed for a real decision

| Record | Why it matters |
|---|---|
| Dated bank reconciliation and restricted cash schedule | Verify the usable opening balance. |
| Monthly collections, payroll, hosting and other commitments | Replace constant net burn with a monthly cash model. |
| Signed subscription contracts and billing reconciliation | Verify recurring revenue and renewal exposure. |
| Dated milestone plan and spending schedule | Test whether month 15 is attainable. |
| Signed financing terms and fully diluted ownership | Test close timing, dilution and proceeds. |

No actual external research, company evidence or independent review was performed for this example. The [regression fixtures](../benchmarks/README.md) and [report kit](../report-kit/README.md) separately demonstrate the executable contracts.
