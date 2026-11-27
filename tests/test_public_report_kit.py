import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]/"report-kit"
spec=importlib.util.spec_from_file_location("render",ROOT/"render.py")
render=importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)
class ReportTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/"example.json").read_text())
    def test_fixture(self):
        html=render.report_html(self.data)
        self.assertIn(render.LABEL,html)
        self.assertIn("Missing information",html)
        self.assertIn("Not estimable",html)
    def test_escaping(self):
        self.data["company"]="<script>alert(1)</script>"
        self.assertNotIn("<script>",render.report_html(self.data))
    def test_missing_ref(self):
        self.data["sections"][0]["source_ids"]=["S1"]
        with self.assertRaises(ValueError): render.validate(self.data)
    def test_order(self):
        self.data["sections"].reverse()
        with self.assertRaises(ValueError): render.validate(self.data)
    def test_no_gaps(self):
        self.data["missing_information"]=[]
        with self.assertRaises(ValueError): render.validate(self.data)
    def test_csv_formula(self):
        self.data["missing_information"][0]["item"]="=1+1"
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/"missing.csv"
            render.write_missing(self.data,p)
            self.assertIn("'=1+1",p.read_text())
    def test_invalid_url(self):
        self.data["sources"]=[{"id":"S1","title":"Test","locator":"Test","url":"javascript:alert(1)","type":"independent public source"}]
        with self.assertRaises(ValueError): render.validate(self.data)
if __name__=="__main__": unittest.main()
