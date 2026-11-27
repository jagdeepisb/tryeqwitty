"""Exercise v2.0 source binding, report tampering and release thresholds."""

from copy import deepcopy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from subprocess import CompletedProcess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "release"))
sys.path.insert(0, str(ROOT / "analysis-kit"))

from certify import check_pilot, json_bytes
from conformance import PROFILE, check, json_document, source_commit
from to_report import convert

COMMIT = "1" * 40


class ConformanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.bundle_path = Path(self.directory.name) / "bundle.json"
        self.report_path = Path(self.directory.name) / "report.json"
        bundle = json.loads((ROOT / "benchmarks/research-early-saas-v1.4.json").read_bytes())
        bundle["standard_commit"] = COMMIT
        self.bundle_path.write_bytes(json_bytes(bundle))
        _, digest = json_document(self.bundle_path)
        self.report = convert(bundle, digest)
        self.report_path.write_bytes(json_bytes(self.report))

    def test_v20_levels_include_file_digests(self):
        analysis = check(self.bundle_path, None, COMMIT)
        reconciled = check(self.bundle_path, self.report_path, COMMIT)
        self.assertEqual(analysis["standard_release"], "2.0.0")
        self.assertEqual(analysis["level"], "analytical-bundle")
        self.assertEqual(reconciled["level"], "reconciled-report")
        self.assertEqual(reconciled["source_commit"], COMMIT)
        self.assertEqual(reconciled["profile_sha256"], json_document(PROFILE)[1])
        self.assertEqual(reconciled["bundle_sha256"], json_document(self.bundle_path)[1])
        self.assertEqual(reconciled["report_sha256"], json_document(self.report_path)[1])

    def test_stale_provenance_and_legacy_format_cannot_claim_v20(self):
        with self.assertRaisesRegex(ValueError, "differs from the source commit"):
            check(self.bundle_path, None, "2" * 40)
        with self.assertRaisesRegex(ValueError, "requires analytical bundle v1.4"):
            check(ROOT / "benchmarks/report-complete-v1.3.json", None, COMMIT)

    def test_valid_report_json_with_substituted_bundle_hash_fails(self):
        self.report["methodology"]["bundle_sha256"] = "f" * 64
        self.report_path.write_bytes(json_bytes(self.report))
        with self.assertRaisesRegex(ValueError, r"validated bundle at .+bundle_sha256"):
            check(self.bundle_path, self.report_path, COMMIT)


class SourceCommitTests(unittest.TestCase):
    def test_dirty_checkout_cannot_claim_committed_provenance(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / ".git").mkdir()
            with patch("conformance.ROOT", root), patch("conformance.run") as git:
                git.side_effect = [
                    CompletedProcess([], 0, stdout=COMMIT + "\n"),
                    CompletedProcess([], 0, stdout=" M analysis-kit/validate.py\n"),
                ]
                with self.assertRaisesRegex(ValueError, "uncommitted tracked changes"):
                    source_commit(COMMIT)

    def test_clean_checkout_accepts_matching_commit(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / ".git").mkdir()
            with patch("conformance.ROOT", root), patch("conformance.run") as git:
                git.side_effect = [
                    CompletedProcess([], 0, stdout=COMMIT + "\n"),
                    CompletedProcess([], 0, stdout=""),
                ]
                self.assertEqual(source_commit(COMMIT), COMMIT)


class AcceptanceTests(unittest.TestCase):
    def test_pilot_is_accepted_and_hard_failure_cannot_be_averaged_away(self):
        profile, _ = json_document(PROFILE)
        results, _ = json_document(ROOT / "benchmarks/v1.5/results.json")
        check_pilot(results, profile["benchmark"])
        gated = deepcopy(results)
        gated["summaries"][0]["hard_gate_clear"]["count"] -= 1
        with self.assertRaisesRegex(ValueError, "fixed: hard-failure gate"):
            check_pilot(gated, profile["benchmark"])
        gated = deepcopy(results)
        gated["summaries"][1]["metrics"]["factual_accuracy"]["count"] = 17
        with self.assertRaisesRegex(ValueError, "live: factual_accuracy below 95%"):
            check_pilot(gated, profile["benchmark"])


if __name__ == "__main__":
    unittest.main()
