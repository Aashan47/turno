"""Evaluation sites: real places in regions with heat ordinances.

Coordinates are town centres to two decimals. A 0.25 degree forecast cannot
resolve a single site, so each site is read from the nearest land grid cell and
the README says so. Regions are chosen because their ordinances are in force,
not because their weather flatters the model.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Site:
    key: str
    name: str
    region: str
    lat: float
    lon: float
    work: str
    why: str


SITES = (
    Site("roma", "Roma", "Lazio", 41.90, 12.50, "construction",
         "Rome on-site venue; Lazio ordinance"),
    Site("latina", "Borgo Piave, Latina", "Lazio", 41.47, 12.90, "agriculture",
         "Agro Pontino farm work; Lazio ordinance"),
    Site("imperia", "Imperia", "Liguria", 43.89, 8.03, "construction",
         "Imperia on-site venue; Liguria ordinance; coastal, a hard case for a 25 km grid"),
    Site("milano", "Milano", "Lombardia", 45.46, 9.19, "construction",
         "Milan on-site venue; Lombardia ordinance (primary text pending)"),
    Site("foggia", "Foggia", "Puglia", 41.46, 15.54, "agriculture",
         "Tavoliere harvest; Puglia ordinance"),
)

BY_KEY = {s.key: s for s in SITES}
