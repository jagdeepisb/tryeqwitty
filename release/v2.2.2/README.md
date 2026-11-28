# Eqwitty Open Diligence Standard v2.2.2

This maintenance patch strengthens release recovery, assessment provenance, agent discovery and documentation and financial boundary tests. It does not change accepted analytical bundle 1.4, financial model 1.2 or structured report 1.3 formats, financial formulas or the historical benchmark. The sole maintainer uses voluntary pull requests and successful CI checks; no GitHub branch ruleset is enforced. See [governance](../../GOVERNANCE.md) and [draft recovery](../RECOVERY.md).

## Conformance

The analytical-bundle check validates the bundle against the release profile. The reconciled-report check additionally verifies its deterministic projection. Neither establishes source truth or commercial judgment. The offline receipt identifies the local profile and exact commit, but marks publication as unverified. Separately verify the public immutable tag and commit before describing an assessment as using a published release. Keep the original bundle, report and receipt.

## Reproduce and verify

Use the exact [v2.2.2 release](https://github.com/jagdeepisb/tryeqwitty/releases/tag/v2.2.2) checkout. Install Python 3.11+, Pango, HarfBuzz and Poppler as described in the [report kit](../../report-kit/README.md).

```sh
python -m pip install -r report-kit/requirements.txt
EQWITTY_REQUIRE_PDF_CHECKS=1 python -m unittest discover -s tests
python release/verify_release.py build --out /tmp/eqwitty-v222
python release/verify_release.py verify --out /tmp/eqwitty-v222
```

Download all three release assets together and verify them with the exact release checkout. Regenerated tagged PDF bytes may differ; review pages and semantic checks. Never combine assets from different builds. Maintainer verification is not independent certification. Independent prospective evaluation remains outstanding.

[Profile](profile.json) · [Release notes](RELEASE-NOTES.md) · [Compatibility](../COMPATIBILITY.md)
