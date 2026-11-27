# Eqwitty Open Diligence Standard (v1.0)

Open, tool-agnostic methodology and offline report renderer for evaluating unlisted startups and private companies. Maintained by [Eqwitty](https://tryeqwitty.com) and distinct from the hosted Eqwitty platform.

## Repository contents

- `evaluation-protocol.md`: 11-stage private company diligence protocol (scope, claim extraction, independent thesis and reconciliation, material factors, specialist research, financial diligence, evidence-led assessment, valuation, synthesis, red-team challenge, and missing-information register).
- `report-spec.md`: Investment memo structure, typography, colour palette, and export integrity rules.
- `report-kit/`: Standalone offline Python renderer (`render.py`), JSON schema (`schema.json`), example fixture (`example.json`), and dependencies (`requirements.txt`).
- `tests/test_public_report_kit.py`: Unit tests validating schema rules, HTML escaping, CSV formula neutralisation, and section ordering.

## Quick start with an AI agent

1. Copy the v1.0 prompt from [tryeqwitty.com/agents](https://tryeqwitty.com/agents).
2. Attach authorised company materials (pitch deck, financial model, investor memo, cap table, or data room files).
3. Specify your evaluation objective. The prompt instructs your AI agent to read `evaluation-protocol.md` and `report-spec.md` directly from this repository.

## Running the offline PDF kit

```sh
cd report-kit
python -m pip install -r requirements.txt
python render.py example.json --out ../output
```

See `report-kit/README.md` for font setup (Space Grotesk and DM Sans) and `--html-only` usage.
