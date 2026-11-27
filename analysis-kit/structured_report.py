"""Project a validated bundle into the v1.3 report contract."""

from decimal import Decimal, localcontext

from finance_context import decimal_text
from finance_metrics import LEGACY_METRIC_UNITS

ACCOUNTING_LABELS = {"ifrs": "IFRS", "us_gaap": "US GAAP", "local_gaap": "Local GAAP",
                     "management_accrual": "Management accrual"}
FINANCIAL_LABELS = {"saas_arr": "SaaS ARR", "saas_logo_churn": "SaaS logo churn",
                    "ev_revenue": "EV/revenue", "ev_ebitda": "EV/EBITDA"}


def label(value):
    return value.replace("_", " ").capitalize()


def links(source_ids=(), input_ids=(), gap_ids=()):
    return {k: list(dict.fromkeys(v)) for k, v in (
        ("source_ids", source_ids), ("input_ids", input_ids), ("gap_ids", gap_ids)
    ) if v}


def cell(text, *, note=None, **references):
    result = {"text": text, **links(**references)}
    if note:
        result["note"] = note
    return result


def numeric(value, kind="amount", *, note=None, highlight=False, **references):
    result = {"value": value, "format": kind, **links(**references)}
    if note:
        result["note"] = note
    if highlight:
        result["highlight"] = True
    return result


def table(caption, headers, rows, **options):
    return {"caption": caption, "headers": headers, "rows": rows, **options}


def section(heading, paragraphs=(), tables=(), sources=()):
    return {"heading": heading, "paragraphs": list(paragraphs),
            "tables": list(tables), "source_ids": list(dict.fromkeys(sources))}


def request_status(title, result):
    return table(title, ["Status", "Reason"], [
        [cell("Unavailable"), cell(result["rationale"], gap_ids=result["gap_ids"])]
    ])


def source_cell(ids):
    return cell("Sources" if ids else "None recorded", source_ids=ids)


def claims_table(claims):
    return table("Claim evidence matrix", ["Claim", "Assessment", "Supporting", "Opposing"], [
        [cell(f"{c['id']} · {c['statement']}"),
         cell(f"{label(c['kind'])} · {label(c['status'])}", note=c["rationale"]),
         source_cell(c["support"]), source_cell(c["oppose"])]
        for c in claims
    ])


def factor_table(caption, factors):
    return table(caption, ["Factor", "Assessment", "Evidence"], [
        [cell(f"{f['id']} · {f['question']}", note=f"{f['priority']} priority"),
         cell(f"{label(f['status'])} · {f['confidence']} confidence",
              note=f"{f['finding']}\nImplication · {f['impact']}\nNext test · {f['next_test']}"),
         cell("Supporting " + (", ".join(f["support"]) or "none recorded")
              + "\nOpposing " + (", ".join(f["oppose"]) or "none recorded"),
              source_ids=(f["support"] + f["oppose"]))]
        for f in factors
    ])


def comparisons(comparison_rows):
    for comparison in comparison_rows:
        peers = [company for company in comparison["companies"] if company["id"] != "subject"]
        subject = next(company for company in comparison["companies"] if company["id"] == "subject")
        for start in range(0, len(peers), 3):
            group = [subject, *peers[start:start + 3]]
            rows = []
            for criterion in comparison["criteria"]:
                row = [cell(criterion["label"], note=criterion["definition"])]
                for company in group:
                    item = criterion["cells"][company["id"]]
                    status = label(item["status"])
                    note = item["rationale"]
                    if item["value"] is not None:
                        note = f"{status}\n{note}"
                    row.append(cell(item["value"] if item["value"] is not None else status,
                                    note=note, source_ids=item["evidence_ids"], gap_ids=item["gap_ids"]))
                rows.append(row)
            yield table(f"{comparison['id']} · {comparison['title']}",
                        ["Criterion", *[company["name"] for company in group]], rows, note=comparison["scope"])


def unit_format(unit, formula):
    if unit == "ratio":
        return "ratio" if formula == "current_ratio" else "percent"
    return "amount" if unit.startswith("money") else "ratio"


def scalar_table(title, requested, results, inputs, *, valuation=False):
    rows = []
    for request in requested:
        rid = request["id"]
        result = results.get(rid, {})
        formula = request["method" if valuation else "formula"]
        referenced = list(request["operands"].values())
        source_ids = result.get("evidence_ids", [e for i in referenced for e in inputs[i]["evidence_ids"]])
        calculation = " · ".join(f"{key} {value}" for key, value in request["operands"].items())
        row_label = cell(f"{rid} · {FINANCIAL_LABELS.get(formula, label(formula))}", note=formula,
                         input_ids=referenced, source_ids=source_ids)
        if request["status"] == "unavailable":
            value = cell("Unavailable", gap_ids=request.get("gap_ids", []))
            basis = label(request["basis"]) if "basis" in request else label(request["value_basis"])
        else:
            amount = result.get("value", request["value"])
            unit = "money" if valuation else result.get("unit", LEGACY_METRIC_UNITS.get(formula, "ratio"))
            currency = next((inputs[i]["currency"] for i in referenced if inputs[i]["currency"]), None)
            unit_note = unit.replace("_", " ") if unit != "ratio" else None
            if currency and unit.startswith("money"):
                unit_note = unit_note.replace("money", currency, 1)
            value = numeric(amount, unit_format(unit, formula), note=unit_note)
            if valuation:
                basis = f"{label(request['value_basis'])} · {label(request['scenario'])}"
            else:
                basis = label(request["basis"])
            if result.get("formula_version"):
                basis = f"{basis} · formula v{result['formula_version']}"
        reason = request["rationale" if valuation else "reason"]
        rows.append([row_label, value, cell(basis), cell(reason, note=calculation)])
    return table(title, ["Calculation", "Value", "Basis", "Rationale"], rows)


def cap_tables(cap, config, currency, inputs):
    if cap["status"] == "unavailable":
        yield request_status("Capitalisation and dilution", cap)
        return
    opening = cap["opening"]
    opening_inputs = {row["id"]: row["shares"] for row in config["holders"]}
    yield table("Opening fully diluted ownership", ["Holder", "Shares", "Ownership"], [
        [cell(cap["holders"][holder]["name"], input_ids=[opening_inputs[holder]],
              source_ids=inputs[opening_inputs[holder]]["evidence_ids"]),
         numeric(value, "integer"), numeric(opening["ownership"][holder], "percent")]
        for holder, value in opening["positions"].items()
    ], note=f"{opening['date']} · Observed · {cap['rationale']}")
    for term, terms_in in zip(cap["rounds"], config["rounds"], strict=True):
        name = term["id"]
        basis = "Observed terms" if term["basis"] == "observed" else "Assumed terms"
        trace = [terms_in["pre_money"], terms_in["pool_top_up"],
                 *[r["amount"] for r in terms_in["subscriptions"]]]
        yield table(f"{name} financing terms · {currency}", ["Measure", "Value", "Measure", "Value"], [
            [cell("Pre-money equity value"), numeric(term["pre_money_equity_value"]),
             cell("Primary cash"), numeric(term["new_primary_cash"])],
            [cell("Post-money equity value"), numeric(term["post_money_equity_value"]),
             cell("Issue price per share"), numeric(term["issue_price_per_share"], "ratio")],
            [cell("Shares before closing"), numeric(term["pre_round_fully_diluted_shares"], "integer"),
             cell("Shares after closing"), numeric(term["post_round_fully_diluted_shares"], "integer")],
            [cell("Pre-money pool top-up"), numeric(term["pool_top_up_shares"], "integer"),
             cell("Existing-share dilution", input_ids=trace, source_ids=term["evidence_ids"]),
             numeric(term["existing_share_dilution"], "percent")],
        ], note=f"{term['date']} · {basis} · {cap['formula']}")
        yield table(f"{name} ownership and dilution", ["Holder", "Shares after", "Before", "After", "Change (pp)"], [
            [cell(cap["holders"][holder]["name"]), numeric(row["shares_after"], "integer"),
             numeric(row["ownership_before"], "percent"), numeric(row["ownership_after"], "percent"),
             numeric(row["ownership_change"], "percentage_points")]
            for holder, row in term["holders"].items()
        ], note="Change is after minus before, in percentage points.")


def runway_cell(result):
    if result["status"] == "at_least":
        return numeric(str(result["months"]), "integer", note="At least · no breach within horizon")
    return numeric(str(result["months"]), "integer", note=f"First breach {result['first_breach']}")


def scenario_tables(result, config, currency, inputs):
    if result["status"] == "unavailable":
        yield request_status("Monthly cash and runway", result)
        return
    yield table(f"Scenario opening balances · {currency}", ["Measure", "Value", "Basis"], [
        [cell("Unrestricted opening cash", input_ids=[config["opening_cash"]],
              source_ids=inputs[config["opening_cash"]]["evidence_ids"]),
         numeric(result["opening_unrestricted_cash"]), cell("Observed")],
        [cell("Minimum unrestricted cash", input_ids=[config["cash_floor"]],
              source_ids=inputs[config["cash_floor"]]["evidence_ids"]),
         numeric(result["minimum_unrestricted_cash"]), cell("Assumption")],
    ], note=f"{result['as_of']} · {result['months_in_horizon']} months · {result['formula']} · {result['rationale']}")
    yield table(f"Scenario cash and funding requirements · {currency}",
                ["Case", "Closing cash", "Capital before rounds", "Residual capital",
                 "Runway before (mo)", "Runway after (mo)"], [
        [cell(label(name), note=case["rationale"], source_ids=case["evidence_ids"]),
         numeric(case["months"][-1]["closing_cash"]),
         numeric(case["capital_required_before_linked_rounds"]),
         numeric(case["residual_capital_required"]),
         runway_cell(case["runway_before_linked_rounds"]), runway_cell(case["runway_after_linked_rounds"])]
        for name, case in result["cases"].items()
    ], note="Runway counts completed months before the first cash floor breach. Proposed primary financing is conditional.",
        charts=[{"caption": "Closing cash by scenario", "columns": [1], "unit": currency},
                {"caption": "Capital required before and after linked equity rounds", "columns": [2, 3], "unit": currency}])


def scenario_schedules(result, currency, inputs, cap):
    round_map = {r["id"]: r for r in cap.get("rounds", [])}
    for name, case in result["cases"].items():
        rows = []
        for month in case["months"]:
            operand_ids = list(month["operands"].values())
            sources = [eid for i in operand_ids for eid in inputs[i]["evidence_ids"]]
            round_names = month["round_ids"]
            for key in round_names:
                sources += round_map[key]["evidence_ids"]
            first, last = month["period"].split("/")
            rows.append([
                cell(last, note=f"From {first}", input_ids=operand_ids, source_ids=sources),
                numeric(month["fcff"]), numeric(month["other_cash_flow"]),
                numeric(month["linked_round_cash"], note=", ".join(round_names) or None),
                numeric(month["net_cash_flow"]), numeric(month["closing_cash"]),
                numeric(month["residual_floor_gap"]),
            ])
        yield table(f"{label(name)} monthly cash · {currency}",
                    [f"{label(name)} period end", "FCFF", "Other cash flow", "Primary cash", "Net cash flow",
                     "Closing cash", "Floor shortfall"],
                    rows, note="Projected monthly balances with the linked equity rounds recorded in this case.")


def rate_label(value):
    with localcontext() as context:
        context.prec = 100
        return decimal_text(Decimal(value) * 100) + "%"


def dcf_tables(result, config, inputs, currency):
    if result["status"] == "unavailable":
        yield request_status("Discounted cash flow", result)
        return
    yield table(f"Annual FCFF and present values · {currency}", ["Year ending", "Free cash flow to firm", "Present value"], [
        [cell(row["year_end"]), numeric(row["fcff"]), numeric(pv)]
        for row, pv in zip(result["annual_fcff"], result["present_values_of_annual_fcff"], strict=True)
    ], note=f"{label(result['scenario'])} scenario · {result['formula']} · {result['rationale']}")
    rate_rows = [["Cost of equity", config["wacc"]["cost_of_equity"]],
                 ["Pre-tax cost of debt", config["wacc"]["pretax_cost_of_debt"]],
                 ["Target debt weight", config["wacc"]["debt_weight"]],
                 ["Marginal tax rate", config["wacc"]["tax_rate"]],
                 ["Terminal growth", config["terminal_growth"]]]
    yield table("Discount rate and terminal assumptions", ["Assumption", "Rate"], [
        [cell(name, input_ids=[input_id], source_ids=inputs[input_id]["evidence_ids"]),
         numeric(inputs[input_id]["value"], "percent")]
        for name, input_id in rate_rows
    ] + [[cell("Calculated WACC", input_ids=[i for _, i in rate_rows[:-1]],
               source_ids=result["evidence_ids"]), numeric(result["wacc"], "percent", highlight=True)]])
    bridge = result["equity_bridge"]
    yield table(f"Enterprise to equity value · {currency}", ["Measure", "Value", "Basis"], [
        [cell("Terminal value at final year end"), numeric(result["terminal_value"]), cell("Scenario")],
        [cell("Present value of terminal cash flows"), numeric(result["present_value_of_terminal"]), cell("Scenario")],
        [cell("Enterprise value of operations", source_ids=result["evidence_ids"]),
         numeric(result["enterprise_value"], highlight=True), cell("Scenario")],
        *[[cell(name, input_ids=[config["bridge"][key]], source_ids=inputs[config["bridge"][key]]["evidence_ids"]),
           numeric(bridge[key]), cell("Observed")]
          for key, name in (("excess_cash", "Excess cash added"), ("debt", "Interest-bearing debt deducted"),
                            ("other_adjustments", "Net other adjustments added"))],
        [cell("Implied equity value"), numeric(result["equity_value"], highlight=True), cell("Scenario")],
    ])
    grid = {(x["wacc"], x["terminal_growth"]): x for x in result["sensitivity"]}
    rates = list(dict.fromkeys(w for w, _ in grid))
    growth = list(dict.fromkeys(g for _, g in grid))
    for key, name in (("enterprise_value", "Enterprise value"), ("equity_value", "Equity value")):
        yield table(f"{name} sensitivity · {currency}",
                    ["WACC / terminal growth", *map(rate_label, growth)], [
            [numeric(w, "percent"), *[
                numeric(grid[w, g][key], highlight=(w, g) == (result["wacc"], result["terminal_growth"]),
                        note="Base" if (w, g) == (result["wacc"], result["terminal_growth"]) else None)
                for g in growth
            ]]
            for w in rates
        ])


def build_report(bundle, digest, validated):
    profile = bundle["profile"]
    decision = bundle["decision"]
    inputs = {x["id"]: x for x in bundle["inputs"]}
    model = validated.get("financial_model", {})
    currency = model.get("currency")
    config = bundle.get("financial_model", {})
    financial = []
    valuation = []
    schedules = []
    if bundle["metrics"]:
        financial.append(scalar_table("Financial and operating metrics", bundle["metrics"], model.get("metrics", {}), inputs))
    if "cap_table" in model:
        financial.extend(cap_tables(model["cap_table"], config["cap_table"], currency, inputs))
    if "scenarios" in model:
        scenarios = model["scenarios"]
        financial.extend(scenario_tables(scenarios, config["scenarios"], currency, inputs))
        if scenarios["status"] == "calculated":
            schedules.extend(scenario_schedules(scenarios, currency, inputs, model.get("cap_table", {})))
    if "dcf" in model:
        valuation.extend(dcf_tables(model["dcf"], config["dcf"], inputs, currency))
    if bundle["valuations"]:
        valuation.append(scalar_table("Other valuation methods", bundle["valuations"], model.get("valuations", {}), inputs, valuation=True))

    factors = bundle["factors"]
    scope = [f"{profile['legal_entity']} · {profile['jurisdiction']} · {label(profile['stage'])}", profile["scope"]]
    documents = [table("Documents reviewed", ["Document", "Review", "Limitations"], [
        [cell(doc["name"], note=doc["version"]), cell(doc["reviewed"]), cell(doc["limitations"])]
        for doc in bundle["documents"]
    ])] if bundle["documents"] else []
    coverage_keys = ("applicable", "assessed", "fully_supported", "unknown")
    coverage = table("Factor coverage", ["Measure", "Count"],
                     [[cell(label(key)), numeric(str(validated[key]), "integer")] for key in coverage_keys])
    evidence_matrix = factor_table("Material factors and evidence matrix", factors)
    team = [f["finding"] for f in factors if f["id"] == "C04"]
    market = [f["finding"] for f in factors if f["id"] in {"C02", "C05", "C08"}]
    comparison_tables = list(comparisons(bundle.get("competitor_comparisons", [])))
    if not comparison_tables:
        market.append("Structured competitor comparison unavailable within this assessment.")
    thesis = bundle["thesis"]
    divergences = [table("Thesis differences", ["Finding", "Implication"], [
        [cell(row["finding"], note=", ".join(row["claim_ids"]) or None), cell(row["impact"])]
        for row in thesis["divergences"]
    ])] if thesis["divergences"] else []
    safeguards = [table("Safeguards", ["Check", "Status", "Rationale"], [
        [cell(s["check"]), cell(label(s["status"])), cell(s["rationale"], source_ids=s["evidence_ids"])]
        for s in bundle["safeguards"]
    ])] if bundle["safeguards"] else []
    gaps = [{k: g[k] for k in ("id", "priority", "item", "period", "why", "conclusion", "action", "availability")}
            for g in bundle["gaps"]]
    questions = [table("Information to request", ["Priority", "Item", "Reassessment"], [
        [cell(g["priority"]), cell(g["item"], gap_ids=[g["id"]]), cell(g["action"])]
        for g in bundle["gaps"]
    ])] if gaps else []
    limits = [decision["limitations"]]
    limits.extend(f"{r['id']} · {label(r['status'])} · {r['reason']}" for r in bundle["research"])
    limits.extend(f"{q['id']} · {q['severity']} · {label(q['status'])}\n{q['finding']}\n{q['correction']}"
                  for q in bundle["challenges"])
    if not gaps:
        limits.append("No material gaps listed within the declared scope.")
    financial_context = [
        f"{model['entity']} · {currency} in base units · {ACCOUNTING_LABELS[model['accounting_basis']]}"
    ] if model else []
    return {
        "version": "1.3", "company": profile["company"], "objective": profile["objective"], "as_of": bundle["as_of"],
        "methodology": {"version": bundle["version"], "standard_commit": bundle["standard_commit"], "bundle_sha256": digest},
        "sections": [
            section("Executive assessment", [f"{label(decision['status'])} · {decision['conclusion']}", *decision["strengths"]]),
            section("Scope and input inventory", scope, documents),
            section("Business and product", [profile["model_rationale"],
                    ", ".join("SaaS" if m == "saas" else label(m) for m in profile["models"])],
                    [claims_table(bundle["claims"])] if bundle["claims"] else []),
            section("Team", team), section("Market and competition", market, comparison_tables),
            section("Independent thesis and reconciliation",
                    [f"Management · {thesis['management'] or 'Unavailable'}", f"Independent · {thesis['independent']}",
                     *thesis["falsifiers"]], divergences, thesis["independent_evidence"]),
            section("Financial analysis and calculations", financial_context, financial),
            section("Material factors and evidence coverage", tables=[coverage, evidence_matrix]),
            section("Risks and safeguards", decision["risks"], safeguards),
            section("Valuation and sensitivity", tables=valuation),
            section("Management questions", tables=questions), section("Methodology and limitations", limits),
        ],
        "sources": bundle["evidence"], "missing_information": gaps, "operands": bundle["inputs"],
        "schedules": schedules,
    }
