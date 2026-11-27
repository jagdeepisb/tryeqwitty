# Eqwitty Open Diligence Standard v2.0.0

The release profile pins analytical bundle **1.4**, financial model **1.2**, structured report **1.3** and the measured benchmark **1.5** to one source commit. Treat the profile, listed contracts and computed reference figures as a set. [Machine-readable profile](profile.json) · [Compatibility and migration](../COMPATIBILITY.md) · [Release notes](RELEASE-NOTES.md)

## Conformance

| Level | What passes | Review evidence |
|---|---|---|
| Analytical bundle | The 1.4 bundle identifies the reviewed release commit and passes schema, references, stage, evidence, research ledger, financial, valuation and decision checks. | Bundle, its SHA-256, validation calculations and JSON receipt. |
| Reconciled report | The analytical bundle passes. The 1.3 report passes its own checks and matches the exact projection of that bundle, including its numbers, citations, scope and gaps. | Bundle, report JSON, their SHA-256 digests, receipt and resulting exports. |

Hard failures include a wrong contract or source commit, broken source or operand references, unsupported figures, an unrecorded research claim, an unresolved critical challenge presented as cleared, and any report mismatch. A hard failure yields a nonzero exit with no receipt. An explicitly unavailable calculation can pass when its required evidence and disposition are correctly recorded. Source relevance, factual accuracy and decision judgment remain review tasks. Check PDF readability and links separately for each delivered assessment.

```sh
python -m pip install -r analysis-kit/requirements.txt
python analysis-kit/conformance.py bundle.json
python analysis-kit/to_report.py bundle.json report.json
python analysis-kit/conformance.py bundle.json --report report.json
python report-kit/render.py report.json --out output --bundle bundle.json
```

Set `bundle.json`'s `standard_commit` after reviewing the work against this release. Run the commands from the pinned repository or supply `--commit <verified-release-commit>` to conformance in a verified source archive. The receipt reports the analytical level and the input and profile digests. It applies to those files. [Report specification](../../report-spec.md)

## Release acceptance

| Gate | Required evidence |
|---|---|
| Preceding milestones | Issues [#2](https://github.com/jagdeepisb/tryeqwitty/issues/2), [#3](https://github.com/jagdeepisb/tryeqwitty/issues/3), [#4](https://github.com/jagdeepisb/tryeqwitty/issues/4) and [#5](https://github.com/jagdeepisb/tryeqwitty/issues/5) are completed. |
| Contract and CI | All tests pass with PDF checks required. Known-answer tests cover financial calculations, liquidity, dilution, DCF sensitivity, research disclosures, and the report projection and legacy compatibility. |
| Frozen benchmark | Replay matches the archived result exactly. The fixed track has 3 sessions and 18 case responses with 111 required answers and 15 eligible contradictions. The live track has 3 sessions and 3 case responses with 21 required answers. The archived pilot has 84 paired reviewer judgments and all 6 runs clear the hard gates. |
| Measured thresholds | In each track, fact and arithmetic accuracy, answer and citation coverage, and confidence forecast coverage reach 95%. Contradiction recall, materiality, decision match and usefulness, and answer and decision agreement reach 90% wherever eligible. Mean Brier error is at most 0.10. |
| Reference PDFs | The full finance, research, and sparse references all pass PDF tag, font, text, page-bound, citation and gap-link checks. Inspect each page for legibility, clipping, tables and chart presentation before publishing. [Visual review](PDF-REVIEW.md) |
| Provenance | Source commit, contract and artifact hashes, benchmark seal, runtime versions and the reference checks are available for independent review. Licensing has documented maintainer approval. |

These thresholds confirm the measured baseline. They were set with the pilot results available. The recorded runs use one Codex configuration, and the live evidence covers one registry case. The pilot has repeated questions and no observed answer errors. Provider comparison, calibration on errors and outcomes on live financing decisions are outside this release's measured scope. [Archived pilot and limitations](../../benchmarks/v1.5/pilot-results.md) · [Licensing](../../NOTICE.md)

## Reproduce and verify

Work from the exact source commit in the [GitHub release](https://github.com/jagdeepisb/tryeqwitty/releases/tag/v2.0.0). Install Python 3.11 or later, the report kit requirements, Pango, HarfBuzz and Poppler utilities. CI uses Ubuntu 24.04 and Python 3.12. [Report setup](../../report-kit/README.md#generate-a-report)

```sh
python -m pip install -r report-kit/requirements.txt
EQWITTY_REQUIRE_PDF_CHECKS=1 python -m unittest discover -s tests
python release/certify.py build --out /tmp/eqwitty-v2-build
python release/certify.py verify --out /tmp/eqwitty-v2-build
```

Download the manifest, checksums and reference ZIP together. From the verified source checkout, run `python release/certify.py verify --out <download-directory>` to check the hashes and provenance. The ZIP includes the scored pilot, verification results, calculation outputs, inputs, reports, PDFs, HTML and request lists. The research and sparse cases include v2.0 conformance receipts. The finance case exercises the full financial exhibits through the retained v1.3 contract.

The recorded checksums identify the exact released files. Rebuilds reproduce the scored pilot, calculation results, report JSON, HTML and CSV from the same commit. WeasyPrint's PDF structure identifiers vary between renders. The verification record includes extracted text and page-coordinate hashes for like-for-like rebuilds. Rendering libraries can also affect layout across environments. Use the semantic PDF checks and visual review for regenerated PDFs. Maintainer release acceptance describes these checks. Independent third-party certification requires a separate decision by an identified certifier. [Governance](../../GOVERNANCE.md)

Maintainers stage the release with all assets as a GitHub draft from the accepted `main` revision. Enable release immutability in the repository before publishing. Publish the draft and verify that the GitHub release is immutable and its tag resolves to the manifest commit. [GitHub release integrity verification](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/verify-release-integrity)
