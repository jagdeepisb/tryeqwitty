import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"analysis-kit"))
from validate import validate,compute
from to_report import convert
from decimal import Decimal
class ContractTests(unittest.TestCase):
    def setUp(self):
        self.full=json.loads((ROOT/"benchmarks/reported-saas.json").read_text())
        self.sparse=json.loads((ROOT/"benchmarks/sparse-manufacturing.json").read_text())
    def test_sparse(self):
        self.assertEqual(validate(self.sparse)["assessed"],0)
    def test_full(self):
        self.assertEqual(validate(self.full)["assessed"],1)
    def test_bridge(self):
        spec=importlib.util.spec_from_file_location("renderer",ROOT/"report-kit/render.py")
        r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
        r.validate(convert(self.full,"0"*64))
        r.validate(convert(self.sparse,"0"*64))
    def test_bad_arithmetic(self):
        self.full["metrics"][0]["value"]="0.7"
        with self.assertRaises(ValueError):validate(self.full)
    def test_missing_factor(self):
        self.full["factors"].pop()
        with self.assertRaises(ValueError):validate(self.full)
    def test_false_verified(self):
        self.full["claims"][0]["status"]="verified"
        with self.assertRaises(ValueError):validate(self.full)
    def test_currency(self):
        self.full["inputs"][1]["currency"]="EUR"
        with self.assertRaises(ValueError):validate(self.full)
    def test_zero_denominator(self):
        self.full["inputs"][0]["value"]="0"
        with self.assertRaises(ValueError):validate(self.full)
    def test_assumed_observed(self):
        self.full["inputs"][0]["basis"]="assumption"
        with self.assertRaises(ValueError):validate(self.full)
    def test_unknown_not_zero(self):
        self.sparse["metrics"][0]["value"]="0"
        with self.assertRaises(ValueError):validate(self.sparse)
    def test_unresolved(self):
        self.full["decision"]["status"]="complete_within_scope"
        with self.assertRaises(ValueError):validate(self.full)
    def test_valuation_basis(self):
        self.full["valuations"][0].update(status="calculated",value="100000",value_basis="equity")
        with self.assertRaises(ValueError):validate(self.full)
    def test_multiple_math(self):
        inputs={i["id"]:i for i in self.full["inputs"]}
        inputs["I5"]={**inputs["I1"],"unit":"ratio","currency":None,"value":"3","basis":"assumption"}
        self.assertEqual(compute("ev_revenue",{"revenue":"I1","multiple":"I5"},inputs,"scenario","Synthetic multiple"),Decimal("300000"))
    def test_wrong_period(self):
        self.full["inputs"][1]["period"]="FY2025"
        with self.assertRaises(ValueError):validate(self.full)
    def test_no_research_task(self):
        self.full["research"]=[]
        with self.assertRaises(ValueError):validate(self.full)
    def test_missing_evidence(self):
        self.full["inputs"][0]["evidence_ids"]=[]
        with self.assertRaises(ValueError):validate(self.full)
    def test_conflicting_evidence(self):
        self.full["claims"][0]["oppose"]=["E1"]
        with self.assertRaises(ValueError):validate(self.full)
if __name__=="__main__":unittest.main()
