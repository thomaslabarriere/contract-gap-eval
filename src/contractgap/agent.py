"""Agents that produce a gap verdict for a (contract, rule) pair.

`HeuristicAgent` is the offline baseline: reference checks for structured rules,
keyword clause detection for judgment rules. It is realistic, not an oracle —
it misses the C-4 IP clause that names the right words but grants nothing (a
keyword scan can't read the negation). Mutation fixtures (`LaxAgent`,
`HallucinatorAgent`) drive the reliability tests. `OracleAgent` replays gold.
"""

from __future__ import annotations

from typing import Protocol

from .models import Contract, GapStatus, GapVerdict, GoldItem, PolicyRule, RuleKind, TokenUsage
from .policy import REFERENCE_CHECKS

# Keyword evidence for judgment rules: rule_id -> phrases that signal presence.
_KEYWORDS: dict[str, list[str]] = {
    "RGPD-28": ["rgpd", "sous-traitant", "article 28", "données personnelles"],
    "RESIL": ["résili"],
    "IP": ["propriété intellectuelle", "licence", "cession"],
    "CONF": ["confidentialité"],
}


class Agent(Protocol):
    name: str

    def run(self, contract: Contract, rule: PolicyRule) -> tuple[GapVerdict, TokenUsage]: ...


def _rgpd_applicable(contract: Contract, rule_id: str) -> bool:
    return rule_id != "RGPD-28" or contract.has_personal_data


def _verdict(
    rule_id: str, status: GapStatus, explanation: str, evidence: str | None = None
) -> GapVerdict:
    return GapVerdict(rule_id=rule_id, status=status, evidence=evidence, explanation=explanation)


def _matching_clause(contract: Contract, keywords: list[str]) -> str | None:
    for clause in contract.clauses:
        haystack = f"{clause.heading}. {clause.text}".lower()
        if any(kw in haystack for kw in keywords):
            return clause.text
    return None


class HeuristicAgent:
    name = "heuristic"

    def run(self, contract: Contract, rule: PolicyRule) -> tuple[GapVerdict, TokenUsage]:
        rid = rule.rule_id
        if rule.kind is RuleKind.STRUCTURED:
            status = REFERENCE_CHECKS[rid](contract)
            return _verdict(rid, status, "contrôle sur champ"), TokenUsage()
        if not _rgpd_applicable(contract, rid):
            return _verdict(rid, GapStatus.NOT_APPLICABLE, "non applicable"), TokenUsage()
        clause = _matching_clause(contract, _KEYWORDS[rid])
        if clause is not None:
            return _verdict(rid, GapStatus.COMPLIANT, "clause détectée", clause), TokenUsage()
        return _verdict(rid, GapStatus.GAP, "clause absente"), TokenUsage()


class LaxAgent:
    """Mutation fixture: rubber-stamps everything compliant -> misses every gap."""

    name = "lax"

    def run(self, contract: Contract, rule: PolicyRule) -> tuple[GapVerdict, TokenUsage]:
        return _verdict(rule.rule_id, GapStatus.COMPLIANT, "(laxiste)"), TokenUsage()


class HallucinatorAgent:
    """Mutation fixture: flags a gap and cites a clause that isn't in the
    contract -> the citation-hallucination guard must catch it."""

    name = "hallucinator"

    def run(self, contract: Contract, rule: PolicyRule) -> tuple[GapVerdict, TokenUsage]:
        return (
            GapVerdict(
                rule_id=rule.rule_id,
                status=GapStatus.GAP,
                evidence="Clause 99 : disposition inexistante inventée par l'agent.",
                explanation="(hallucination)",
            ),
            TokenUsage(),
        )


class OracleAgent:
    """Control: replays the gold labels -> perfect recall, must not be flagged."""

    name = "oracle"

    def __init__(self, gold: list[GoldItem]) -> None:
        self._labels = {(g.contract_id, g.rule_id): g.expected for g in gold}

    def run(self, contract: Contract, rule: PolicyRule) -> tuple[GapVerdict, TokenUsage]:
        status = self._labels.get((contract.contract_id, rule.rule_id), GapStatus.NOT_APPLICABLE)
        return GapVerdict(rule_id=rule.rule_id, status=status, explanation="(gold)"), TokenUsage()
