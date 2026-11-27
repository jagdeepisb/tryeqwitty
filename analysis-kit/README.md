# Executable analytical contract

Use [analysis bundle v1.2](../schemas/analysis-bundle-v1.2.json) and the [financial model schema](../schemas/financial-model-v1.2.json) from the same reviewed commit. The validator loads the schemas locally and accepts existing [v1.1 bundles](../schemas/analysis-bundle.json). Keep company data and results private. The [benchmarks](../benchmarks/README.md) contain synthetic input and expected figures.

```sh
python -m pip install -r analysis-kit/requirements.txt
python analysis-kit/validate.py analysis.json > calculations.json
python analysis-kit/to_report.py analysis.json report.json
python -m pip install -r report-kit/requirements.txt
python report-kit/render.py report.json --out output
```

The validator emits coverage and, for v1.2, a `financial_model` object with calculated and unavailable requests, formula versions, result units, input IDs, evidence IDs and linked gaps. It checks submitted scalar metric and valuation values against computed values. It derives detailed monthly cash, cap table and DCF results directly from the frozen inputs. The report bridge uses the verified results from that same bundle. Keep the bundle, its SHA-256 and the calculation output together for audit.

The v1.0 report schema and renderer still accept reports from either analytical version. Reports summarise calculations and link sources. The validation output carries the full schedules, ownership changes and sensitivity cells. See the [financial guide](../financial-analysis/guide.md) and [valuation guide](../valuation/guide.md) for basis, eligibility and withholding rules. Evidence accuracy, comparable relevance and the reasonableness of assumptions require analyst review.
