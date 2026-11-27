"""Verify stored trials, failure gates and report-to-bundle reconciliation."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis-kit"))

from benchmark import DEFAULT, evaluate, prepare_inputs, read_json
from to_report import convert


def put(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def replace_trial(root, trial, edit):
    path = root / "trials" / f"{trial}.json"
    report = read_json(path)
    edit(report)
    put(path, report)
    campaign = read_json(root / "campaign.json")
    record = next(r for r in campaign["trials"] if r["id"] == trial)
    record["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    put(root / "campaign.json", campaign)


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.suite = Path(self.directory.name) / "benchmark"
        shutil.copytree(DEFAULT, self.suite)

    def test_recorded_scores_reproduce_without_running_a_provider(self):
        actual = evaluate(self.suite)
        self.assertEqual(actual, read_json(self.suite / "results.json"))
        fixed, live = actual["summaries"]
        self.assertEqual((fixed["trial_cases"], live["trial_cases"]), (18, 3))
        self.assertEqual((fixed["search_actions"], live["search_actions"]), (0, 9))
        self.assertEqual(fixed["metrics"]["contradiction_recall"], {"count": 15, "out_of": 15})
        self.assertEqual(live["metrics"]["contradiction_recall"], {"count": 0, "out_of": 0})
        self.assertEqual(fixed["answer_agreement"], {"count": 111, "out_of": 111})
        self.assertEqual(live["decision_agreement"], {"count": 3, "out_of": 3})
        self.assertEqual(actual["reviewer_agreement"], {"count": 84, "out_of": 84})

    def test_frozen_case_and_raw_trial_cannot_change_silently(self):
        packet = self.suite / "cases/saas-early.json"
        packet.write_bytes(packet.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "Frozen input changed"):
            evaluate(self.suite)
        packet.write_bytes((DEFAULT / "cases/saas-early.json").read_bytes())
        raw = self.suite / "trials/B8.json"
        raw.write_bytes(raw.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "B8: trial output changed"):
            evaluate(self.suite)

    def test_prepared_live_input_preserves_blinding(self):
        live = prepare_inputs(self.suite, "live")
        fixed = prepare_inputs(self.suite, "fixed")
        self.assertIn('"source_targets"', live)
        self.assertNotIn("27 August 2026", live)
        self.assertIn('"sources"', fixed)
        self.assertIn("27 August 2026", fixed)
        for output in (live, fixed):
            self.assertNotIn('"adjudication"', output)
            self.assertNotIn('"material":', output)

    def test_trials_must_follow_the_dated_input_seal(self):
        path = self.suite / "campaign.json"
        metadata = read_json(path)
        metadata["trials"][0]["output_recorded_at"] = "2026-11-26T00:00:00+00:00"
        put(path, metadata)
        with self.assertRaisesRegex(ValueError, "trial output predates the benchmark seal"):
            evaluate(self.suite)

    def test_zero_fabricated_value_and_copied_origin_hurt_scores(self):
        def change(result):
            fields = result["cases"]["saas-early"]["answers"]
            fields["ev_usd"]["value"] = "0"
            result["cases"]["marketplace-growth"]["answers"]["independent_origins"]["value"] = "1"

        replace_trial(self.suite, "B8", change)
        report = evaluate(self.suite)
        fixed = report["summaries"][0]
        self.assertEqual(fixed["metrics"]["factual_accuracy"], {"count": 59, "out_of": 60})
        self.assertEqual(fixed["metrics"]["arithmetic_accuracy"], {"count": 35, "out_of": 36})
        self.assertEqual(fixed["hard_gate_clear"], {"count": 2, "out_of": 3})
        self.assertEqual(fixed["answer_agreement"], {"count": 107, "out_of": 111})
        self.assertGreater(float(fixed["calibration"]["brier_mean"]), 0.01)
        self.assertIn("unsupported_value", report["runs"][0]["hard_failures"])

    def test_live_citation_without_successful_open_and_wrong_entity_fail(self):
        def change(result):
            result["search_log"][-1]["outcome"] = "blocked"
            result["cases"]["registry-uk"]["answers"]["entity"]["value"] = "Monzo Bank Holding Group Limited"

        replace_trial(self.suite, "H6", change)
        report = evaluate(self.suite)
        run = next(r for r in report["runs"] if r["metadata"]["id"] == "H6")
        self.assertIn("unconfirmed_citation", run["hard_failures"])
        self.assertIn("wrong_entity", run["hard_failures"])
        self.assertEqual(report["summaries"][1]["hard_gate_clear"], {"count": 2, "out_of": 3})

    def test_fixed_search_exceeds_budget(self):
        replace_trial(self.suite, "Q2", lambda output: output["search_log"].append(
            {"kind": "query", "target": "outside lookup", "outcome": "success"}))
        result = evaluate(self.suite)
        run = next(r for r in result["runs"] if r["metadata"]["id"] == "Q2")
        self.assertIn("search_budget_exceeded", run["hard_failures"])
        self.assertEqual(result["summaries"][0]["search_actions"], 1)

    def test_missing_answer_counts_in_denominator_but_not_as_calibrated(self):
        replace_trial(self.suite, "B8", lambda output: output["cases"]["saas-early"]["answers"].pop("grr"))
        fixed = evaluate(self.suite)["summaries"][0]
        self.assertEqual(fixed["metrics"]["answer_coverage"], {"count": 110, "out_of": 111})
        self.assertEqual(fixed["metrics"]["arithmetic_accuracy"], {"count": 35, "out_of": 36})
        self.assertEqual(fixed["calibration"]["scored"], 110)
        self.assertEqual(fixed["calibration"]["eligible"], 111)
        self.assertEqual(fixed["answer_agreement"], {"count": 109, "out_of": 111})

    def test_independent_review_disagreement_requires_a_resolution(self):
        path = self.suite / "judgments/B.json"
        review = read_json(path)
        first = review["reviews"][0]
        first["evidence"] = False
        put(path, review)
        with self.assertRaisesRegex(ValueError, "Unresolved reviewer disagreement"):
            evaluate(self.suite)
        path = self.suite / "campaign.json"
        campaign = read_json(path)
        campaign["resolutions"] = [
            {"trial": first["trial"], "case": first["case"], "criterion": "evidence",
             "pass": False, "reason": "Adjudicated in this negative-control test."}
        ]
        put(path, campaign)
        result = evaluate(self.suite)
        self.assertEqual(result["reviewer_agreement"], {"count": 83, "out_of": 84})


class ReportAuditTests(unittest.TestCase):
    def test_render_gate_rejects_disclosure_that_differs_from_bundle(self):
        path = ROOT / "benchmarks/research-early-saas-v1.4.json"
        raw = path.read_bytes()
        report = convert(json.loads(raw), hashlib.sha256(raw).hexdigest())
        spec = importlib.util.spec_from_file_location("audited_renderer", ROOT / "report-kit/render.py")
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)
        with TemporaryDirectory() as directory:
            report_file = Path(directory) / "report.json"
            valid = Path(directory) / "valid"
            failed = Path(directory) / "failed"
            put(report_file, report)
            args = [sys.executable, str(ROOT / "report-kit/render.py"), str(report_file),
                    "--bundle", str(path), "--html-only", "--out"]
            subprocess.run([*args, str(valid)], check=True, capture_output=True)
            self.assertTrue((valid / "assessment.html").is_file())
            corrupt = copy.deepcopy(report)
            methodology = next(s for s in corrupt["sections"] if s["heading"] == "Methodology and limitations")
            activity = next(t for t in methodology["tables"] if t["caption"] == "Actual research activity")
            activity["rows"][0][2]["value"] = "12"
            renderer.validate(corrupt)
            put(report_file, corrupt)
            failure = subprocess.run([*args, str(failed)], capture_output=True, text=True)
            self.assertNotEqual(failure.returncode, 0)
            self.assertIn("Report differs from the validated bundle", failure.stderr)
            self.assertFalse(failed.exists())


if __name__ == "__main__":
    unittest.main()
