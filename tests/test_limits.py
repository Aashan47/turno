"""NIOSH limits and the work-minutes rule."""

import pytest

from turno.limits import (
    WORKLOADS,
    minutes_band,
    rel_c,
    snap_down,
    work_minutes_exact,
)


def test_rel_matches_niosh_table_5_1_for_heavy_work():
    """Table 5-1 gives 26 C for heavy work, 350-465 W, acclimatized. The equation
    across that band should bracket it closely: a cheap cross-check of the
    implementation against the same document."""
    lo, hi = rel_c(465.0), rel_c(350.0)
    assert lo - 0.5 <= 26.0 <= hi + 0.5, (lo, hi)


def test_rel_matches_niosh_table_5_1_for_very_heavy_work():
    lo, hi = rel_c(580.0), rel_c(466.0)
    assert lo - 0.5 <= 25.0 <= hi + 0.5, (lo, hi)


def test_cool_hour_allows_full_work():
    assert minutes_band(20.0, "heavy", acclimatized=True).fewest == 60


def test_extreme_hour_allows_no_work():
    assert minutes_band(34.0, "heavy", acclimatized=True).most == 0


def test_minutes_never_increase_with_heat():
    prev = 60
    for w in [x / 2 for x in range(40, 72)]:
        m = minutes_band(w, "heavy", acclimatized=True).fewest
        assert m <= prev
        prev = m


def test_unacclimatized_workers_get_no_more_minutes_than_acclimatized():
    for w in [24.0, 26.0, 28.0, 30.0]:
        a = minutes_band(w, "heavy", acclimatized=True).fewest
        u = minutes_band(w, "heavy", acclimatized=False).fewest
        assert u <= a


@pytest.mark.parametrize("raw,step", [(59.9, 45), (45.0, 45), (44.9, 30), (14.0, 0), (60.0, 60)])
def test_snap_rounds_down_never_up(raw, step):
    assert snap_down(raw) == step


def test_band_is_undetermined_somewhere_in_the_transition():
    """Somewhere between full work and none, the workload range must straddle a
    step, otherwise the band would be hiding real uncertainty."""
    assert any(
        not minutes_band(w / 10, "heavy", True).determined for w in range(240, 320)
    )


def test_exact_minutes_are_bounded():
    for key in WORKLOADS:
        for w in range(15, 40):
            m = work_minutes_exact(float(w), WORKLOADS[key].m_high_w, True)
            assert 0.0 <= m <= 60.0
