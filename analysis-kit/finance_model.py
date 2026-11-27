"""Deterministic cap table, liquidity scenarios and FCFF valuation for contract 1.2."""

from datetime import date
from decimal import Decimal
from fractions import Fraction

from contract import refs, require
from finance_context import ONE_DAY, OPERATING_STAGES, add_months, decimal_text

CASES = ("downside", "base", "upside")
FORECAST_QUANTITIES = {
    "ebit": "ebit",
    "cash_tax": "unlevered_cash_income_tax",
    "da": "depreciation_amortisation",
    "capex": "capital_expenditure",
    "working_capital_change": "change_in_noncash_operating_working_capital",
    "other_cash_flow": "net_cash_flow_outside_fcff_and_linked_rounds",
}
WACC_QUANTITIES = {
    "cost_of_equity": "cost_of_equity",
    "pretax_cost_of_debt": "pretax_cost_of_debt",
    "debt_weight": "market_value_debt_weight",
    "tax_rate": "marginal_tax_rate",
}


def ownership(positions, total):
    return {holder: Decimal(shares) / total for holder, shares in positions.items()}


def whole_shares(value, label):
    require(value >= 0 and value == value.to_integral_value(), f"{label}: expected nonnegative whole shares")
    return int(value)


def cap_table(context, config):
    opening_date = date.fromisoformat(config["opening_date"])
    require(opening_date <= context.as_of, "Cap table opening date is in the future")
    holders = {holder["id"]: holder for holder in config["holders"]}
    require(len(holders) == len(config["holders"]), "Duplicate cap table holder ID")
    pools = [holder["id"] for holder in holders.values() if holder["kind"] == "option_pool"]
    require(len(pools) <= 1, "Only one unallocated option pool is supported")
    positions = {}
    opening_ids = [holder["shares"] for holder in holders.values()]
    require(len(set(opening_ids)) == len(opening_ids), "Each opening shares input must identify one position")
    for holder, row in holders.items():
        shares = context.read(row["shares"], "fully_diluted_shares_held", "shares",
                              period=config["opening_date"], basis="observed")
        positions[holder] = whole_shares(shares, row["shares"])
    total = sum(positions.values())
    require(total > 0, "Cap table needs positive opening fully diluted shares")
    opening = {"date": config["opening_date"], "basis": "observed", "fully_diluted_shares": str(total),
               "positions": {k: str(v) for k, v in positions.items()},
               "ownership": {k: decimal_text(v) for k, v in ownership(positions, total).items()},
               **context.trace(opening_ids)}
    last_date = opening_date
    rounds = []
    input_ids = opening_ids[:]
    seen = set()
    for term in config["rounds"]:
        round_id = term["id"]
        context.use(round_id)
        require(round_id not in seen, f"Duplicate cap table round {round_id}")
        seen.add(round_id)
        round_date = date.fromisoformat(term["date"])
        require(round_date > last_date, f"{round_id}: rounds must follow the opening date in chronological order")
        last_date = round_date
        basis = "observed" if round_date <= context.as_of else "assumption"
        period = term["date"]
        pre_money = context.read(term["pre_money"], "pre_money_equity_value", "money", period=period, basis=basis)
        top_up = whole_shares(context.read(term["pool_top_up"], "pre_money_pool_top_up", "shares",
                                          period=period, basis=basis), term["pool_top_up"])
        require(pre_money > 0, f"{round_id}: pre-money equity value must be positive")
        require(not top_up or pools, f"{round_id}: pre-money top-up needs an option pool")
        before = ownership(positions, total)
        pre_shares = total + top_up
        if pools:
            positions[pools[0]] += top_up
        allocations = {}
        cash = Decimal(0)
        round_ids = [term["pre_money"], term["pool_top_up"]]
        for subscription in term["subscriptions"]:
            holder = subscription["holder"]
            require(holder in holders and holder not in pools and holder not in allocations,
                    f"{round_id}: invalid or duplicate subscribing holder")
            amount_id = subscription["amount"]
            require(amount_id not in round_ids, f"{round_id}: subscription evidence reused across holders")
            amount = context.read(amount_id, "primary_equity_subscription", "money", period=period, basis=basis)
            require(amount > 0, f"{round_id}: subscription cash must be positive")
            issued = Fraction(amount) * pre_shares / Fraction(pre_money)
            require(issued.denominator == 1, f"{round_id}: terms imply fractional issued shares")
            allocations[holder] = {"cash": decimal_text(amount), "issued_shares": str(issued.numerator)}
            positions[holder] += issued.numerator
            cash += amount
            round_ids.append(amount_id)
        input_ids.extend(round_ids)
        closing_shares = sum(positions.values())
        after = ownership(positions, closing_shares)
        rounds.append({
            "id": round_id, "date": period, "basis": basis,
            "pre_money_equity_value": decimal_text(pre_money), "new_primary_cash": decimal_text(cash),
            "post_money_equity_value": decimal_text(pre_money + cash), "pool_top_up_shares": str(top_up),
            "issue_price_per_share": decimal_text(pre_money / pre_shares),
            "pre_round_fully_diluted_shares": str(total), "post_round_fully_diluted_shares": str(closing_shares),
            "existing_share_dilution": decimal_text(Decimal(closing_shares - total) / closing_shares),
            "allocations": allocations,
            "holders": {
                k: {"shares_after": str(positions[k]), "ownership_before": decimal_text(before[k]),
                    "ownership_after": decimal_text(after[k]),
                    "ownership_change": decimal_text(after[k] - before[k])}
                for k in holders
            },
            **context.trace(input_ids),
        })
        total = closing_shares
    return {"formula": "priced_primary_equity.v1.2", "opening": opening, "rounds": rounds,
            "holders": {k: {"name": v["name"], "kind": v["kind"]} for k, v in holders.items()},
            **context.trace(input_ids)}


def runway(cash_path, floor):
    # cash_path includes the anchor followed by one observation per projected month.
    for month, (when, cash) in enumerate(cash_path):
        if cash < floor:
            return {"status": "breach", "months": max(0, month - 1), "first_breach": when}
    return {"status": "at_least", "months": len(cash_path) - 1, "first_breach": None}


def scenario_case(context, case, opening, floor, opening_ids, planned_rounds):
    start = context.as_of + ONE_DAY
    initial = context.as_of.isoformat()
    both_paths = [(initial, opening)]
    without_rounds = [(initial, opening)]
    rounds_used = []
    monthly = []
    input_ids = opening_ids[:]
    require(bool(case["rationale"].strip()), "Scenario needs a rationale")
    for month, row in enumerate(case["months"], start=1):
        end = add_months(context.as_of, month)
        period = f"{start.isoformat()}/{end.isoformat()}"
        x = {
            key: context.read(row[key], quantity, "money", period=period, basis="assumption")
            for key, quantity in FORECAST_QUANTITIES.items()
        }
        require(all(x[key] >= 0 for key in ("cash_tax", "da", "capex")),
                f"{period}: cash tax, D&A and capex must be nonnegative")
        round_refs = row["round_ids"]
        refs(round_refs, planned_rounds, "scenario financing")
        linked_rounds = [planned_rounds[round_id] for round_id in round_refs]
        require(all(start <= date.fromisoformat(term["date"]) <= end for term in linked_rounds),
                f"{period}: linked financing outside the forecast month")
        rounds_used.extend(round_refs)
        expected = list(planned_rounds)[:len(rounds_used)]
        require(rounds_used == expected, f"{period}: scenario must include an ordered prefix of forecast rounds")
        proceeds = sum((Decimal(term["new_primary_cash"]) for term in linked_rounds), Decimal(0))
        operating_cash = x["ebit"] - x["cash_tax"] + x["da"] - x["working_capital_change"]
        fcff = operating_cash - x["capex"]
        before_round_cash_flow = fcff + x["other_cash_flow"]
        cash_flow = before_round_cash_flow + proceeds
        closing_before = without_rounds[-1][1] + before_round_cash_flow
        closing = both_paths[-1][1] + cash_flow
        without_rounds.append((end.isoformat(), closing_before))
        both_paths.append((end.isoformat(), closing))
        operand_ids = {key: row[key] for key in FORECAST_QUANTITIES}
        input_ids.extend(operand_ids.values())
        for term in linked_rounds:
            input_ids.extend(term["input_ids"])
        monthly.append({
            "period": period, "operating_cash_before_capex": decimal_text(operating_cash),
            "fcff": decimal_text(fcff), "other_cash_flow": decimal_text(x["other_cash_flow"]),
            "net_cash_flow_before_linked_rounds": decimal_text(before_round_cash_flow),
            "linked_round_cash": decimal_text(proceeds), "net_cash_flow": decimal_text(cash_flow),
            "closing_cash_before_linked_rounds": decimal_text(closing_before), "closing_cash": decimal_text(closing),
            "residual_floor_gap": decimal_text(max(Decimal(0), floor - closing)),
            "operands": operand_ids, "round_ids": round_refs,
        })
        start = end + ONE_DAY
    before_gap = max(Decimal(0), floor - min(cash for _, cash in without_rounds))
    after_gap = max(Decimal(0), floor - min(cash for _, cash in both_paths))
    return {
        "rationale": case["rationale"], "basis": "scenario", "months": monthly,
        "capital_required_before_linked_rounds": decimal_text(before_gap),
        "residual_capital_required": decimal_text(after_gap),
        "runway_before_linked_rounds": runway(without_rounds, floor),
        "runway_after_linked_rounds": runway(both_paths, floor),
        **context.trace(input_ids),
    }


def scenarios(context, config, cap):
    period = context.as_of.isoformat()
    opening = context.read(config["opening_cash"], "unrestricted_cash", "money", period=period, basis="observed")
    floor = context.read(config["cash_floor"], "minimum_unrestricted_cash", "money", period=period,
                         basis="assumption")
    require(opening >= 0 and floor >= 0, "Opening unrestricted cash and minimum cash must be nonnegative")
    horizon = len(config["cases"]["base"]["months"])
    require(all(len(case["months"]) == horizon for case in config["cases"].values()),
            "Downside, base and upside need an identical monthly horizon")
    opening_ids = [config["opening_cash"], config["cash_floor"]]
    forecast_rounds = {term["id"]: term for term in cap.get("rounds", []) if term["basis"] == "assumption"}
    results = {
        name: scenario_case(context, config["cases"][name], opening, floor, opening_ids, forecast_rounds)
        for name in CASES
    }
    return {"formula": "monthly_cash_and_runway.v1.2", "as_of": period, "months_in_horizon": horizon,
            "opening_unrestricted_cash": decimal_text(opening), "minimum_unrestricted_cash": decimal_text(floor),
            "cases": results,
            **context.trace(i for case in results.values() for i in case["input_ids"])}


def discounted_values(annual, rate, growth, adjustment):
    require(rate > 0 and -1 < growth < rate, "DCF requires WACC > 0 and -100% < terminal growth < WACC")
    explicit = [cash / (1 + rate) ** year for year, cash in enumerate(annual, start=1)]
    terminal = annual[-1] * (1 + growth) / (rate - growth)
    terminal_pv = terminal / (1 + rate) ** len(annual)
    operating_ev = sum(explicit) + terminal_pv
    return {"present_values_of_annual_fcff": [decimal_text(value) for value in explicit],
            "terminal_value": decimal_text(terminal), "present_value_of_terminal": decimal_text(terminal_pv),
            "enterprise_value": decimal_text(operating_ev), "equity_value": decimal_text(operating_ev + adjustment)}


def dcf(context, config, forecast):
    require(context.stage in OPERATING_STAGES and "lending" not in context.models,
            "FCFF DCF is ineligible for this business model or stage")
    require(forecast.get("status") == "calculated", "DCF needs calculated linked scenarios")
    context.independent(config["eligibility_evidence_ids"], "DCF eligibility")
    selected = forecast["cases"][config["scenario"]]
    rows = selected["months"]
    require(len(rows) >= 24 and len(rows) % 12 == 0, "DCF needs at least two complete annual FCFF periods")
    annual = [sum(Decimal(row["fcff"]) for row in rows[i:i + 12]) for i in range(0, len(rows), 12)]
    require(annual[-1] > 0, "DCF needs positive normalised final-year FCFF")
    period = context.as_of.isoformat()
    w = {
        name: context.read(config["wacc"][name], quantity, "ratio", period=period, basis="assumption",
                           independent=name == "cost_of_equity")
        for name, quantity in WACC_QUANTITIES.items()
    }
    require(w["cost_of_equity"] > 0 and w["pretax_cost_of_debt"] >= 0
            and (not w["debt_weight"] or w["pretax_cost_of_debt"] > 0)
            and 0 <= w["debt_weight"] < 1 and 0 <= w["tax_rate"] <= 1,
            "DCF: invalid WACC cost, market weight or tax rate")
    rate = w["cost_of_equity"] * (1 - w["debt_weight"]) + (
        w["pretax_cost_of_debt"] * (1 - w["tax_rate"]) * w["debt_weight"]
    )
    growth = context.read(config["terminal_growth"], "terminal_growth_rate", "ratio",
                          period=period, basis="assumption", independent=True)
    bridge = {
        name: context.read(config["bridge"][name], quantity, "money", period=period, basis="observed")
        for name, quantity in {"excess_cash": "excess_nonoperating_cash", "debt": "interest_bearing_debt",
                               "other_adjustments": "net_noncash_equity_bridge_adjustments"}.items()
    }
    require(0 <= bridge["excess_cash"] <= Decimal(forecast["opening_unrestricted_cash"]) and bridge["debt"] >= 0,
            "DCF: excess cash must fit opening unrestricted cash and debt must be nonnegative")
    adjustment = bridge["excess_cash"] - bridge["debt"] + bridge["other_adjustments"]
    base = discounted_values(annual, rate, growth, adjustment)
    sensitivity = config["sensitivity"]
    rate_ids = sensitivity["wacc"]
    growth_ids = sensitivity["terminal_growth"]
    rate_low, rate_high = [context.read(i, "sensitivity_wacc", "ratio", period=period,
                                       basis="assumption") for i in rate_ids]
    g_low, g_high = [context.read(i, "terminal_growth_rate", "ratio", period=period,
                                  basis="assumption") for i in growth_ids]
    require(rate_low < rate < rate_high and g_low < growth < g_high,
            "DCF sensitivities must bracket base WACC and terminal growth strictly")
    grid = []
    for discount_rate in (rate_low, rate, rate_high):
        for stable_growth in (g_low, growth, g_high):
            cell = discounted_values(annual, discount_rate, stable_growth, adjustment)
            grid.append({"wacc": decimal_text(discount_rate), "terminal_growth": decimal_text(stable_growth),
                         "enterprise_value": cell["enterprise_value"], "equity_value": cell["equity_value"]})
    cash_inputs = [row["operands"][key] for row in rows for key in FORECAST_QUANTITIES if key != "other_cash_flow"]
    input_ids = [*cash_inputs, config["wacc"]["cost_of_equity"], config["wacc"]["pretax_cost_of_debt"],
                 config["wacc"]["debt_weight"], config["wacc"]["tax_rate"], config["terminal_growth"],
                 *config["bridge"].values(), *rate_ids, *growth_ids, context.config["scenarios"]["opening_cash"]]
    return {
        "formula": "fcff_wacc_perpetual_growth.v1.2", "basis": "scenario",
        "scenario": config["scenario"], "wacc": decimal_text(rate), "terminal_growth": decimal_text(growth),
        "annual_fcff": [{"year_end": rows[i * 12 + 11]["period"].split("/")[1], "fcff": decimal_text(value)}
                        for i, value in enumerate(annual)],
        "equity_bridge": {name: decimal_text(value) for name, value in bridge.items()},
        **base, "sensitivity": grid, **context.trace(input_ids, config["eligibility_evidence_ids"]),
    }


def calculate(context):
    result = {"currency": context.currency, "accounting_basis": context.accounting_basis, "entity": context.entity}
    requests = {
        "cap_table": lambda config: cap_table(context, config),
        "scenarios": lambda config: scenarios(context, config, result.get("cap_table", {})),
        "dcf": lambda config: dcf(context, config, result.get("scenarios", {})),
    }
    for key, evaluate in requests.items():
        config = context.request(key)
        if config is None:
            continue
        if config["status"] == "unavailable":
            result[key] = {"status": "unavailable", "value": None, "rationale": config["rationale"],
                           "gap_ids": config["gap_ids"]}
        else:
            result[key] = {"status": "calculated", "rationale": config["rationale"], **evaluate(config)}
    return result
