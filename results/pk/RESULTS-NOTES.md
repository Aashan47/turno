# Pakistan run: notes that go with `grid_summary.md`

Run 2 November 2026, 7:40 PM PKT. `grid_summary.md` is written by `scripts/summarize_grid.py --region pk`;
pass and fail are computed by that code against the thresholds in `PREREGISTRATION-PK.md`.

## Outcome of the pre-registered predictions

- **Prediction 1 FAILED at lead 1** and passed at leads 2 and 3. Heavy work, unacclimatized limit: ENS
  missed 3.8% of heat-restricted times against IFS 5.0% one day ahead, a 24% relative reduction, under the
  30% set in advance. Leads 2 and 3: 2.4% against 7.6% (69%) and 3.5% against 5.9% (40%). The
  pre-registration says any application text states the lead-1 failure; the MIT Solve tech-stack answer does.
- **Prediction 2 PASSED** at leads 1 to 3: ENS handed 0.6%, 1.5% and 2.4% of working times to the supervisor.

## What the reader needs to weigh these numbers

- **Every working time was heat-restricted under the primary measure** (340 of 340 at each lead). For heavy
  work and the unacclimatized limit, ERA5 allowed under 60 work minutes in every working hour, 08:00 to 17:00
  PKT, May to August, at all five sites. So the primary measure here never asks whether a time is restricted;
  a miss is a time where the plan allowed more minutes than the truth. That makes it a test of the minutes,
  and a weaker test of the decision than Italy, where many times were unrestricted.
- **The counts are small and not independent.** Lead-1 misses are 13 (ENS) and 17 (IFS) of 340 times; the
  340 times share 17 dates and five nearby sites, so a single hot spell moves several at once. The lead-1
  failure and the lead-2 and lead-3 passes are all within what a few days' weather could change.
- **Forecasts ran cooler than ERA5 at every lead** (bias -0.15 to -0.54 C), most at lead 1.
- **Arms reported without a prediction** (acclimatized limit, moderate work) all show the ensemble missing
  fewer times than the single forecast at every lead, with hand-off rates up to 21.8% (moderate, REL, lead 5).
  They were not predicted, so they do not rescue prediction 1.

## Checks

- **Truth source** (amendment 1): ARCO-ERA5 on Google Cloud, hours 01 to 12 UTC. The four month files have no
  missing values. Equivalence with Copernicus was checked on Italy before any Pakistan field was fetched.
  The Copernicus request for May was still queued at 7:40 PM PKT; if it completes, the comparison goes here.
- **Scored-steps forecast files.** The full 6 May IFS file (`data/ecmwf_pk_full/`) and the scored-steps file
  give identical decision results in all 100 rows (restricted, missed, handed over, minutes). WBGT MAE and bias
  differ by at most 1.1e-6 C, because the full file stores float32 and the subset float64.
- All 34 forecast files (17 IFS, 17 ENS) downloaded; no date dropped.
