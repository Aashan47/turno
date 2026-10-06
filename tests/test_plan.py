"""The hour plan: three outcomes, deterministic, cautious when unsure."""

import pytest

from turno.plan import Outcome, plan_hour


def test_cool_agreeing_members_give_full_work():
    p = plan_hour("09:00", [20.1, 20.4, 19.8], "heavy", True)
    assert p.outcome is Outcome.WORK and p.minutes == 60 and not p.needs_supervisor


def test_an_ordinance_wins_over_any_forecast():
    p = plan_hour("13:00", [18.0, 18.0], "heavy", True, banned_minutes=60, ban_reason="Lazio ordinance")
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


def test_a_half_hour_ban_caps_the_twelve_oclock_hour_at_thirty_minutes():
    p = plan_hour("12:00", [20.0, 20.0], "heavy", True, banned_minutes=30, ban_reason="Lazio ordinance")
    assert p.outcome is Outcome.WORK and p.minutes == 30


def test_an_unconfirmed_ban_is_handed_over_with_the_ban_assumed():
    p = plan_hour("14:00", [20.0, 20.0], "heavy", True, banned_minutes=60,
                  ban_reason="Confirm today's Worklimate rating", ban_uncertain=True)
    assert p.outcome is Outcome.UNDETERMINED and p.needs_supervisor and p.minutes == 0


def test_workload_range_alone_is_planned_cautiously_not_handed_over():
    """Find a WBGT where the two ends of heavy work land on different steps; one
    forecast member there must plan the hard end and keep the hour, with a note."""
    from turno.limits import minutes_band

    w = next(x / 10 for x in range(240, 320) if not minutes_band(x / 10, "heavy", True).determined)
    p = plan_hour("11:00", [w], "heavy", True)
    assert p.outcome is Outcome.WORK and not p.needs_supervisor
    assert p.minutes == minutes_band(w, "heavy", True).fewest
    assert any("hard end" in r for r in p.reasons)
