"""Source, calendar and measurement context shared by the v1.2 calculations."""

from calendar import monthrange
from datetime import date, timedelta

from contract import number, refs, require

ONE_DAY = timedelta(days=1)
OPERATING_STAGES = frozenset(("early_revenue", "repeatable_growth", "mature"))
LIVE_STAGES = OPERATING_STAGES | {"pilot"}
COMPONENTS = ("scenarios", "cap_table", "dcf")


def add_months(anchor, months):
    year, month0 = divmod(anchor.year * 12 + anchor.month - 1 + months, 12)
    new_end = monthrange(year, month0 + 1)[1]
    month_end = anchor.day == monthrange(anchor.year, anchor.month)[1]
    return date(year, month0 + 1, new_end if month_end else min(anchor.day, new_end))


def bounds(period):
    start, separator, end = period.partition("/")
    first = date.fromisoformat(start)
    last = date.fromisoformat(end) if separator else first
    require(first <= last, f"Period start follows end: {period}")
    return first, last


def decimal_text(value):
    if not value:
        return "0"
    result = format(value, "f")
    return result.rstrip("0").rstrip(".") if "." in result else result


class FinanceContext:
    def __init__(self, bundle, inputs, evidence, claims, gaps, source_origins=None):
        self.as_of = date.fromisoformat(bundle["as_of"])
        self.entity = bundle["profile"]["legal_entity"]
        self.stage = bundle["profile"]["stage"]
        self.models = set(bundle["profile"]["models"])
        self.config = bundle["financial_model"]
        self.currency = self.config["currency"]
        self.accounting_basis = self.config["accounting_basis"]
        self.inputs = inputs
        self.evidence = evidence
        self.claims = claims
        self.gaps = gaps
        self.source_origins = source_origins
        material_severities = {"High", "Critical"} if source_origins is not None else {"Critical"}
        self.blocked = {
            affected
            for challenge in bundle["challenges"]
            if challenge["severity"] in material_severities and challenge["status"] == "unresolved"
            for affected in challenge["affected"]
        }
        for input_id, row in inputs.items():
            _, last = bounds(row["period"])
            require(
                row["basis"] != "observed" or last <= self.as_of,
                f"{input_id}: observed period extends past the analysis date",
            )
            require(bool(row["rationale"].strip()), f"{input_id}: input needs a source rationale")
            refs(row["claim_ids"], claims, f"{input_id} financial claims")

    def use(self, identifier):
        severity = "material" if self.source_origins is not None else "critical"
        require(identifier not in self.blocked, f"{identifier}: unresolved {severity} challenge")

    def independent(self, ids, label):
        refs(ids, self.evidence, label)
        for eid in ids:
            self.use(eid)
        if self.source_origins is not None:
            require(self.source_origins.independent(ids), f"{label}: needs independent A/B evidence")
            return
        require(any(
            self.evidence[eid]["type"] in ("independent_public", "authoritative_record")
            and self.evidence[eid]["grade"] in ("A", "B") for eid in ids
        ), f"{label}: needs independent A/B evidence")

    def read(self, input_id, quantity, unit, *, period=None, basis=None, independent=False):
        refs((input_id,), self.inputs, quantity)
        row = self.inputs[input_id]
        self.use(input_id)
        require(row["quantity"] == quantity and row["unit"] == unit,
                f"{input_id}: expected {quantity} in {unit}")
        require(row["entity"] == self.entity and row["accounting_basis"] == self.accounting_basis,
                f"{input_id}: incompatible entity or accounting basis")
        require(row["currency"] == (self.currency if unit.startswith("money") else None),
                f"{input_id}: incompatible currency")
        require(period is None or row["period"] == period, f"{input_id}: wrong period, expected {period}")
        require(basis is None or row["basis"] == basis, f"{input_id}: expected {basis} basis")
        for eid in row["evidence_ids"]:
            self.use(eid)
        for claim_id in row["claim_ids"]:
            self.use(claim_id)
            claim = self.claims[claim_id]
            require(
                claim["status"] in ("reported", "verified") and not claim["oppose"]
                and (row["basis"] != "observed" or claim["kind"] == "historical")
                and bool(set(row["evidence_ids"]) & set(claim["support"])),
                f"{input_id}: unresolved, incompatible or unrelated financial claim {claim_id}",
            )
        if independent:
            self.independent(row["evidence_ids"], input_id)
        return number(row["value"])

    def trace(self, inputs, evidence=()):
        input_ids = list(dict.fromkeys(inputs))
        evidence_ids = set(evidence)
        for input_id in input_ids:
            evidence_ids.update(self.inputs[input_id]["evidence_ids"])
        return {"input_ids": input_ids, "evidence_ids": sorted(evidence_ids)}

    def request(self, name):
        request = self.config.get(name)
        if request is None:
            return None
        require(bool(request["rationale"].strip()), f"{name}: rationale required")
        if request["status"] == "unavailable":
            refs(request["gap_ids"], self.gaps, f"{name} missing information")
        else:
            self.use(name)
        return request
