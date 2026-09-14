"""The evidence-relevance judge is itself calibrated (who judges the judge?)."""

from __future__ import annotations

from contractgap.contracts import get_contract
from contractgap.evaluate import citation_hallucinated
from contractgap.goldset import GROUND_GOLD
from contractgap.judge import AlwaysRelevantJudge, StaticRelevanceJudge, calibrate_judge
from contractgap.models import GapStatus, GapVerdict


def test_static_judge_beats_a_rubber_stamp() -> None:
    static = calibrate_judge(StaticRelevanceJudge(), GROUND_GOLD)
    stamp = calibrate_judge(AlwaysRelevantJudge(), GROUND_GOLD)
    # The overlap judge is not perfect (boilerplate nouns like "contrat" /
    # "clause" are deliberately NOT stopped), but it must be strictly better
    # than a rubber stamp: higher agreement and fewer false positives.
    assert static.agreement_rate > stamp.agreement_rate
    assert static.false_positive < stamp.false_positive
    # It never rejects a genuinely relevant clause on this gold set.
    assert static.false_negative == 0


def test_calibration_catches_a_rubber_stamp_judge() -> None:
    cal = calibrate_judge(AlwaysRelevantJudge(), GROUND_GOLD)
    assert cal.false_positive > 0
    assert cal.agreement_rate < 1.0


def test_judge_gold_evidence_passes_the_citation_guard() -> None:
    """Every evidence quote in the judge gold must be a verbatim substring of
    its contract, i.e. pass the SAME citation-hallucination guard the agent
    verdicts are held to. Paraphrased calibration evidence would be a direct
    self-contradiction: gold that its own repo would flag as hallucinated.
    """
    for item in GROUND_GOLD:
        contract = get_contract(item.contract_id)
        verdict = GapVerdict(
            rule_id=item.rule_id,
            status=GapStatus.GAP,
            evidence=item.evidence,
            explanation="(judge gold citation guard)",
        )
        assert not citation_hallucinated(contract, verdict), (
            f"{item.contract_id}/{item.rule_id}: evidence is not a verbatim "
            f"substring of the contract: {item.evidence!r}"
        )
