"""The evidence-relevance judge is itself calibrated (who judges the judge?)."""

from __future__ import annotations

from contractgap.goldset import GROUND_GOLD
from contractgap.judge import AlwaysRelevantJudge, StaticRelevanceJudge, calibrate_judge


def test_static_judge_is_well_calibrated() -> None:
    cal = calibrate_judge(StaticRelevanceJudge(), GROUND_GOLD)
    assert cal.false_positive == 0
    assert cal.agreement_rate == 1.0


def test_calibration_catches_a_rubber_stamp_judge() -> None:
    cal = calibrate_judge(AlwaysRelevantJudge(), GROUND_GOLD)
    assert cal.false_positive > 0
    assert cal.agreement_rate < 1.0
