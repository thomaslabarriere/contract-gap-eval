"""Evidence-relevance judge (who judges the judge?).

The objective guard in evaluate.py already checks that a cited clause EXISTS in
the contract. This judge asks the softer question: does that clause actually
pertain to the rule it is cited for — or is it a real-but-irrelevant clause? It
is delegated to a judge whose OWN reliability is measured against a labelled
gold set. Static judge here; an LLM judge would plug in behind the same shape.
"""

from __future__ import annotations

from typing import Protocol

from .models import GroundGoldItem, JudgeCalibration, PolicyRule
from .policy import get_rule

# Boilerplate legal vocabulary that appears in almost any clause and must not,
# on its own, make an off-topic clause look relevant to a specific rule.
_STOP = {
    "contrat", "clause", "partie", "parties", "applicable", "present", "regle",
    "cas", "sinon", "comporter", "prevoir", "faire", "etre", "doit", "aucune",
    "standard", "livrables", "sens", "chaque", "grave",
}


def _tokens(text: str) -> set[str]:
    lowered = text.lower().translate(str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc"))
    words = "".join(c if c.isalnum() else " " for c in lowered).split()
    return {t for t in words if len(t) > 3 and t not in _STOP}


class RelevanceJudge(Protocol):
    name: str

    def evidence_relevant(self, rule: PolicyRule, evidence: str) -> bool: ...


class StaticRelevanceJudge:
    """Evidence is relevant if it shares content vocabulary with the rule."""

    def __init__(self, min_overlap: int = 1) -> None:
        # Overlap on domain vocabulary (boilerplate is stopped out), so a shared
        # generic word like "contrat" can't make an off-topic clause relevant.
        self.name = "static-overlap"
        self._min = min_overlap

    def evidence_relevant(self, rule: PolicyRule, evidence: str) -> bool:
        rule_terms = _tokens(f"{rule.title} {rule.statement}")
        return len(_tokens(evidence) & rule_terms) >= self._min


class AlwaysRelevantJudge:
    """Deliberately bad judge — calibration must catch its false positives."""

    name = "always-relevant"

    def evidence_relevant(self, rule: PolicyRule, evidence: str) -> bool:
        return True


def calibrate_judge(judge: RelevanceJudge, gold: list[GroundGoldItem]) -> JudgeCalibration:
    agree = false_positive = false_negative = 0
    for item in gold:
        verdict = judge.evidence_relevant(get_rule(item.rule_id), item.evidence)
        if verdict == item.supports_gap:
            agree += 1
        elif verdict and not item.supports_gap:
            false_positive += 1
        else:
            false_negative += 1
    return JudgeCalibration(
        judge_name=judge.name,
        total=len(gold),
        agree=agree,
        false_positive=false_positive,
        false_negative=false_negative,
    )
