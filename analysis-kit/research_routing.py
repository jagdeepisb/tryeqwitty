"""Select the public v1.4 research playbook for a company profile."""

import argparse
from fractions import Fraction
import json
from pathlib import Path

from contract import require

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = json.loads((ROOT / "factor-library/research-playbooks-v1.4.json").read_text(encoding="utf-8"))
PRIORITY = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}


def select_factors(stage, models, objective):
    """Return the union of applicable routes and the highest priority floor for each factor."""
    require(stage in PLAYBOOK["stages"], f"Unknown research stage {stage}")
    require(objective in PLAYBOOK["objectives"], f"Unknown research objective {objective}")
    require(bool(models) and len(set(models)) == len(models), "Provide distinct business models")
    require(set(models) <= PLAYBOOK["models"].keys(), "Unknown research business model")
    stage_group = PLAYBOOK["stage_groups"][stage]
    routes = [
        ("baseline", PLAYBOOK["baseline"]),
        (f"stage:{stage}", PLAYBOOK["stages"][stage]),
        (f"objective:{objective}", PLAYBOOK["objectives"][objective]),
        *((f"model:{model}", PLAYBOOK["models"][model][stage_group]) for model in sorted(models)),
    ]
    selected = {}
    for route, floors in routes:
        for factor_id, floor in floors.items():
            if factor_id not in selected:
                selected[factor_id] = {"minimum_priority": floor, "routes": []}
            factor = selected[factor_id]
            factor["minimum_priority"] = max(floor, factor["minimum_priority"], key=PRIORITY.get)
            factor["routes"].append(route)
    return {key: selected[key] for key in sorted(selected)}


def question_priority(question, factors, objective):
    materiality = max(PRIORITY[factors[key]["priority"]] for key in question["factor_ids"])
    objective_factors = PLAYBOOK["objectives"][objective]
    relevance = 2 if any(key in objective_factors for key in question["factor_ids"]) else 1
    return Fraction(materiality * question["uncertainty"] * question["answerability"] * relevance,
                    question["estimated_attempts"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, choices=PLAYBOOK["stages"])
    parser.add_argument("--models", required=True, nargs="+", choices=PLAYBOOK["models"])
    parser.add_argument("--objective", required=True, choices=PLAYBOOK["objectives"])
    args = parser.parse_args()
    factors = select_factors(args.stage, args.models, args.objective)
    print(json.dumps({
        "version": PLAYBOOK["version"],
        "stage": args.stage,
        "models": args.models,
        "objective": args.objective,
        "factors": [{"id": key, **PLAYBOOK["factors"][key], **record} for key, record in factors.items()],
        "budget_examples": PLAYBOOK["budget_examples"],
    }, indent=2))


if __name__ == "__main__":
    main()
