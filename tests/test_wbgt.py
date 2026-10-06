"""WBGT: units, determinism and physical direction."""

import numpy as np

from turno.wbgt import WbgtInputs, relative_humidity_pct, wbgt_c


def _inputs(t_c=34.0, td_c=20.0, ssrd=850.0, cossza=0.85, fdir=0.8, wind=2.0):
    k = 273.15
    return WbgtInputs(
        t2_k=np.array([t_c + k]),
        d2_k=np.array([td_c + k]),
        sp_pa=np.array([101000.0]),
        u10_ms=np.array([wind]),
        v10_ms=np.array([0.0]),
        ssrd_wm2=np.array([ssrd]),
        cossza=np.array([cossza]),
        fdir=np.array([fdir]),
    )


def test_wbgt_is_deterministic():
    """The standing check on any component treated as fixed: same input twice,
    identical output."""
    assert wbgt_c(_inputs()).tolist() == wbgt_c(_inputs()).tolist()


def test_wbgt_is_plausible_and_in_celsius():
    v = float(wbgt_c(_inputs())[0])
    assert 20.0 < v < 40.0, v


def test_hotter_gives_higher_wbgt():
    assert wbgt_c(_inputs(t_c=38.0))[0] > wbgt_c(_inputs(t_c=30.0))[0]


def test_more_humid_gives_higher_wbgt():
    assert wbgt_c(_inputs(td_c=24.0))[0] > wbgt_c(_inputs(td_c=12.0))[0]


def test_sun_adds_heat():
    assert wbgt_c(_inputs(ssrd=900.0))[0] > wbgt_c(_inputs(ssrd=0.0, cossza=0.0, fdir=0.0))[0]


def test_relative_humidity_is_capped_at_100():
    assert relative_humidity_pct(np.array([300.0]), np.array([301.0]))[0] == 100.0
