"""The scorer must count the error that hurts someone, and count it the same way for every arm."""

import numpy as np
import pytest

from turno.evaluate import decision_score, wbgt_score


def test_wbgt_score_of_a_perfect_forecast_is_zero():
    s = wbgt_score([25.0, 27.0], [25.0, 27.0])
    assert s.mae_c == 0.0 and s.bias_c == 0.0 and s.n == 2


def test_wbgt_score_sign_of_bias():
    assert wbgt_score([26.0], [25.0]).bias_c == pytest.approx(1.0)


def test_wbgt_score_refuses_empty():
    with pytest.raises(ValueError):
        wbgt_score([np.nan], [25.0])


def test_a_forecast_too_cool_on_a_hot_hour_is_a_miss():
    s = decision_score([[20.0]], [31.0], "heavy", True)
    assert s.restricted_truth == 1 and s.missed == 1 and s.caught == 0


def test_a_forecast_too_hot_on_a_cool_hour_is_a_false_restriction_not_a_miss():
    s = decision_score([[31.0]], [20.0], "heavy", True)
    assert s.missed == 0 and s.false_restrictions == 1


def test_disagreeing_members_are_counted_as_handed_over():
    s = decision_score([[22.0, 30.0]], [25.0], "heavy", True)
    assert s.handed_to_supervisor == 1


def test_non_finite_hours_are_skipped_not_scored():
    s = decision_score([[np.nan], [20.0]], [25.0, 20.0], "heavy", True)
    assert s.hours == 1
