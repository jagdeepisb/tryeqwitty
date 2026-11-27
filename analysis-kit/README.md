# Executable analytical contract

Use the v1.3 analysis bundle schema and v1.2 financial model schema from the same reviewed commit. The validator loads the schemas locally and accepts v1.1 and v1.2 bundles. [v1.3 analysis schema](../schemas/analysis-bundle-v1.3.json) · [Financial model schema](../schemas/financial-model-v1.2.json) · [v1.1 schema](../schemas/analysis-bundle.json). Keep company data and results private. The [benchmarks](../benchmarks/README.md) contain synthetic input and expected figures.

```sh
python -m pip install -r analysis-kit/requirements.txt
python analysis-kit/validate.py analysis.json > calculations.json
python analysis-kit/to_report.py analysis.json report.json
python -m pip install -r report-kit/requirements.txt
python report-kit/render.py report.json --out output
```

The validator emits coverage and, for v1.2 and v1.3, a `financial_model` object with calculated and unavailable requests, formula versions, result units, input IDs, evidence IDs and linked gaps. It checks submitted scalar metric and valuation values against computed values. It derives detailed monthly cash, cap table and DCF results directly from the frozen inputs. The report bridge uses the verified results from that same bundle. Keep the bundle, its SHA-256 and the calculation output together for audit.

A v1.3 bundle produces the structured report by default. Existing bundle versions retain their v1.0 report format unless you pass `--report-version 1.3`. The renderer accepts both report formats. The v1.3 PDF includes financial and valuation exhibits, and the HTML includes the input register. [Reference reports](../report-kit/README.md). See the [financial guide](../financial-analysis/guide.md) and [valuation guide](../valuation/guide.md) for basis, eligibility and withholding rules. Evidence accuracy, comparable relevance and the reasonableness of assumptions require analyst review.
