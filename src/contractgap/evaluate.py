"""Run an agent over the policy and diagnose it.

`analyze_contract` produces the gap matrix (the shippable artifact).
`evaluate_reliability` scores the agent against the labelled gold set: the star
metric is GAP-RECALL (of the real gaps, how many were caught) overall and by
severity, plus precision, plus an OBJECTIVE citation-hallucination guard (the
evidence quote must actually appear in the contract).
"""

from __future__ import annotations

import time

from .agent import Agent
from .contracts import get_contract
from .models import (
    Contract,
    ContractReport,
    GapResult,
    GapStatus,
    GapVerdict,
    GoldItem,
    ReliabilityReport,
    Severity,
    TokenUsage,
)
from .policy import RULES, get_rule


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def citation_hallucinated(contract: Contract, verdict: GapVerdict) -> bool:
    """True if the agent cited evidence that does not appear in the contract."""
    if verdict.evidence is None:
        return False
    return _norm(verdict.evidence) not in _norm(contract.full_text())


def analyze_contract(agent: Agent, contract: Contract) -> ContractReport:
    verdicts: list[GapVerdict] = []
    usage = TokenUsage()
    start = time.perf_counter()
    for rule in RULES:
        verdict, u = agent.run(contract, rule)
        verdicts.append(verdict)
        usage.prompt_tokens += u.prompt_tokens
        usage.completion_tokens += u.completion_tokens
    return ContractReport(
        contract_id=contract.contract_id,
        title=contract.title,
        agent_name=agent.name,
        verdicts=verdicts,
        latency_ms=(time.perf_counter() - start) * 1000,
        usage=usage,
    )


def evaluate_reliability(agent: Agent, gold: list[GoldItem]) -> ReliabilityReport:
    results: list[GapResult] = []
    agree = caught = missed = false_alarms = hallucinated = critical_missed = 0
    true_gaps = 0
    per_sev: dict[Severity, list[int]] = {s: [0, 0] for s in Severity}  # [caught, true]
    prompt_tokens = completion_tokens = 0
    total_latency_ms = 0.0

    for item in gold:
        contract = get_contract(item.contract_id)
        rule = get_rule(item.rule_id)
        start = time.perf_counter()
        verdict, usage = agent.run(contract, rule)
        total_latency_ms += (time.perf_counter() - start) * 1000
        prompt_tokens += usage.prompt_tokens
        completion_tokens += usage.completion_tokens

        got = verdict.status
        expected = item.expected
        is_missed = expected is GapStatus.GAP and got is not GapStatus.GAP
        is_false_alarm = expected is not GapStatus.GAP and got is GapStatus.GAP
        is_hall = citation_hallucinated(contract, verdict)

        if got is expected:
            agree += 1
        if expected is GapStatus.GAP:
            true_gaps += 1
            per_sev[rule.severity][1] += 1
            if not is_missed:
                caught += 1
                per_sev[rule.severity][0] += 1
            else:
                missed += 1
                if rule.severity is Severity.CRITICAL:
                    critical_missed += 1
        if is_false_alarm:
            false_alarms += 1
        if is_hall:
            hallucinated += 1

        results.append(
            GapResult(
                contract_id=item.contract_id,
                rule_id=item.rule_id,
                severity=rule.severity,
                expected=expected,
                got=got,
                missed_gap=is_missed,
                false_alarm=is_false_alarm,
                hallucinated_citation=is_hall,
            )
        )

    return ReliabilityReport(
        agent_name=agent.name,
        total=len(gold),
        agree=agree,
        true_gaps=true_gaps,
        caught_gaps=caught,
        missed_gaps=missed,
        false_alarms=false_alarms,
        hallucinated_citations=hallucinated,
        critical_missed=critical_missed,
        recall_by_severity={s: (v[0], v[1]) for s, v in per_sev.items()},
        results=results,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_latency_ms=total_latency_ms,
    )
