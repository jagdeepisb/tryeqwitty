"""Validate the open analysis bundle and calculate the v1.2 financial model."""
import argparse
from decimal import Decimal, localcontext
import json
from pathlib import Path
from urllib.parse import urlsplit
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from contract import indexed, number, refs, require
from finance_context import COMPONENTS, FinanceContext, decimal_text
from finance_metrics import LEGACY_METRIC_UNITS, MODEL_METRICS, check_legacy, new_metric
from finance_model import calculate
from research_validation import ResearchAudit, SourceOrigins

ROOT=Path(__file__).resolve().parents[1]
SCHEMA=json.loads((ROOT/"schemas/analysis-bundle.json").read_text(encoding="utf-8"))
SCHEMA_V12=json.loads((ROOT/"schemas/analysis-bundle-v1.2.json").read_text(encoding="utf-8"))
SCHEMA_V13=json.loads((ROOT/"schemas/analysis-bundle-v1.3.json").read_text(encoding="utf-8"))
SCHEMA_V14=json.loads((ROOT/"schemas/analysis-bundle-v1.4.json").read_text(encoding="utf-8"))
REGISTRY=Registry().with_resources([
    ("analysis-bundle.json", Resource.from_contents(SCHEMA)),
    ("analysis-bundle-v1.2.json", Resource.from_contents(SCHEMA_V12)),
    ("analysis-bundle-v1.3.json", Resource.from_contents(SCHEMA_V13)),
    ("financial-model-v1.2.json", Resource.from_contents(
        json.loads((ROOT/"schemas/financial-model-v1.2.json").read_text(encoding="utf-8"))
    )),
])
SCHEMAS={"1.1": SCHEMA, "1.2": SCHEMA_V12, "1.3": SCHEMA_V13, "1.4": SCHEMA_V14}
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

def verify_financial_rows(b, inputs, finance=None):
    advanced = {"metrics": {}, "valuations": {}}
    for key, field in (("metrics", "formula"), ("valuations", "method")):
        for row in b[key]:
            row_id = row["id"]
            method = row[field]
            valuation = key == "valuations"
            is_new_metric = not valuation and finance is not None and method in MODEL_METRICS
            if not valuation:
                require(is_new_metric or method in FORMULAS and method not in VALUATIONS, "Unknown metric formula")
            if valuation and row["status"] == "calculated":
                require(VALUATIONS.get(method) == row["value_basis"], "Wrong or unsupported valuation basis")
            operand_ids = row["operands"].values()
            refs(operand_ids, inputs, "result operand")
            if row["status"] == "unavailable":
                require(row["value"] is None, "Unavailable result must be null")
                if finance is not None:
                    refs(row["gap_ids"], finance.gaps, f"{row_id} missing information")
                    reason = row["rationale" if valuation else "reason"]
                    require(bool(reason.strip()), f"{row_id}: reason required")
                    advanced[key][row_id] = {
                        field: method, "formula_version": "1.2", "status": "unavailable", "value": None,
                        "reason": reason, "gap_ids": row["gap_ids"], **finance.trace(operand_ids),
                    }
                continue
            require(row["value"] is not None, "Calculated result missing")
            basis = "scenario" if valuation else row["basis"]
            if finance is not None:
                finance.use(row_id)
                if not is_new_metric:
                    check_legacy(finance, row, method, FORMULAS[method][0], valuation=valuation)
            if is_new_metric:
                expected, unit = new_metric(finance, row)
            else:
                expected = compute(method, row["operands"], inputs, basis, row.get("reason", row.get("rationale")))
                unit = "money" if valuation else LEGACY_METRIC_UNITS[method]
            actual = number(row["value"])
            tolerance = max(D("0.00000001"), abs(expected) * D("0.000000000001"))
            if finance is not None:
                require((actual > 0) == (expected > 0) and (actual < 0) == (expected < 0),
                        "Calculation mismatch " + row_id)
            require(abs(actual - expected) <= tolerance, "Calculation mismatch " + row_id)
            if finance is not None:
                advanced[key][row_id] = {
                    field: method, "formula_version": "1.2", "status": "calculated", "basis": basis, "unit": unit,
                    "value": decimal_text(expected), **finance.trace(operand_ids),
                }
    return advanced


def validate_comparisons(comparisons, subject, evidence, gaps, strong):
    identifiers = indexed(comparisons, "competitor comparison")
    for comparison in comparisons:
        label = comparison["id"]
        companies = indexed(comparison["companies"], f"{label} company")
        require(companies.get("subject", {}).get("name") == subject, f"{label}: missing or mismatched subject")
        names = {company["name"].strip().casefold() for company in companies.values()}
        require("" not in names and len(names) == len(companies), f"{label}: blank or duplicate company names")
        criteria = {row["label"].strip().casefold() for row in comparison["criteria"]}
        require("" not in criteria and len(criteria) == len(comparison["criteria"]),
                f"{label}: blank or duplicate criteria")
        for criterion in comparison["criteria"]:
            require(criterion["cells"].keys() == companies.keys(), f"{label}: every company needs one cell per criterion")
            for cell in criterion["cells"].values():
                status = cell["status"]
                refs(cell["evidence_ids"], evidence, f"{label} competitor evidence")
                refs(cell["gap_ids"], gaps, f"{label} competitor gap")
                require(bool(cell["rationale"].strip()), f"{label}: comparison cell needs rationale")
                if status in ("unknown", "not_applicable"):
                    require(cell["value"] is None, f"{label}: unavailable comparator cell must be null")
                else:
                    require(cell["value"] is not None and bool(cell["value"].strip()) and cell["evidence_ids"],
                            f"{label}: comparison value needs evidence")
                if status == "independently_supported":
                    require(strong(cell["evidence_ids"]), f"{label}: independent comparator value needs A/B evidence")
    return identifiers


def validate(b):
    version = b.get("version") if isinstance(b, dict) else None
    require(isinstance(version, str) and version in SCHEMAS, "Unsupported analytical bundle version")
    Draft202012Validator(SCHEMAS[version], registry=REGISTRY, format_checker=FormatChecker()).validate(b)
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
    origins = SourceOrigins(E) if version == "1.4" else None
    audit = ResearchAudit(b, F, E, C, G, origins) if origins is not None else None
    if audit is not None:
        audit.validate_selection()
    def evidence_pair(row):
        refs(row["support"],E,"support"); refs(row["oppose"],E,"opposition")
        require(not set(row["support"])&set(row["oppose"]),"Same evidence used as support and opposition")
    def strong(ids):
        if origins is not None:
            return bool(origins.independent(ids))
        return any(E[k]["type"] in ("independent_public","authoritative_record") and E[k]["grade"] in ("A","B") for k in ids)
    for c in C.values():
        evidence_pair(c)
        if c["status"]=="verified": require(c["kind"]=="historical" and strong(c["support"]) and not c["oppose"],"Verified claim lacks independent evidence or has unresolved opposition")
        if c["status"] in ("disputed","contradicted"): require(bool(c["oppose"]),"Contradiction lacks opposing evidence")
        if c["status"]=="reported": require(bool(c["support"]),"Reported claim lacks source")
    refs(b["thesis"]["independent_evidence"],E,"independent thesis")
    for x in b["thesis"]["divergences"]: refs(x["claim_ids"],C,"thesis divergence")
    if audit is None:
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
    if audit is None:
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
    comparison_ids = validate_comparisons(b.get("competitor_comparisons", []), b["profile"]["company"], E, G, strong)
    finance = FinanceContext(b, I, E, C, G, source_origins=origins) if version != "1.1" else None
    with localcontext() as ctx:
        ctx.prec = 90 if finance is not None else 40
        financial_rows = verify_financial_rows(b, I, finance)
        models = calculate(finance) if finance is not None else {}
    for method in VALUATIONS:
        vals=[v for v in b["valuations"] if v["method"]==method and v["status"]=="calculated" and v["scenario"]!="standalone"]
        if vals:
            by={v["scenario"]:number(v["value"]) for v in vals}
            require(len(vals)==3 and set(by)=={"low","base","high"} and by["low"]<=by["base"]<=by["high"],"Incomplete or inverted valuation range")
    unresolved=False
    model_ids = set()
    if finance is not None:
        model_ids.update(key for key in COMPONENTS if key in models)
        model_ids.update(term["id"] for term in b["financial_model"].get("cap_table", {}).get("rounds", []))
    identity_groups = [E, C, F, I, G, comparison_ids, model_ids,
                       *({x["id"] for x in b[k]} for k in ("metrics", "valuations", "research"))]
    if audit is not None:
        identity_groups.extend((audit.questions, audit.attempts, {"profile", "thesis", "decision", "report"}))
    all_ids = set().union(*identity_groups)
    if audit is not None:
        challenge_ids = {row["id"] for row in b["challenges"]}
        require(len(all_ids) == sum(len(group) for group in identity_groups) and not challenge_ids & all_ids,
                "Research and analytical identities overlap")
    require(not (set(C)&set(F)), "Claim and factor identities overlap")
    for g in G.values(): refs(g["affected_factor_ids"],F,"gap factor")
    for q in b["challenges"]:
        refs(q["affected"],all_ids,"challenge affected"); refs(q["gap_ids"],G,"challenge gap")
        if q["status"]=="unresolved":
            require(bool(q["gap_ids"]),"Unresolved challenge needs missing-information request")
            unresolved |= q["severity"]=="Critical"
    applicable=[f for f in F.values() if f["status"]!="not_applicable"]
    unresolved_factor_states = ("unknown", "partial", "contradicted") if audit is None else ("unknown", "partial")
    critical_unknown=[f["id"] for f in applicable if f["priority"]=="Critical" and f["status"] in unresolved_factor_states]
    covered_gaps={k for g in G.values() for k in g["affected_factor_ids"]}
    require(set(critical_unknown)<=covered_gaps,"Critical unresolved factor lacks a specific information request")
    if unresolved or critical_unknown or any(s["status"] in ("fail","unknown") for s in b["safeguards"]):
        require(b["decision"]["status"]=="qualified" and bool(G),"Material unresolved issue requires qualified decision and gaps")
    assessed=sum(f["status"] in ("supported","partial","contradicted") for f in applicable)
    result = {"applicable":len(applicable),"assessed":assessed,"fully_supported":sum(f["status"]=="supported" for f in applicable),"unknown":sum(f["status"]=="unknown" for f in applicable),"critical_unresolved":critical_unknown,"decision_status":b["decision"]["status"]}
    if finance is not None:
        result["financial_model"] = {**models, **financial_rows}
    if audit is not None:
        result["research_coverage"] = audit.audit(all_ids, comparison_ids, model_ids)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("bundle",type=Path);a=p.parse_args()
    require(a.bundle.stat().st_size<=5_000_000,"Bundle exceeds 5 MB")
    print(json.dumps(validate(json.loads(a.bundle.read_text(encoding="utf-8"))),indent=2))
if __name__=="__main__": main()
