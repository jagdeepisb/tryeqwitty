# November 2026 cross-agent pilot

Six fresh Codex sessions ran on 27 November 2026. Three fixed-evidence sessions each evaluated six cases. Three live-retrieval sessions each evaluated the same narrowly scoped Companies House registry task. Raw submissions, masked decisions and the input seal are retained. [Campaign metadata](campaign.json) · [Frozen inputs](frozen.json) · [Raw trial outputs](trials) · [Blinded judgments](judgments)

| Measure | Fixed evidence | Live retrieval |
|---|---:|---:|
| Trial cases | 18 | 3 |
| Factual answers correct | 60/60 | 18/18 |
| Arithmetic answers correct | 36/36 | 3/3 |
| Contradictions found | 15/15 | No eligible contradictions |
| Required answers supplied | 111/111 | 21/21 |
| Answers with required admitted citations | 111/111 | 21/21 |
| Material priorities selected | 36/36 | 6/6 |
| Dispositions matched | 18/18 | 3/3 |
| Decision-usefulness criteria passed | 54/54 | 9/9 |
| Trials clearing hard failure gates | 3/3 | 3/3 |
| Pairwise answer agreement | 111/111 | 21/21 |
| Pairwise disposition agreement | 18/18 | 3/3 |
| Brier mean with confidence forecasts scored | 0.000048 with 111/111 | 0.000038 with 21/21 |
| Recorded web actions | 0 | 9 |

Both independent reviewers agreed on all 84 criterion and gate votes across 21 case evaluations. All live logs recorded one query and both approved official source opens. The registry case had seven correct answers in every fixed and live session. [Machine-readable scores](results.json) · [Scoring method](README.md)

## Interpretation and limits

These counts describe six independent runs of one inherited Codex configuration. The exact model build, token use and comparable wall time were unavailable. Claude and Gemini had no configured trial access. The decision reviewers were separate Codex sessions working with masked responses.

The same six packets recur across the three fixed-evidence sessions, so the 111 scored answers are clustered by case and solver. The live evidence covers one public registry case. The priority questions offer a closed set of choices. All forecasted answers were correct in this sample, so the observed Brier means mainly reflect confidence on successful items. The pilot supports a narrow repeatability finding within these tasks. Comparative provider quality, broader case performance and calibration on errors remain unmeasured.

The pre-run review improved citation sufficiency for the registry case and clarified the marketplace origin question. Regression tests exercise hard failures and detect a report with altered numerical disclosure even when its structure is valid. [Reference review](reference-review.md) · [Report audit](../../report-spec.md#v15-bundle-reconciliation)
