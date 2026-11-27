"""Validate v1.4 research plans, work logs and correction trails offline."""

from collections import Counter, defaultdict
from functools import lru_cache
from urllib.parse import parse_qsl, urlsplit
import unicodedata

from contract import indexed, refs, require
from research_routing import PRIORITY, question_priority, select_factors

COMPANY_TYPES = {"company_material", "company_public"}
INDEPENDENT_TYPES = {"independent_public", "authoritative_record"}
TRACKING_KEYS = {"gclid", "fbclid", "msclkid"}
MATERIAL = {"High", "Critical"}
CAPABILITY = {"web_search": "web", "web_open": "web",
              "document_review": "documents", "private_request": "private_requests"}
STOP_REASONS = {
    "completed": {"criteria_met"},
    "partial": {"insufficient_evidence", "diminishing_returns", "access_blocked", "budget_limit", "contradiction"},
    "blocked": {"private_information", "tool_unavailable", "access_blocked", "prerequisite", "contradiction"},
    "deferred": {"budget_limit", "low_expected_value", "prerequisite"},
}


def normal(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def url_key(url):
    parts = urlsplit(url)
    require(parts.scheme in ("http", "https") and parts.hostname and not parts.username and not parts.password
            and not any(c.isspace() or ord(c) < 32 for c in url), "Unsafe research URL")
    host = parts.hostname.casefold().removeprefix("www.")
    port = parts.port
    query = tuple(sorted((name, value) for name, value in parse_qsl(parts.query, keep_blank_values=True)
                         if not name.casefold().startswith("utm_") and name.casefold() not in TRACKING_KEYS))
    return host, None if port in (None, 80, 443) else port, parts.path.rstrip("/") or "/", query


class SourceOrigins:
    def __init__(self, evidence):
        self.evidence = evidence
        self.by_id = {}
        self.members = defaultdict(list)
        aliases = {}
        for row in evidence.values():
            source_id = row["id"]
            origin = normal(row["origin"])
            require(bool(origin), f"{source_id}: source origin is blank")
            self.by_id[source_id] = origin
            self.members[origin].append(source_id)
            doc = ("document", normal(row["publisher"]), normal(row["title"]))
            key = ("url", url_key(row["url"])) if row["url"] else doc
            require(aliases.setdefault(key, origin) == origin,
                    f"{source_id}: the same source document or URL has multiple origins")
        self.company = self.groups(k for k, e in evidence.items() if e["type"] in COMPANY_TYPES)

    def groups(self, ids):
        return {self.by_id[key] for key in ids}

    def usable(self, ids):
        return self.groups(key for key in ids if self.evidence[key]["grade"] != "D")

    def independent(self, ids):
        return self.groups(key for key in ids if self.evidence[key]["grade"] in ("A", "B")
                           and self.evidence[key]["type"] in INDEPENDENT_TYPES) - self.company


def check_graph(questions, dependencies, name):
    for key in questions:
        refs(dependencies(key), questions, name)
    visiting = set()

    @lru_cache(maxsize=None)
    def visit(key):
        require(key not in visiting, f"Cycle in research {name}")
        visiting.add(key)
        for other in dependencies(key):
            visit(other)
        visiting.remove(key)

    for key in questions:
        visit(key)


class ResearchAudit:
    def __init__(self, bundle, factors, evidence, claims, gaps, origins):
        self.bundle = bundle
        self.plan = bundle["research_plan"]
        self.factors = factors
        self.evidence = evidence
        self.claims = claims
        self.gaps = gaps
        self.origins = origins
        self.questions = indexed(self.plan["questions"], "research question")
        self.attempts = indexed(bundle["research_attempts"], "research attempt")
        self.results = {row["question_id"]: row for row in bundle["research"]}
        require(len(self.results) == len(bundle["research"]) and self.results.keys() == self.questions.keys(),
                "Each planned question needs exactly one actual research record")
        self.selected = select_factors(bundle["profile"]["stage"], bundle["profile"]["models"], self.plan["objective"])
        self.required = set(self.selected)
        self.active = {key for key, row in factors.items() if row["status"] != "not_applicable"}
        self.material_unknown = set()
        self.used_attempts = set()
        self.challenge_attempts = set()

    def validate_selection(self):
        require(self.required <= self.factors.keys(),
                "Missing mandatory research factors: " + ", ".join(sorted(self.required - self.factors.keys())))
        require(all(PRIORITY[self.factors[key]["priority"]] >= PRIORITY[rule["minimum_priority"]]
                    for key, rule in self.selected.items()), "Factor priority is below its research playbook minimum")
        for field in ("objective_rationale", "stage_rationale", "limitations"):
            require(bool(self.plan[field].strip()), f"Research plan needs {field}")
        stage_ids = self.plan["stage_evidence_ids"]
        refs(stage_ids, self.evidence, "research stage evidence")
        require(self.bundle["profile"]["stage"] == "unknown" or self.origins.usable(stage_ids),
                "Declared stage needs usable evidence or must be unknown")

        exclusions = {row["factor_id"]: row for row in self.plan["exclusions"]}
        require(len(exclusions) == len(self.plan["exclusions"]) and exclusions.keys() == self.factors.keys() - self.active,
                "Each not-applicable factor needs exactly one exclusion and scoped evidence")
        for key, row in exclusions.items():
            refs(row["evidence_ids"], self.evidence, "factor exclusion evidence")
            require(bool(row["rationale"].strip()) and self.origins.usable(row["evidence_ids"]),
                    f"{key}: factor exclusion needs a rationale and usable evidence")
            require(not (self.factors[key]["support"] or self.factors[key]["oppose"]),
                    f"{key}: an excluded factor has evidence assigned to a finding")

    def validate_attempts(self):
        inventory = {f"{doc['name']} | {doc['version']}" for doc in self.bundle["documents"]}
        capabilities = self.plan["capabilities"]
        sources = set()
        for attempt_id, attempt in self.attempts.items():
            channel = attempt["channel"]
            outcome = attempt["outcome"]
            ids = attempt["evidence_ids"]
            refs(ids, self.evidence, f"{attempt_id} research evidence")
            require(capabilities[CAPABILITY[channel]], f"{attempt_id}: recorded use of an unavailable research tool")
            require(attempt["date"] <= self.bundle["as_of"], f"{attempt_id}: research after the analysis date")
            require(all(self.evidence[key]["accessed"] <= attempt["date"] for key in ids),
                    f"{attempt_id}: cited source accessed after research attempt")
            require(bool(attempt["target"].strip() and attempt["note"].strip()), f"{attempt_id}: missing target or note")
            require(bool(ids) == (outcome == "evidence_found"), f"{attempt_id}: attempt outcome and evidence disagree")
            if channel == "private_request":
                require(outcome in ("request_sent", "access_blocked"), f"{attempt_id}: request cannot attest to a review")
            else:
                require(outcome != "request_sent", f"{attempt_id}: request outcome needs private request channel")
            if channel == "web_search":
                require(all(self.evidence[key]["grade"] == "D" for key in ids),
                        f"{attempt_id}: search results alone may only be recorded as research leads")
            elif channel == "web_open":
                target = url_key(attempt["target"])
                require(all(self.evidence[key]["url"] and url_key(self.evidence[key]["url"]) == target for key in ids),
                        f"{attempt_id}: opened URL and evidence URL disagree")
            elif channel == "document_review":
                require(attempt["target"] in inventory, f"{attempt_id}: reviewed document missing from inventory")
            sources.update(ids)
        require(sources == set(self.evidence), "Evidence register contains sources without recorded research")
        budget = self.plan["budget"]
        self.counts = Counter(a["phase"] for a in self.attempts.values())
        ordinary_budget = budget["max_attempts"] - budget["challenge_reserve"]
        self.remaining = ordinary_budget - self.counts["research"]
        require(self.remaining >= 0 and len(self.attempts) <= budget["max_attempts"],
                "Research attempt budget or challenge reserve exceeded")

    def validate_questions(self):
        check_graph(self.questions, lambda key: self.questions[key]["depends_on"], "dependencies")
        check_graph(self.questions, lambda key: [self.questions[key]["parent_id"]]
                    if self.questions[key]["parent_id"] else [], "parent links")
        covered = set()
        texts = set()
        self.scores = {}
        for key, question in self.questions.items():
            refs(question["factor_ids"], self.active, f"{key} applicable factors")
            refs(question["claim_ids"], self.claims, f"{key} research claims")
            for field in ("question", "evidence_required", "counter_test", "decision_use"):
                require(bool(question[field].strip()), f"{key}: missing {field}")
            text = normal(question["question"])
            require(text not in texts, f"{key}: duplicate research question")
            texts.add(text)
            require(question["min_independent_origins"] <= question["min_origins"],
                    f"{key}: independent origin minimum exceeds usable origin minimum")
            covered.update(question["factor_ids"])
            self.scores[key] = question_priority(question, self.factors, self.plan["objective"])
        require(covered == self.active, "Applicable factor has no planned research question")

    def require_gap(self, gap_ids, factor_ids, label):
        refs(gap_ids, self.gaps, f"{label} research gaps")
        for factor_id in factor_ids:
            floor = PRIORITY[self.factors[factor_id]["priority"]]
            require(any(factor_id in self.gaps[key]["affected_factor_ids"] and
                        PRIORITY[self.gaps[key]["priority"]] >= floor for key in gap_ids),
                    f"{label}: material gap missing or under-prioritised for {factor_id}")

    def validate_results(self):
        evidence_by_factor = defaultdict(set)
        completed = set()
        open_statuses = {"unknown", "partial"}
        for key, row in self.results.items():
            question = self.questions[key]
            factors = question["factor_ids"]
            material = {factor for factor in factors if self.factors[factor]["priority"] in MATERIAL}
            refs(row["attempt_ids"], self.attempts, f"{key} research attempts")
            refs(row["evidence_ids"], self.evidence, f"{key} result evidence")
            refs(row["gap_ids"], self.gaps, f"{key} result gaps")
            self.used_attempts.update(row["attempt_ids"])
            attempts = [self.attempts[key] for key in row["attempt_ids"]]
            logged = {e for attempt in attempts for e in attempt["evidence_ids"]}
            require(set(row["evidence_ids"]) <= logged, f"{key}: result cites evidence absent from its recorded attempts")
            status, stop = row["status"], row["stop_reason"]
            require(stop in STOP_REASONS[status] and bool(row["reason"].strip()),
                    f"{key}: incompatible stop reason or missing research explanation")
            ready = all(self.results[dependency]["status"] == "completed" for dependency in question["depends_on"])
            disputed = any(self.claims[c]["status"] == "disputed" for c in question["claim_ids"])
            if status == "completed":
                self.check_completion(key, question, row, attempts, ready, disputed)
                completed.update(factors)
            else:
                self.check_stop(key, question, row, attempts, ready, disputed)
                if material:
                    self.require_gap(row["gap_ids"], material, key)
                    self.material_unknown.update(material)
            for factor in factors:
                evidence_by_factor[factor].update(row["evidence_ids"])

        for key in self.active:
            row = self.factors[key]
            cited = row["support"] + row["oppose"]
            require(set(cited) <= evidence_by_factor[key], f"{key}: factor evidence does not trace to research")
            if row["status"] in ("supported", "partial"):
                require(self.origins.usable(row["support"]), f"{key}: factor support contains only research leads")
            if row["status"] == "contradicted":
                require(self.origins.usable(row["oppose"]), f"{key}: factor opposition contains only research leads")
            if row["status"] == "supported":
                reconciled = not row["oppose"] or any(
                    item["status"] == "resolved" and item["route"] == "evidence" and key in item["affected"]
                    for item in self.bundle["challenges"]
                )
                require(key in completed and reconciled, f"{key}: factor support needs completed research and reconciled opposition")
            if row["priority"] in MATERIAL and row["status"] in open_statuses:
                self.require_gap(self.gaps, [key], f"Unresolved factor {key}")
                self.material_unknown.add(key)

    def check_completion(self, key, question, row, attempts, ready, disputed):
        require(ready, f"{key}: completed research has an unresolved prerequisite")
        require(not disputed, f"{key}: completed research has an unresolved disputed claim")
        require(not row["gap_ids"], f"{key}: completed research still has a linked unresolved gap")
        usable = len(self.origins.usable(row["evidence_ids"]))
        independent = len(self.origins.independent(row["evidence_ids"]))
        require(usable >= question["min_origins"] and independent >= question["min_independent_origins"],
                f"{key}: completed research lacks the required distinct source origins")
        require(any(a["intent"] in ("counter", "both") and a["outcome"] in ("evidence_found", "no_evidence")
                    for a in attempts), f"{key}: completed research lacks an executed counter-evidence test")

    def check_stop(self, key, question, row, attempts, ready, disputed):
        reason = row["stop_reason"]
        capabilities = self.plan["capabilities"]
        reachable = {
            "public": capabilities["web"], "provided": capabilities["documents"],
            "private": capabilities["private_requests"], "mixed": capabilities["web"] or capabilities["documents"],
        }
        conditions = {
            "budget_limit": self.remaining < question["estimated_attempts"],
            "low_expected_value": self.scores[key] < self.plan["budget"]["minimum_priority"],
            "diminishing_returns": bool(attempts),
            "access_blocked": any(a["outcome"] == "access_blocked" for a in attempts),
            "insufficient_evidence": bool(attempts),
            "private_information": question["evidence_route"] in ("private", "mixed") and bool(row["gap_ids"]),
            "tool_unavailable": not reachable[question["evidence_route"]],
            "prerequisite": not ready,
            "contradiction": disputed or any(self.claims[c]["status"] == "contradicted" for c in question["claim_ids"])
            or any(self.factors[f]["status"] == "contradicted" for f in question["factor_ids"]),
        }
        require(conditions[reason], f"{key}: research stop reason {reason} is unsupported")
        require(row["status"] != "partial" or attempts, f"{key}: partial research lacks recorded work")

    def validate_thesis_and_claims(self):
        thesis = self.bundle["thesis"]
        thesis_ids = thesis["question_ids"]
        refs(thesis_ids, self.questions, "independent thesis tests")
        recorded = {e for key in thesis_ids for e in self.results[key]["evidence_ids"]}
        require(set(thesis["independent_evidence"]) <= recorded, "Independent thesis evidence is absent from its tests")
        require(bool(thesis["independent"].strip()) and all(f.strip() for f in thesis["falsifiers"]),
                "Independent thesis needs an explicit conclusion and falsifiers")
        if thesis["management"]:
            require(normal(thesis["management"]) != normal(thesis["independent"]),
                    "Independent thesis repeats the management thesis")
        if thesis["status"] == "corroborated":
            completed = {e for key in thesis_ids if self.results[key]["status"] == "completed"
                         for e in self.results[key]["evidence_ids"]}
            require(self.origins.independent(set(thesis["independent_evidence"]) & completed),
                    "Corroborated thesis needs a completed independent test and evidence")
        if thesis["status"] == "unavailable":
            require(not thesis["independent_evidence"], "Unavailable thesis claims independent evidence")

        divergences = {key for row in thesis["divergences"] for key in row["claim_ids"]}
        related = defaultdict(list)
        for key, question in self.questions.items():
            for claim_id in question["claim_ids"]:
                related[claim_id].append(key)
        for claim_id, claim in self.claims.items():
            if claim["status"] == "reported":
                require(self.origins.usable(claim["support"]), f"{claim_id}: reported claim has no reviewed source")
            if claim["oppose"]:
                require(claim["status"] in ("disputed", "contradicted"), f"{claim_id}: opposing evidence must remain visible")
                require(self.origins.usable(claim["oppose"]), f"{claim_id}: opposing evidence contains only research leads")
                require(claim_id in divergences and related[claim_id],
                        f"{claim_id}: contradiction requires thesis divergence and a planned test")
                tested = {e for key in related[claim_id] for e in self.results[key]["evidence_ids"]}
                require(set(claim["support"] + claim["oppose"]) <= tested,
                        f"{claim_id}: contradiction evidence missing from its research")
                severity = max(PRIORITY[self.factors[f]["priority"]]
                               for key in related[claim_id] for f in self.questions[key]["factor_ids"])
                challenges = [item for item in self.bundle["challenges"]
                              if claim_id in item["affected"] and PRIORITY[item["severity"]] >= severity
                              and set(item["question_ids"]) & set(related[claim_id])]
                if claim["status"] == "disputed":
                    require(self.origins.usable(claim["support"]), f"{claim_id}: disputed claim lacks reviewed support")
                    require(any(c["status"] == "unresolved" for c in challenges),
                            f"{claim_id}: unresolved dispute needs a routed challenge of matching severity")
                elif severity >= PRIORITY["High"]:
                    require(challenges, f"{claim_id}: material contradiction needs a routed correction")

    def validate_challenges(self, universe, comparison_ids, model_ids):
        comparison_ids = set(comparison_ids)
        targets = {
            "scope": {"profile"} | self.factors.keys(),
            "evidence": {"thesis"} | self.evidence.keys() | self.claims.keys() | self.factors.keys()
            | self.questions.keys() | comparison_ids | {r["id"] for r in self.results.values()},
            "financial_model": model_ids - {"dcf"} | {r["id"] for key in ("inputs", "metrics") for r in self.bundle[key]},
            "valuation": (model_ids & {"dcf"}) | {r["id"] for r in self.bundle["valuations"]},
            "report": {"decision", "report"},
        }
        material_challenges = []
        for item in self.bundle["challenges"]:
            key = item["id"]
            affected = set(item["affected"])
            refs(item["question_ids"], self.questions, f"{key} corrective research questions")
            refs(item["attempt_ids"], self.attempts, f"{key} corrective research attempts")
            refs(item["rechecked_ids"], universe, f"{key} rechecked objects")
            refs(item["gap_ids"], self.gaps, f"{key} corrective gaps")
            require(bool(affected & targets[item["route"]]), f"{key}: correction route does not match affected objects")
            if item["route"] == "evidence":
                require(item["question_ids"], f"{key}: evidence correction needs a research question")
                linked = {v for q in item["question_ids"] for field in ("factor_ids", "claim_ids") for v in self.questions[q][field]}
                linked |= {e for q in item["question_ids"] for e in self.results[q]["evidence_ids"]}
                linked |= set(item["question_ids"]) | {self.results[q]["id"] for q in item["question_ids"]}
                require(not (affected & (self.claims.keys() | self.factors.keys() | self.evidence.keys())) - linked,
                        f"{key}: corrective questions do not cover the affected evidence, factors or claims")
                recorded = {a for q in item["question_ids"] for a in self.results[q]["attempt_ids"]}
                require(set(item["attempt_ids"]) <= recorded, f"{key}: corrective attempt missing from linked research")
            attempts = [self.attempts[a] for a in item["attempt_ids"]]
            require(all(a["phase"] == "challenge" for a in attempts), f"{key}: correction cites ordinary research as review work")
            self.challenge_attempts.update(item["attempt_ids"])
            if item["status"] == "resolved":
                require(affected <= set(item["rechecked_ids"]) and not item["gap_ids"],
                        f"{key}: resolved correction needs a recheck of affected objects and no unresolved gaps")
                if item["route"] == "evidence" and item["severity"] in MATERIAL:
                    require(any(a["intent"] in ("counter", "both") and a["outcome"] in ("evidence_found", "no_evidence")
                                for a in attempts), f"{key}: resolved material evidence needs a recorded counter-review")
            elif item["severity"] in MATERIAL:
                require(any(PRIORITY[self.gaps[g]["priority"]] >= PRIORITY[item["severity"]] for g in item["gap_ids"]),
                        f"{key}: material unresolved challenge needs a gap of matching priority")
                active_factors = affected & self.active
                active_factors |= {f for q in item["question_ids"] for f in self.questions[q]["factor_ids"]}
                self.require_gap(item["gap_ids"], {f for f in active_factors if self.factors[f]["priority"] in MATERIAL}, key)
                material_challenges.append(key)
        self.used_attempts |= self.challenge_attempts
        require(self.used_attempts == set(self.attempts), "Research attempts without a question or challenge record")
        require(self.challenge_attempts == {key for key, a in self.attempts.items() if a["phase"] == "challenge"},
                "Challenge reserve used outside a corrective review")
        if self.material_unknown or material_challenges:
            require(self.bundle["decision"]["status"] == "qualified", "Material unresolved research requires a qualified decision")
        return material_challenges

    def audit(self, universe, comparison_ids, model_ids):
        self.validate_attempts()
        self.validate_questions()
        self.validate_results()
        self.validate_thesis_and_claims()
        material_challenges = self.validate_challenges(universe, comparison_ids, model_ids)
        rank = sorted(self.questions, key=lambda key: (-self.scores[key], int(key[2:])))
        statuses = Counter(r["status"] for r in self.results.values())
        return {
            "playbook_version": "1.4",
            "objective": self.plan["objective"], "stage": self.bundle["profile"]["stage"],
            "required_factors": self.selected, "excluded_factors": sorted(self.factors.keys() - self.active),
            "question_counts": {status: statuses[status] for status in STOP_REASONS},
            "attempts_by_channel": dict(sorted(Counter(a["channel"] for a in self.attempts.values()).items())),
            "budget": {**self.plan["budget"], "research_used": self.counts["research"],
                       "challenge_used": self.counts["challenge"], "research_remaining": self.remaining},
            "source_records": len(self.evidence), "source_origins": len(self.origins.members),
            "independent_origins": len(self.origins.independent(self.evidence)),
            "origin_groups": {k: sorted(v) for k, v in sorted(self.origins.members.items())},
            "thesis_status": self.bundle["thesis"]["status"],
            "unresolved_material_factors": sorted(self.material_unknown),
            "unresolved_material_challenges": material_challenges,
            "limitations": self.plan["limitations"],
            "priorities": [{"question_id": key, "priority": str(self.scores[key]),
                            "status": self.results[key]["status"], "stop_reason": self.results[key]["stop_reason"]}
                           for key in rank],
        }
