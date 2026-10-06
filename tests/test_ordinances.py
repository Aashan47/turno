"""The ordinance rules: decide only from verified text, never guess the Worklimate rating."""

from datetime import date, time

import pytest

from turno.ordinances import BanStatus, ban_for_hour, load, minutes_in_window

ORD = load()


def test_twelve_thirty_ban_covers_half_of_the_twelve_oclock_hour():
    assert minutes_in_window(12, time(12, 30), time(16, 0)) == 30
    assert minutes_in_window(13, time(12, 30), time(16, 0)) == 60
    assert minutes_in_window(16, time(12, 30), time(16, 0)) == 0


def test_lazio_alto_day_bans_fifteen_hundred():
    r = ban_for_hour(ORD, "Lazio", date(2026, 7, 30), 15, worklimate_alto=True, sector_confirmed=True)
    assert r.status is BanStatus.APPLIES and r.banned_minutes == 60


def test_unconfirmed_rating_is_never_guessed():
    r = ban_for_hour(ORD, "Lazio", date(2026, 7, 30), 14, worklimate_alto=None, sector_confirmed=True)
    assert r.status is BanStatus.CANNOT_DETERMINE and "worklimate.it" in r.reason


def test_no_ban_outside_validity():
    r = ban_for_hour(ORD, "Liguria", date(2026, 9, 10), 14, worklimate_alto=True, sector_confirmed=True)
    assert r.status is BanStatus.DOES_NOT_APPLY


def test_sardegna_gap_first_week_of_september():
    gap = ban_for_hour(ORD, "Sardegna", date(2026, 9, 3), 14, True, True)
    after = ban_for_hour(ORD, "Sardegna", date(2026, 9, 8), 14, True, True)
    assert gap.status is BanStatus.DOES_NOT_APPLY and after.status is BanStatus.APPLIES


def test_press_only_region_is_not_decided():
    r = ban_for_hour(ORD, "Basilicata", date(2026, 7, 30), 14, True, True)
    assert r.status is BanStatus.CANNOT_DETERMINE


def test_morning_hours_are_never_banned():
    for region in ORD:
        assert ban_for_hour(ORD, region, date(2026, 7, 30), 9, True, True).status is BanStatus.DOES_NOT_APPLY


@pytest.mark.parametrize("region", ["Lazio", "Liguria", "Lombardia"])
def test_venue_regions_are_verified_from_primary_text(region):
    assert any(o.decidable for o in ORD[region])


def test_an_undetermined_ban_carries_the_minutes_it_would_cover():
    """So a caller assuming the ban, the cautious reading, never plans full work."""
    r = ban_for_hour(ORD, "Lazio", date(2026, 7, 30), 12, worklimate_alto=None, sector_confirmed=True)
    assert r.status is BanStatus.CANNOT_DETERMINE and r.banned_minutes == 30
