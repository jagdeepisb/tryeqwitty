"""Reconcile v1.3 exhibits and exercise the offline PDF and HTML exports."""

import copy
import csv
from decimal import Decimal
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis-kit"))

from to_report import convert
from validate import validate

spec = importlib.util.spec_from_file_location("structured_renderer", ROOT / "report-kit/render.py")
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


EXAMPLES = {
    "complete": "report-complete-v1.3.json",
    "sparse": "report-sparse-v1.3.json",
    "juniper": "research-early-saas-v1.4.json",
    "cedar-pilot": "research-pilot-manufacturing-v1.4.json",
}


def benchmark(name):
    raw = (ROOT / "benchmarks" / EXAMPLES[name]).read_bytes()
    bundle = json.loads(raw)
    return bundle, convert(bundle, hashlib.sha256(raw).hexdigest())


def exhibits(report):
    return {table["caption"]: table for table in [
        *(t for section in report["sections"] for t in section["tables"]), *report["schedules"],
    ]}


def numeric_rows(table):
    return [[cell["value"] for cell in row if "value" in cell] for row in table["rows"]]


class StructuredReportTests(unittest.TestCase):
    def test_all_numeric_exhibits_match_validated_calculations(self):
        bundle, report = benchmark("complete")
        renderer.validate(report)
        result = validate(bundle)
        model = result["financial_model"]
        dcf = model["dcf"]
        inputs = {row["id"]: row for row in bundle["inputs"]}
        expected = {
            "Financial and operating metrics": [[model["metrics"][row["id"]]["value"]] for row in bundle["metrics"]],
            "Other valuation methods": [[]],
            "Factor coverage": [[str(result[k])] for k in ("applicable", "assessed", "fully_supported", "unknown")],
            "Scenario opening balances · USD": [[model["scenarios"][k]] for k in ("opening_unrestricted_cash",
                                                                                 "minimum_unrestricted_cash")],
            "Opening fully diluted ownership": [[shares, model["cap_table"]["opening"]["ownership"][holder]]
                                                for holder, shares in model["cap_table"]["opening"]["positions"].items()],
            "Annual FCFF and present values · USD": [[row["fcff"], pv] for row, pv in
                    zip(dcf["annual_fcff"], dcf["present_values_of_annual_fcff"], strict=True)],
            "Discount rate and terminal assumptions": [[inputs[input_id]["value"]]
                for input_id in (*bundle["financial_model"]["dcf"]["wacc"].values(),
                                 bundle["financial_model"]["dcf"]["terminal_growth"])] + [[dcf["wacc"]]],
            "Enterprise to equity value · USD": [[v] for v in (
                dcf["terminal_value"], dcf["present_value_of_terminal"], dcf["enterprise_value"],
                dcf["equity_bridge"]["excess_cash"], dcf["equity_bridge"]["debt"],
                dcf["equity_bridge"]["other_adjustments"], dcf["equity_value"],
            )],
        }
        for term in model["cap_table"]["rounds"]:
            expected[f"{term['id']} financing terms · USD"] = [[term[k] for k in row] for row in (
                ("pre_money_equity_value", "new_primary_cash"), ("post_money_equity_value", "issue_price_per_share"),
                ("pre_round_fully_diluted_shares", "post_round_fully_diluted_shares"),
                ("pool_top_up_shares", "existing_share_dilution"),
            )]
            expected[f"{term['id']} ownership and dilution"] = [
                [row[k] for k in ("shares_after", "ownership_before", "ownership_after", "ownership_change")]
                for row in term["holders"].values()
            ]
        summary = []
        for name, case in model["scenarios"]["cases"].items():
            summary.append([
                case["months"][-1]["closing_cash"], case["capital_required_before_linked_rounds"],
                case["residual_capital_required"], str(case["runway_before_linked_rounds"]["months"]),
                str(case["runway_after_linked_rounds"]["months"]),
            ])
            expected[f"{name.title()} monthly cash · USD"] = [
                [m[k] for k in ("fcff", "other_cash_flow", "linked_round_cash", "net_cash_flow", "closing_cash",
                                "residual_floor_gap")] for m in case["months"]
            ]
            for projected, validated in zip(
                exhibits(report)[f"{name.title()} monthly cash · USD"]["rows"], case["months"], strict=True
            ):
                self.assertEqual(set(projected[0]["input_ids"]), set(validated["operands"].values()))
        expected["Scenario cash and funding requirements · USD"] = summary
        for name in ("Enterprise", "Equity"):
            grid = dcf["sensitivity"]
            expected[f"{name} value sensitivity · USD"] = [
                [grid[i]["wacc"], *(cell[f"{name.lower()}_value"] for cell in grid[i:i + 3])]
                for i in range(0, len(grid), 3)
            ]
        actual = {name: numeric_rows(table) for name, table in exhibits(report).items()}
        self.assertEqual({name: rows for name, rows in actual.items() if any(rows)},
                         {name: rows for name, rows in expected.items() if any(rows)})

    def test_claim_links_competitor_unknowns_charts_and_exact_values(self):
        bundle, report = benchmark("complete")
        tables = exhibits(report)
        c2 = tables["Claim evidence matrix"]["rows"][1]
        self.assertEqual(c2[2]["source_ids"], ["E5"])
        self.assertEqual(c2[3]["source_ids"], ["E6"])
        competitor = tables["CC1 · Finance workflow alternatives"]["rows"][1]
        self.assertEqual(competitor[1]["text"], "Unknown")
        self.assertEqual(competitor[1]["gap_ids"], ["G3"])
        self.assertEqual(competitor[2]["text"], "USD 35 per month")
        self.assertEqual(report["operands"], bundle["inputs"])
        page = renderer.report_html(report)
        self.assertIn('scope="col"', page)
        self.assertIn('scope="row"', page)
        for target in ("source-E5", "source-E6", "gap-G3", "input-I1"):
            self.assertIn(f'href="#{target}"', page)
            self.assertIn(f'id="{target}"', page)
        self.assertEqual(re.findall(r'class="chart-value">([^<]+)', page),
                         ["-260", "30", "210", "300", "300", "60", "10", "0", "0"])
        self.assertIn("#3b82f6 0.000000%, #3b82f6 55.319149%", page)
        self.assertIn('data-value="1472.727', page)
        self.assertIn(">1,472.73</span>", page)
        self.assertEqual(renderer.number_display("0.00000002", "amount"), "2.000E-8")
        self.assertEqual(renderer.number_display("-0.02", "percentage_points"), "-2 pp")

    def test_optional_brief_preserves_material_information_and_full_output(self):
        _, report = benchmark("juniper")
        snapshot = copy.deepcopy(report)
        full = renderer.report_html(report)
        brief = renderer.report_html(report, brief=True)
        self.assertEqual(report, snapshot)
        self.assertEqual(renderer.report_html(report), full)
        self.assertIn("Decision brief.", brief)
        self.assertIn("Decision subject to further evidence:", brief)
        self.assertIn("The available records did not support a like-for-like competitor comparison.", brief)
        self.assertNotIn("Observed · formula v1.2", brief)
        self.assertIn("Reported inputs", brief)
        self.assertIn("lower-priority unknown factors", brief)
        self.assertIn("Factor coverage", brief)
        self.assertIn("Red-team corrections", brief)
        self.assertNotIn("Planned questions and recorded outcomes", brief)
        self.assertNotIn("Calculation operands", brief)
        self.assertLess(len(brief), len(full))
        for source in report["sources"]:
            self.assertIn(f'id="source-{source["id"]}"', brief)
        for gap in report["missing_information"]:
            self.assertIn(f'id="gap-{gap["id"]}"', brief)
        self.assertNotIn("\u2014", brief)

    def test_financing_brief_retains_figures_with_plain_labels(self):
        _, report = benchmark("complete")
        before = copy.deepcopy(report)
        full = renderer.report_html(report)
        brief = renderer.report_html(report, brief=True)
        self.assertIn("Financing round 1: financing terms", brief)
        self.assertNotIn("RND1 financing terms", brief)
        self.assertIn("1,472.73", brief)
        self.assertIn("Closing cash by scenario", brief)
        self.assertNotIn("Monthly cash schedules</h2>", brief)
        self.assertEqual(report, before)
        self.assertEqual(renderer.report_html(report), full)

    def test_reader_publication_links_and_punctuation(self):
        _, report = benchmark("complete")
        original = copy.deepcopy(report)
        report["sections"][0]["paragraphs"].append("Evidence E5 and E6 \u2014 assess the variance.")
        snapshot = copy.deepcopy(report)
        page = renderer.report_html(report)
        self.assertRegex(page, r'<a href="#source-E5"[^>]*>E5</a> and <a href="#source-E6"[^>]*>E6</a>')
        self.assertNotIn("\u2014", page)
        self.assertNotIn("Standard commit", page)
        self.assertNotIn("Bundle SHA-256", page)
        self.assertEqual(report, snapshot)
        self.assertEqual(report["methodology"], original["methodology"])
        report["sections"][0]["paragraphs"].append("Fallback export")
        with self.assertRaisesRegex(ValueError, "editorial check"):
            renderer.report_html(report)

    def test_sparse_withholds_financial_values_and_charts(self):
        _, report = benchmark("sparse")
        data = exhibits(report)
        for name in ("Discounted cash flow", "Monthly cash and runway", "Capitalisation and dilution"):
            self.assertEqual(data[name]["rows"][0][0]["text"], "Unavailable")
            self.assertTrue(data[name]["rows"][0][1]["gap_ids"])
        numeric = {name for name, table in data.items() if any(numeric_rows(table))}
        self.assertEqual(numeric, {"Factor coverage"})
        matrix = data["Material factors and evidence matrix"]
        self.assertEqual(matrix["headers"], ["Factor", "Assessment"])
        self.assertIn("No supporting or opposing evidence", matrix["note"])
        self.assertFalse(report["schedules"])
        page = renderer.report_html(report)
        self.assertNotIn('class="chart"', page)
        self.assertIn("Source records unavailable", page)

    def test_pricing_dispute_links_to_the_two_price_sources(self):
        _, report = benchmark("complete")
        difference = exhibits(report)["Thesis differences"]["rows"][0]
        self.assertEqual(difference[0]["source_ids"], ["E5", "E6"])

    def test_example_findings_and_requests_answer_each_question(self):
        for path in sorted((ROOT / "benchmarks").glob("*.json")):
            bundle = json.loads(path.read_bytes())
            with self.subTest(example=path.name):
                documents = bundle["documents"]
                self.assertEqual(len({d["limitations"] for d in documents}), len(documents), "document limitations")
                factors = bundle["factors"]
                for field in ("finding", "next_test"):
                    self.assertEqual(len({f[field] for f in factors}), len(factors), field)
                for gap in bundle["gaps"]:
                    self.assertNotRegex(gap["conclusion"], r"\b(?:C|MF|ST|SA|OB)\d{2}\b")
        _, report = benchmark("complete")
        opening = report["sections"][0]["paragraphs"][0]
        for measure in ("12 to 22 months", "USD 10", "USD 40"):
            self.assertIn(measure, opening)

    def test_legacy_bundle_default_and_explicit_structured_format(self):
        path = ROOT / "benchmarks" / "reported-saas.json"
        bundle = json.loads(path.read_text())
        self.assertEqual(convert(bundle, "0" * 64)["version"], "1.0")
        upgraded = convert(bundle, "0" * 64, "1.3")
        self.assertEqual(upgraded["methodology"]["version"], "1.1")
        self.assertIn("data-value=\"0.6\"", renderer.report_html(upgraded))
        v12 = json.loads((ROOT / "benchmarks/financial-model-v1.2.json").read_text())
        self.assertEqual(convert(v12, "0" * 64)["version"], "1.0")
        structured = convert(v12, "0" * 64, "1.3")
        self.assertEqual(structured["methodology"]["version"], "1.2")
        renderer.validate(structured)

    def test_rejects_unbound_or_incompatible_competitor_cells(self):
        bundle, _ = benchmark("complete")
        cases = [
            ("unavailable comparator cell must be null", lambda x: x["criteria"][1]["cells"]["subject"].update(value="0")),
            ("independent comparator value needs A/B", lambda x: x["criteria"][0]["cells"]["maple"].update(evidence_ids=["E5"])),
            ("comparison value needs evidence", lambda x: x["criteria"][0]["cells"]["subject"].update(evidence_ids=[])),
            ("one cell per criterion", lambda x: x["criteria"][0]["cells"].update(unknown=x["criteria"][0]["cells"].pop("maple"))),
            ("Unknown reference in CC1 competitor gap", lambda x: x["criteria"][1]["cells"]["subject"].update(gap_ids=["G900"])),
        ]
        for error, alter in cases:
            with self.subTest(error=error):
                changed = copy.deepcopy(bundle)
                alter(changed["competitor_comparisons"][0])
                with self.assertRaisesRegex(ValueError, error):
                    validate(changed)

    def test_exhibit_validation_and_output_escaping(self):
        _, report = benchmark("complete")
        for kind, value in (("source_ids", ["E999"]), ("gap_ids", ["G999"]), ("input_ids", ["I999"])):
            with self.subTest(reference=kind):
                broken = copy.deepcopy(report)
                exhibits(broken)["Factor coverage"]["rows"][0][0][kind] = value
                with self.assertRaisesRegex(ValueError, f"Unknown exhibit {kind}"):
                    renderer.validate(broken)
        chart = exhibits(report)["Scenario cash and funding requirements · USD"]
        chart["charts"][0]["columns"] = [8]
        with self.assertRaisesRegex(ValueError, "outside its exhibit"):
            renderer.validate(report)
        chart["charts"][0]["columns"] = [1]
        chart["rows"][0][0]["text"] = '<img src="https://example.com/a">'
        page = renderer.report_html(report)
        self.assertNotIn("<img", page)
        self.assertIn("&lt;img", page)
        with self.assertRaises(ValueError):
            renderer.deny_fetch("https://example.com/a")

    def test_reference_html_csv_match_current_render(self):
        for sample in EXAMPLES:
            _, report = benchmark(sample)
            path = ROOT / "report-kit/reference" / sample
            fresh_html = renderer.report_html(report)
            self.assertEqual(fresh_html, (path / "assessment.html").read_text(encoding="utf-8"))
            self.assertNotIn("Bundle SHA-256", fresh_html)
            self.assertNotIn("Standard commit", fresh_html)
            with TemporaryDirectory() as tmp:
                output = Path(tmp) / "missing-information.csv"
                renderer.write_missing(report, output)
                self.assertEqual(output.read_bytes(), (path / output.name).read_bytes())
                rows = list(csv.DictReader(io.StringIO(output.read_text())))
                self.assertEqual(sorted(row["id"] for row in rows),
                                 sorted(row["id"] for row in report["missing_information"]))


def poppler(command, pdf, *args):
    return subprocess.run([command, *args, str(pdf)], check=True, capture_output=True, text=True).stdout


class PDFRenderingTests(unittest.TestCase):
    def test_reference_pdfs_and_fresh_exports(self):
        missing = [name for name in ("pdftotext", "pdfinfo", "pdffonts", "pdftoppm") if not shutil.which(name)]
        if importlib.util.find_spec("weasyprint") is None:
            missing.append("WeasyPrint")
        if missing:
            message = "PDF checks require " + ", ".join(missing)
            if os.environ.get("EQWITTY_REQUIRE_PDF_CHECKS") == "1":
                self.fail(message)
            self.skipTest(message)

        markers = {
            "complete": ("Harbour Ledger", "Claim evidence matrix", "Maple Relay", "Finance workflow alternatives",
                         "Closing cash by scenario", "Equity value sensitivity", "1,472.73", "1,442.73", "-260",
                         "Downside monthly cash", "Upside monthly cash"),
            "juniper": ("Juniper Workflows", "Two accounts paid", "signed", "recurring revenue", "G4", "G5"),
            "cedar-pilot": ("Cedar Components", "one supervised shift", "unit", "equipment", "G2"),
            "sparse": ("Cedar Components", "Monthly cash and runway", "Discounted cash flow", "Unavailable",
                       "Source records unavailable", "G3"),
        }
        for sample, required in markers.items():
            _, report = benchmark(sample)
            with TemporaryDirectory() as tmp:
                fresh = Path(tmp) / "assessment.pdf"
                fresh.write_bytes(renderer.pdf_bytes(report))
                release = ROOT / "report-kit/reference" / sample / fresh.name
                for pdf in (fresh, release):
                    with self.subTest(fixture=sample, file=str(pdf)):
                        info = poppler("pdfinfo", pdf)
                        self.assertRegex(info, r"Tagged:\s+yes")
                        text = subprocess.run(
                            ["pdftotext", "-layout", str(pdf), "-"], check=True, capture_output=True, text=True
                        ).stdout
                        for marker in required:
                            self.assertIn(marker, " ".join(text.split()))
                        self.assertIn("Methodology v", text)
                        self.assertNotIn("\u2014", text)
                        self.assertNotIn("Bundle SHA-256", text)
                        self.assertNotIn("Renderer v", text)
                        self.assertNotIn("\ufffd", text)
                        fonts = [line.split() for line in poppler("pdffonts", pdf).splitlines()[2:] if line.strip()]
                        for name in ("Space-Grotesk", "DM-Sans"):
                            self.assertTrue(any(name in f[0] and f[-5:-2] == ["yes", "yes", "yes"] for f in fonts))
                        dests = poppler("pdfinfo", pdf, "-dests")
                        self.assertIn("gap-G1", dests)
                        urls = poppler("pdfinfo", pdf, "-url")
                        for source in report["sources"]:
                            if source["url"]:
                                self.assertIn(source["url"], urls)
                                self.assertIn("source-" + source["id"], dests)
                        self.assert_page_bounds(pdf)
                        if sample == "complete":
                            self.assert_charts_painted(pdf, text)

    def assert_charts_painted(self, pdf, text):
        from PIL import Image

        for caption, color in (("Closing cash by scenario", (59, 130, 246)),
                               ("Capital required before and after linked equity rounds", (36, 77, 133))):
            page = next(n for n, content in enumerate(text.split("\f"), 1) if caption in " ".join(content.split()))
            image = subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-singlefile",
                                    "-r", "72", "-png", str(pdf)], check=True, capture_output=True).stdout
            with Image.open(io.BytesIO(image)) as png:
                pixels = png.convert("RGB")
                counts = dict((rgb, count) for count, rgb in pixels.getcolors(pixels.width * pixels.height))
            self.assertGreater(counts.get(color, 0), 50, f"Chart bars missing for {caption}")

    def assert_page_bounds(self, pdf):
        bbox = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"], check=True,
                              capture_output=True, text=True).stdout
        root = ElementTree.fromstring(bbox)
        pages = root.findall(".//{*}page")
        self.assertTrue(pages)
        for page in pages:
            width, height = (Decimal(page.attrib[k]) for k in ("width", "height"))
            words = page.findall("{*}word")
            self.assertGreater(len(words), 15, "Blank or clipped page")
            for word in words:
                left, top, right, bottom = (Decimal(word.get(k)) for k in ("xMin", "yMin", "xMax", "yMax"))
                self.assertTrue(0 <= left < right <= width and 0 <= top < bottom <= height, word.text)


if __name__ == "__main__":
    unittest.main()
