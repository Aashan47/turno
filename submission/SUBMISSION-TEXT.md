# Turno: paste-ready copy for the lablab.ai submission form

AMD Developer Hackathon: ACT III. Closes 18 October 2026. Every number below is taken from the repository's `README.md` or `results/` files; the source is named in brackets where it is not obvious.

## Project title

Turno

## Short description (under 200 characters)

Heat-safe shift planning for outdoor crews: an ensemble forecast and fixed NIOSH rules set the minutes of work per hour; models on AMD read the regional heat ordinance and explain hand-offs.

(190 characters)

## Long description

Every summer, Italian regions ban manual outdoor work from 12:30 to 16:00 on days the national Worklimate service rates heat risk ALTO. The ban is the easy part. A site supervisor still has to decide, hour by hour, how long a crew can work outside that window, prove the ban was respected, and tell the crew in a language they read. Measured on ERA5 for June to August 2026 at five Italian sites, 59 to 66% of heat-restricted working hours (07:00 to 19:00) fall outside the ban window, even counting the ban as if it applied every day. Those are the hours Turno plans.

Turno takes ECMWF's open-data ensemble (10 members) at the site's grid cell, computes WBGT heat stress for every member and hour with the Liljegren method (ECMWF thermofeel), and applies the NIOSH 2016-106 limits as fixed rules: 60, 45, 30, 15 or 0 minutes of work per hour, planned on the hottest member and for the hard end of the workload. When members are 30 minutes of work apart, the hour goes to the supervisor with the reason. The supervisor confirms the Worklimate rating; until confirmed, the ban is assumed. The result is one strip per day: column height is minutes of work, colour is heat, hatched hours are banned, dashed hours are the supervisor's, plus a briefing in Italian and English and a compliance log.

What runs on AMD. The ordinance reader runs on AMD Token Factory (AMD Radeon Cloud): MinerU2.5-Pro reads the region's signed PDF and DeepSeek-V4-Flash proposes each rule field with a verbatim quote. Code accepts a field only if the quote is in the document and contains the value; the rest goes to a person. DeepSeek-V4-Flash, also on AMD Token Factory, explains each hand-off. Every AMD call is logged with model, latency, tokens and cost. What does not run on AMD: Gemma 4 (gemma-4-31b-it) writes the crew briefing through Google's Gemini API, so it runs on Google's servers; one setting moves it to a Gemma endpoint on an AMD GPU unchanged. The plan was to run the Aurora 1.5 weather model on an AMD Instinct MI300X; the event provides the Token Factory model API and no GPU instances, and no GPU was available to us, so no Aurora run happened and the forecast is the ECMWF ensemble.

No model decides anything. Rules set the minutes, the supervisor sets the rating, and every number in a model's text is checked against the plan before anyone sees it.

Results, with their caveats. Dates and predictions were committed before scoring. Settings were chosen on four June dates; July and August (10 forecast dates, 5 sites, heavy work, crew new to the heat) are the untouched test set. A miss is an hour planned with more work than ERA5 allowed. The single ECMWF forecast missed 6.6, 7.2, 12.2, 20.4 and 14.5% of heat-restricted hours at leads 1 to 5 days; Turno missed 1.1, 0.6, 3.9, 4.4 and 3.9%, handing 3.0 to 17.0% of working hours to the supervisor. The ordinance reader, on the 10 regions whose rule is one document, accepted 7, 8 and 8 of 10 fields in run 1 and 8, 9 and 9 of 10 in run 2 (season end, ban start, ban end), with 0 fields accepted and wrong across both runs. A live re-read of the Puglia ordinance on the deployed app took 44.9 s of OCR and 34.7 s of extraction.

Limitations. Truth is ERA5, a 0.25 degree reanalysis; there is no thermometer on the site. The ensemble is too confident early in the day: on 30 July in Rome all 10 members ran cooler than what happened at 08:00 and 09:00. ECMWF open data is 3-hourly. The number check proves that every number came from the plan; it does not prove that each sentence is right. Two live failures are in the commit history with their fixes. Model outputs vary between runs, so both reader runs are reported. Not yet tried with a real crew, and no substitute for the employer's risk assessment.

Live app: https://turno.aashanjaved.com. Code: https://github.com/Aashan47/turno (MIT licence).

## Technology tags

If the form takes free text: AMD Token Factory, DeepSeek-V4-Flash, MinerU2.5-Pro, Gemma 4, Gemini API, ECMWF open data, ERA5, thermofeel, NIOSH, FastAPI, Python.

If the form only offers a fixed list, pick the ones that are true: AMD, DeepSeek, Gemma, ECMWF, FastAPI, Python.

Do not tag AMD Developer Cloud or ROCm: neither was used. The AMD part is the Token Factory model API.

## Category

Health and Wellbeing (occupational heat-illness prevention) and Intelligent Industry (monitoring safety conditions).

## AMD evidence

AMD hardware or infrastructure used: AMD Token Factory, the model API on AMD Radeon Cloud, reached over HTTPS from the deployed app. No GPU instance and no AMD Developer Cloud machine was used; the plan to run Aurora 1.5 on an AMD Instinct MI300X could not be carried out because no GPU was available to us. Model and serving stack: MinerU2.5-Pro through the Token Factory document OCR endpoint, and DeepSeek-V4-Flash through the Token Factory chat completions endpoint, both called from Python (httpx) in `turno/amd_llm.py` and `turno/ordinance_reader.py`. Benchmark: a live re-read of the Puglia ordinance on the deployed app on 15 October 2026 took 44.9 s for MinerU OCR and 34.7 s for DeepSeek extraction on AMD Token Factory and verified 6 of 7 fields against the text (README). On the benchmark of 10 single-document regions, DeepSeek-V4-Flash on AMD accepted 7, 8 and 8 of 10 fields in run 1 and 8, 9 and 9 of 10 in run 2, with 0 accepted and wrong in either run; per-region latencies from 16.1 s to 110.7 s are in `results/ordinance_reader.md`. What ran on AMD: the ordinance reader (OCR and field extraction with quotes) and the hand-off explanations in Italian and English. Every AMD call is logged with model, latency, prompt and completion tokens and cost in `results/amd_calls.jsonl`. What did not run on AMD: the Gemma 4 crew briefing (Gemini API, Google servers) and the ECMWF forecast (ECMWF open data).

## Evaluation

Business result: on the pre-registered July and August 2026 test set (10 forecast dates, 5 sites, heavy work, crew new to the heat), planning on the ECMWF ensemble with Turno's rules missed 1.1, 0.6, 3.9, 4.4 and 3.9% of heat-restricted working hours at leads 1 to 5 days, against 6.6, 7.2, 12.2, 20.4 and 14.5% for a single ECMWF forecast; at lead 1 this cuts over-planned work six-fold (0.15 against 0.90 minutes per hour) for 0.9 more minutes of safe work withheld per hour (`results/grid_summary.md`). Known limitation: the truth is ERA5, a 0.25 degree reanalysis read at the grid cell's mean height, with no thermometer on the site, and ECMWF open data is 3-hourly, so the evaluation uses 3-hourly times. Failure case: on 30 July 2026 in Rome all 10 ensemble members ran cooler than what happened at 08:00 and 09:00, and the plan allowed 15 minutes more work than reality would have in each of those hours; the app marks these hours as "plan too high". Two live text failures, an invented "31 C threshold" and heat stops called "banned", are recorded in the commit history with their fixes. Safeguard and human review: no model decides anything. NIOSH rules set the minutes; the supervisor confirms the Worklimate rating and, until confirmed, the ban is assumed; hours where the ensemble members are 30 minutes of work apart (3.0 to 17.0% of working hours at leads 1 to 5) are handed to the supervisor with the reason; an ordinance field is accepted only if the model's quote is found verbatim in the document and contains the value, otherwise it goes to a person; every number in a briefing or explanation must appear in the plan, hour labels are fixed by code, and on any failure a template replaces the model text.
