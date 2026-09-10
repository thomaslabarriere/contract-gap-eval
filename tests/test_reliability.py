"""Mutation proof: the harness rewards a correct agent, catches a lax one and a
hallucinating one, and reports the baseline's real (semantic) miss exactly."""

from __future__ import annotations

from contractgap.agent import HallucinatorAgent, HeuristicAgent, LaxAgent, OracleAgent
from contractgap.contracts import CONTRACTS
from contractgap.evaluate import evaluate_reliability
from contractgap.goldset import build_gold_set
from contractgap.models import GapStatus, Severity
from contractgap.policy import REFERENCE_CHECKS, RULES


def test_gold_set_shape() -> None:
    gold = build_gold_set()
    assert len(gold) == len(CONTRACTS) * len(RULES) == 28
    gaps = [g for g in gold if g.expected is GapStatus.GAP]
    assert len(gaps) == 8
    critical_ids = {r.rule_id for r in RULES if r.severity is Severity.CRITICAL}
    critical_gaps = [g for g in gaps if g.rule_id in critical_ids]
    assert len(critical_gaps) == 2


def test_structured_reference_checks_match_contracts() -> None:
    from contractgap.contracts import get_contract

    c2 = get_contract("C-2")
    assert REFERENCE_CHECKS["LIAB-CAP"](c2) is GapStatus.GAP  # no cap
    assert REFERENCE_CHECKS["PAY-60"](c2) is GapStatus.GAP    # 90 > 60
    assert REFERENCE_CHECKS["LAW-FR"](c2) is GapStatus.GAP    # anglais
    assert REFERENCE_CHECKS["PAY-60"](get_contract("C-3")) is GapStatus.COMPLIANT  # 60
    assert REFERENCE_CHECKS["PAY-60"](get_contract("C-4")) is GapStatus.GAP        # missing


def test_lax_agent_misses_every_gap() -> None:
    rel = evaluate_reliability(LaxAgent(), build_gold_set())
    assert rel.true_gaps == 8
    assert rel.caught_gaps == 0
    assert rel.gap_recall == 0.0
    assert rel.critical_missed == 2


def test_oracle_agent_is_perfect_and_clean() -> None:
    gold = build_gold_set()
    rel = evaluate_reliability(OracleAgent(gold), gold)
    assert rel.gap_recall == 1.0
    assert rel.missed_gaps == 0
    assert rel.false_alarms == 0
    assert rel.hallucinated_citations == 0


def test_hallucinator_citations_are_caught() -> None:
    rel = evaluate_reliability(HallucinatorAgent(), build_gold_set())
    # Every verdict cites a clause that is not in the contract.
    assert rel.hallucinated_citations == 28


def test_heuristic_baseline_misses_only_the_ip_disclaimer() -> None:
    # The keyword baseline is honest but blind to the C-4 IP clause that names
    # the right words while granting nothing -> exactly one missed gap, a major.
    rel = evaluate_reliability(HeuristicAgent(), build_gold_set())
    assert rel.true_gaps == 8
    assert rel.caught_gaps == 7
    assert rel.missed_gaps == 1
    assert rel.critical_missed == 0
    assert rel.false_alarms == 0
    assert rel.hallucinated_citations == 0
    assert rel.recall_by_severity[Severity.CRITICAL] == (2, 2)
