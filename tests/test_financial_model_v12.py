"""Known answers and adversarial tests for the v1.2 analytical contract."""

import copy
from datetime import date
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis-kit"))

from finance_context import add_months
from finance_metrics import LEGACY_QUANTITIES, MODEL_METRICS
from finance_model import CASES, runway
from to_report import convert
from validate import FORMULAS, LIB, SCHEMAS, validate

D = Decimal
COMPLETE = (ROOT / "benchmarks/financial-model-v1.2.json").read_text(encoding="utf-8")
SPARSE = (ROOT / "benchmarks/financial-sparse-v1.2.json").read_text(encoding="utf-8")


def with_model(bundle, model):
    """Add the needed factor rows so eligibility is tested through the public entry point."""
    bundle["profile"]["models"].append(model)
    known = {row["id"] for row in bundle["factors"]}
    for factor in LIB["models"][model]:
        if factor["id"] not in known:
            row = {**bundle["factors"][0], "id": factor["id"], "question": factor["test"]}
            bundle["factors"].append(row)
            bundle["research"][0]["factor_ids"].append(row["id"])


class FinancialModelTests(unittest.TestCase):
    def setUp(self):
        self.bundle = json.loads(COMPLETE)
        self.model = self.bundle["financial_model"]
        self.inputs = {row["id"]: row for row in self.bundle["inputs"]}

    def evaluated(self):
        return validate(self.bundle)["financial_model"]

    def reject(self, pattern):
        with self.assertRaisesRegex((ValueError, ValidationError), pattern):
            self.evaluated()

    def test_versioned_schemas_and_legacy_formula_map(self):
        for schema in SCHEMAS.values():
            Draft202012Validator.check_schema(schema)
        finance_schema = ROOT / "schemas/financial-model-v1.2.json"
        Draft202012Validator.check_schema(json.loads(finance_schema.read_text()))
        self.assertEqual(FORMULAS.keys(), LEGACY_QUANTITIES.keys())

    def test_annual_dcf_known_answers_and_all_sensitivity_cells(self):
        result = self.evaluated()["dcf"]
        self.assertEqual(result["wacc"], "0.1")
        self.assertEqual(result["annual_fcff"], [
            {"year_end": "2027-11-30", "fcff": "120"}, {"year_end": "2028-11-30", "fcff": "120"},
        ])
        self.assertEqual(result["terminal_value"], "1530")
        self.assertAlmostEqual(D(result["present_value_of_terminal"]), D(1530) / D("1.21"), places=22)
        self.assertEqual(result["equity_bridge"], {"excess_cash": "15", "debt": "40", "other_adjustments": "-5"})
        self.assertAlmostEqual(D(result["enterprise_value"]), D(1782) / D("1.21"), places=22)
        self.assertAlmostEqual(D(result["equity_value"]), D(1782) / D("1.21") - 30, places=22)
        cells = result["sensitivity"]
        self.assertEqual([(x["wacc"], x["terminal_growth"]) for x in cells],
                         [(r, g) for r in ("0.08", "0.1", "0.12") for g in ("0.01", "0.02", "0.03")])
        # Closed-form constant annual FCFF yields EV = 120/(1+r) + (120 + TV)/(1+r)**2.
        for cell in cells:
            r, g = D(cell["wacc"]), D(cell["terminal_growth"])
            terminal = D(120) * (1 + g) / (r - g)
            ev = (D(120) * (2 + r) + terminal) / (1 + r) ** 2
            self.assertAlmostEqual(D(cell["enterprise_value"]), ev, places=22)
            self.assertAlmostEqual(D(cell["equity_value"]), ev - 30, places=22)
        self.assertEqual(cells[4]["enterprise_value"], result["enterprise_value"])
        self.assertEqual(cells[4]["equity_value"], result["equity_value"])
        self.assertEqual(set(result["evidence_ids"]), {"E1", "E2", "E3"})
        self.assertNotIn(self.model["scenarios"]["cases"]["base"]["months"][0]["other_cash_flow"], result["input_ids"])

    def test_cap_table_opening_two_rounds_pool_and_existing_subscriber(self):
        cap = self.evaluated()["cap_table"]
        opening = cap["opening"]
        self.assertEqual(opening["fully_diluted_shares"], "100")
        self.assertEqual(opening["ownership"], {"H1": "0.8", "H2": "0.2", "H3": "0", "H4": "0"})
        first, second = cap["rounds"]
        self.assertEqual(
            [first[f] for f in ("issue_price_per_share", "post_money_equity_value", "post_round_fully_diluted_shares")],
            ["2", "300", "150"],
        )
        self.assertEqual(first["allocations"]["H3"], {"cash": "50", "issued_shares": "25"})
        self.assertAlmostEqual(D(first["existing_share_dilution"]), D(1) / 3, places=22)
        self.assertAlmostEqual(D(first["holders"]["H1"]["ownership_change"]), -D(4) / 15, places=22)
        self.assertEqual(first["holders"]["H2"]["shares_after"], "45")
        self.assertEqual(
            [second[f] for f in ("issue_price_per_share", "new_primary_cash", "post_money_equity_value",
                                "post_round_fully_diluted_shares")],
            ["3", "60", "510", "170"],
        )
        self.assertEqual(second["holders"]["H1"]["shares_after"], "90")
        self.assertEqual(second["allocations"]["H4"]["issued_shares"], "10")
        self.assertAlmostEqual(D(second["holders"]["H1"]["ownership_change"]), D(9) / 17 - D(8) / 15, places=22)
        self.assertAlmostEqual(D(second["existing_share_dilution"]), D(2) / 17, places=22)
        self.assertEqual(first["basis"], "assumption")
        self.assertLess(set(first["input_ids"]), set(second["input_ids"]))

    def test_linked_cash_flows_cash_floor_capital_and_runway(self):
        plan = self.evaluated()["scenarios"]
        self.assertEqual(plan["months_in_horizon"], 24)
        self.assertEqual(plan["opening_unrestricted_cash"], "100")
        self.assertEqual(plan["minimum_unrestricted_cash"], "40")
        downside, base, upside = (plan["cases"][name] for name in CASES)
        zero = downside["months"][0]
        self.assertEqual(zero["fcff"], "0")
        self.assertEqual(zero["closing_cash"], "85")
        self.assertEqual(downside["capital_required_before_linked_rounds"], "300")
        self.assertEqual(downside["residual_capital_required"], "300")
        self.assertEqual(downside["runway_after_linked_rounds"]["months"], 4)
        first_base = base["months"][0]
        self.assertEqual(first_base["operating_cash_before_capex"], "15")
        self.assertEqual(first_base["fcff"], "10")
        self.assertEqual(first_base["net_cash_flow_before_linked_rounds"], "-5")
        self.assertEqual(first_base["closing_cash"], "95")
        round_close = base["months"][3]
        self.assertEqual(round_close["linked_round_cash"], "50")
        self.assertEqual(round_close["net_cash_flow"], "45")
        self.assertEqual(round_close["closing_cash_before_linked_rounds"], "80")
        self.assertEqual(round_close["closing_cash"], "130")
        self.assertEqual(base["months"][-1]["residual_floor_gap"], "10")
        self.assertEqual(base["capital_required_before_linked_rounds"], "60")
        self.assertEqual(base["residual_capital_required"], "10")
        self.assertEqual(base["runway_before_linked_rounds"]["months"], 12)
        self.assertEqual(base["runway_after_linked_rounds"],
                         {"status": "breach", "months": 22, "first_breach": "2028-10-31"})
        self.assertEqual(upside["months"][12]["linked_round_cash"], "60")
        self.assertEqual(upside["months"][-1]["closing_cash"], "210")
        self.assertEqual(upside["residual_capital_required"], "0")
        self.assertEqual(upside["runway_after_linked_rounds"], {"status": "at_least", "months": 24, "first_breach": None})

    def test_initial_cash_breach_remains_a_breach_after_recovery(self):
        self.inputs[self.model["scenarios"]["cash_floor"]]["value"] = "101"
        result = self.evaluated()["scenarios"]["cases"]["upside"]
        self.assertEqual(result["runway_after_linked_rounds"],
                         {"status": "breach", "months": 0, "first_breach": "2026-11-30"})
        self.assertEqual(result["residual_capital_required"], "1")
        self.assertEqual(runway([("start", D(1)), ("month1", D(1))], D(1))["status"], "at_least")

    def test_month_end_and_mid_month_schedule_alignment(self):
        self.assertEqual(add_months(date(2028, 1, 31), 1), date(2028, 2, 29))
        self.assertEqual(add_months(date(2028, 1, 31), 2), date(2028, 3, 31))
        self.assertEqual(add_months(date(2028, 1, 30), 2), date(2028, 3, 30))
        self.assertEqual(add_months(date(2026, 11, 27), 1), date(2026, 12, 27))

    def test_observed_rounds_never_fund_forecast_twice(self):
        cap = self.model["cap_table"]
        cap["opening_date"] = "2026-10-31"
        for holder in cap["holders"]:
            self.inputs[holder["shares"]]["period"] = cap["opening_date"]
        first = cap["rounds"][0]
        first["date"] = "2026-11-15"
        for key in (first["pre_money"], first["pool_top_up"], first["subscriptions"][0]["amount"]):
            self.inputs[key].update(basis="observed", period=first["date"])
        self.reject("Unknown reference in scenario financing")
        for name in ("base", "upside"):
            self.model["scenarios"]["cases"][name]["months"][3]["round_ids"] = []
        result = self.evaluated()
        self.assertEqual(result["cap_table"]["rounds"][0]["basis"], "observed")
        self.assertEqual(result["scenarios"]["cases"]["base"]["months"][3]["linked_round_cash"], "0")
        self.assertEqual(result["scenarios"]["cases"]["upside"]["months"][12]["linked_round_cash"], "60")

    def test_round_guardrails(self):
        edits = {
            "pre-money equity value must be positive": lambda cap, inputs: inputs[cap["rounds"][0]["pre_money"]].update(value="0"),
            "subscription cash must be positive": lambda cap, inputs: inputs[cap["rounds"][0]["subscriptions"][0]["amount"]].update(value="0"),
            "chronological order": lambda cap, inputs: cap["rounds"][1].update(date=cap["rounds"][0]["date"]),
            "fractional issued shares": lambda cap, inputs: inputs[cap["rounds"][0]["subscriptions"][0]["amount"]].update(value="51"),
            "nonnegative whole shares": lambda cap, inputs: inputs[cap["holders"][0]["shares"]].update(value="79.5"),
            "positive opening": lambda cap, inputs: [inputs[row["shares"]].update(value="0") for row in cap["holders"]],
            "top-up needs an option pool": lambda cap, inputs: cap["holders"][1].update(kind="holder"),
            "one unallocated option pool": lambda cap, inputs: cap["holders"][2].update(kind="option_pool"),
            "invalid or duplicate": lambda cap, inputs: cap["rounds"][0]["subscriptions"][0].update(holder="H2"),
            "reused across holders": lambda cap, inputs: cap["rounds"][0]["subscriptions"].append(
                {"holder": "H4", "amount": cap["rounds"][0]["subscriptions"][0]["amount"]}),
        }
        for pattern, edit in edits.items():
            with self.subTest(guard=pattern):
                self.setUp()
                edit(self.model["cap_table"], self.inputs)
                self.reject(pattern)

    def test_scenario_guardrails(self):
        def clear_round(case, month):
            case["months"][month]["round_ids"] = []

        for guard in ("horizon", "prefix", "not_date", "missing_round", "cash_tax", "opening"):
            with self.subTest(guard=guard):
                self.setUp()
                plan = self.model["scenarios"]
                cases = plan["cases"]
                if guard == "horizon":
                    cases["upside"]["months"].pop()
                    pattern = "identical monthly horizon"
                elif guard == "prefix":
                    clear_round(cases["upside"], 3)
                    pattern = "ordered prefix"
                elif guard == "not_date":
                    cases["base"]["months"][2]["round_ids"] = ["RND1"]
                    pattern = "outside the forecast month"
                elif guard == "missing_round":
                    self.model.pop("cap_table")
                    pattern = "Unknown reference in scenario financing"
                elif guard == "cash_tax":
                    self.inputs[cases["base"]["months"][0]["cash_tax"]]["value"] = "-1"
                    pattern = "must be nonnegative"
                else:
                    self.inputs[plan["opening_cash"]]["value"] = "-1"
                    self.bundle["metrics"].pop(1)
                    pattern = "Opening unrestricted cash"
                self.reject(pattern)

    def test_dcf_gating_for_underwriting_stage_and_unsupported_terminal(self):
        for guard in ("stage", "lending", "independent", "terminal", "two_years", "dependency", "excess_cash"):
            with self.subTest(guard=guard):
                self.setUp()
                request = self.model["dcf"]
                if guard == "stage":
                    self.bundle["metrics"].clear()
                    self.bundle["profile"]["stage"] = "concept"
                    pattern = "ineligible for this business model or stage"
                elif guard == "lending":
                    with_model(self.bundle, "lending")
                    pattern = "ineligible for this business model or stage"
                elif guard == "independent":
                    request["eligibility_evidence_ids"] = ["E1"]
                    pattern = "independent A/B"
                elif guard == "terminal":
                    request["scenario"] = "downside"
                    pattern = "positive normalised final-year"
                elif guard == "two_years":
                    for case in self.model["scenarios"]["cases"].values():
                        case["months"].pop()
                    pattern = "two complete annual FCFF"
                elif guard == "dependency":
                    self.model.pop("scenarios")
                    pattern = "needs calculated linked scenarios"
                else:
                    self.inputs[request["bridge"]["excess_cash"]]["value"] = "101"
                    pattern = "excess cash must fit"
                self.reject(pattern)

    def test_wacc_and_sensitivity_domain_guards(self):
        for key, invalid in (("cost_of_equity", "0"), ("pretax_cost_of_debt", "0"),
                             ("debt_weight", "1"), ("tax_rate", "1.01")):
            with self.subTest(wacc=key):
                self.setUp()
                self.inputs[self.model["dcf"]["wacc"][key]]["value"] = invalid
                self.reject("invalid WACC")
        for guard, values, pattern in (
            ("terminal_growth", "0.1", "terminal growth < WACC"),
            ("terminal_growth", "-1", "terminal growth < WACC"),
            ("sensitivity_wacc", ("0.11", "0.12"), "bracket base WACC"),
            ("sensitivity_wacc", ("0.025", "0.12"), "terminal growth < WACC"),
            ("sensitivity_wacc", ("0", "0.12"), "WACC > 0"),
        ):
            with self.subTest(guard=guard, values=values):
                self.setUp()
                dcf = self.model["dcf"]
                if guard == "terminal_growth":
                    self.inputs[dcf[guard]]["value"] = values
                else:
                    for input_id, value in zip(dcf["sensitivity"]["wacc"], values, strict=True):
                        self.inputs[input_id]["value"] = value
                self.reject(pattern)

    def test_forecast_source_period_currency_and_quantity_binding(self):
        for key, value, pattern in (
            ("quantity", "normalised_ebitda", "expected ebit"),
            ("unit", "money_per_month", "expected ebit in money"),
            ("currency", "EUR", "incompatible currency"),
            ("entity", "Other entity", "incompatible entity"),
            ("accounting_basis", "ifrs", "incompatible entity or accounting basis"),
            ("period", "2026-12-01/2026-12-30", "wrong period"),
            ("period", "2026-12-31/2026-12-01", "Period start follows end"),
            ("basis", "observed", "observed period extends past"),
            ("evidence_ids", ["E9999"], "Unknown reference in financial operand"),
            ("evidence_ids", [], "non-empty"),
            ("rationale", " ", "input needs a source rationale"),
        ):
            with self.subTest(field=key):
                self.setUp()
                row = self.model["scenarios"]["cases"]["base"]["months"][0]
                self.inputs[row["ebit"]][key] = value
                self.reject(pattern)

    def test_financial_challenges_and_source_claims_block_only_dependent_results(self):
        for affected in ("dcf", "RND1", "scenarios", "C1", "E1"):
            with self.subTest(affected=affected):
                self.setUp()
                self.bundle["challenges"][0]["affected"] = [affected]
                self.reject("unresolved critical challenge")
        self.setUp()
        self.bundle["claims"][0].update(status="disputed", oppose=["E2"])
        self.reject("unresolved, incompatible or unrelated financial claim")

    def test_unavailable_results_are_null_and_require_specific_gaps(self):
        self.bundle = json.loads(SPARSE)
        result = self.evaluated()
        for item in (result["metrics"]["M1"], result["valuations"]["V1"]):
            self.assertEqual(item["status"], "unavailable")
            self.assertIsNone(item["value"])
            self.assertTrue(item["gap_ids"])
        for key in ("cap_table", "scenarios", "dcf"):
            self.assertEqual(result[key]["status"], "unavailable")
            self.assertIsNone(result[key]["value"])
        self.bundle["metrics"][0]["value"] = "0"
        self.reject("Unavailable result must be null")
        self.bundle["metrics"][0]["value"] = None
        self.bundle["financial_model"]["dcf"]["gap_ids"] = ["G99"]
        self.reject("Unknown reference in dcf missing information")

    def test_legacy_multiple_with_typed_sources_and_no_observed_forecast_mixture(self):
        revenue = self.bundle["metrics"][0]["operands"]["revenue"]
        source = self.inputs[self.model["dcf"]["terminal_growth"]]
        multiple = {**source, "id": "I999", "quantity": "comparable_ev_revenue_multiple", "value": "2",
                    "period": self.inputs[revenue]["period"], "label": "Synthetic peer set EV/revenue multiple"}
        self.bundle["inputs"].append(multiple)
        row = self.bundle["valuations"][0]
        row.pop("gap_ids")
        row.update(status="calculated", value="200000", operands={"revenue": revenue, "multiple": "I999"})
        result = self.evaluated()["valuations"]["V1"]
        self.assertEqual(result["value"], "200000")
        self.assertEqual(result["basis"], "scenario")
        multiple["basis"] = "observed"
        self.reject("expected assumption basis")
        multiple.update(basis="assumption", evidence_ids=["E1"])
        self.reject("independent A/B evidence")

    def test_legacy_renderer_reads_complete_and_sparse_v12(self):
        spec = importlib.util.spec_from_file_location("renderer", ROOT / "report-kit/render.py")
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)
        for fixture, markers in (
            (COMPLETE, ("1,472.73", "1,442.73", "RND2", "existing-share dilution", "residual capital required USD 10")),
            (SPARSE, ("Discounted cash flow unavailable", "Monthly scenarios unavailable", "Cap table unavailable")),
        ):
            with self.subTest(markers=markers):
                digest = hashlib.sha256(fixture.encode()).hexdigest()
                report = convert(json.loads(fixture), digest)
                renderer.validate(report)
                self.assertEqual(report["version"], "1.0")
                output = renderer.report_html(report)
                for marker in ("Open standard v1.2", digest, *markers):
                    self.assertIn(marker, output)


METRIC_CASES = {
    "saas_arr": ("2026-11-30", {"mrr": "10.25"}, "123"),
    "saas_logo_churn": ("2026-11-01/2026-11-30", {"churned": "2", "opening": "8"}, "0.25"),
    "marketplace_match_rate": ("2026-11-01/2026-11-30", {"matched": "70", "eligible": "100"}, "0.7"),
    "manufacturing_first_pass_yield": ("2026-11-01/2026-11-30", {"passed": "90", "processed": "100"}, "0.9"),
    "manufacturing_cash_conversion_days": ("2026-11-01/2026-11-30", {
        "inventory": "15", "cogs": "30", "receivables": "10", "credit_sales": "20", "payables": "30",
        "credit_purchases": "60",
    }, "15"),
    "lending_net_charge_off_rate": ("2025-12-01/2026-11-30", {
        "charge_offs": "10", "recoveries": "4", "average_loans": "300",
    }, "0.02"),
    "lending_par30": ("2026-11-30", {"past_due": "15", "portfolio": "300"}, "0.05"),
    "consumer_repeat_purchase_rate": ("2026-11-01/2026-11-30", {"repeat": "3", "eligible": "10"}, "0.3"),
    "services_billable_utilisation": ("2026-11-01/2026-11-30", {"billed": "120", "available": "160"}, "0.75"),
}


class ModelMetricTests(unittest.TestCase):
    def make_metric(self, formula):
        bundle = json.loads(COMPLETE)
        bundle["financial_model"] = {k: bundle["financial_model"][k] for k in ("accounting_basis", "currency")}
        bundle["metrics"] = []
        bundle["valuations"] = []
        bundle["inputs"] = []
        model, _, _, operands, _ = MODEL_METRICS[formula]
        if model not in bundle["profile"]["models"]:
            with_model(bundle, model)
        period, values, answer = METRIC_CASES[formula]
        row = {"id": "M1", "formula": formula, "status": "calculated", "basis": "observed",
               "value": answer, "reason": "Synthetic known-answer operands.", "operands": {}}
        for idx, (key, (quantity, unit)) in enumerate(operands.items(), 1):
            input_id = f"I{idx}"
            row["operands"][key] = input_id
            bundle["inputs"].append({
                "id": input_id, "quantity": quantity, "unit": unit, "value": values[key], "period": period,
                "currency": "USD" if unit.startswith("money") else None, "entity": bundle["profile"]["legal_entity"],
                "accounting_basis": "us_gaap", "basis": "observed", "claim_ids": [],
                "rationale": "Synthetic known-answer input.", "label": key, "evidence_ids": ["E1"],
            })
        bundle["metrics"].append(row)
        return bundle, row

    def test_every_new_formula_from_bundle_to_known_answer(self):
        self.assertEqual(METRIC_CASES.keys(), MODEL_METRICS.keys())
        for formula, (_, _, _, _, unit) in MODEL_METRICS.items():
            with self.subTest(formula=formula):
                bundle, _ = self.make_metric(formula)
                result = validate(bundle)["financial_model"]["metrics"]["M1"]
                self.assertEqual(result["value"], METRIC_CASES[formula][2])
                self.assertEqual(result["unit"], unit)
                self.assertEqual(result["evidence_ids"], ["E1"])

    def test_each_new_formula_blocks_wrong_stage_model_and_negative_inputs(self):
        for formula in MODEL_METRICS:
            for guard in ("stage", "model", "negative", "wrong_arithmetic", "zero"):
                with self.subTest(formula=formula, guard=guard):
                    bundle, row = self.make_metric(formula)
                    if guard == "stage":
                        bundle["profile"]["stage"] = "development"
                    elif guard == "model":
                        bundle["profile"]["models"] = []
                        with_model(bundle, "other")
                    elif guard == "negative":
                        bundle["inputs"][0]["value"] = "-1"
                    elif guard == "wrong_arithmetic":
                        row["value"] = "999"
                    elif guard == "zero":
                        row["value"] = "0"
                    pattern = ("ineligible" if guard in ("stage", "model") else
                               "negative input" if guard == "negative" else "Calculation mismatch")
                    with self.assertRaisesRegex(ValueError, pattern):
                        validate(bundle)

    def test_positive_denominators_and_compatible_cohorts(self):
        for formula in MODEL_METRICS.keys() - {"saas_arr"}:
            with self.subTest(formula=formula):
                bundle, _ = self.make_metric(formula)
                bundle["inputs"][-1]["value"] = "0"
                with self.assertRaisesRegex(ValueError, "positive"):
                    validate(bundle)
        bundle, _ = self.make_metric("manufacturing_cash_conversion_days")
        for index in (1, 3, 5):
            with self.subTest(input=index):
                altered = copy.deepcopy(bundle)
                altered["inputs"][index]["value"] = "0"
                with self.assertRaisesRegex(ValueError, "denominators must be positive"):
                    validate(altered)
        bundle, _ = self.make_metric("manufacturing_first_pass_yield")
        for invalid, pattern in (("101", "numerator must fit"), ("90.5", "fractional count")):
            bundle["inputs"][0]["value"] = invalid
            with self.assertRaisesRegex(ValueError, pattern):
                validate(bundle)

    def test_metric_periods_and_basis_and_negative_net_charge_off(self):
        bundle, row = self.make_metric("lending_net_charge_off_rate")
        bundle["inputs"][1]["value"] = "13"
        row["value"] = "-0.01"
        self.assertEqual(validate(bundle)["financial_model"]["metrics"]["M1"]["value"], "-0.01")
        for operand in bundle["inputs"]:
            operand["period"] = "2026-11-01/2026-11-30"
        with self.assertRaisesRegex(ValueError, "full 12-month period"):
            validate(bundle)
        bundle, row = self.make_metric("marketplace_match_rate")
        bundle["inputs"][0]["period"] = "2026-10-01/2026-10-31"
        with self.assertRaisesRegex(ValueError, "mixed periods"):
            validate(bundle)
        bundle["inputs"][0]["period"] = bundle["inputs"][1]["period"]
        row["basis"] = "scenario"
        with self.assertRaisesRegex(ValueError, "expected assumption basis"):
            validate(bundle)
        for operand in bundle["inputs"]:
            operand["basis"] = "assumption"
        self.assertEqual(validate(bundle)["financial_model"]["metrics"]["M1"]["basis"], "scenario")
        bundle, _ = self.make_metric("saas_arr")
        bundle["inputs"][0]["period"] = "2026-11-01/2026-11-30"
        with self.assertRaisesRegex(ValueError, "point period"):
            validate(bundle)


if __name__ == "__main__":
    unittest.main()
