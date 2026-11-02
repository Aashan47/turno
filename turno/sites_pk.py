"""Evaluation sites in Pakistan, fixed in results/pk/PREREGISTRATION-PK.md.

Large centres of outdoor work in Sindh and Punjab, plus Jacobabad as a known
extreme-heat place. Coordinates are town centres to two decimals; each site is
read from the nearest mostly-land 0.25 degree cell, as in Italy.
"""

from __future__ import annotations

from .sites import Site

SITES = (
    Site("karachi", "Karachi", "Sindh", 24.86, 67.01, "delivery, construction, port",
         "largest city; coastal, a hard case for a 25 km grid"),
    Site("hyderabad", "Hyderabad", "Sindh", 25.40, 68.37, "construction",
         "second city of Sindh"),
    Site("jacobabad", "Jacobabad", "Sindh", 28.28, 68.44, "agriculture",
         "known extreme-heat place, a hard case"),
    Site("multan", "Multan", "Punjab", 30.20, 71.47, "agriculture, construction",
         "southern Punjab"),
    Site("lahore", "Lahore", "Punjab", 31.55, 74.34, "construction, delivery",
         "second-largest city"),
)

BY_KEY = {s.key: s for s in SITES}
