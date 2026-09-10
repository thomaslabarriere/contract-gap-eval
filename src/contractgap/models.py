"""Shared contracts for contract-gap-eval. Every module imports from here.

SCOPE: SYNTHETIC contracts and a SIMPLIFIED illustrative internal policy — not
legal advice, not a real compliance product, no client data. The value is the
instrument: an agent that flags contract-vs-policy gaps AND a measure of how
many real gaps it MISSES (gap-recall), the number a legal team needs before it
trusts an agent. Plug in a real policy + contracts for real numbers.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class RuleKind(StrEnum):
    """STRUCTURED rules read an extracted field (objective); JUDGMENT rules turn
    on reading the clause text (needs an expert / LLM)."""

    STRUCTURED = "structured"
    JUDGMENT = "judgment"


class GapStatus(StrEnum):
    COMPLIANT = "compliant"
    GAP = "gap"
    NOT_APPLICABLE = "not_applicable"


class Clause(BaseModel):
    heading: str
    text: str


class Contract(BaseModel):
    """A synthetic supplier/commercial contract."""

    contract_id: str
    title: str
    # Extracted structured fields (None = not stated in the contract).
    payment_days: float | None = None
    liability_cap: float | None = None
    governing_law: str = ""
    # Whether the contract involves processing personal data (drives RGPD rule).
    has_personal_data: bool = False
    clauses: list[Clause] = Field(default_factory=list)

    def full_text(self) -> str:
        return "\n".join(f"{c.heading}. {c.text}" for c in self.clauses)


class PolicyRule(BaseModel):
    """One internal-policy requirement, as a legal team would state it."""

    rule_id: str
    title: str
    statement: str
    kind: RuleKind
    severity: Severity


class GapVerdict(BaseModel):
    """The agent's decision for one (contract, rule) pair."""

    rule_id: str
    status: GapStatus
    # A verbatim quote from the contract grounding the verdict (the "where").
    evidence: str | None = None
    explanation: str = ""


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ContractReport(BaseModel):
    """The shippable artifact: the gap matrix for one contract."""

    contract_id: str
    title: str
    agent_name: str = ""
    verdicts: list[GapVerdict] = Field(default_factory=list)
    latency_ms: float = 0.0
    usage: TokenUsage = Field(default_factory=TokenUsage)

    @property
    def gaps(self) -> list[GapVerdict]:
        return [v for v in self.verdicts if v.status is GapStatus.GAP]


class GoldItem(BaseModel):
    """Ground truth for one (contract, rule) pair."""

    contract_id: str
    rule_id: str
    expected: GapStatus


class ReliabilityReport(BaseModel):
    """How well the agent finds the gaps that truly exist."""

    agent_name: str
    total: int
    agree: int
    true_gaps: int
    caught_gaps: int
    missed_gaps: int
    false_alarms: int          # flagged a gap where there was none
    hallucinated_citations: int  # evidence quote not found in the contract
    critical_missed: int
    # Recall per severity: severity -> (caught, true).
    recall_by_severity: dict[Severity, tuple[int, int]] = Field(default_factory=dict)
    results: list[GapResult] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_latency_ms: float = 0.0

    @property
    def gap_recall(self) -> float:
        return self.caught_gaps / self.true_gaps if self.true_gaps else 1.0

    @property
    def precision(self) -> float:
        flagged = self.caught_gaps + self.false_alarms
        return self.caught_gaps / flagged if flagged else 1.0

    @property
    def agreement_rate(self) -> float:
        return self.agree / self.total if self.total else 1.0


class GapResult(BaseModel):
    """Per (contract, rule) diagnosis, for the reliability report."""

    contract_id: str
    rule_id: str
    severity: Severity
    expected: GapStatus
    got: GapStatus
    missed_gap: bool = False
    false_alarm: bool = False
    hallucinated_citation: bool = False


class GroundGoldItem(BaseModel):
    """Labelled example for calibrating the evidence-groundedness judge: does
    `evidence` genuinely support flagging a gap on this rule?"""

    contract_id: str
    rule_id: str
    evidence: str
    supports_gap: bool


class JudgeCalibration(BaseModel):
    judge_name: str
    total: int
    agree: int
    false_positive: int
    false_negative: int

    @property
    def agreement_rate(self) -> float:
        return self.agree / self.total if self.total else 1.0
