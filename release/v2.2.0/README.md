# Eqwitty Open Diligence Standard v2.2.0

This backward-compatible release adds an optional decision brief to the existing full assessment. The full report, analytical bundle, financial model and benchmark retain their prior formats. The brief keeps the decision, coverage, assessed and high-priority factors, financial summaries, gaps and source links; it omits detailed schedules, repeated paragraphs and lower-priority unknown factor rows. Read it with the full report.

The reference archive contains complete and brief PDFs and HTML, inputs, calculation outputs, request lists and automated PDF verification. The public financing example illustrates plausible cash and financing amounts; the older regression cases deliberately use simplified operands. Neither is an expert opinion about a real company.

The November 2026 pilot remains a descriptive repeatability measurement, with retrospective thresholds. [Prospective evaluation requirements](../../benchmarks/prospective-evaluation.md) define the conditions for broader claims; no new human-reviewed or cross-provider campaign has been completed.

Use the [profile](profile.json) at the published tag. The optional `--brief` flag in the [report kit](../../report-kit/README.md#optional-decision-brief) produces the additional files. Automated checks do not replace visual review or independent review of source relevance and commercial judgment. [Release notes](RELEASE-NOTES.md).

## Conformance

The analytical-bundle check validates the supplied bundle against the release contract. The reconciled-report check additionally verifies the report against the bundle's deterministic projection. Neither checks whether sources are true or judgments commercially sound.

## Reproduce and verify v2.2.0

Use the exact [v2.2.0 release](https://github.com/jagdeepisb/tryeqwitty/releases/tag/v2.2.0) checkout, not a different tag. Install Python 3.11+, Pango, HarfBuzz and Poppler as described in the [report kit](../../report-kit/README.md).

```sh
python -m pip install -r report-kit/requirements.txt
EQWITTY_REQUIRE_PDF_CHECKS=1 python -m unittest discover -s tests
python release/certify.py build --out /tmp/eqwitty-v22
python release/certify.py verify --out /tmp/eqwitty-v22
```

Download the reference ZIP, manifest and checksums together. Verify the downloaded directory with the same command and exact release checkout. Regenerated PDF bytes may vary with rendering libraries; inspect the pages and compare the semantic checks. The immutable v2.2.0 tag remains authoritative for its published artifacts.
