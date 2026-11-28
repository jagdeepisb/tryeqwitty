<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/banner-light.svg">
    <img src="assets/banner-light.svg" alt="eqwitty. | Open Diligence Standard" width="900">
  </picture>
</p>

# Eqwitty Open Diligence Standard

Use this standard to assess a private company from a pitch deck, financial records or public sources. It connects each conclusion to evidence, calculates the financial measures the inputs support and identifies the records needed for the next decision. Eqwitty maintains the standard and a separate [hosted platform](https://tryeqwitty.com).

[Evaluation prompt](prompts/evaluate.md) · [Published release](https://github.com/jagdeepisb/tryeqwitty/releases/latest) · [Code license](LICENSE) · [Methodology license](NOTICE.md)

## Start an assessment

Give an AI agent the [evaluation prompt](prompts/evaluate.md), the decision you need to make and the company records you have permission to share. Use the commit attached to the latest published release throughout the assessment. Research and evidence review happen before the offline tools validate the inputs, calculate eligible metrics and render the memo.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/workflow-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/workflow-light.svg">
    <img src="assets/workflow-light.svg" alt="Identify the business, investigate evidence, reconcile financials, challenge findings and verify the report." width="900">
  </picture>
</p>

[Agent instructions](AGENT.md) · [Evaluation protocol](evaluation-protocol.md) · [Execution and evidence requirements](methodology/execution.md)

## See the method in use

- [Monzo: growth, earnings quality and regulatory risk](examples/monzo-fy2026.md). A scoped public-source decision note on a real private banking group, with calculations and a regulatory record. AI-assisted, not independently expert-reviewed.
- [Alder Workflow: sizing a financing round](examples/financing-decision.md). A fictional worked example of cash runway and dilution.

The [report kit](report-kit/README.md) contains synthetic regression fixtures and instructions for generating reports. These test the software rather than establish investment judgment. The published release archive includes full assessments and decision briefs.

## Technical reference

| AREA | DOCUMENTATION |
| :--- | :--- |
| Evidence and research | [Evidence rules](methodology/evidence.md) · [Research playbooks and adaptive depth](methodology/research-playbooks.md) |
| Material factors | [Factor library](factor-library/factors.json) |
| Financial analysis | [Financial guide](financial-analysis/guide.md) · [Financial model schema](schemas/financial-model-v1.2.json) |
| Valuation | [Valuation guide](valuation/guide.md) |
| Analytical contract | [Analytical bundle schema](schemas/analysis-bundle-v1.4.json) · [Validator and report bridge](analysis-kit/README.md) |
| Structured reporting | [Report specification](report-spec.md) · [Offline renderer](report-kit/README.md) |
| Benchmarks | [Synthetic benchmarks](benchmarks/README.md) · [Cross-agent acceptance rubric](benchmarks/acceptance-rubric.md) |
| Release | [Release conformance](release/v2.2.0/README.md) · [Compatibility and migration](release/COMPATIBILITY.md) · [Change history](CHANGELOG.md) |

## What has been tested

The executable checks reconcile calculations and report contents against supplied inputs. The archived November 2026 pilot measures repeatability on six fixed cases and one repeated registry lookup using a single Codex configuration. Its acceptance thresholds were retrospective; no baseline comparison, cross-model evaluation or human expert validation is documented. [Pilot data and limitations](benchmarks/v1.5/pilot-results.md) · [Next evaluation requirements](benchmarks/prospective-evaluation.md).

## Run the manufacturing example

```sh
python -m pip install -r report-kit/requirements.txt
python -m unittest discover -s tests
python analysis-kit/research_routing.py --stage pilot --models manufacturing --objective fundraising_readiness
python analysis-kit/validate.py benchmarks/research-pilot-manufacturing-v1.4.json
python analysis-kit/to_report.py benchmarks/research-pilot-manufacturing-v1.4.json /tmp/eqwitty-report.json
python report-kit/render.py /tmp/eqwitty-report.json --out /tmp/eqwitty-report --bundle benchmarks/research-pilot-manufacturing-v1.4.json
```
The renderer bundles its licensed fonts. Install the platform dependencies in the report kit instructions to create PDFs. To use a v1.1 or v1.2 bundle with the structured renderer, pass `--report-version 1.3` to the report bridge. [Report kit](report-kit/README.md)

Recompute the stored v1.5 pilot results offline with `python analysis-kit/benchmark.py`. The pilot uses the existing v1.4 analytical contract.

## Governance and licensing

MIT covers the original code. CC BY 4.0 covers the original methodology. Third-party materials and brand rights are subject to the applicable notices.

[Licensing and attribution](NOTICE.md) · [Contributing](CONTRIBUTING.md) · [Governance](GOVERNANCE.md)

---

**eqwitty.** · [tryeqwitty.com](https://tryeqwitty.com)

Informational analysis, not investment advice.
