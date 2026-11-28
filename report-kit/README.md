# Eqwitty portable report kit

Generate an independent branded PDF, accessible HTML and a missing-information CSV from a validated assessment. The renderer works offline. It accepts structured report v1.3 and legacy report v1.0. v1.4 analytical bundles use the structured renderer and include the recorded research scope, source origins, question outcomes and corrections. [Research disclosure](../report-spec.md#v14-research-disclosure)

## Reference reports

All four examples are synthetic regression fixtures, not professional opinions or economically calibrated operating models. Harbour Ledger deliberately uses small cash and equity operands. For a separate commercially plausible illustrative decision note, see [financing decision](../examples/financing-decision.md). The two Cedar cases deliberately start from different evidence. The manufacturing pilot includes an inspection. The intake-only case has no source records.

| Example | PDF | HTML | Missing records | Input |
|---|---|---|---|---|
| Harbour Ledger, conditional financing | [PDF](reference/complete/assessment.pdf) | [HTML](reference/complete/assessment.html) | [CSV](reference/complete/missing-information.csv) | [Bundle](../benchmarks/report-complete-v1.3.json) |
| Juniper Workflows, recurring revenue | [PDF](reference/juniper/assessment.pdf) | [HTML](reference/juniper/assessment.html) | [CSV](reference/juniper/missing-information.csv) | [Bundle](../benchmarks/research-early-saas-v1.4.json) |
| Cedar Components, one-shift pilot | [PDF](reference/cedar-pilot/assessment.pdf) | [HTML](reference/cedar-pilot/assessment.html) | [CSV](reference/cedar-pilot/missing-information.csv) | [Bundle](../benchmarks/research-pilot-manufacturing-v1.4.json) |
| Cedar Components, intake only | [PDF](reference/sparse/assessment.pdf) | [HTML](reference/sparse/assessment.html) | [CSV](reference/sparse/missing-information.csv) | [Bundle](../benchmarks/report-sparse-v1.3.json) |

Download the HTML for linked evidence and financial inputs. The [published release](https://github.com/jagdeepisb/tryeqwitty/releases/latest) packages the financing, subscription and pilot examples with the actual release commit. In-tree example inputs use a zero commit sentinel.

## Generate a report

Clone the repository at one reviewed commit. Use Python 3.11+ and install WeasyPrint's platform dependencies, including Pango and HarfBuzz. The kit includes the fonts and their licences. [WeasyPrint installation](https://doc.courtbouillon.org/weasyprint/v68.0/first_steps.html) · [Fonts](fonts/README.md)

Run from the repository root.

```sh
python -m pip install -r report-kit/requirements.txt
python analysis-kit/to_report.py benchmarks/report-complete-v1.3.json report.json
python report-kit/render.py report.json --out output --bundle benchmarks/report-complete-v1.3.json
```

The output contains `assessment.pdf`, `assessment.html` and `missing-information.csv`. Use a fresh output directory per assessment. Run with `--html-only` to produce the HTML and CSV without WeasyPrint or its platform dependencies. Use the analysis-kit requirements for this fallback. Keep real company input, report JSON and outputs private.

Pass `--bundle` when the validated analytical bundle is available. The renderer checks the versioned projection and its disclosures against the original bundle before writing files. The bundle check uses the analysis kit from the same checkout. Standalone report input can still be rendered with schema validation.

The structured report uses deterministic results from the validated bundle and preserves the exact decimal strings. Money displays up to two decimal places and ratios and percentages up to four. The report shows very small nonzero values in scientific notation. The HTML exposes raw exhibit values and retains the complete operand register, while the PDF shows the associated input IDs. For v1.1 and v1.2 bundles, `--report-version 1.3` opts into this format. [v1.3 schema](schema-v1.3.json) · [v1.0 schema](schema.json) · [Report specification](../report-spec.md)

## Optional decision brief

For a structured report, add `--brief` to generate `decision-brief.html` and, unless `--html-only` is used, `decision-brief.pdf` alongside the unchanged full assessment and CSV. The brief removes exact repeated paragraphs and lower-priority unknown factor rows, and omits the detailed research-attempt table and monthly schedules. It retains the executive conclusion, coverage counts, all assessed and high-priority factors, risks, research limitations, financial summaries, requests and source records. Read it with the full assessment; it is not a substitute for the complete analytical record. No figures or evidence statuses are recalculated.

## Verify the export

Use Poppler to check the PDF and review every page visually. The test suite reconciles the numeric exhibits, checks the complete and sparse documents, confirms embedded fonts and checks source URLs and link targets.

```sh
EQWITTY_REQUIRE_PDF_CHECKS=1 python -m unittest discover -s tests
pdffonts output/assessment.pdf
pdfinfo -url output/assessment.pdf
pdftoppm -png output/assessment.pdf /tmp/eqwitty-page
```

## Publication quality

The reader-facing HTML and PDF omit technical provenance blocks; the original report JSON and analytical bundle retain all contract metadata. Evidence references link to descriptive source records, including IDs embedded in prose. Display punctuation is normalised without changing the original record. Run the publication regression tests and verify extracted PDF text, clickable annotations and actual rendered pages. See the [mandatory editorial rules](../report-spec.md#reader-facing-publication-quality-mandatory). Historical release artifacts remain immutable.
