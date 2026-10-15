# Turno

**Heat-safe shift planning for outdoor crews.** Live: **https://turno.aashanjaved.com**

Every summer, Italian regions legally ban manual outdoor work from 12:30 to 16:00 on days the national
Worklimate service rates heat risk "ALTO". A site supervisor still has to decide, hour by hour, how long
each crew can work outside that window, prove the ban was respected, and tell the crew in a language they
read. Turno does that: it forecasts heat stress for the site, fixed rules decide the minutes of work per
hour, the ordinance in force is applied from its own text, and when the forecast cannot support a
decision the hour goes to the supervisor with the reason.

AMD Developer Hackathon: ACT III (lablab.ai, 12 to 18 October 2026). Tracks: **Health and Wellbeing**
(occupational heat-illness prevention) and **Intelligent Industry** (monitoring safety conditions).

## What runs on AMD, and what it does

| Part | Runs on | What it does | Evidence |
|---|---|---|---|
| **Ordinance reader** | AMD Token Factory (AMD Radeon Cloud): **MinerU2.5-Pro** reads the region's signed PDF; **DeepSeek-V4-Flash** proposes each rule field with a verbatim quote | Keeps the rules current: 16 regions issue and amend these orders every summer (Lazio three times in 2026). Code accepts a field only if its quote is in the document and contains the value | `results/ordinance_reader.md` |
| **Hand-off explanation** | AMD Token Factory, DeepSeek-V4-Flash | Explains in Italian and English why an hour needs the supervisor and what to check on site | live in the app; `results/amd_calls.jsonl` |

Every call to AMD is logged with model, latency, tokens and cost in `results/amd_calls.jsonl`.

**Gemma 4** (`gemma-4-31b-it`) writes the crew briefing, through Google's Gemini API, so it runs on
Google's servers. It is behind one setting (`GEMMA_BACKEND=vllm`, `GEMMA_BASE_URL`) and moves to
a Gemma endpoint on an AMD GPU unchanged.

**What we could not run on AMD.** The plan was to run the Aurora 1.5 weather foundation model on an AMD
Instinct MI300X. The event provides AMD's Token Factory model API, not GPU instances, and no GPU was
available to us, so the forecast is ECMWF's open-data ensemble. The decision layer is unchanged, and the
evaluation below is on that ensemble.

## No model decides anything

| Step | Done by | Checked by |
|---|---|---|
| Heat stress (WBGT) per forecast member, per hour | Liljegren method, ECMWF thermofeel | Tests; solar inputs measured against ERA5 |
| Minutes of work per hour | NIOSH 2016-106 limits as 1-hour averages, planned for the hard end of the workload | Tests; the equation matches NIOSH Table 5-1 to 0.1 C |
| Whether today is an "ALTO" day | **The supervisor**, from worklimate.it | Until confirmed, the ban is assumed |
| Which ordinance applies | Rules built from 15 regions' primary texts | Verbatim text and URL per region in `data/ordinances_2026.json` |
| The words in the briefing and explanations | Gemma 4, DeepSeek on AMD | Every number must be in the plan; hour labels are fixed by the rules; on failure a template is used |

## Results

All comparison dates and predictions were written down and committed **before** the test set was scored
(`results/PREREGISTRATION.md`, with two dated amendments made before any test result, each with its reason).
Settings were chosen on the four June dates only; July and August are the untouched test set.

**Test set: 10 forecast dates, July and August 2026, 5 sites, working hours (07:00 to 19:00), heavy work,
unacclimatized limit.** A "miss" is an hour planned as more work than what actually happened (ERA5) allowed.

| Lead (days) | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Single ECMWF forecast: missed heat-restricted hours | 6.6% | 7.2% | 12.2% | 20.4% | 14.5% |
| **Turno (ECMWF ensemble + rules): missed** | **1.1%** | **0.6%** | **3.9%** | **4.4%** | **3.9%** |
| Turno: hours handed to the supervisor | 3.0% | 8.5% | 14.5% | 17.0% | 16.5% |
| Turno: over-planned minutes per hour (single forecast) | 0.15 (0.90) | 0.15 (1.12) | 0.53 (1.73) | 0.68 (2.85) | 0.53 (2.33) |
| Turno: safe minutes withheld per hour (single forecast) | 2.85 (1.95) | 4.28 (1.95) | 4.88 (2.10) | 4.12 (2.17) | 4.58 (2.25) |

Full table: `results/grid_summary.md`. At lead 1 the ensemble cuts over-planned work six-fold for 0.9 more
minutes of safe work withheld per hour.

**What the law alone leaves exposed** (`results/value.md`, ERA5, every working hour of June to August 2026 at
the 5 sites): **59 to 66% of heat-restricted working hours fall outside the 12:30 to 16:00 ban window**, even
counting the ban as if it applied every day (heavy work, not acclimatized: 3,444 of 5,239 hours). Those are the
hours Turno plans and the ordinance does not touch. Each replayed day in the app shows the same count.

**Ordinance reader on AMD** (`results/ordinance_reader.md`; run 1 kept as `ordinance_reader_run1.md`). On the 10
regions whose rule is one document, scored against the verified records:

| Field | Run 1: accepted, all correct | Run 2 (one re-ask when quotes are missing): accepted, all correct | Accepted and wrong, either run |
|---|---|---|---|
| End of the ban season | 7 of 10 | 8 of 10 | **0** |
| Daily ban start | 8 of 10 | 9 of 10 | **0** |
| Daily ban end | 8 of 10 | 9 of 10 | **0** |

Every field not accepted went to a person with the reason. All 5 regions with amended rules were flagged as
amending; 4 of 10 single orders were wrongly flagged too. A live re-read on the deployed app (Puglia, 15 October)
took 44.9 s for MinerU OCR and 34.7 s for extraction on AMD Token Factory, and verified 6 of 7 fields.

**Solar inputs** (`results/solar-validation.md`): top-of-atmosphere sunlight within 0.6% of ERA5; the
direct-diffuse split costs 0.15 to 0.20 C of WBGT on average, 1.06 C at worst.

## Limitations, plainly

- **Truth is ERA5**, a 0.25 degree reanalysis, not a thermometer on the site. Every arm is read at the same
  grid cell at its mean height; a coastal town at 50 m in a cell averaging 544 m (Imperia) is a different place.
- **The ensemble is too confident early in the day.** On 30 July in Rome all 10 members ran cooler than what
  happened at 08:00 and 09:00, and the plan allowed 15 minutes more than reality would have in each hour. The
  app shows these hours as "plan too high".
- ECMWF open data is 3-hourly; the app interpolates linearly to each hour. The evaluation uses 3-hourly times.
- The number check proves every number came from the plan, not that each sentence is right. Hour labels are
  fixed by code for that reason, and two live failures (an invented "31 C threshold", heat stops called
  "banned") are recorded in the commit history with their fixes.
- Model outputs vary between runs even at temperature 0; the reader's two benchmark runs are both reported.
- NIOSH limits are a US standard; Worklimate itself uses the same NIOSH alert-limit formula.
- Not yet tried with a real crew. Not a substitute for the employer's risk assessment.

## Run it

```
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -e . pytest
.venv/bin/python -m pytest -q                      # 64 tests, no network
.venv/bin/python -m uvicorn web.app:app --port 8765 # the app on http://localhost:8765
```

Keys, from the environment or a `.env` file above the repo: `TOKEN_FACTORY_KEY` (AMD Token Factory) for the
reader and explanations, `GEMENI_KEY` (Gemini API) for the briefing. Without them the app still runs and
falls back to templates. To rebuild the data: `scripts/fetch_era5_italy.py`, `scripts/fetch_all_ecmwf.sh`,
`scripts/build_site_data.py`; to rerun the evaluation: `scripts/score_grid.py` then
`scripts/summarize_grid.py`, and `scripts/bench_ordinance_reader.py`.

## Built before and during the event

Before 12 October 2026: the WBGT and solar code, the NIOSH rules, the ordinance rules, the evaluation and
the ECMWF baselines, all without any model. From 12 October: everything that calls a model, the web app and
the deployment. The aim on 6 October was Aurora on an MI300X (see above).

## Sources and licences

NIOSH 2016-106; ECMWF thermofeel (Apache-2.0); Erbs, Klein and Duffie (1982); NOAA solar equations; ERA5 and
ECMWF open data (CC BY 4.0); regional ordinances and INAIL-CNR Worklimate, quoted with URLs. Details:
`SOURCES.md`. Code written with Claude Code. Licence: MIT.
