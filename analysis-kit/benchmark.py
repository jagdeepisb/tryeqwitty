"""Verify a frozen benchmark campaign and score submitted agent outputs offline."""

import argparse
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, localcontext
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator

from contract import indexed, refs, require

DEFAULT = Path(__file__).resolve().parents[1] / "benchmarks" / "v1.5"
NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,59}")
DECISION_CRITERIA = ("objective", "evidence", "next_step")
METRICS = ("factual_accuracy", "arithmetic_accuracy", "contradiction_recall", "answer_coverage",
           "citation_accuracy", "material_priorities", "decision_match", "decision_usefulness")
CATEGORIES = {"fact": "factual_accuracy", "arithmetic": "arithmetic_accuracy", "contradiction": "contradiction_recall"}


def object_with(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


TEXT = {"type": "string", "minLength": 1, "maxLength": 2000}
CITATIONS = {"type": "array", "items": TEXT, "uniqueItems": True, "maxItems": 12}
ANSWER = object_with({
    "value": {"anyOf": [TEXT, {"type": "null"}]},
    "confidence": {"type": "string", "pattern": r"^(?:0(?:\.[0-9]+)?|1(?:\.0+)?)(?![\s\S])", "maxLength": 30},
    "citations": CITATIONS,
})
TRIAL_SCHEMA = object_with({
    "cases": {"type": "object", "additionalProperties": object_with({
        "answers": {"type": "object", "additionalProperties": ANSWER},
        "priorities": {**CITATIONS, "maxItems": 2},
        "decision": object_with({
            "status": {"enum": ["hold", "advance", "reject", "scope_only"]},
            "rationale": TEXT, "next_request": TEXT, "citations": CITATIONS,
        }),
    })},
    "search_log": {"type": "array", "maxItems": 100, "items": object_with({
        "kind": {"enum": ["query", "open"]}, "target": TEXT,
        "outcome": {"enum": ["success", "no_result", "blocked"]},
    })},
})
REVIEW_SCHEMA = object_with({"reviews": {"type": "array", "items": object_with({
    "trial": TEXT, "case": TEXT, **dict.fromkeys(DECISION_CRITERIA, {"type": "boolean"}),
    "reason": TEXT, "hard_failures": {"type": "array", "items": TEXT, "uniqueItems": True},
})}})


def no_duplicate_keys(pairs):
    result = dict(pairs)
    require(len(pairs) == len(result), "Duplicate keys in JSON")
    return result


def parse(raw):
    return json.loads(raw, object_pairs_hook=no_duplicate_keys)


def read_json(path):
    return parse(path.read_bytes())


def digest(raw):
    return sha256(raw).hexdigest()


def artifact_id(value):
    require(isinstance(value, str) and ID.fullmatch(value), f"Invalid benchmark ID {value!r}")
    return value


def fingerprint(files):
    return digest(json.dumps(files, sort_keys=True, separators=(",", ":")).encode())


def verified_files(root):
    frozen = read_json(root / "frozen.json")
    files = frozen["files"]
    require(fingerprint(files) == frozen["fingerprint"], "Frozen manifest fingerprint mismatch")
    for name, expected in files.items():
        path = (root / name).resolve()
        require(path.is_relative_to(root), f"Invalid frozen path {name}")
        require(digest(path.read_bytes()) == expected, f"Frozen input changed: {name}")
    return frozen


def canonical(value):
    if value is None:
        return None
    if NUMBER.fullmatch(value):
        return Decimal(value)
    return " ".join(value.casefold().split())


def correct_value(value, expected):
    actual = canonical(value)
    target = canonical(expected["value"])
    if isinstance(actual, Decimal) and isinstance(target, Decimal):
        tolerance = Decimal(expected.get("tolerance") or "0")
        return abs(actual - target) <= tolerance
    return actual == target or actual in [canonical(v) for v in expected.get("aliases", [])]


def valid_citations(cited, expected):
    required = set(expected["refs"])
    present = set(cited)
    return bool(required & present) if expected.get("citation_policy") == "any" else required <= present


def pair_count(num, den):
    return {"count": num, "out_of": den}


def known_cases(root, suite, frozen):
    cases = {}
    keys = {}
    expected_files = {"suite.json", "solver.md", "reviewer.md", "sources.md", "reference-review.md"}
    for key in suite["cases"]:
        artifact_id(key)
        expected_files.update((f"cases/{key}.json", f"keys/{key}.json"))
        case = read_json(root / "cases" / f"{key}.json")
        answers = read_json(root / "keys" / f"{key}.json")
        require(case["id"] == answers["case"] == key and key not in cases, "Benchmark case ID mismatch")
        questions = indexed(case["questions"], "benchmark questions")
        require(questions.keys() == answers["answers"].keys(), f"{key}: reference questions do not match")
        source_ids = indexed(case["sources"], "benchmark sources")
        for expected in answers["answers"].values():
            require(expected["category"] in CATEGORIES and expected["refs"], f"{key}: reference answer lacks evidence")
            refs(expected["refs"], source_ids, "expected citation")
        refs(answers["material"], case["priority_options"], "material priority")
        require(len(answers["material"]) == len(set(answers["material"])) == 2, f"{key}: expected two material priorities")
        cases[key], keys[key] = case, answers
    for key in suite["tracks"]["live"]["cases"]:
        expected_files.add(f"cases/live-{key}.json")
        live = read_json(root / "cases" / f"live-{key}.json")
        require("sources" not in live and all(live[field] == cases[key][field]
                for field in ("id", "questions", "objective", "priority_options", "stage", "model")),
                f"{key}: live packet must preserve the task and omit frozen evidence")
        targets = {x["id"]: x["url"] for x in live["source_targets"]}
        require(targets and all(targets.values()) and targets == {x["id"]: x["url"] for x in cases[key]["sources"]},
                f"{key}: live targets do not match frozen sources")
    require(set(frozen["files"]) == expected_files, "Frozen manifest does not match the full benchmark input set")
    return cases, keys


def adjudicate(root, campaign, pairs):
    reviewers = campaign["reviewers"]
    require(len(reviewers) == len(set(reviewers)) == 2, "Campaign needs two distinct reviewers")
    votes = []
    for reviewer in reviewers:
        review = read_json(root / "judgments" / f"{artifact_id(reviewer)}.json")
        Draft202012Validator(REVIEW_SCHEMA).validate(review)
        by_case = {(r["trial"], r["case"]): r for r in review["reviews"]}
        require(len(by_case) == len(review["reviews"]) and by_case.keys() == pairs,
                f"Reviewer {reviewer} must cover every planned trial case exactly once")
        votes.append(by_case)
    overrides = campaign["resolutions"]
    choices = {(r["trial"], r["case"], r["criterion"]): r for r in overrides}
    require(len(choices) == len(overrides), "Duplicate adjudication resolutions")
    used = set()
    agreed = 0
    judged = {}
    for pair in sorted(pairs):
        a, b = (v[pair] for v in votes)
        criteria = {}
        for criterion in (*DECISION_CRITERIA, "hard_failure"):
            flag_a = bool(a["hard_failures"]) if criterion == "hard_failure" else a[criterion]
            flag_b = bool(b["hard_failures"]) if criterion == "hard_failure" else b[criterion]
            if flag_a == flag_b:
                criteria[criterion] = flag_a
                agreed += 1
            else:
                key = (*pair, criterion)
                require(key in choices, f"Unresolved reviewer disagreement: {key}")
                choice = choices[key]
                require(type(choice["pass"]) is bool and bool(choice["reason"].strip()), f"Invalid adjudication: {key}")
                criteria[criterion] = choice["pass"]
                used.add(key)
        judged[pair] = criteria
    require(used == choices.keys(), "Resolution supplied without a matching disagreement")
    return judged, pair_count(agreed, len(pairs) * (len(DECISION_CRITERIA) + 1))


def checked_output(raw):
    try:
        report = parse(raw)
        if Draft202012Validator(TRIAL_SCHEMA).is_valid(report):
            return report, []
    except ValueError:
        pass
    return {"cases": {}, "search_log": []}, ["invalid_output"]


def search_usage(output, track, definitions, cases):
    actions = output["search_log"]
    failures = []
    queries = [a for a in actions if a["kind"] == "query"]
    opens = [a for a in actions if a["kind"] == "open"]
    if len(actions) > definitions["max_search_actions"]:
        failures.append("search_budget_exceeded")
    if track == "live" and (len(queries) != 1 or len(opens) > 2):
        failures.append("live_action_protocol")
    approved = {s["url"] for key in definitions["cases"] for s in cases[key]["sources"] if s["url"]}
    if any(a["target"] not in approved for a in opens):
        failures.append("unapproved_source_open")
    return {a["target"] for a in opens if a["outcome"] == "success"}, failures


def add(counts, name, hits, total=1):
    counts[name][0] += hits
    counts[name][1] += total


def score_case(case, key, response, admitted, review):
    totals = {k: [0, 0] for k in METRICS}
    issues, errors = set(), []
    confidence_error, confidence_count = Decimal(0), 0
    answers = response.get("answers", {})
    if answers.keys() - key["answers"].keys():
        issues.add("unregistered_answer")
    for qid, expected in key["answers"].items():
        answer = answers.get(qid)
        correct = answer is not None and correct_value(answer["value"], expected)
        cited = answer is not None and valid_citations(answer["citations"], expected) and set(answer["citations"]) <= admitted
        add(totals, CATEGORIES[expected["category"]], correct)
        add(totals, "answer_coverage", answer is not None)
        add(totals, "citation_accuracy", cited)
        if answer is not None:
            confidence_count += 1
            confidence_error += (Decimal(answer["confidence"]) - int(correct)) ** 2
            if set(answer["citations"]) - admitted:
                issues.add("unconfirmed_citation")
        if not correct:
            gate = expected["gate"]
            if gate == "wrong_entity":
                issues.add("missing_identity" if answer is None or answer["value"] is None else gate)
            if gate == "unsupported_value" and answer is not None and answer["value"] is not None:
                issues.add(gate)
        if not correct or not cited:
            errors.append({"question": qid, "value_correct": correct, "citation_correct": cited})
    priorities = set(response.get("priorities", []))
    if priorities - case["priority_options"].keys():
        issues.add("unregistered_priority")
    add(totals, "material_priorities", len(priorities & set(key["material"])), len(key["material"]))
    decision = response.get("decision", {})
    if set(decision.get("citations", [])) - admitted:
        issues.add("unconfirmed_citation")
    if decision.get("status") == "advance" and key["decision"] != "advance":
        issues.add("unqualified_advance")
    if review["hard_failure"]:
        issues.add("adjudicated_hard_failure")
    add(totals, "decision_match", decision.get("status") == key["decision"])
    add(totals, "decision_usefulness", sum(review[k] for k in DECISION_CRITERIA), len(DECISION_CRITERIA))
    for criterion in DECISION_CRITERIA:
        require(not review[criterion] or decision, "Decision review passes an absent decision")
    return {
        "case": case["id"], "metrics": {name: pair_count(*pair) for name, pair in totals.items()},
        "brier_squared_error_sum": str(confidence_error), "calibration_scored": confidence_count,
        "hard_failures": sorted(issues), "answer_errors": errors,
    }


def output_agreement(runs, keys):
    values_match = values_eligible = values_present = decisions_match = decisions_eligible = 0
    for left, right in combinations(runs, 2):
        for case in left["case_ids"]:
            a, b = (r["output"]["cases"].get(case, {}) for r in (left, right))
            for q in keys[case]["answers"]:
                values_eligible += 1
                answers = [r.get("answers", {}).get(q) for r in (a, b)]
                if all(x is not None for x in answers):
                    values_present += 1
                    values_match += canonical(answers[0]["value"]) == canonical(answers[1]["value"])
            decisions_eligible += 1
            a_status, b_status = (r.get("decision", {}).get("status") for r in (a, b))
            decisions_match += a_status is not None and a_status == b_status
    return {"answer_agreement": pair_count(values_match, values_eligible),
            "answers_present_in_both": values_present, "decision_agreement": pair_count(decisions_match, decisions_eligible)}


def summarize_cases(cases):
    return {
        "metrics": {name: pair_count(sum(r["metrics"][name]["count"] for r in cases),
                                     sum(r["metrics"][name]["out_of"] for r in cases)) for name in METRICS},
        "calibration": {
            "scored": sum(r["calibration_scored"] for r in cases),
            "eligible": sum(r["metrics"]["answer_coverage"]["out_of"] for r in cases),
            "squared_error_sum": str(sum((Decimal(r["brier_squared_error_sum"]) for r in cases), Decimal(0))),
        },
    }


def evaluate(root):
    root = root.resolve()
    frozen = verified_files(root)
    suite = read_json(root / "suite.json")
    campaign = read_json(root / "campaign.json")
    sealed_at = datetime.fromisoformat(frozen["sealed_at"])
    require(sealed_at.utcoffset() is not None, "Benchmark seal requires a timestamp with a timezone")
    require(campaign["fingerprint"] == frozen["fingerprint"] and suite["suite_id"] == frozen["suite_id"],
            "Campaign must match the frozen input set")
    require(set(suite["tracks"]) == {"fixed", "live"} and suite["tracks"]["fixed"]["max_search_actions"] == 0,
            "Benchmark needs separate fixed and live tracks")
    cases, keys = known_cases(root, suite, frozen)
    specs = indexed(campaign["trials"], "trial")
    groups = defaultdict(list)
    pairs = set()
    for trial, spec in specs.items():
        artifact_id(trial)
        track = spec["track"]
        require(track in suite["tracks"], "Unknown trial track")
        require(all(spec[field].strip() for field in ("provider", "configuration", "execution_date", "tools")),
                f"{trial}: missing execution metadata")
        recorded_at = datetime.fromisoformat(spec["output_recorded_at"])
        require(recorded_at.utcoffset() is not None and recorded_at >= sealed_at,
                f"{trial}: trial output predates the benchmark seal or lacks a timezone")
        plan = suite["tracks"][track]
        refs(plan["cases"], cases, "trial track cases")
        require(plan["cases"] and len(set(plan["cases"])) == len(plan["cases"]), "Duplicate or missing track cases")
        groups[track, spec["provider"], spec["configuration"], spec["model_version"]].append(trial)
        pairs.update((trial, key) for key in plan["cases"])
    require({group[0] for group in groups} == suite["tracks"].keys(), "Both benchmark tracks need recorded trials")
    reviews, agreement = adjudicate(root, campaign, pairs)
    runs = {}
    with localcontext() as ctx:
        ctx.prec = 80
        for trial, spec in specs.items():
            raw = (root / "trials" / f"{trial}.json").read_bytes()
            require(digest(raw) == spec["sha256"], f"{trial}: trial output changed")
            output, issues = checked_output(raw)
            track = spec["track"]
            plan = suite["tracks"][track]
            require(valid_replicate(plan["replicates"]), "Track needs a positive recorded repeat count")
            opened, tool_failures = search_usage(output, track, plan, cases)
            issues.extend(tool_failures)
            if output["cases"].keys() - set(plan["cases"]):
                issues.append("unexpected_case")
            rows = []
            for key in plan["cases"]:
                admitted = {source["id"] for source in cases[key]["sources"] if track == "fixed" or source["url"] in opened}
                rows.append(score_case(cases[key], keys[key], output["cases"].get(key, {}), admitted, reviews[trial, key]))
            runs[trial] = {
                "metadata": spec, "output": output, "case_ids": plan["cases"], "cases": rows,
                "metrics": summarize_cases(rows)["metrics"],
                "search_actions": len(output["search_log"]),
                "hard_failures": sorted(set(issues) | {f for row in rows for f in row["hard_failures"]}),
            }
        summaries = []
        for (track, provider, config, version), trials in groups.items():
            planned = suite["tracks"][track]["replicates"]
            require(len(trials) == planned, f"Incomplete {track} repeat set for {provider}/{config}")
            grouped = [runs[key] for key in trials]
            case_rows = [row for result in grouped for row in result["cases"]]
            stats = summarize_cases(case_rows)
            calibration = stats["calibration"]
            n = calibration["scored"]
            calibration["brier_mean"] = format(Decimal(calibration["squared_error_sum"]) / n, ".6f") if n else None
            summaries.append({
                "track": track, "provider": provider, "configuration": config, "model_version": version,
                "trials": len(grouped), "trial_cases": len(case_rows),
                "search_actions": sum(result["search_actions"] for result in grouped),
                "hard_gate_clear": pair_count(sum(not r["hard_failures"] for r in grouped), len(grouped)),
                **stats, **output_agreement(grouped, keys),
            })
    return {
        "suite_id": suite["suite_id"], "fingerprint": frozen["fingerprint"],
        "reviewer_agreement": agreement, "summaries": summaries,
        "runs": [{k: v for k, v in run.items() if k not in ("output", "case_ids")} for run in runs.values()],
    }


def valid_replicate(value):
    return type(value) is int and value > 0


def prepare_inputs(root, track):
    root = root.resolve()
    frozen = verified_files(root)
    suite = read_json(root / "suite.json")
    known_cases(root, suite, frozen)
    template = (root / "solver.md").read_text(encoding="utf-8").rstrip()
    names = suite["tracks"][track]["cases"]
    packets = [read_json(root / "cases" / f"{'live-' if track == 'live' else ''}{name}.json") for name in names]
    budget = suite["tracks"][track]["max_search_actions"]
    return (f"{template}\n\n## Selected track\n\n{track} · {budget} allowed web actions\n\n"
            f"```json\n{json.dumps(packets, indent=2, ensure_ascii=False)}\n```")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite-dir", type=Path, default=DEFAULT)
    parser.add_argument("--prepare", choices=("fixed", "live"), help="Print the sealed solver brief and packet")
    args = parser.parse_args()
    if args.prepare:
        print(prepare_inputs(args.suite_dir, args.prepare))
    else:
        print(json.dumps(evaluate(args.suite_dir), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
