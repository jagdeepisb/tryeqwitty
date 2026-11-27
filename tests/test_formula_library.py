"""Independent known-answer arithmetic cases for every supported formula."""
import sys
from pathlib import Path
import unittest
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"analysis-kit"))
from validate import FORMULAS,compute
CASES={
 "revenue_growth":({"current":"150","prior":"100"},"0.5"),
 "gross_margin":({"revenue":"100","cogs":"40"},"0.6"),
 "contribution_margin":({"revenue":"100","variable_cost":"25"},"0.75"),
 "ebitda_margin":({"ebitda":"-10","revenue":"100"},"-0.1"),
 "cac":({"spend":"200","customers":"10"},"20"),
 "cac_payback":({"cac":"60","monthly_contribution":"10"},"6"),
 "nrr":({"opening":"100","expansion":"20","contraction":"5","churn":"5"},"1.1"),
 "grr":({"opening":"100","contraction":"5","churn":"10"},"0.85"),
 "take_rate":({"revenue":"20","gmv":"100"},"0.2"),
 "utilisation":({"used":"80","available":"100"},"0.8"),
 "inventory_turns":({"annual_cogs":"100","avg_inventory":"25"},"4"),
 "runway":({"cash":"60","monthly_burn":"10"},"6"),
 "current_ratio":({"assets":"100","liabilities":"50"},"2"),
 "net_debt":({"debt":"30","cash":"50"},"-20"),
 "balance_sheet_gap":({"assets":"100","liabilities":"40","equity":"60"},"0"),
 "cash_flow_gap":({"closing":"120","opening":"100","operating":"30","investing":"-20","financing":"10"},"0"),
 "ev_revenue":({"revenue":"100","multiple":"3"},"300"),
 "ev_ebitda":({"ebitda":"20","multiple":"5"},"100"),
 "net_assets":({"assets":"100","liabilities":"60"},"40"),
 "ev_to_equity":({"ev":"300","debt":"50","cash":"20"},"270"),
}
class KnownAnswerTests(unittest.TestCase):
    def test_all_formula_ids_have_known_answers(self):
        self.assertEqual(set(CASES),set(FORMULAS))
        for formula,(values,expected) in CASES.items():
            with self.subTest(formula=formula):
                units=FORMULAS[formula][0]
                inputs={}
                mapping={}
                for j,(key,value) in enumerate(values.items()):
                    i="I"+str(j+1);mapping[key]=i
                    unit=units[key]
                    inputs[i]={"value":value,"unit":unit,"currency":"USD" if unit.startswith("money") else None,"entity":"Synthetic entity","period":"prior" if formula=="revenue_growth" and key=="prior" else "current","basis":"observed"}
                self.assertEqual(compute(formula,mapping,inputs,"observed","Comparable synthetic periods"),Decimal(expected))
if __name__=="__main__":unittest.main()
