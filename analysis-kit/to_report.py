"""Bridge validated v1.1 bundle to the compatible v1.0 report renderer."""
import argparse
import hashlib
import json
from pathlib import Path
from validate import validate
def convert(b, digest):
    coverage=validate(b)
    evidence={e["id"]:e for e in b["evidence"]}
    mapping={k:"S"+str(i+1) for i,k in enumerate(evidence)}
    sources=[{"id":mapping[k],"title":e["title"],"locator":e["publisher"]+" | "+e["locator"]+" | Accessed "+e["accessed"],"url":e["url"],"type":{"company_material":"company material","company_public":"company public source","independent_public":"independent public source","authoritative_record":"independent public source"}[e["type"]]} for k,e in evidence.items()]
    def citations(ids): return sorted({mapping[k] for k in ids})
    def cite(ids): return " ["+", ".join(citations(ids))+"]" if ids else ""
    def section(heading,paragraphs,ids=()):
        chunks=[p[i:i+3800] for p in paragraphs for i in range(0,len(p),3800)]
        if len(chunks)>40 or len(citations(ids))>100: raise ValueError("Report section exceeds legacy renderer capacity; use structured bundle for detail")
        return {"heading":heading,"paragraphs":chunks or ["Not assessed within available evidence."],"source_ids":citations(ids)}
    p=b["profile"];d=b["decision"]
    inputs={x["id"]:x for x in b["inputs"]}
    def calc(x,key):
        return x["id"]+" | "+x[key]+" | "+x["status"]+" | "+(x["value"] if x["value"] is not None else "Not available")+" | "+x.get("reason",x.get("rationale",""))+" | "+", ".join(k+"="+inputs[v]["value"]+" "+inputs[v]["unit"]+" "+str(inputs[v]["currency"] or "")+" ("+inputs[v]["period"]+"; "+inputs[v]["basis"]+")"+cite(inputs[v]["evidence_ids"]) for k,v in x["operands"].items())
    claims=[c["statement"]+" | "+c["kind"]+" | "+c["status"]+" | "+c["rationale"]+cite(c["support"]+c["oppose"]) for c in b["claims"]]
    fac=lambda f:f["id"]+" | "+f["priority"]+" | "+f["status"]+" | "+f["confidence"]+" | "+f["finding"]+" | Impact: "+f["impact"]+" | Next: "+f["next_test"]+cite(f["support"]+f["oppose"])
    all_f=[i for f in b["factors"] for i in f["support"]+f["oppose"]]
    all_i=[i for x in b["inputs"] for i in x["evidence_ids"]]
    all_c=[i for x in b["claims"] for i in x["support"]+x["oppose"]]
    def selected(prefix): return [f for f in b["factors"] if f["id"] in prefix]
    def fs(head,ids):
        rows=selected(ids)
        return section(head,[fac(f) for f in rows],[i for f in rows for i in f["support"]+f["oppose"]])
    gaps=[{k:g[k] for k in ("priority","item","period","why","conclusion","action","availability")} for g in b["gaps"]]
    limits=[d["limitations"],"Open standard v1.1; source commit "+b["standard_commit"]+"; bundle SHA-256 "+digest,"Coverage (count, not performance score): "+json.dumps(coverage), *[r["id"]+" | "+r["status"]+" | "+r["reason"] for r in b["research"]],*[q["id"]+" | "+q["severity"]+" | "+q["status"]+" | "+q["finding"]+" | "+q["correction"] for q in b["challenges"]]]
    if not gaps: limits.append("No material gaps listed within the declared scope; see limitations above.")
    return {"version":"1.0","company":p["company"],"objective":p["objective"],"as_of":b["as_of"],"sections":[
      section("Executive assessment",[d["status"]+": "+d["conclusion"],*d["strengths"],*d["risks"]],all_f),
      section("Scope and input inventory",[p["legal_entity"]+" | "+p["jurisdiction"]+" | "+p["stage"],p["scope"],*[x["name"]+" | "+x["version"]+" | "+x["reviewed"]+" | "+x["limitations"] for x in b["documents"]]]),
      section("Business and product",[p["model_rationale"],"Models: "+", ".join(p["models"]),*claims],all_c),
      fs("Team",["C04"]),fs("Market and competition",["C02","C05","C08"]),
      section("Independent thesis and reconciliation",["Management: "+(b["thesis"]["management"] or "Not available"),"Independent: "+b["thesis"]["independent"],*b["thesis"]["falsifiers"],*[x["finding"]+" | "+x["impact"] for x in b["thesis"]["divergences"]]],b["thesis"]["independent_evidence"]+all_c),
      section("Financial analysis and calculations",[calc(x,"formula") for x in b["metrics"]],all_i),
      section("Material factors and evidence coverage",[fac(f) for f in b["factors"]],all_f),
      section("Risks and safeguards",[x["check"]+" | "+x["status"]+" | "+x["rationale"]+cite(x["evidence_ids"]) for x in b["safeguards"]]+d["risks"],[i for x in b["safeguards"] for i in x["evidence_ids"]]),
      section("Valuation and sensitivity",[calc(x,"method")+" | "+x["value_basis"]+" | "+x["scenario"] for x in b["valuations"]],all_i),
      section("Management questions",[g["priority"]+" | "+g["item"]+" | "+g["action"] for g in gaps]),
      section("Methodology and limitations",limits)
    ],"sources":sources,"missing_information":gaps}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("bundle",type=Path);p.add_argument("output",type=Path);a=p.parse_args()
    raw=a.bundle.read_bytes()
    if len(raw)>5_000_000: raise ValueError("Bundle too large")
    result=convert(json.loads(raw),hashlib.sha256(raw).hexdigest())
    a.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
if __name__=="__main__": main()
