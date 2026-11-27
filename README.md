# Eqwitty Open Diligence Standard
Open, tool-agnostic methodology and offline report generation for private companies. Maintained by [Eqwitty](https://tryeqwitty.com), distinct from the hosted platform.

## Start here
- [Canonical agent prompt](prompts/evaluate.md) and [agent instructions](AGENT.md)
- [Evaluation protocol](evaluation-protocol.md) and [detailed execution gates](methodology/execution.md)
- [Evidence rules](methodology/evidence.md), [factor library](factor-library/factors.json), [financial guide](financial-analysis/guide.md), [valuation guide](valuation/guide.md)
- [Research playbooks and adaptive depth](methodology/research-playbooks.md), [v1.4 analytical bundle schema](schemas/analysis-bundle-v1.4.json), [financial model schema](schemas/financial-model-v1.2.json), [validator and report bridge](analysis-kit/README.md)
- [Report specification](report-spec.md), [v1.3 offline renderer and reference reports](report-kit/README.md)
- [Synthetic benchmarks](benchmarks/README.md), [cross-agent acceptance rubric](benchmarks/acceptance-rubric.md), [change history](CHANGELOG.md)

The v1.5 benchmark includes sealed case packets, independent reference checks and a measured fixed-evidence and live-retrieval pilot. [Benchmark methodology](benchmarks/v1.5/README.md) · [Pilot results](benchmarks/v1.5/pilot-results.md)

## Run an evaluation
Choose a reviewed commit or release and pin all files to it. Attach authorised company materials to an AI agent, specify the decision and give it the canonical prompt. Require actual research, evidence registers, calculation operands, qualified conclusions, challenges and missing information. Use the validator, bridge and renderer when tools permit; preserve the bundle. The kit does not itself conduct web research or guarantee factual accuracy.

## Execute a v1.4 research benchmark
```sh
python -m pip install -r report-kit/requirements.txt
python -m unittest discover -s tests
python analysis-kit/research_routing.py --stage pilot --models manufacturing --objective fundraising_readiness
python analysis-kit/validate.py benchmarks/research-pilot-manufacturing-v1.4.json
python analysis-kit/to_report.py benchmarks/research-pilot-manufacturing-v1.4.json /tmp/eqwitty-report.json
python report-kit/render.py /tmp/eqwitty-report.json --out /tmp/eqwitty-report --bundle benchmarks/research-pilot-manufacturing-v1.4.json
```
The renderer bundles its licensed fonts. Install the platform dependencies in the report kit instructions to create PDFs. Both example assessments are fictional. To use a v1.1 or v1.2 bundle with the structured renderer, pass `--report-version 1.3` to the report bridge. [Report kit](report-kit/README.md)

Recompute the stored v1.5 pilot results offline with `python analysis-kit/benchmark.py`. The pilot uses the existing v1.4 analytical contract.
