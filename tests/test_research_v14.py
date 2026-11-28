"""Exercise routing and reject false claims of completed research."""

import copy
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis-kit"))

from research_routing import PLAYBOOK, question_priority, select_factors
from research_validation import SourceOrigins
from to_report import convert
from validate import LIB, SCHEMAS, validate


def fixture(kind):
    path = ROOT / "benchmarks" / f"research-{kind}-v1.4.json"
    return json.loads(path.read_text(encoding="utf-8"))


def row(bundle, collection, identifier):
    return next(item for item in bundle[collection] if item["id"] == identifier)


def question(bundle, identifier):
    return next(item for item in bundle["research_plan"]["questions"] if item["id"] == identifier)


class RoutingTests(unittest.TestCase):
    def test_playbook_coverage_and_schema(self):
        profile = SCHEMAS["1.1"]["properties"]["profile"]["properties"]
        self.assertEqual(set(profile["stage"]["enum"]), set(PLAYBOOK["stages"]))
        self.assertEqual(set(profile["models"]["items"]["enum"]), set(PLAYBOOK["models"]))
        self.assertEqual({x["id"] for x in LIB["core"]}, set(PLAYBOOK["baseline"]))
        for model in PLAYBOOK["models"]:
            for stage in PLAYBOOK["stages"]:
                for goal in PLAYBOOK["objectives"]:
                    factors = select_factors(stage, [model], goal)
                    self.assertLessEqual(PLAYBOOK["baseline"].keys(), factors.keys())
                    self.assertLessEqual(factors.keys(), PLAYBOOK["factors"].keys())
        for factor in PLAYBOOK["factors"].values():
            self.assertTrue(all(factor[key] for key in ("evidence_required", "counter_test", "decision_use", "preferred_sources")))
        Draft202012Validator.check_schema(SCHEMAS["1.4"])

    def test_model_stage_and_objective_change_what_is_required(self):
        early = select_factors("early_revenue", ["saas"], "valuation")
        concept = select_factors("concept", ["saas"], "valuation")
        mature = select_factors("mature", ["saas"], "investment")
        pilot = select_factors("pilot", ["manufacturing"], "fundraising_readiness")
        lending = select_factors("development", ["lending"], "investment")
        comparisons = (
            (early, {"SA01", "SA02", "ST04", "OB04"}, {"SA04", "ST01", "MF04", "OB02"}),
            (concept, {"SA04", "ST01", "OB04"}, {"SA01", "SA02", "ST04"}),
            (mature, {"SA01", "SA02", "SA03", "ST06", "OB01"}, {"SA04", "OB04", "ST04"}),
            (pilot, {"MF04", "MF01", "MF02", "ST03", "OB02"}, {"SA02", "MF03", "OB04", "ST04"}),
            (lending, {"LE04", "LE02", "ST02", "OB01"}, {"LE01", "LE03", "MF02"}),
        )
        for actual, present, absent in comparisons:
            self.assertLessEqual(present, actual.keys())
            self.assertTrue(absent.isdisjoint(actual))
        hybrid = select_factors("pilot", ["manufacturing", "lending"], "fundraising_readiness")
        self.assertEqual(hybrid, select_factors("pilot", ["lending", "manufacturing"], "fundraising_readiness"))
        self.assertEqual(hybrid["LE04"]["minimum_priority"], "Critical")
        self.assertLessEqual({"LE04", "MF04", "ST03", "OB02"}, hybrid.keys())
        self.assertEqual(hybrid["C03"]["minimum_priority"], "High")

    def test_cli_outputs_the_evidence_and_counter_test_for_selected_factors(self):
        output = subprocess.check_output(
            [sys.executable, str(ROOT / "analysis-kit/research_routing.py"), "--stage", "pilot",
             "--models", "manufacturing", "--objective", "fundraising_readiness"], text=True
        )
        plan = json.loads(output)
        rows = {r["id"]: r for r in plan["factors"]}
        self.assertEqual(plan["version"], "1.4")
        self.assertIn("production trial", rows["MF04"]["evidence_required"])
        self.assertIn("prototype", rows["MF04"]["counter_test"])
        self.assertNotIn("SA02", rows)


class ResearchValidationTests(unittest.TestCase):
    def setUp(self):
        self.saas = fixture("early-saas")
        self.pilot = fixture("pilot-manufacturing")

    def reject(self, bundle, message):
        with self.assertRaisesRegex(ValueError, message):
            validate(bundle)

    def test_known_benchmarks_and_attempt_dedup(self):
        saas = validate(self.saas)
        pilot = validate(self.pilot)
        a, b = saas["research_coverage"], pilot["research_coverage"]
        self.assertEqual(a["question_counts"], {"completed": 0, "partial": 4, "blocked": 3, "deferred": 1})
        self.assertEqual(b["question_counts"], {"completed": 1, "partial": 2, "blocked": 4, "deferred": 1})
        self.assertEqual((a["source_records"], a["source_origins"], a["independent_origins"]), (5, 4, 2))
        self.assertEqual(a["origin_groups"]["juniper price release"], ["E3", "E5"])
        self.assertEqual(a["attempts_by_channel"], {"document_review": 5})
        self.assertEqual(a["budget"]["research_used"], 4)
        self.assertEqual(a["budget"]["challenge_used"], 1)
        self.assertEqual(b["attempts_by_channel"], {"document_review": 2})
        self.assertEqual(b["thesis_status"], "corroborated")
        self.assertEqual(a["thesis_status"], "provisional")
        self.assertEqual(a["unresolved_material_challenges"], ["Q1"])
        self.assertEqual(b["unresolved_material_challenges"], ["Q2"])
        self.assertEqual(saas["financial_model"]["metrics"]["M1"]["value"], "0.6")
        self.assertEqual(b["unresolved_material_factors"], ["C01", "C06", "C07", "MF01", "MF02", "MF04", "OB02", "ST03"])

    def test_priority_is_exact_and_ties_are_stable(self):
        results = validate(self.saas)["research_coverage"]["priorities"]
        self.assertEqual([r["question_id"] for r in results], ["RQ2", "RQ3", "RQ1", "RQ5", "RQ8", "RQ4", "RQ6", "RQ7"])
        self.assertEqual(results[0]["priority"], "36")
        factors = {r["id"]: r for r in self.saas["factors"]}
        q = question(self.saas, "RQ2").copy()
        q["estimated_attempts"] = 7
        self.assertEqual(question_priority(q, factors, "valuation"), Fraction(36, 7))

    def test_omitted_factor_downgraded_floor_and_missing_work(self):
        missing = copy.deepcopy(self.saas)
        missing["factors"].remove(row(missing, "factors", "SA01"))
        self.reject(missing, "Missing mandatory research factors: SA01")
        weak = copy.deepcopy(self.saas)
        row(weak, "factors", "OB04")["priority"] = "Low"
        self.reject(weak, "below its research playbook minimum")
        missing_result = copy.deepcopy(self.saas)
        missing_result["research"].remove(row(missing_result, "research", "R2"))
        self.reject(missing_result, "exactly one actual research record")
        unplanned = copy.deepcopy(self.saas)
        unplanned["factors"].append({**row(unplanned, "factors", "C08"), "id": "EX01"})
        self.reject(unplanned, "Applicable factor has no planned research question")

    def test_stage_and_exclusion_have_evidence(self):
        self.saas["research_plan"]["stage_evidence_ids"] = []
        self.reject(self.saas, "Declared stage needs usable evidence")
        self.saas["research_plan"]["stage_evidence_ids"] = ["E1"]
        row(self.saas, "factors", "SA02")["status"] = "not_applicable"
        self.reject(self.saas, "one exclusion and scoped evidence")
        self.saas["research_plan"]["exclusions"] = [
            {"factor_id": "SA02", "evidence_ids": ["E1"], "rationale": "Scoped test case excludes this cohort metric."}
        ]
        question(self.saas, "RQ7")["factor_ids"] = ["C08"]
        self.assertEqual(validate(self.saas)["research_coverage"]["excluded_factors"], ["SA02"])

    def test_attempts_disclose_actual_channels_dates_and_evidence(self):
        for failure, update in [
            ("unavailable research tool", {"channel": "web_search"}),
            ("accessed after research attempt", {"date": "2026-11-26"}),
            ("research after the analysis date", {"date": "2026-11-28"}),
            ("attempt outcome and evidence disagree", {"outcome": "no_evidence"}),
            ("reviewed document missing from inventory", {"target": "another spreadsheet"}),
        ]:
            with self.subTest(failure=failure):
                case = copy.deepcopy(self.saas)
                row(case, "research_attempts", "A1").update(update)
                self.reject(case, failure)
        self.saas["research_plan"]["capabilities"]["web"] = True
        row(self.saas, "research_attempts", "A1").update(channel="web_search", target="Juniper information")
        self.reject(self.saas, "search results alone may only be recorded as research leads")
        row(self.saas, "research_attempts", "A1").update(channel="web_open", target="https://example.org/statement")
        row(self.saas, "evidence", "E1")["url"] = "https://example.org/other"
        self.reject(self.saas, "opened URL and evidence URL disagree")

    def test_research_cannot_claim_completion_without_a_real_counter_test(self):
        for attempt in self.pilot["research_attempts"]:
            attempt["intent"] = "support"
        self.reject(self.pilot, "completed research lacks an executed counter-evidence test")
        row(self.saas, "research", "R1")["attempt_ids"] = []
        self.reject(self.saas, "result cites evidence absent from its recorded attempts")

    def test_paid_accounts_and_registered_name_leave_open_questions(self):
        for factor, gap in (("C01", "G4"), ("SA01", "G5"), ("ST04", "G5")):
            self.assertEqual(row(self.saas, "factors", factor)["status"], "partial")
            self.assertIn(factor, row(self.saas, "gaps", gap)["affected_factor_ids"])
        for key in ("R1", "R2"):
            self.assertEqual(row(self.saas, "research", key)["status"], "partial")
        self.assertEqual([r["formula"] for r in self.saas["metrics"]], ["gross_margin"])
        self.assertIsNone(self.saas["valuations"][0]["value"])

    def test_narrow_completed_question_does_not_override_outstanding_material_gap(self):
        # The supervised shift was accepted. Output across shifts is still being investigated.
        question(self.pilot, "RQ3")["factor_ids"].append("MF04")
        row(self.pilot, "factors", "MF04")["status"] = "supported"
        self.reject(self.pilot, "open research question still needs evidence for this factor")

    def test_origins_cannot_be_split_by_tracking_url_or_title_aliases(self):
        evidence = {e["id"]: copy.deepcopy(e) for e in self.saas["evidence"]}
        evidence["E3"]["url"] = "https://www.example.com/offers/?utm_medium=x&edition=Q4#pricing"
        evidence["E5"]["url"] = "http://example.com/offers?edition=Q4&fbclid=a"
        self.assertEqual(len(SourceOrigins(evidence).usable(["E3", "E5"])), 1)
        evidence["E5"]["origin"] = "new source"
        with self.assertRaisesRegex(ValueError, "multiple origins"):
            SourceOrigins(evidence)
        evidence["E5"].update(url=None, publisher=evidence["E3"]["publisher"], title=evidence["E3"]["title"])
        evidence["E3"]["url"] = None
        with self.assertRaisesRegex(ValueError, "multiple origins"):
            SourceOrigins(evidence)
        evidence["E4"]["origin"] = "juniper price release"
        evidence["E5"]["origin"] = "juniper price release"
        self.assertFalse(SourceOrigins(evidence).independent(["E4"]))

    def test_completion_counts_origins_and_retains_disputed_claims(self):
        result = row(self.saas, "research", "R3")
        result.update(status="completed", stop_reason="criteria_met", gap_ids=[])
        self.reject(self.saas, "completed research has an unresolved disputed claim")
        row(self.saas, "claims", "C2")["status"] = "contradicted"
        question(self.saas, "RQ3").update(min_origins=3, min_independent_origins=1)
        self.reject(self.saas, "required distinct source origins")
        question(self.saas, "RQ3").update(min_origins=1, min_independent_origins=1)
        row(self.saas, "evidence", "E4")["origin"] = "juniper price release"
        self.reject(self.saas, "required distinct source origins")

    def test_dependency_and_parent_cycles_and_unmet_prerequisite(self):
        for field, value, expected in [
            ("depends_on", ["RQ1"], "Cycle in research dependencies"),
            ("parent_id", "RQ1", "Cycle in research parent links"),
        ]:
            with self.subTest(field=field):
                case = copy.deepcopy(self.saas)
                question(case, "RQ1")[field] = value
                self.reject(case, expected)
        question(self.pilot, "RQ2")["depends_on"] = ["RQ1"]
        self.reject(self.pilot, "completed research has an unresolved prerequisite")

    def test_stop_reasons_and_reserve_cannot_be_gamed(self):
        limited = copy.deepcopy(self.saas)
        limited["research_plan"]["budget"]["max_attempts"] = 5
        self.reject(limited, "budget or challenge reserve exceeded")
        ample = copy.deepcopy(self.saas)
        ample["research_plan"]["budget"]["max_attempts"] = 20
        self.reject(ample, "stop reason budget_limit is unsupported")
        untouched = copy.deepcopy(self.saas)
        row(untouched, "challenges", "Q1")["attempt_ids"] = []
        self.reject(untouched, "Challenge reserve used outside a corrective review")
        valuable = copy.deepcopy(self.pilot)
        q = question(valuable, "RQ8")
        q.update(uncertainty=3, answerability=3, estimated_attempts=1)
        self.reject(valuable, "stop reason low_expected_value is unsupported")

    def test_material_gaps_match_question_and_decision(self):
        row(self.saas, "research", "R4")["gap_ids"] = ["G2"]
        self.reject(self.saas, "material gap missing or under-prioritised")
        row(self.saas, "research", "R4")["gap_ids"] = ["G1"]
        row(self.saas, "gaps", "G1")["priority"] = "Medium"
        self.reject(self.saas, "material gap missing or under-prioritised")
        row(self.saas, "gaps", "G1")["priority"] = "High"
        self.saas["decision"]["status"] = "complete_within_scope"
        self.reject(self.saas, "qualified decision")

    def test_thesis_and_contradictions_are_explicit(self):
        self.saas["thesis"]["divergences"] = []
        self.reject(self.saas, "contradiction requires thesis divergence")
        self.pilot["thesis"]["independent"] = self.pilot["thesis"]["management"]
        self.reject(self.pilot, "repeats the management thesis")
        self.pilot = fixture("pilot-manufacturing")
        self.pilot["thesis"]["independent_evidence"] = ["E1"]
        self.reject(self.pilot, "needs a completed independent test")

    def test_correction_routing_rechecks_and_material_financial_hold(self):
        row(self.pilot, "challenges", "Q1")["rechecked_ids"] = []
        self.reject(self.pilot, "resolved correction needs a recheck")
        self.pilot = fixture("pilot-manufacturing")
        row(self.pilot, "challenges", "Q2")["route"] = "valuation"
        self.reject(self.pilot, "correction route does not match")
        item = row(self.saas, "challenges", "Q1")
        item["affected"].append("M1")
        self.reject(self.saas, "M1: unresolved material challenge")

    def test_report_discloses_actual_attempts_and_thesis_status(self):
        spec = importlib.util.spec_from_file_location("renderer_v14", ROOT / "report-kit/render.py")
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)
        report = convert(self.saas, "0" * 64)
        self.assertEqual(report["methodology"]["version"], "1.4")
        self.assertEqual(report["version"], "1.3")
        page = renderer.report_html(report)
        for text in ("Actual research activity", "Shared origin", "Planned questions and recorded outcomes",
                     "Red-team corrections", "Independent · Provisional", "Web searches", "No attempts recorded"):
            self.assertIn(text.lower(), page.lower())
        activity = next(t for s in report["sections"] for t in s["tables"] if t["caption"] == "Actual research activity")
        self.assertEqual([r[2]["value"] for r in activity["rows"]], ["0", "0", "5", "0"])
        self.assertEqual(activity["rows"][0][1]["text"], "Unavailable")
        renderer.validate(convert(self.pilot, "0" * 64))
        renderer.validate(convert(self.pilot, "0" * 64, "1.0"))

    def test_no_tools_or_sources_preserves_unknowns_without_claimed_work(self):
        bundle = self.pilot
        bundle["profile"]["stage"] = "unknown"
        plan = bundle["research_plan"]
        plan.update(stage_evidence_ids=[], stage_rationale="The intake has no dated activity records.",
                    budget={"max_attempts": 0, "challenge_reserve": 0, "minimum_priority": 0})
        plan["capabilities"]["documents"] = False
        bundle.update(evidence=[], documents=[], research_attempts=[])
        bundle["thesis"].update(status="unavailable", independent="No independent records were available.",
                               independent_evidence=[])
        bundle["safeguards"][0].update(status="unknown", evidence_ids=[])
        bundle["challenges"] = [row(bundle, "challenges", "Q2")]
        row(bundle, "factors", "ST03")["id"] = "ST07"
        question(bundle, "RQ2")["factor_ids"].remove("ST03")
        question(bundle, "RQ2")["factor_ids"].append("ST07")
        for factor in bundle["factors"]:
            factor.update(status="unknown", confidence="unknown", support=[], oppose=[])
        material = [r["id"] for r in bundle["factors"] if r["priority"] == "High"]
        for gap in bundle["gaps"]:
            gap["affected_factor_ids"] = ["ST07" if key == "ST03" else key for key in gap["affected_factor_ids"]]
        row(bundle, "gaps", "G1")["affected_factor_ids"] = material
        for result in bundle["research"]:
            result.update(status="blocked", stop_reason="tool_unavailable", attempt_ids=[], evidence_ids=[], gap_ids=["G1"])
            question(bundle, result["question_id"])["evidence_route"] = "provided"
        result = validate(bundle)
        self.assertEqual(result["assessed"], 0)
        self.assertEqual(result["research_coverage"]["attempts_by_channel"], {})
        self.assertEqual(result["research_coverage"]["source_origins"], 0)
        self.assertEqual(result["research_coverage"]["thesis_status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
