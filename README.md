# Turno

Heat-safe work planning for outdoor crews. A weather foundation model forecasts heat stress for each
site and hour; fixed rules, not the model, decide how many minutes of each hour a crew may work; and
when the forecast cannot support a decision, Turno says so and hands the hour to the site supervisor.

Built for the AMD Developer Hackathon: ACT III (lablab.ai, 12 to 18 October 2026), Health and
Wellbeing track.

## Status

Work in progress. Nothing below is a result until it appears in the evidence section with a dated log.

## What was built before the event, and what during it

The hackathon guide expects the core AI functionality to be built during the event. This repository
keeps the line visible:

- **Before 12 October 2026**, tagged `pre-act-iii`: the WBGT calculation (ported from the author's own
  [heatline](https://github.com/Aashan47/heatline), MIT), sun geometry and the direct-diffuse split,
  NIOSH work/rest limits, the hour-planning rules, ERA5 ground-truth download, the evaluation harness
  and non-AI baselines. None of it uses a model.
- **From 12 October 2026**: running Microsoft Aurora 1.5 Ensemble on an AMD Instinct MI300X, the
  hindcast and every reported number, the language layer, the product and the demo.

## How it decides

| Step | What | Source |
|---|---|---|
| WBGT | Liljegren method via ECMWF's thermofeel | Liljegren et al. 2008; thermofeel (Apache-2.0) |
| Direct sunlight share | Erbs, Klein and Duffie (1982) hourly correlation | Solar Energy 28(4):293-302 |
| Sun position | NOAA General Solar Position Calculations | gml.noaa.gov |
| Work minutes per hour | Largest of 60, 45, 30, 15, 0 that keeps the 1-hour TWA metabolic rate within the NIOSH REL (acclimatized) or RAL | NIOSH 2016-106 |
| Bans | Regional ordinances: no manual outdoor work 12:30 to 16:00 on Worklimate "Alto" days. The supervisor confirms the official rating; Turno never imitates it | each ordinance, linked in SOURCES.md |

## Run the tests

```
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e . pytest
.venv/bin/python -m pytest -q
```

## AI tools used

Code in this repository was written with the help of Claude Code. Every rule, constant and citation is
sourced in SOURCES.md.

## Licence

MIT. Weather data: ERA5 (Copernicus Climate Change Service, CC BY 4.0).
