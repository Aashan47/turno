"""The briefing check: numbers from the plan pass, invented ones do not. No network."""

from turno.briefing import check

PLAN = {"date": "2026-07-30", "ban_window": [],
        "hours": [{"hour": "14:00", "work_minutes": 0, "work_minutes_range": [0, 15],
                   "wbgt_c": {"min": 32.8, "median": 34.0, "max": 34.8, "members": 10},
                   "reasons": ["Lazio ordinance Z00001 bans 12:30 to 16:00 on Worklimate ALTO days."]}]}


def test_numbers_from_the_reasons_are_allowed():
    t = "ITALIANO\nAlle 14:00 vale l'ordinanza Z00001, divieto 12:30-16:00; 10 previsioni.\nENGLISH\nAt 14:00 the ban runs 12:30 to 16:00."
    assert check(t, PLAN) == []


def test_an_invented_number_is_caught():
    t = "ITALIANO\nAlle 14:00 lavorate 50 minuti.\nENGLISH\nAt 14:00 work 50 minutes."
    assert any("50" in p for p in check(t, PLAN))


def test_a_missing_language_section_is_caught():
    assert any("Italian or English" in p for p in check("At 14:00 stop.", PLAN))


def test_a_rounded_temperature_threshold_is_caught():
    """The real failure: a model wrote 'above the 31 C threshold for the ban' from a member at 31.2."""
    plan = dict(PLAN, hours=[dict(PLAN["hours"][0], wbgt_c={"min": 31.2, "median": 32.2, "max": 32.8, "members": 10})])
    t = "ITALIANO\nSupera la soglia di 31 C.\nENGLISH\nAbove the 31 C threshold."
    assert any("31" in p for p in check(t, plan))
