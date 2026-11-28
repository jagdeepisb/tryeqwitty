# Recover an interrupted draft release

A published release is immutable; do not attempt to replace its tag or files. A partial **draft** upload is recoverable only from the exact original artifact set. Tagged PDF bytes may change between builds.

1. Check the draft's target SHA, release version, existing asset names and the successful workflow that built the original three files. Download that workflow's artifact before its retention expires. The validation workflow retains artifacts for 30 days, subject to repository settings.
2. In the exact original source checkout, run `python release/verify_release.py verify --out ORIGINAL`. Check that the manifest's source commit matches the draft target.
3. Download the existing draft assets to a separate directory and run `python release/staging.py EXISTING ORIGINAL`. If any existing asset differs, stop. Do not mix files from another build.
4. Upload only missing files from ORIGINAL using `gh release upload TAG FILE...` without `--clobber`. Download all three assets and verify the complete package again using the original checkout.
5. If the original artifact cannot be recovered, record the failure in the release PR. A maintainer must explicitly review a complete replacement set and discard the unpublished draft assets before retrying. Do not publish partially replaced assets.

If a draft points to an earlier source commit, staging stops rather than clobbering assets. The maintainer must explicitly verify the new complete package and recreate the unpublished draft at its reviewed target. A complete draft at the same target can be staged again only after checksums and stable manifest content match. Dispatch against an already published release is a no-op. Do not treat a successful recovery as authorisation to publish.
