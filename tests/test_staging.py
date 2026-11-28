"""Recovery requires matching bytes from one original artifact set."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "release"))
from staging import same_asset_recovery


class StagingRecoveryTests(unittest.TestCase):
    def test_empty_partial_and_complete_matching_sets(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            original, existing = root / "original", root / "existing"
            original.mkdir()
            existing.mkdir()
            files = {"reference.zip": b"original-pdf-bytes",
                     "release-manifest.json": b"manifest",
                     "SHA256SUMS.txt": b"checksums"}
            for name, raw in files.items():
                (original / name).write_bytes(raw)
            same_asset_recovery(existing, original)
            for name, raw in files.items():
                (existing / name).write_bytes(raw)
                same_asset_recovery(existing, original)
            (existing / "reference.zip").write_bytes(b"regenerated-pdf-bytes")
            with self.assertRaisesRegex(ValueError, "do not mix builds"):
                same_asset_recovery(existing, original)
            (existing / "reference.zip").write_bytes(files["reference.zip"])
            (existing / "unexpected").write_bytes(b"unexpected")
            with self.assertRaisesRegex(ValueError, "Unexpected existing release asset"):
                same_asset_recovery(existing, original)
