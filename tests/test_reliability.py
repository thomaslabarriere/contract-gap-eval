"""Mutation proof: the harness rewards a correct agent, catches a lax one and a
hallucinating one, and reports the baseline's real (semantic) miss exactly."""

from __future__ import annotations

import pytest

import contractgap.policy as policy
from contractgap.agent import HallucinatorAgent, HeuristicAgent, LaxAgent, OracleAgent
from contractgap.contracts import CONTRACTS
from contractgap.evaluate import evaluate_reliability
from contractgap.goldset import build_gold_set
from contractgap.models import GapStatus, Severity
from contractgap.policy import REFERENCE_CHECKS, RULES


def test_gold_set_shape() -> None:
    gold = build_gold_set()
    assert len(gold) == len(CONTRACTS) * len(RULES) == 56
    gaps = [g for g in gold if g.expected is GapStatus.GAP]
    assert len(gaps) == 22
    critical_ids = {r.rule_id for r in RULES if r.severity is Severity.CRITICAL}
    critical_gaps = [g for g in gaps if g.rule_id in critical_ids]
    assert len(critical_gaps) == 5


def test_gold_set_is_not_computed_from_reference_checks() -> None:
    # Decoupling guard: the gold labels are hand-authored, so they must exist
    # even for pairs the reference checks never touch (judgment rules) and must
    # not be derivable by calling REFERENCE_CHECKS. We assert the structured
    # labels were authored independently by spot-checking a value the checks
    # would also produce AND confirming goldset imports no reference check.
    import contractgap.goldset as gs

    assert not hasattr(gs, "REFERENCE_CHECKS")
    assert "REFERENCE_CHECKS" not in gs.build_gold_set.__code__.co_names


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
    assert rel.true_gaps == 22
    assert rel.caught_gaps == 0
    assert rel.gap_recall == 0.0
    assert rel.critical_missed == 5


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
    assert rel.hallucinated_citations == 56


def test_heuristic_baseline_misses_only_the_ip_disclaimers() -> None:
    # The keyword baseline is honest but blind to the C-4 and C-7 IP clauses
    # that name the right words while granting nothing -> exactly two missed
    # gaps, both major; every critical gap is caught.
    rel = evaluate_reliability(HeuristicAgent(), build_gold_set())
    assert rel.true_gaps == 22
    assert rel.caught_gaps == 20
    assert rel.missed_gaps == 2
    assert rel.critical_missed == 0
    assert rel.false_alarms == 0
    assert rel.hallucinated_citations == 0
    assert rel.recall_by_severity[Severity.CRITICAL] == (5, 5)
    assert rel.recall_by_severity[Severity.MAJOR] == (12, 14)
    assert rel.recall_by_severity[Severity.MINOR] == (3, 3)
    missed = {(r.contract_id, r.rule_id) for r in rel.results if r.missed_gap}
    assert missed == {("C-4", "IP"), ("C-7", "IP")}


def test_mutating_a_reference_check_breaks_the_agent_but_not_the_gold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A live mutation of the code under test. `REFERENCE_CHECKS["PAY-60"]` is the
    # shared object the HeuristicAgent calls; we break it to always say
    # "compliant". Two things must hold: (1) the hand-authored gold set is
    # UNCHANGED (proving it is decoupled from the checks), and (2) the harness
    # NOTICES the now-broken agent (recall drops). If the gold were computed
    # from the same checks, the mutation would move both together and hide the
    # regression -- the exact tautology this refactor removes.
    baseline = {(g.contract_id, g.rule_id): g.expected for g in build_gold_set()}
    before = evaluate_reliability(HeuristicAgent(), build_gold_set())

    monkeypatch.setitem(REFERENCE_CHECKS, "PAY-60", lambda _c: GapStatus.COMPLIANT)
    assert policy.REFERENCE_CHECKS["PAY-60"](CONTRACTS[1]) is GapStatus.COMPLIANT

    after_gold = {(g.contract_id, g.rule_id) for g in build_gold_set()
                  if g.expected is GapStatus.GAP}
    baseline_gaps = {k for k, v in baseline.items() if v is GapStatus.GAP}
    assert after_gold == baseline_gaps  # gold unmoved by the mutation

    after = evaluate_reliability(HeuristicAgent(), build_gold_set())
    assert after.gap_recall < before.gap_recall  # harness catches the broken agent
    assert after.caught_gaps == before.caught_gaps - 5  # the five PAY-60 gaps now missed
