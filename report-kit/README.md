# Eqwitty portable report kit

Generate an independent branded PDF, accessible HTML and a missing-information CSV from a validated assessment. The renderer works offline. It accepts structured report v1.3 and legacy report v1.0.

## Reference reports

Both assessments use fictional companies and figures.

| Case | PDF | HTML | Missing information | Input bundle |
|---|---|---|---|---|
| Harbour Ledger, full financial exhibits | [PDF](reference/complete/assessment.pdf) | [HTML](reference/complete/assessment.html) | [CSV](reference/complete/missing-information.csv) | [Bundle](../benchmarks/report-complete-v1.3.json) |
| Cedar Components, sparse evidence | [PDF](reference/sparse/assessment.pdf) | [HTML](reference/sparse/assessment.html) | [CSV](reference/sparse/missing-information.csv) | [Bundle](../benchmarks/report-sparse-v1.3.json) |

Download the HTML file and open it in a browser for table navigation, linked evidence, linked gaps and the full operand register. The PDF includes source links, embedded Space Grotesk and DM Sans, and the monthly cash appendix when data supports it. The synthetic example bundles use a zero commit sentinel. Real assessments should use the reviewed standard's commit.

## Generate a report

Clone the repository at one reviewed commit. Use Python 3.11+ and install WeasyPrint's platform dependencies, including Pango and HarfBuzz. The kit includes the fonts and their licences. [WeasyPrint installation](https://doc.courtbouillon.org/weasyprint/v68.0/first_steps.html) · [Fonts](fonts/README.md)

Run from the repository root.

```sh
python -m pip install -r report-kit/requirements.txt
python analysis-kit/to_report.py benchmarks/report-complete-v1.3.json report.json
python report-kit/render.py report.json --out output
```

The output contains `assessment.pdf`, `assessment.html` and `missing-information.csv`. Use a fresh output directory per assessment. Run with `--html-only` to produce the HTML and CSV without WeasyPrint or its platform dependencies. Use the analysis-kit requirements for this fallback. Keep real company input, report JSON and outputs private.

The structured report uses deterministic results from the validated bundle and preserves the exact decimal strings. Money displays up to two decimal places and ratios and percentages up to four. The report shows very small nonzero values in scientific notation. The HTML exposes raw exhibit values and retains the complete operand register, while the PDF shows the associated input IDs. For v1.1 and v1.2 bundles, `--report-version 1.3` opts into this format. [v1.3 schema](schema-v1.3.json) · [v1.0 schema](schema.json) · [Report specification](../report-spec.md)

## Verify the export

Use Poppler to check the PDF and review every page visually. The test suite reconciles the numeric exhibits, checks the complete and sparse documents, confirms embedded fonts and checks source URLs and link targets.

```sh
EQWITTY_REQUIRE_PDF_CHECKS=1 python -m unittest discover -s tests
pdffonts output/assessment.pdf
pdfinfo -url output/assessment.pdf
pdftoppm -png output/assessment.pdf /tmp/eqwitty-page
```
