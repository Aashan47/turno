# Pre-registration

Written 2026-10-06, before any Aurora forecast has been run. Committed to git so the date is checkable.
Whatever the results, every arm below is reported, including any that contradicts these predictions.

## What is compared

All arms are read on the identical 0.25 degree grid, at the nearest mostly-land ERA5 cell to each site
(`turno/grid.py`), and scored by `turno/evaluate.py` against WBGT computed from ERA5 with ERA5's own
direct fraction. Workload: heavy (NIOSH Table 5-1, 350 to 465 W). Both acclimatized (REL) and
unacclimatized (RAL) are reported; RAL is the one Worklimate and the ordinances use.

| Arm | What it is |
|---|---|
| Persistence | ERA5 WBGT at the same hour, `lead` days earlier |
| ECMWF IFS | ECMWF open data, deterministic, 0.25 degrees |
| ECMWF ENS | ECMWF open data, the 50 perturbed members, 0.25 degrees |
| Aurora 1.5 | `AuroraV1p5`, deterministic, initialised from ERA5 |
| Aurora 1.5 Ensemble | `AuroraV1p5Ensemble`, members from noise injection, initialised from ERA5 |

Aurora's direct fraction comes from the Erbs split (cost measured: 0.15 to 0.20 C mean WBGT). The
ECMWF arms' direct fraction also comes from the Erbs split applied to their `ssrd`, so no arm gets
ERA5-quality radiation the others lack.

## Initialisation dates, fixed now

00 UTC on every seventh day from 3 June 2026: **3, 10, 17, 24 June; 1, 8, 15, 22, 29 July; 5, 12, 19,
26 August** (13 dates), chosen by calendar, not by weather. Plus **30 July 2026**, chosen in advance as a
known heat day. Leads 1 to 5 days. If GPU time runs short, dates are dropped from the end of the list,
never selected by result.

## Predictions

1. **Aurora is not the most accurate WBGT forecast.** ECMWF IFS will have a lower WBGT mean absolute
   error than the Aurora deterministic run at lead 1 day. (Aurora was fine-tuned for IFS analysis and is
   here started from ERA5.)
2. **The ensemble plus refusal protects workers better than any single forecast.** Using the cautious
   value in undetermined hours, Aurora Ensemble's miss rate on heat-restricted hours will be at least
   30% lower, relative, than the single ECMWF IFS forecast's, at lead 1 to 3 days.
3. **The price is supervisor hand-offs.** That reduction will cost a hand-off rate under 25% of daylight
   working hours (07:00 to 19:00 local). Above 25% the refusal is too frequent to be useful, and the
   README will say so.
4. **ECMWF ENS with the same rules does at least as well as Aurora Ensemble.** If true, Turno's claim is
   the decision layer and the self-hosted ensemble on one GPU, not better weather.

## What would count against Turno

- Prediction 2 fails: the ensemble does not reduce misses enough to justify itself.
- Prediction 3 fails: the refusal fires too often to be a product.
- Aurora does not run on ROCm, or its output is unphysical at the sites (kill test 1, `05-BUILD-PLAN.md`).

## Amendment 1, 2026-10-06, before any Aurora output exists

**What changed.** The hour plan now always plans for the hard end of the workload range, and only
forecast members that disagree send an hour to the supervisor. Before, a workload range that straddled
a work step also sent the hour to the supervisor.

**Why, and what prompted it.** Scoring the ECMWF IFS arm on all 14 dates showed that a single
deterministic forecast, which has no members to disagree, was handing over 27 to 40% of all 3-hourly
times, purely because heavy work spans 350 to 465 W. That would break prediction 3's 25% ceiling before
any ensemble was involved, and a supervisor asked about four hours in ten would stop reading. Planning
for the hard end is the conservative reading NIOSH's own 30% workload-error statement supports; the range
is still shown to the user as a note.

**What it does not change.** The truth plan, the miss definition, the dates, the arms and predictions 1,
2 and 4 are unchanged. Miss rates for the IFS arm were identical before and after (they already used the
cautious value). Prediction 3 now measures hand-offs caused by forecast disagreement only.

**The bar Aurora must clear**, ECMWF IFS, unacclimatized limit (RAL), pooled over 5 sites and 14 dates,
miss rate on heat-restricted 3-hourly times: lead 1: 16.1%, lead 2: 18.2%, lead 3: 23.4%, lead 4:
25.7%, lead 5: 19.2%. Full table: `grid_summary.md`.
