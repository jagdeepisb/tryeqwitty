"""Eligibility and calculations for the v1.2 financial metric and valuation rows."""

from contract import refs, require
from finance_context import LIVE_STAGES, ONE_DAY, OPERATING_STAGES, add_months, bounds

# New formula -> applicable model, earliest supported stage group, period, operands and output unit.
MODEL_METRICS = {
    "saas_arr": ("saas", OPERATING_STAGES, "point",
                 {"mrr": ("contracted_recurring_mrr", "money_per_month")}, "money"),
    "saas_logo_churn": ("saas", OPERATING_STAGES, "span",
                        {"churned": ("churned_opening_customers", "count"),
                         "opening": ("opening_customers", "count")}, "ratio"),
    "marketplace_match_rate": ("marketplace", LIVE_STAGES, "span",
                               {"matched": ("matched_requests", "count"),
                                "eligible": ("eligible_requests", "count")}, "ratio"),
    "manufacturing_first_pass_yield": ("manufacturing", LIVE_STAGES, "span",
                                       {"passed": ("first_pass_good_units", "count"),
                                        "processed": ("first_pass_processed_units", "count")}, "ratio"),
    "manufacturing_cash_conversion_days": ("manufacturing", OPERATING_STAGES, "span",
                                          {"inventory": ("average_inventory", "money"),
                                           "cogs": ("cogs", "money"),
                                           "receivables": ("average_trade_receivables", "money"),
                                           "credit_sales": ("credit_sales", "money"),
                                           "payables": ("average_trade_payables", "money"),
                                           "credit_purchases": ("credit_purchases", "money")}, "days"),
    "lending_net_charge_off_rate": ("lending", LIVE_STAGES, "year",
                                   {"charge_offs": ("gross_charge_offs", "money"),
                                    "recoveries": ("charge_off_recoveries", "money"),
                                    "average_loans": ("average_gross_loan_principal", "money")}, "ratio"),
    "lending_par30": ("lending", LIVE_STAGES, "point",
                      {"past_due": ("principal_on_loans_over_30_days_past_due", "money"),
                       "portfolio": ("gross_loan_principal", "money")}, "ratio"),
    "consumer_repeat_purchase_rate": ("consumer", OPERATING_STAGES, "span",
                                      {"repeat": ("repeat_buyers", "count"),
                                       "eligible": ("eligible_buyers", "count")}, "ratio"),
    "services_billable_utilisation": ("services", LIVE_STAGES, "span",
                                     {"billed": ("billable_hours", "hours"),
                                      "available": ("available_delivery_hours", "hours")}, "ratio"),
}

# Legacy operands still use v1.1 arithmetic. v1.2 explicitly binds their financial definitions.
LEGACY_QUANTITIES = {
    "revenue_growth": ("recognised_revenue", "recognised_revenue"),
    "gross_margin": ("recognised_revenue", "cogs"),
    "contribution_margin": ("recognised_revenue", "variable_cost"),
    "ebitda_margin": ("ebitda", "recognised_revenue"),
    "cac": ("acquisition_spend", "acquired_customers"),
    "cac_payback": ("customer_acquisition_cost", "monthly_contribution_per_acquired_customer"),
    "nrr": ("opening_recurring_revenue", "expansion_recurring_revenue",
            "contraction_recurring_revenue", "churned_recurring_revenue"),
    "grr": ("opening_recurring_revenue", "contraction_recurring_revenue", "churned_recurring_revenue"),
    "take_rate": ("recognised_marketplace_revenue", "matched_gmv"),
    "utilisation": ("used_capacity", "available_capacity"),
    "inventory_turns": ("cogs", "average_inventory"),
    "runway": ("unrestricted_cash", "monthly_net_burn"),
    "current_ratio": ("current_assets", "current_liabilities"),
    "net_debt": ("interest_bearing_debt", "unrestricted_cash"),
    "balance_sheet_gap": ("total_assets", "total_liabilities", "total_equity"),
    "cash_flow_gap": ("closing_cash", "opening_cash", "operating_cash_flow",
                      "investing_cash_flow", "financing_cash_flow"),
    "ev_revenue": ("recognised_revenue", "comparable_ev_revenue_multiple"),
    "ev_ebitda": ("normalised_ebitda", "comparable_ev_ebitda_multiple"),
    "net_assets": ("realisable_assets", "settlement_liabilities"),
    "ev_to_equity": ("enterprise_value", "interest_bearing_debt", "unrestricted_cash"),
}

LEGACY_METRIC_UNITS = {
    **dict.fromkeys(("revenue_growth", "gross_margin", "contribution_margin", "ebitda_margin",
                    "nrr", "grr", "take_rate", "utilisation", "current_ratio"), "ratio"),
    **dict.fromkeys(("net_debt", "balance_sheet_gap", "cash_flow_gap"), "money"),
    "cac": "money_per_customer", "cac_payback": "months", "runway": "months",
    "inventory_turns": "turns_per_year",
}

LEGACY_MODEL_GUARDS = {
    "nrr": ("saas", OPERATING_STAGES),
    "grr": ("saas", OPERATING_STAGES),
    "take_rate": ("marketplace", OPERATING_STAGES),
    "utilisation": ("manufacturing", LIVE_STAGES),
    "inventory_turns": ("manufacturing", OPERATING_STAGES),
}
LEGACY_OPERATING_METRICS = {
    "revenue_growth", "gross_margin", "contribution_margin", "ebitda_margin", "cac", "cac_payback",
}
POINT_FORMULAS = {"runway", "current_ratio", "net_debt", "balance_sheet_gap", "net_assets", "ev_to_equity"}
YEAR_FORMULAS = {"ev_revenue", "ev_ebitda", "inventory_turns"}


def check_calendar(period, shape, formula):
    start, end = bounds(period)
    span = "/" in period
    require(span == (shape != "point"), f"{formula}: expected a {shape} period")
    if shape == "year":
        require(end == add_months(start - ONE_DAY, 12), f"{formula}: needs a full 12-month period")
    return start, end


def check_growth_dates(current, prior):
    c0, c1 = check_calendar(current, "span", "revenue_growth")
    p0, p1 = check_calendar(prior, "span", "revenue_growth")
    months = (c1.year - c0.year) * 12 + c1.month - c0.month + 1
    same_calendar_months = (c0.day == p0.day == 1
                            and c1 == add_months(c0 - ONE_DAY, months)
                            and p1 == add_months(p0 - ONE_DAY, months))
    require(p1 < c0 and (c1 - c0 == p1 - p0 or same_calendar_months),
            "revenue_growth: prior period must precede current and have a comparable duration")


def check_model(context, formula, model, stages):
    require(model in context.models and context.stage in stages,
            f"{formula}: ineligible business model or stage")


def read_operands(context, row, specs, bases):
    operands = row["operands"]
    require(operands.keys() == specs.keys(), f"{row['id']}: operand keys do not match formula")
    return {
        name: context.read(operands[name], quantity, unit, basis=bases[name],
                           independent=quantity.startswith("comparable_")
                           or quantity in {"enterprise_value", "realisable_assets", "settlement_liabilities"})
        for name, (quantity, unit) in specs.items()
    }


def new_metric(context, row):
    formula = row["formula"]
    model, stages, shape, specs, unit = MODEL_METRICS[formula]
    check_model(context, formula, model, stages)
    ids = row["operands"].values()
    refs(ids, context.inputs, row["id"])
    basis = "observed" if row["basis"] == "observed" else "assumption"
    x = read_operands(context, row, specs, dict.fromkeys(specs, basis))
    periods = {context.inputs[input_id]["period"] for input_id in ids}
    require(len(periods) == 1, f"{formula}: mixed periods")
    start, end = check_calendar(periods.pop(), shape, formula)
    require(all(v >= 0 for v in x.values()), f"{formula}: negative input")
    require(all(x[k] == x[k].to_integral_value() for k, (_, u) in specs.items() if u == "count"),
            f"{formula}: fractional count")
    if formula == "saas_arr":
        value = x["mrr"] * 12
    elif formula == "manufacturing_cash_conversion_days":
        require(all(x[key] > 0 for key in ("cogs", "credit_sales", "credit_purchases")),
                f"{formula}: cost and credit-sales/purchase denominators must be positive")
        value = ((end - start).days + 1) * (
            x["inventory"] / x["cogs"] + x["receivables"] / x["credit_sales"]
            - x["payables"] / x["credit_purchases"]
        )
    elif formula == "lending_net_charge_off_rate":
        require(x["average_loans"] > 0, f"{formula}: average gross loan principal must be positive")
        value = (x["charge_offs"] - x["recoveries"]) / x["average_loans"]
    else:
        numerator, denominator = x.values()
        require(0 <= numerator <= denominator and denominator > 0,
                f"{formula}: numerator must fit a positive denominator")
        value = numerator / denominator
    return value, unit


def check_legacy(context, row, formula, units, *, valuation=False):
    if formula in LEGACY_MODEL_GUARDS:
        check_model(context, formula, *LEGACY_MODEL_GUARDS[formula])
    if formula in LEGACY_OPERATING_METRICS:
        require(context.stage in OPERATING_STAGES, f"{formula}: ineligible commercial stage")
    if valuation and formula != "net_assets":
        require(context.stage in OPERATING_STAGES and "lending" not in context.models,
                f"{formula}: ineligible valuation model or stage")
    basis = "observed" if valuation or row["basis"] == "observed" else "assumption"
    bases = dict.fromkeys(units, basis)
    if formula in ("ev_revenue", "ev_ebitda"):
        bases["multiple"] = "assumption"
    specs = {key: (quantity, units[key]) for key, quantity in zip(units, LEGACY_QUANTITIES[formula], strict=True)}
    x = read_operands(context, row, specs, bases)
    periods = {name: context.inputs[input_id]["period"] for name, input_id in row["operands"].items()}
    if formula == "revenue_growth":
        check_growth_dates(periods["current"], periods["prior"])
    else:
        shape = "point" if formula in POINT_FORMULAS else "year" if formula in YEAR_FORMULAS else "span"
        for period in set(periods.values()):
            check_calendar(period, shape, formula)
        if formula in ("net_assets", "ev_to_equity"):
            require(set(periods.values()) == {context.as_of.isoformat()},
                    f"{formula}: equity bridge and net assets must use analysis-date inputs")
    if formula == "take_rate":
        require(x["revenue"] <= x["gmv"], "take_rate: marketplace fees exceed matched GMV")
    if formula in ("net_assets", "ev_to_equity"):
        require(all(v >= 0 for v in x.values()), f"{formula}: negative valuation operand")
