"""WBGT from reanalysis or forecast fields, by the Liljegren method.

Ported from heatline (github.com/Aashan47/heatline, MIT, same author), which
computed it from Open-Meteo point forecasts. Turno takes ERA5-style fields
instead: 2 m temperature and dewpoint, surface pressure, 10 m wind components and
hourly-mean downward shortwave. The Liljegren solver itself is ECMWF's
implementation in thermofeel (Apache-2.0), not ours.

NIOSH 2016-106 defines outdoor WBGT as 0.7 tnwb + 0.2 tg + 0.1 ta. A forecast
has no wet bulb or globe instrument, so Liljegren et al. (2008) solve both energy
balances from standard variables. Every value here is a modelled WBGT, never a
measured one, and the output says so.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import thermofeel as tf

KELVIN = 273.15


@dataclass(frozen=True)
class WbgtInputs:
    """One time step of fields, any shape, all arrays broadcastable together."""

    t2_k: np.ndarray
    d2_k: np.ndarray
    sp_pa: np.ndarray
    u10_ms: np.ndarray
    v10_ms: np.ndarray
    ssrd_wm2: np.ndarray
    cossza: np.ndarray
    fdir: np.ndarray


def relative_humidity_pct(t2_k, d2_k) -> np.ndarray:
    """From temperature and dewpoint, capped at 100 so supersaturated cells do
    not feed the solver a humidity it was not built for."""
    return np.minimum(tf.calculate_relative_humidity_percent(np.asarray(t2_k), np.asarray(d2_k)), 100.0)


def wind_speed_ms(u10, v10) -> np.ndarray:
    return np.hypot(np.asarray(u10, dtype=float), np.asarray(v10, dtype=float))


def wbgt_c(x: WbgtInputs) -> np.ndarray:
    """Liljegren WBGT in degrees Celsius."""
    out_k = tf.calculate_wbgt_liljegren(
        t2_k=np.asarray(x.t2_k, dtype=float),
        rh=relative_humidity_pct(x.t2_k, x.d2_k),
        pressure=np.asarray(x.sp_pa, dtype=float) / 100.0,
        va=wind_speed_ms(x.u10_ms, x.v10_ms),
        ssrd=np.asarray(x.ssrd_wm2, dtype=float),
        fdir=np.asarray(x.fdir, dtype=float),
        cossza=np.asarray(x.cossza, dtype=float),
    )
    return np.asarray(out_k, dtype=float) - KELVIN
