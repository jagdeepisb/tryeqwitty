# Eqwitty Open Diligence Standard
Open, tool-agnostic methodology and offline report generation for private companies. Maintained by [Eqwitty](https://tryeqwitty.com), distinct from the hosted platform.

## Start here
- [Canonical agent prompt](prompts/evaluate.md) and [agent instructions](AGENT.md)
- [Evaluation protocol](evaluation-protocol.md) and [detailed execution gates](methodology/execution.md)
- [Evidence rules](methodology/evidence.md), [factor library](factor-library/factors.json), [financial guide](financial-analysis/guide.md), [valuation guide](valuation/guide.md)
- [v1.1 analytical bundle schema](schemas/analysis-bundle.json), [validator and report bridge](analysis-kit/README.md)
- [Report specification](report-spec.md), [v1.0 offline renderer](report-kit/README.md)
- [Synthetic benchmarks](benchmarks/README.md), [cross-agent acceptance rubric](benchmarks/acceptance-rubric.md), [change history](CHANGELOG.md)

## Run an evaluation
Choose a reviewed commit or release and pin all files to it. Attach authorised company materials to an AI agent, specify the decision and give it the canonical prompt. Require actual research, evidence registers, calculation operands, qualified conclusions, challenges and missing information. Use the validator, bridge and renderer when tools permit; preserve the bundle. The kit does not itself conduct web research or guarantee factual accuracy.

## Execute the synthetic benchmark
```sh
python -m pip install -r analysis-kit/requirements.txt
python -m unittest discover -s tests
python analysis-kit/validate.py benchmarks/reported-saas.json
python analysis-kit/to_report.py benchmarks/reported-saas.json /tmp/eqwitty-report.json
python report-kit/render.py /tmp/eqwitty-report.json --out /tmp/eqwitty-report --html-only
```
Install licensed Space Grotesk and DM Sans and WeasyPrint dependencies for actual PDF rendering; see report kit instructions. The examples are fictional, not actual evaluations. The original v1.0 renderer remains compatible; no hosted app score or exact app format is asserted. No licence has been selected; public availability alone does not grant redistribution rights. Contact the maintainer for permission where necessary.
