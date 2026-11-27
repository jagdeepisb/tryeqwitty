# v1.4 research playbooks

Start with the identified company, the achieved commercial stage and the decision the reader needs to make. Record the stage evidence and why the declared objective represents the request. For an ambiguous stage, use `unknown` and identify the dated records that would resolve it. For a custom objective, use `other` and state a decision and testable conditions. Hybrid companies use the applicable routes for each material model.

The routing command prints the mandatory factors, priority floors, evidence requirements, counter-evidence tests and preferred sources for one assessment. It uses the public playbook catalogue at the pinned commit. [Playbook catalogue](../factor-library/research-playbooks-v1.4.json)

```sh
python analysis-kit/research_routing.py --stage pilot --models manufacturing --objective fundraising_readiness
```

## Route the assessment

| Achieved stage | Focus of the additional stage test |
|---|---|
| Concept | Customer problem, willingness to pay and a falsifiable validation test. |
| Development | Readiness, failed tests, acceptance criteria and cost to the next milestone. |
| Pilot | Pilot conditions, paid status, limitations and a credible path to conversion. |
| Early revenue | Recognised sales, collections and initial evidence of repeatability. |
| Repeatable growth | Cohort quality, incrementally acquired customers, concentration and contribution. |
| Mature | Sustainable cash after maintenance spend, normalisation and working capital requirements. |
| Unknown | Identify what records would determine the stage and qualify dependent conclusions. |

The objective adds its own decision test and can raise the priority of common factors. Investment tests decision-reversing evidence and terms. Fundraising readiness tests the use of funds and evidenced milestones. Mandate screening tests engagement criteria and exclusions. Valuation tests basis, eligibility and sensitivity. Strategic review ranks scoped alternatives against the binding constraint.

Business models determine the most useful evidence at that stage. Before revenue, SaaS tests workflow adoption and paid pilot conditions. Once trading, it tests recurring revenue and cohorts. A marketplace starts with commitments on both sides and moves to matching, net monetisation and resilience. Manufacturing moves from trials to effective capacity, working capital and supplier dependence. Lending starts with who originates and retains risk, then adds actual loan vintages, funding risk and loss-adjusted economics when relevant. Consumer businesses, biotech, deeptech, services and other models have their own evidence and failure tests in the catalogue.

## Select factors and ask questions

Use the union of the baseline, achieved stage, objective and model routes. When routes overlap, keep the highest minimum priority and reuse the evidence. Raise priority when company-specific facts make a question more consequential. Record material company-specific factors with their impact and one or more planned questions. A single specific question may address several factors.

- **Critical** factors can invalidate the decision, lawful operating perimeter or assessed financial basis.
- **High** factors can materially change a decision, financing need, valuation, timeline or objective.
- **Medium** factors affect confidence or a meaningful secondary choice.
- **Low** factors add context with limited decision effect.

Each applicable factor needs a question in `research_plan.questions`. Record a specific question, affected factors and claims, evidence and counter-evidence tests, downstream decision use, source route, priority inputs and completion criteria. Group related child questions with `parent_id`. Use `depends_on` only when the answer truly requires a completed upstream test. Where a required row is out of scope on the evidence, retain it as `not_applicable` and supply an exclusion rationale and source references. Missing information yields `unknown` and an appropriate request.

## Prioritise by expected informational value

Reserve resources for the required decisions, genuine prerequisites and challenge work. Within that scope, prioritise the work likely to change a decision, scenario or action. The ranking uses the following ordinal heuristic.

```text
priority = materiality × uncertainty × answerability × objective relevance ÷ estimated attempts
```

| Input | Meaning |
|---|---|
| Materiality | The highest priority of the linked factors. Low = 1, Medium = 2, High = 3, Critical = 4. |
| Uncertainty | 1 for reasonably established and worth confirming, 2 for incomplete, 3 for unresolved or actively disputed. |
| Answerability | 0 when no usable route is currently available, 1 when evidence is unlikely, 2 when credible but access is uncertain, 3 when the necessary evidence is readily accessible. |
| Objective relevance | 2 if a linked factor appears in the objective route, otherwise 1. |
| Estimated attempts | Expected number of distinct research actions to reach the stated completion condition. |

The validator outputs exact priorities and orders equal values by question ID. Complete prerequisites before claiming completion of dependent work. Use zero answerability to guide information requests and disclosure. Keep material unresolved factors visible even when their work stops. The ranking is a planning heuristic.

Declare a maximum number of attempts, an allowance reserved for corrective review, and a minimum priority for low-value deferrals. The catalogue gives adjustable screen, standard and deep examples. Each performed search, source open, document review or authorised request uses one action. Reuse its attempt ID when multiple questions benefit. An unsuccessful action still uses the budget. Reserve work must link to a correction. Stop when the condition is met, the necessary records or tools are unavailable, the remaining allowance is too small, or repeated work is unlikely to change the decision. Record the applicable stopping condition and what evidence could make further work worthwhile.

## Record actual work and completion

Declare which web, document and authorised private-request capabilities were available. Add one `research_attempts` row for each actual action with the date, action, target, support or counter-evidence intent, result, source IDs and scope note. Use the exact reviewed URL for a source open and `document name | version` for a document review. For a failed attempt, record the access or evidence outcome. A search hit can be recorded as a grade D lead. To use it as factual evidence, open the source or review an available copy. For private information outside access or permission, log the block and list the request.

Every planned question needs one outcome row in `research`, with the IDs of the actions actually used, reviewed evidence, reason, stopping condition and any information requests. A shared action is referenced by each question it genuinely informs. Link every entered source to a recorded attempt. Record dated captures as documents when reviewing an offline packet.

| Outcome | When to use it |
|---|---|
| Completed | Prerequisites are complete. Relevant reviewed evidence meets the stated distinct-origin minima and an executed counter-evidence test is recorded. Resolve contradictions that prevent completion for that question. |
| Partial | Some actual work was performed. The stated condition is incomplete and the reason remains visible. |
| Blocked | A tool or source is unavailable, the question needs private information, a prerequisite is unresolved, or material evidence is in conflict. |
| Deferred | The remaining ordinary budget is below the estimated cost, the question is below the declared priority threshold, or a prerequisite is unresolved. |

Set `min_origins` and `min_independent_origins` for the question before research. A primary reviewed document can establish a bounded company-reported finding. Set the necessary independent corroboration for stronger claims. An actual counter-test can confirm the finding, uncover opposition or record a documented search that found no responsive evidence.

## Count originating sources and handle contradictions

An origin represents the underlying producer or record. Assign a shared origin to reprints, syndicated releases, copies and different excerpts of the same underlying source. The validator normalises origin names, groups shared origins and rejects inconsistent origin assignments for the same canonical URL or offline publisher/title pair. A company-origin group cannot be used as independent A/B corroboration. Review lineage when sources use different URLs, titles or publishers. The validator checks the declared lineage, record consistency and distinct-origin counts.

Write the independent thesis in its own terms and link it to its planned tests. Use `corroborated` only when a completed relevant test yielded independent evidence. Use `provisional` when the case remains conditional and explain the limits. Use `unavailable` when the evidence does not support an independent conclusion. State what observable evidence would overturn the current assessment.

Keep supporting and opposing records for material disputed or contradicted claims. Link them to the thesis divergence, the actual question and the correction. Route corrections to scope, evidence, financial model, valuation or report, with the affected objects and actions. Add evidence review attempts to the relevant question as well as the correction. A resolved correction records rechecked objects. Material unresolved questions and challenges require relevant missing information of matching priority and a qualified decision. Unresolved material challenges block directly affected calculations and their recorded dependencies.

The validator checks structure and declared provenance. Reviewers still assess whether the recorded actions took place, the evidence is relevant, and the conclusion matches the documents. Reports disclose the capabilities and actions actually recorded. [Evidence discipline](evidence.md) · [Bundle schema](../schemas/analysis-bundle-v1.4.json) · [Benchmarks](../benchmarks/README.md)
