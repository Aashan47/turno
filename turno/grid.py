"""Choosing which 0.25 degree grid cell stands for a site.

The nearest cell to a coastal town can be mostly sea, and a sea cell has a
cooler, damper climate than the land where the crew works. So a site is read
from the nearest cell whose ERA5 land fraction is at least one half. The same
cell is used for the truth and for Aurora, so neither gets a different place.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr

LAND_THRESHOLD = 0.5


def load_lsm(path: Path) -> xr.DataArray:
    ds = xr.open_dataset(path)
    lsm = ds["lsm"]
    if "valid_time" in lsm.dims:
        lsm = lsm.isel(valid_time=0)
    return lsm.load()


def nearest_land_cell(lsm: xr.DataArray, lat: float, lon: float) -> tuple[float, float, float]:
    """Latitude, longitude and land fraction of the nearest mostly-land cell."""
    lats = lsm.latitude.values
    lons = lsm.longitude.values
    glat, glon = np.meshgrid(lats, lons, indexing="ij")
    # Distance on the sphere is overkill at this scale; scale longitude by cos(lat).
    d2 = (glat - lat) ** 2 + ((glon - lon) * np.cos(np.radians(lat))) ** 2
    d2 = np.where(lsm.values >= LAND_THRESHOLD, d2, np.inf)
    i, j = np.unravel_index(np.argmin(d2), d2.shape)
    if not np.isfinite(d2[i, j]):
        raise ValueError("no land cell in the grid")
    return float(lats[i]), float(lons[j]), float(lsm.values[i, j])
