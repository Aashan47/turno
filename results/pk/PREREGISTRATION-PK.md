# Pre-registration: the same planner, tested on Pakistan

Written 2 November 2026, before any Pakistan forecast or ERA5 field has been downloaded, opened or scored.
Committed to git on its own, before the code that runs it, so the order is checkable. Every arm below is
reported whatever it shows, including results that contradict these predictions.

## Why

Turno was built and tested for Italy (`results/PREREGISTRATION.md`, `results/grid_summary.md`). The same
decision layer is now proposed for outdoor workers in Pakistan. Italy's result says nothing about Pakistan:
the heat is more extreme, much of it is humid (Karachi, the Indus plain in the monsoon), and ERA5 and ECMWF
may behave differently there. This run asks whether the Italian result holds.

## What is frozen, taken unchanged from Italy

- The rules: `turno/rules.py`, `PLAN_QUANTILE = 1.0` (plan on the hottest member), `HANDOVER_STEPS = 2`
  (hand the hour to a person when members are two 15-minute work steps apart). Chosen on Italian June data
  (Amendment 2 of the Italy pre-registration). **No setting is tuned on Pakistan data.** All Pakistan dates
  are test dates.
- WBGT by Liljegren (`turno/wbgt.py`), NIOSH 2016-106 limits (`turno/limits.py`), the plan (`turno/plan.py`)
  and the scoring (`turno/evaluate.py`, `scripts/score_grid.py`): unchanged code paths.
- Truth: ERA5 reanalysis (Copernicus Climate Data Store, CC BY 4.0), WBGT computed with ERA5's own direct
  fraction; forecast arms use the Erbs split, exactly as in Italy.
- Members: 10 perturbed ENS members, as in Italy.

## Arms

| Arm | What it is |
|---|---|
| ECMWF IFS (`oper`) | ECMWF open data, deterministic, 0.25 degrees: the single-forecast baseline |
| ECMWF ENS (`enfo`) | ECMWF open data, the first 10 perturbed members, with Turno's frozen rules |

## Sites, fixed now

Read from the nearest ERA5 cell with land fraction at least one half (`turno/grid.py`). Chosen as large
centres of outdoor work in Sindh and Punjab; Jacobabad is included as a known extreme-heat place, a hard case.
None was chosen from any 2026 forecast or ERA5 value, none of which has been seen.

| Key | Place | Lat | Lon | Outdoor work |
|---|---|---|---|---|
| karachi | Karachi | 24.86 | 67.01 | delivery, construction, port; coastal, a hard case for a 25 km grid |
| hyderabad | Hyderabad | 25.40 | 68.37 | construction |
| jacobabad | Jacobabad | 28.28 | 68.44 | agriculture |
| multan | Multan | 30.20 | 71.47 | agriculture, construction |
| lahore | Lahore | 31.55 | 74.34 | construction, delivery |

## Initialisation dates, fixed now

00 UTC on every seventh day from 6 May 2026: **6, 13, 20, 27 May; 3, 10, 17, 24 June; 1, 8, 15, 22, 29 July;
5, 12, 19, 26 August** (17 dates), chosen by calendar. Leads 1 to 5 days. If a date cannot be downloaded after
the fetch script's retries, it is dropped and named in the results; dates are never selected by result.

## Working hours

07:00 to 19:00 Pakistan time (UTC+5). The 3-hourly valid times inside it are 03, 06, 09 and 12 UTC, which are
08:00, 11:00, 14:00 and 17:00 local, the same local times as the Italy test. Every decision metric is over
these times only.

## Primary measure

Workload **heavy** (NIOSH Table 5-1, 350 to 465 W, planned at the hard end), **unacclimatized limit (RAL)**,
pooled over the 5 sites and 17 dates. A heat-restricted time is one where the truth allows under 60 work
minutes. A **miss** is a heat-restricted time the arm planned as more work than the truth allowed. The
**hand-off rate** is the share of working times the plan sends to the supervisor.

Also reported, with no prediction: the acclimatized limit (REL), the **moderate** workload (234 to 349 W, the
closest NIOSH class to motorcycle delivery), WBGT error (MAE, bias) by lead, minutes over and under the truth,
per-site results, and the share of working times that were heat-restricted in ERA5.

## Predictions

1. **The ensemble with the frozen rules protects workers better than the single forecast.** At each of leads
   1, 2 and 3 days, ENS's miss rate is at least 30% lower, relative, than IFS's.
2. **The price stays usable.** ENS's hand-off rate is under 25% of working times at each of leads 1, 2 and 3.

## What would count against using it in Pakistan

- Prediction 1 fails at any of leads 1 to 3: the Italian result does not transfer, and any application text
  says so.
- Prediction 2 fails: the supervisor is asked too often for the plan to be used as it stands.
- Karachi's cell behaves differently from the inland sites (reported per site either way).

## Known limits, stated now

- ERA5 is a 0.25 degree reanalysis, not a thermometer on a street or a field. Karachi's nearest land cell
  averages coast and city. Its humidity over South Asia has not been checked against stations here.
- ECMWF open data is 3-hourly; scoring uses 3-hourly times.
- This tests forecasts and rules against a reanalysis. It says nothing about whether workers or employers
  will use the plan, or whether it reduces heat illness.
