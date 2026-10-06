"""The decision settings Turno ships, fixed in one place.

Chosen on the June development dates by the rule in scripts/sweep_rules.py and
recorded as Amendment 2 of results/PREREGISTRATION.md, before any Aurora output
and before the July and August test dates were scored with them
(results/rule_sweep_june.md):

- follow the hottest of the members (quantile 1.0), which gave the fewest missed
  heat-restricted times;
- hand an hour to the supervisor when members are 2 or more work steps
  (30 minutes) apart, which kept hand-offs at 14% of working hours.

The hottest member depends on how many members there are, so every ensemble arm,
ECMWF ENS and Aurora alike, is scored with the same number of members.
"""

PLAN_QUANTILE = 1.0
HANDOVER_STEPS = 2
ENSEMBLE_MEMBERS = 10
