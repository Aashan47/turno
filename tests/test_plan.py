"""The hour plan: three outcomes, deterministic, cautious when unsure."""

import pytest

from turno.plan import Outcome, plan_hour


def test_cool_agreeing_members_give_full_work():
    p = plan_hour("09:00", [20.1, 20.4, 19.8], "heavy", True)
    assert p.outcome is Outcome.WORK and p.minutes == 60 and not p.needs_supervisor


def test_an_ordinance_wins_over_any_forecast():
    p = plan_hour("13:00", [18.0, 18.0], "heavy", True, banned_by="Lazio ordinance")
    assert p.outcome is Outcome.BANNED and p.minutes == 0
    assert "Lazio ordinance" in p.reasons[0]


def test_disagreeing_members_go_to_the_supervisor_with_the_cautious_value():
    p = plan_hour("15:00", [24.0, 29.5], "heavy", True)
    assert p.outcome is Outcome.UNDETERMINED
    assert p.needs_supervisor
    assert p.minutes == p.minutes_range[0] < p.minutes_range[1]
    assert any("disagree" in r for r in p.reasons)


def test_plan_is_deterministic():
    a = plan_hour("14:00", [26.3, 27.1, 26.8], "heavy", True).as_dict()
    b = plan_hour("14:00", [26.3, 27.1, 26.8], "heavy", True).as_dict()
    assert a == b


def test_nan_member_is_refused_not_silently_dropped():
    with pytest.raises(ValueError):
        plan_hour("14:00", [26.0, float("nan")], "heavy", True)
