# Executable analytical contract

Use the v1.4 analysis bundle schema and v1.2 financial model schema from the same reviewed commit. The validator loads the schemas locally and accepts v1.1 through v1.4 bundles. [v1.4 analysis schema](../schemas/analysis-bundle-v1.4.json) · [Financial model schema](../schemas/financial-model-v1.2.json). Keep company data and results private. The [benchmarks](../benchmarks/README.md) contain synthetic input and expected figures.

```sh
python -m pip install -r analysis-kit/requirements.txt
python analysis-kit/validate.py analysis.json > calculations.json
python analysis-kit/to_report.py analysis.json report.json
python -m pip install -r report-kit/requirements.txt
python report-kit/render.py report.json --out output --bundle analysis.json
```

The validator emits coverage and, for v1.2 and later, a `financial_model` object with calculated and unavailable requests, formula versions, result units, input IDs, evidence IDs and linked gaps. It checks submitted scalar metric and valuation values against computed values. It derives detailed monthly cash, cap table and DCF results directly from the frozen inputs. The report bridge uses the verified results from that same bundle. Keep the bundle, its SHA-256 and the calculation output together for audit.

A v1.3 or v1.4 bundle produces the structured report by default. Older bundles retain their v1.0 report format unless you pass `--report-version 1.3`. The v1.4 validation result adds `research_coverage` with selected factors, exact question priorities, actual attempts, budget use, originating sources and material unresolved issues. Evidence relevance and factual accuracy require reviewer judgement. [Research playbooks](../methodology/research-playbooks.md) · [Reference reports](../report-kit/README.md)

Use `python analysis-kit/benchmark.py` to verify the v1.5 input seal and recompute the pilot from the original submissions and reviews. Use `--prepare fixed` or `--prepare live` to prepare a solver brief with the corresponding packet. [Benchmark methodology](../benchmarks/v1.5/README.md)

For a published assessment, record the source commit of the selected release in the v1.4 bundle. Run `python analysis-kit/conformance.py analysis.json --report report.json` to validate the declared version, commit and report reconciliation. [Conformance levels](../release/v2.2.0/README.md)
