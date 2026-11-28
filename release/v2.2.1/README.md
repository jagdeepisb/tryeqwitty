# Eqwitty Open Diligence Standard v2.2.1

This patch improves the full assessment and optional decision brief without changing analytical bundle 1.4, financial model 1.2 or structured report 1.3. Both formats use clearer calculation and financing labels. The brief suppresses repeated paragraphs only when their evidence context matches. The analytical record retains the original identifiers and figures.

The [Monzo public-source note](../../examples/monzo-fy2026.md) illustrates a bounded financial and regulatory assessment, not an expert-reviewed or fully validated investment memo. Synthetic regression fixtures remain available through the [report kit](../../report-kit/README.md). The archived repeatability pilot and earlier immutable releases are unchanged.

## Conformance

The analytical-bundle check validates the supplied bundle against the release contract. The reconciled-report check additionally verifies the report against the bundle's deterministic projection. Neither establishes source truth or commercial judgment. Record the exact published source commit and retain the original bundle and report.

## Reproduce and verify

Use the exact [v2.2.1 release](https://github.com/jagdeepisb/tryeqwitty/releases/tag/v2.2.1) checkout. Install Python 3.11+, Pango, HarfBuzz and Poppler as described in the [report kit](../../report-kit/README.md).

```sh
python -m pip install -r report-kit/requirements.txt
EQWITTY_REQUIRE_PDF_CHECKS=1 python -m unittest discover -s tests
python release/verify_release.py build --out /tmp/eqwitty-v221
python release/verify_release.py verify --out /tmp/eqwitty-v221
```

Download the reference ZIP, manifest and checksums together. Verify the downloaded directory with the same command and exact release checkout. Regenerated PDF bytes may differ; inspect pages and compare semantic checks. Maintainer verification is not independent certification.

[Profile](profile.json) · [Release notes](RELEASE-NOTES.md) · [Compatibility](../COMPATIBILITY.md)
