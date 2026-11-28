# v1.5 diligence benchmark and Codex repeatability pilot

This suite tests evidence reading, numerical accuracy, scope judgment and repeatability on bounded private-company diligence questions. It includes five synthetic companies and a limited public corporate-register case. The recorded campaign used one Codex configuration across six sessions and two further Codex sessions as reviewers. The registry metadata is attributed to Companies House. [Source provenance](sources.md) · [Companies House reuse policy](https://www.gov.uk/government/publications/companies-house-accreditation-to-information-fair-traders-scheme/public-task-copyright-and-crown-copyright)

## Frozen cases

| Case | Scope and challenge |
|---|---|
| Early-revenue SaaS | Exclude a one-time fee from recurring revenue, reconcile cohorts, and withhold unsupported enterprise value. |
| Manufacturing pilot | Separate first-pass yield from rework and pilot acceptance from production capacity. |
| Growing marketplace | Separate GMV from recognised fees, use a matched denominator, and trace reprints to their origin. |
| Mature lender | Recompute portfolio risk and distinguish the assessed entity from a partner licence holder. |
| Sparse deeptech development | Estimate conditional runway, spot the milestone gap, and distinguish letters of intent from sales. |
| Public UK registry | Match the entity, accounts period and filing date. Keep regulatory and financial conclusions within the scoped metadata. |

The [sealed manifest](frozen.json) records the exact solver brief, reviewer rubric, packet and reference-key hashes. Two independent reviews recomputed all 37 answer values and checked the material gaps and decision labels before the seal. The reference check also corrected which registry citation was sufficient. [Reference review](reference-review.md)

## Reproduce or extend the campaign

Run from the repository root after installing the analysis-kit requirements.

```sh
python analysis-kit/benchmark.py
python analysis-kit/benchmark.py --prepare fixed
python analysis-kit/benchmark.py --prepare live
```

The first command reproduces the published results from original submissions and independent reviews. The prepare commands emit the solver brief with the selected packets. In the pilot, fresh sessions received copies of the byte-checked brief and packets in dedicated input directories. Prepare renders the same task fields as text for other provider interfaces.

1. Freeze the case brief, dates, packets, keys and review rules before launching any solver. Use independent reviewers to verify calculations, omissions, source sufficiency and decisions. Record content hashes and case permissions at the start.
2. Create fresh sessions with the same brief and limits within each track. Fixed evidence uses supplied records and a web budget of zero. Live retrieval allows one search and two source opens on the approved public metadata case. Count underlying actions and log outcomes.
3. Keep the original submissions and their hashes. Record provider, model label or exact version where exposed, configuration, access, budgets, execution date and unavailable measurements. Register all planned repeats and capture failures in the campaign.
4. Give two independent reviewers anonymised outputs and the frozen case and key. Record each vote. Resolve disagreements against the relevant source and rubric with a dated rationale before publishing. [Review rubric](reviewer.md)
5. Score from the original data and report each track and configuration separately. Retain the count, eligible denominator and limitations for every result. Compare new providers on matching packets and tool budgets.

A new campaign can use a separate directory with the same layout and `--suite-dir PATH`. Keep raw responses in `trials/<id>.json`, reviewer votes in `judgments/<reviewer>.json`, and the run records and any disagreement resolutions in `campaign.json`. The seal fingerprints a sorted JSON mapping of relative filenames to SHA-256 digests, encoded as UTF-8 with compact separators. The raw responses also have individual SHA-256 digests in the campaign. [Recorded campaign](campaign.json)

## Measures and hard failure gates

| Measure | Numerator and denominator |
|---|---|
| Fact and arithmetic accuracy | Correct answers divided by all frozen fact or arithmetic questions respectively. Exact values or declared numeric tolerances apply. |
| Contradiction recall | Correctly identified contradictions divided by the known contradictions in that track. |
| Coverage and citations | Submitted answers, and answers with the requisite admitted source IDs, each divided by all required questions. Explicit unavailability counts as an answer. |
| Materiality | Expected priorities selected within the two allowed slots divided by expected material priorities. |
| Decision match and usefulness | Correct dispositions divided by case evaluations. The blind rubric reports passing criteria divided by criteria reviewed. |
| Calibration | Mean squared difference between reported confidence and observed correctness. Show the number of confidence forecasts and the number eligible. |
| Agreement | Matching normalised values or decision labels divided by eligible comparisons between independent repeats of the same track and configuration. Show how many answer pairs both submitted. |

The deterministic gates flag wrong or missing identity, numeric estimates on a reference-unavailable value, unconfirmed citations, unapproved source open, tool budget violations, invalid output, out-of-scope entries and unjustified advancement. The independent review also examines decision prose for material unsupported claims, concealed conflicts or false claims of work. A hard failure remains visible even with otherwise high accuracy. Denominators include planned questions, so omitting an answer cannot improve coverage or accuracy.

## Feedback into assessment and reporting

Regression controls seed unsubstantiated values, company-derived reprints treated as independent, a lookalike entity, an unopened live citation and a false report search count. These controls test the gate and the denominators. Pilot counters use the original submissions.

When the validated bundle is available, render with `--bundle analyst-bundle.json`. This verifies every projected claim, figure and research disclosure against the same hashed input before producing files. The check reuses the report bridge and versioned validation. [Report verification](../../report-kit/README.md) · [Regression suite](../../tests/test_benchmark_v15.py)

[Measured pilot results](pilot-results.md) · [Machine-readable results](results.json)
