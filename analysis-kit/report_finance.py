"""Render compact v1.2 financial summaries in the v1.0 report format."""

from decimal import Decimal, localcontext


def display(value, *, percent=False):
    with localcontext() as ctx:
        ctx.prec = 100
        x = Decimal(value) * (100 if percent else 1)
        output = format(x, ",.2f").rstrip("0").rstrip(".")
        if x and output in ("0", "-0"):
            output = f"{x:.3E}"
    return output + ("%" if percent else "")


def describe_runway(runway):
    months = runway["months"]
    if runway["status"] == "at_least":
        return f"at least {months} months (no breach within the forecast)"
    return f"{months} completed months, first breach {runway['first_breach']}"


def financial_summary(model, cite):
    finance = []
    valuation = []
    finance_ids = set()
    valuation_ids = set()
    currency = model["currency"]

    def add(paragraphs, sources, text, result):
        evidence = result.get("evidence_ids", [])
        sources.update(evidence[:6])
        if len(evidence) > 6:
            text += f" {len(evidence) - 6} additional evidence IDs in the calculation output."
        paragraphs.append(text + cite(evidence[:6]))

    finance.append(
        f"Financial model context: {model['entity']} | {currency}, base currency units | {model['accounting_basis']}."
        " Forecast and proposed-round values are assumptions. See validated calculation output for schedules and operands."
    )
    cap = model.get("cap_table", {})
    if cap.get("status") == "calculated":
        start = cap["opening"]
        add(finance, finance_ids, f"Opening fully diluted ownership on {start['date']}:"
            f" {start['fully_diluted_shares']} shares from observed positions. {cap['rationale']}", start)
        for term in cap["rounds"]:
            basis = "Observed terms" if term["basis"] == "observed" else "Assumed terms"
            existing = sorted(
                ((Decimal(row["ownership_before"]), holder, row) for holder, row in term["holders"].items()
                 if row["ownership_before"] != "0"),
                key=lambda row: (-row[0], row[1]),
            )
            positions = ", ".join(f"{cap['holders'][holder]['name']} {display(row['ownership_before'], percent=True)}"
                                  f" to {display(row['ownership_after'], percent=True)}"
                                  for _, holder, row in existing[:4])
            text = (f"{term['id']} | {term['date']} | {basis} | pre-money {currency} "
                    f"{display(term['pre_money_equity_value'])} | primary cash {currency} "
                    f"{display(term['new_primary_cash'])} | post-money {currency} "
                    f"{display(term['post_money_equity_value'])} | {display(term['issue_price_per_share'])} "
                    f"{currency} per share | {term['pool_top_up_shares']} pool shares added | "
                    f"{term['post_round_fully_diluted_shares']} fully diluted shares after close | "
                    f"existing-share dilution {display(term['existing_share_dilution'], percent=True)}.")
            add(finance, finance_ids, text + (f" Ownership changes: {positions}." if positions else ""), term)

    scenarios = model.get("scenarios", {})
    if scenarios.get("status") == "calculated":
        finance.append(
            f"Monthly scenarios | opening unrestricted cash {currency} "
            f"{display(scenarios['opening_unrestricted_cash'])} (observed) | minimum cash {currency} "
            f"{display(scenarios['minimum_unrestricted_cash'])} (assumed) | horizon "
            f"{scenarios['months_in_horizon']} months. {scenarios['rationale']}"
        )
        for name, case in scenarios["cases"].items():
            last = case["months"][-1]
            text = (f"{name.title()} scenario | closing cash {currency} {display(last['closing_cash'])} | "
                    f"capital required before linked equity rounds {currency} "
                    f"{display(case['capital_required_before_linked_rounds'])} | residual capital required "
                    f"{currency} {display(case['residual_capital_required'])} | runway before rounds "
                    f"{describe_runway(case['runway_before_linked_rounds'])} | runway after rounds "
                    f"{describe_runway(case['runway_after_linked_rounds'])}. {case['rationale']}")
            add(finance, finance_ids, text, case)

    dcf = model.get("dcf", {})
    if dcf.get("status") == "calculated":
        annual = ", ".join(f"{year['year_end']} {currency} {display(year['fcff'])}" for year in dcf["annual_fcff"])
        add(valuation, valuation_ids, f"FCFF discounted cash flow | {dcf['scenario']} forecast assumptions | "
            f"annual FCFF {annual} | WACC {display(dcf['wacc'], percent=True)} | terminal growth "
            f"{display(dcf['terminal_growth'], percent=True)} | present value of terminal cash flows {currency} "
            f"{display(dcf['present_value_of_terminal'])}. {dcf['rationale']}", dcf)
        bridge = dcf["equity_bridge"]
        valuation.append(f"DCF indicated enterprise value {currency} {display(dcf['enterprise_value'])} plus "
                         f"observed excess cash {display(bridge['excess_cash'])}, less interest-bearing debt "
                         f"{display(bridge['debt'])}, plus other adjustments {display(bridge['other_adjustments'])} "
                         f"gives indicated equity value {currency} {display(dcf['equity_value'])}.")
        valuation.append(f"DCF sensitivity in {currency} (WACC, terminal growth, enterprise value, equity value). "
                         + " | ".join(
                             f"{display(cell['wacc'], percent=True)}, {display(cell['terminal_growth'], percent=True)}, "
                             f"{display(cell['enterprise_value'])}, {display(cell['equity_value'])}"
                             for cell in dcf["sensitivity"]
                         ))

    for key, label, paragraphs in (("cap_table", "Cap table", finance), ("scenarios", "Monthly scenarios", finance),
                                   ("dcf", "Discounted cash flow", valuation)):
        result = model.get(key, {})
        if result.get("status") == "unavailable":
            paragraphs.append(f"{label} unavailable. {result['rationale']} "
                              f"See missing information {', '.join(result['gap_ids'])}.")
    return finance, finance_ids, valuation, valuation_ids
