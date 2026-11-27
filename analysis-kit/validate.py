"""Public v1.1 analytical contract; deterministic checks are not factual verification."""
import argparse
from decimal import Decimal, localcontext
import json
from pathlib import Path
from urllib.parse import urlsplit
from jsonschema import Draft202012Validator, FormatChecker
ROOT=Path(__file__).resolve().parents[1]
SCHEMA=json.loads((ROOT/"schemas/analysis-bundle.json").read_text())
LIB=json.loads((ROOT/"factor-library/factors.json").read_text())
D=Decimal
# name -> (operand names and units, operation, denominator checks)
FORMULAS={
 "revenue_growth":({"current":"money","prior":"money"},lambda x:x["current"]/x["prior"]-1,("prior",)),
 "gross_margin":({"revenue":"money","cogs":"money"},lambda x:(x["revenue"]-x["cogs"])/x["revenue"],("revenue",)),
 "contribution_margin":({"revenue":"money","variable_cost":"money"},lambda x:(x["revenue"]-x["variable_cost"])/x["revenue"],("revenue",)),
 "ebitda_margin":({"ebitda":"money","revenue":"money"},lambda x:x["ebitda"]/x["revenue"],("revenue",)),
 "cac":({"spend":"money","customers":"count"},lambda x:x["spend"]/x["customers"],("customers",)),
 "cac_payback":({"cac":"money_per_customer","monthly_contribution":"money_per_customer_month"},lambda x:x["cac"]/x["monthly_contribution"],("monthly_contribution",)),
 "nrr":({"opening":"money","expansion":"money","contraction":"money","churn":"money"},lambda x:(x["opening"]+x["expansion"]-x["contraction"]-x["churn"])/x["opening"],("opening",)),
 "grr":({"opening":"money","contraction":"money","churn":"money"},lambda x:(x["opening"]-x["contraction"]-x["churn"])/x["opening"],("opening",)),
 "take_rate":({"revenue":"money","gmv":"money"},lambda x:x["revenue"]/x["gmv"],("gmv",)),
 "utilisation":({"used":"capacity","available":"capacity"},lambda x:x["used"]/x["available"],("available",)),
 "inventory_turns":({"annual_cogs":"money","avg_inventory":"money"},lambda x:x["annual_cogs"]/x["avg_inventory"],("avg_inventory",)),
 "runway":({"cash":"money","monthly_burn":"money_per_month"},lambda x:x["cash"]/x["monthly_burn"],("monthly_burn",)),
 "current_ratio":({"assets":"money","liabilities":"money"},lambda x:x["assets"]/x["liabilities"],("liabilities",)),
 "net_debt":({"debt":"money","cash":"money"},lambda x:x["debt"]-x["cash"],()),
 "balance_sheet_gap":({"assets":"money","liabilities":"money","equity":"money"},lambda x:x["assets"]-x["liabilities"]-x["equity"],()),
 "cash_flow_gap":({"closing":"money","opening":"money","operating":"money","investing":"money","financing":"money"},lambda x:x["closing"]-x["opening"]-x["operating"]-x["investing"]-x["financing"],()),
 "ev_revenue":({"revenue":"money","multiple":"ratio"},lambda x:x["revenue"]*x["multiple"],("revenue","multiple")),
 "ev_ebitda":({"ebitda":"money","multiple":"ratio"},lambda x:x["ebitda"]*x["multiple"],("ebitda","multiple")),
 "net_assets":({"assets":"money","liabilities":"money"},lambda x:x["assets"]-x["liabilities"],()),
 "ev_to_equity":({"ev":"money","debt":"money","cash":"money"},lambda x:x["ev"]-x["debt"]+x["cash"],())
}
VALUATIONS={"ev_revenue":"enterprise","ev_ebitda":"enterprise","net_assets":"equity","ev_to_equity":"equity"}

def require(ok,msg):
    if not ok: raise ValueError(msg)

def indexed(rows,label):
    result={r["id"]:r for r in rows}
    require(len(result)==len(rows),f"Duplicate {label} IDs")
    return result

def refs(values,table,label):
    require(set(values)<=set(table),f"Unknown reference in {label}")

def number(s):
    require(len(s)<=80,"Decimal too long")
    return D(s)

def compute(formula, operands, inputs, basis, rationale):
    require(formula in FORMULAS,"Unsupported formula")
    units,fn,positive=FORMULAS[formula]
    require(set(operands)==set(units),"Operand keys do not match formula")
    refs(operands.values(),inputs,"operands")
    rows={k:inputs[v] for k,v in operands.items()}
    require(all(r["unit"]==units[k] for k,r in rows.items()),"Wrong operand unit")
    require(len({r["entity"] for r in rows.values()})==1,"Mixed entities")
    require(len({r["currency"] for r in rows.values() if r["currency"]})<=1,"Mixed currencies")
    periods={r["period"] for r in rows.values()}
    if formula=="revenue_growth":
        require(len(periods)==2 and bool(rationale.strip()),"Growth needs two comparable periods and rationale")
    else: require(len(periods)==1,"Mixed periods; reconcile before calculation")
    require(basis!="observed" or all(r["basis"]=="observed" for r in rows.values()),"Assumption in observed calculation")
    x={k:number(r["value"]) for k,r in rows.items()}
    require(all(x[k]>0 for k in positive),"Nonpositive denominator or eligibility input")
    if formula in ("nrr","grr"):
        require(all(v>=0 for v in x.values()) and x["contraction"]+x["churn"]<=x["opening"],"Invalid retention inputs")
    if formula in ("utilisation","take_rate"):
        require(all(v>=0 for v in x.values()),"Negative numerator")
    if formula=="utilisation": require(x["used"]<=x["available"],"Used capacity exceeds declared available capacity; reconcile definitions")
    if formula=="runway": require(x["cash"]>=0,"Negative unrestricted cash")
    if formula in ("cac","cac_payback"): require(all(v>=0 for v in x.values()),"Negative acquisition cost")
    if formula=="cac": require(x["customers"]==x["customers"].to_integral_value(),"Customer count must be integral")
    with localcontext() as ctx:
        ctx.prec=40
        return fn(x)

def validate(b):
    Draft202012Validator(SCHEMA,format_checker=FormatChecker()).validate(b)
    for key in ("evidence","claims","factors","research","inputs","metrics","valuations","challenges","gaps"):
        indexed(b[key],key)
    E=indexed(b["evidence"],"evidence"); C=indexed(b["claims"],"claims"); F=indexed(b["factors"],"factors")
    I=indexed(b["inputs"],"inputs"); G=indexed(b["gaps"],"gaps")
    for e in E.values():
        if e["url"]:
            u=urlsplit(e["url"])
            require(u.scheme in ("https","http") and u.hostname and not u.username and not u.password and not any(ord(c)<32 for c in e["url"]),"Unsafe evidence URL")
        require(e["accessed"]<=b["as_of"],"Evidence after analysis date")
        require(e["type"] not in ("company_material","company_public") or e["grade"] in ("C","D"),"Company-origin evidence cannot independently verify")
    def evidence_pair(row):
        refs(row["support"],E,"support"); refs(row["oppose"],E,"opposition")
        require(not set(row["support"])&set(row["oppose"]),"Same evidence used as support and opposition")
    def strong(ids):
        return any(E[k]["type"] in ("independent_public","authoritative_record") and E[k]["grade"] in ("A","B") for k in ids)
    for c in C.values():
        evidence_pair(c)
        if c["status"]=="verified": require(c["kind"]=="historical" and strong(c["support"]) and not c["oppose"],"Verified claim lacks independent evidence or has unresolved opposition")
        if c["status"] in ("disputed","contradicted"): require(bool(c["oppose"]),"Contradiction lacks opposing evidence")
        if c["status"]=="reported": require(bool(c["support"]),"Reported claim lacks source")
    refs(b["thesis"]["independent_evidence"],E,"independent thesis")
    for x in b["thesis"]["divergences"]: refs(x["claim_ids"],C,"thesis divergence")
    required={x["id"] for x in LIB["core"]}
    for m in b["profile"]["models"]: required.update(x["id"] for x in LIB["models"][m])
    require(required<=set(F),"Missing mandatory core/model factors: "+str(sorted(required-set(F))))
    for f in F.values():
        evidence_pair(f)
        if f["status"] in ("supported","partial"): require(bool(f["support"]),"Factor lacks supporting evidence")
        if f["status"]=="contradicted": require(bool(f["oppose"]),"Factor lacks opposing evidence")
        if f["status"] in ("unknown","not_applicable"): require(f["confidence"]=="unknown","Unknown/N/A factor confidence must be unknown")
        if f["confidence"]=="high": require(strong(f["support"]+f["oppose"]),"High confidence needs independent A/B evidence")
    for s in b["safeguards"]:
        refs(s["evidence_ids"],E,"safeguard")
        if s["status"]=="pass": require(bool(s["evidence_ids"]),"Unsupported safeguard pass")
    covered=set()
    for r in b["research"]:
        refs(r["factor_ids"],F,"research factor"); refs(r["evidence_ids"],E,"research evidence")
        if r["status"]=="completed": require(bool(r["queries"]) and bool(r["evidence_ids"]),"Completed research lacks recorded query/evidence")
        covered.update(r["factor_ids"])
    require({k for k,v in F.items() if v["status"]!="not_applicable"}<=covered,"Applicable factor has no research task")
    for i in I.values():
        refs(i["evidence_ids"],E,"financial operand")
        require(bool(i["currency"])==i["unit"].startswith("money"),"Currency/unit mismatch")
        if i["basis"]=="observed": require(bool(i["evidence_ids"]),"Observed input lacks evidence")
        number(i["value"])
    def verify_result(x,formula,basis):
        refs(x["operands"].values(),I,"result operand")
        if x["status"]=="unavailable": require(x["value"] is None,"Unavailable result must be null"); return
        require(x["value"] is not None,"Calculated result missing")
        expected=compute(formula,x["operands"],I,basis,x.get("reason",x.get("rationale","")))
        with localcontext() as ctx:
            ctx.prec=40
            actual=number(x["value"])
            require(abs(actual-expected)<=max(D("0.00000001"),abs(expected)*D("0.000000000001")),"Calculation mismatch "+x["id"])
    for m in b["metrics"]:
        require(m["formula"] in FORMULAS and m["formula"] not in VALUATIONS,"Unknown metric formula")
        verify_result(m,m["formula"],m["basis"])
    for v in b["valuations"]:
        if v["status"]=="calculated": require(VALUATIONS.get(v["method"])==v["value_basis"],"Wrong or unsupported valuation basis")
        verify_result(v,v["method"],"scenario")
    for method in VALUATIONS:
        vals=[v for v in b["valuations"] if v["method"]==method and v["status"]=="calculated" and v["scenario"]!="standalone"]
        if vals:
            by={v["scenario"]:number(v["value"]) for v in vals}
            require(len(vals)==3 and set(by)=={"low","base","high"} and by["low"]<=by["base"]<=by["high"],"Incomplete or inverted valuation range")
    unresolved=False
    all_ids=set(E)|set(C)|set(F)|set(I)|set(G)|{x["id"] for k in ("metrics","valuations","research") for x in b[k]}
    require(not (set(C)&set(F)), "Claim and factor identities overlap")
    for g in G.values(): refs(g["affected_factor_ids"],F,"gap factor")
    for q in b["challenges"]:
        refs(q["affected"],all_ids,"challenge affected"); refs(q["gap_ids"],G,"challenge gap")
        if q["status"]=="unresolved":
            require(bool(q["gap_ids"]),"Unresolved challenge needs missing-information request")
            unresolved |= q["severity"]=="Critical"
    applicable=[f for f in F.values() if f["status"]!="not_applicable"]
    critical_unknown=[f["id"] for f in applicable if f["priority"]=="Critical" and f["status"] in ("unknown","partial","contradicted")]
    covered_gaps={k for g in G.values() for k in g["affected_factor_ids"]}
    require(set(critical_unknown)<=covered_gaps,"Critical unresolved factor lacks a specific information request")
    if unresolved or critical_unknown or any(s["status"] in ("fail","unknown") for s in b["safeguards"]):
        require(b["decision"]["status"]=="qualified" and bool(G),"Material unresolved issue requires qualified decision and gaps")
    assessed=sum(f["status"] in ("supported","partial","contradicted") for f in applicable)
    return {"applicable":len(applicable),"assessed":assessed,"fully_supported":sum(f["status"]=="supported" for f in applicable),"unknown":sum(f["status"]=="unknown" for f in applicable),"critical_unresolved":critical_unknown,"decision_status":b["decision"]["status"]}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("bundle",type=Path);a=p.parse_args()
    require(a.bundle.stat().st_size<=5_000_000,"Bundle exceeds 5 MB")
    print(json.dumps(validate(json.loads(a.bundle.read_text(encoding="utf-8"))),indent=2))
if __name__=="__main__": main()
