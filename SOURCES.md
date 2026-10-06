# Sources

Every constant and rule in the code, with where it comes from. Read dates are when the source was
opened for this project.

## 1. NIOSH 2016-106, Criteria for a Recommended Standard: Occupational Exposure to Heat and Hot Environments

cdc.gov returned HTTP 403 on 2026-10-06; the document was read from the Wayback Machine copy of
`https://www.cdc.gov/niosh/docs/2016-106/pdfs/2016-106.pdf` the same day.

- Section 8.1: "RAL [°C-WBGT] = 59.9 − 14.1 log10 M [W]", "REL [°C-WBGT] = 56.7 − 11.5 log10 M [W]".
- "The estimates of both environmental and metabolic heat are expressed as 1-hour time-weighted
  averages (TWAs)".
- "RALs and RELs take work/rest schedules into consideration so are shown for 60, 45, 30, and 15 minute
  time periods".
- Table 5-1, NIOSH column: Resting "100 kcal·h-1 (117 W)"; Moderate "201–300 kcal·h-1 (234–349 W)",
  28°C; Heavy "301–400 kcal·h-1 (350–465 W)", 26°C; Very heavy "401–500 kcal·h-1 (466–580 W)", 25°C.
- Cross-check in `tests/test_limits.py`: the REL equation gives 26.02°C at 465 W and 24.92°C at 580 W,
  against the table's 26°C and 25°C.

## 2. Liljegren WBGT

ECMWF thermofeel 2.3.0, `calculate_wbgt_liljegren`, Apache-2.0. Inputs: 2 m temperature (K), relative
humidity (%), surface pressure (hPa), 10 m wind (m/s, scaled to 2 m internally), downward shortwave
(W/m2), direct fraction, cosine of the solar zenith angle.

## 3. Sun position

NOAA Global Monitoring Division, "General Solar Position Calculations",
`https://gml.noaa.gov/grad/solcalc/solareqns.PDF`, read 2026-10-06: fractional year, equation of time,
declination, hour angle and zenith equations used verbatim in `turno/solar.py`.

The Earth-Sun distance factor is not on that page. Its Fourier form is checked empirically: the
top-of-atmosphere irradiance it implies is compared against ERA5's `tisr` field.

## 4. Direct-diffuse split

Erbs, D. G., Klein, S. A. and Duffie, J. A. (1982). "Estimation of the diffuse radiation fraction for
hourly, daily and monthly-average global radiation". Solar Energy 28(4):293-302.
doi:10.1016/0038-092X(82)90302-4 (title, authors, volume and pages confirmed on Crossref 2026-10-06).
Its error on Italian summer hours is measured against ERA5's own direct radiation, not assumed.

## 5. ERA5

Hersbach et al., ERA5 hourly data on single levels, Copernicus Climate Change Service Climate Data
Store, CC BY 4.0. Fetched with `scripts/fetch_era5_italy.py`.

## 6. Italian heat ordinances and Worklimate

INAIL-CNR Worklimate, "Report Caldo e Lavoro n.4", July 2025: "ordinanze regionali vincolanti, che
dispongono il divieto di lavoro all'aperto nelle ore centrali della giornata (12:30–16:00) nei giorni
con rischio "Alto" secondo la piattaforma Worklimate." Per-region ordinance texts: `data/ordinances_2026.json`
(in progress).
