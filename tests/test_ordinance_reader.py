"""The checks that stand between a model's proposal and a rule. No network."""

from turno.ordinance_reader import check_field

SRC = ("Si dispone, fino al 31 agosto 2026, il divieto tra le ore 12:30 e le ore 16:00, "
       "a decorrere dalla data di pubblicazione della presente ordinanza.")


def test_a_true_quote_with_the_value_is_accepted():
    c = check_field("valid_to", {"value": "2026-08-31", "quote": "fino al 31 agosto 2026"}, SRC)
    assert c.accepted


def test_a_date_the_text_never_states_is_refused():
    """The real Liguria case: the model wrote the signing date, the text says 'from publication'."""
    c = check_field("valid_from", {"value": "2026-05-28",
                                   "quote": "a decorrere dalla data di pubblicazione della presente ordinanza"}, SRC)
    assert not c.accepted and "date" in c.reason


def test_an_invented_quote_is_refused():
    c = check_field("valid_to", {"value": "2026-09-30", "quote": "fino al 30 settembre 2026"}, SRC)
    assert not c.accepted and "not in the document" in c.reason


def test_a_wrong_time_inside_a_true_quote_is_refused():
    c = check_field("ban_end", {"value": "17:00", "quote": "tra le ore 12:30 e le ore 16:00"}, SRC)
    assert not c.accepted


def test_quotes_survive_line_breaks_and_curly_quotes():
    src = 'livello di rischio “ALTO”,\nnei cantieri'
    c = check_field("trigger", {"value": "high risk", "quote": 'livello di rischio "ALTO", nei cantieri'}, src)
    assert c.accepted


def test_missing_value_goes_to_a_person():
    assert not check_field("exemptions", {"value": None, "quote": None}, SRC).accepted
