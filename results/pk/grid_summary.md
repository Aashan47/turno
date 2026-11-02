# Pakistan: the frozen planner against ERA5, pooled over 5 sites

Run 2026-11-02. Pre-registration: `PREREGISTRATION-PK.md` (commit e824b49, before any data). Rules frozen from Italy (`turno/rules.py`). 3-hourly valid times inside working hours only (03, 06, 09, 12 UTC = 08, 11, 14, 17 PKT). A time is heat-restricted when the ERA5 truth allows under 60 work minutes.

## Predictions (heavy work, unacclimatized limit, leads 1 to 3)

| Lead | IFS miss rate | ENS miss rate | Relative reduction | P1: at least 30% | ENS hand-off rate | P2: under 25% |
|---|---|---|---|---|---|---|
| 1 | 5.0% | 3.8% | 24% | FAIL | 0.6% | PASS |
| 2 | 7.6% | 2.4% | 69% | PASS | 1.5% | PASS |
| 3 | 5.9% | 3.5% | 40% | PASS | 2.4% | PASS |

## All arms, workloads, limits and leads

| Workload | Limit | Arm | Lead (days) | Inits | Times | WBGT MAE C | Bias C | Restricted | Missed | Miss rate | Handed over | Min over per time | Min withheld per time |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| heavy | RAL | ECMWF ENS + Turno rules | 1 | 17 | 340 | 0.98 | -0.54 | 340 | 13 | 3.8% | 0.6% | 0.57 | 0.18 |
| heavy | RAL | ECMWF ENS + Turno rules | 2 | 17 | 340 | 1.00 | -0.53 | 340 | 8 | 2.4% | 1.5% | 0.40 | 0.22 |
| heavy | RAL | ECMWF ENS + Turno rules | 3 | 17 | 340 | 0.91 | -0.40 | 340 | 12 | 3.5% | 2.4% | 0.53 | 0.49 |
| heavy | RAL | ECMWF ENS + Turno rules | 4 | 17 | 340 | 1.09 | -0.19 | 340 | 6 | 1.8% | 1.5% | 0.26 | 0.71 |
| heavy | RAL | ECMWF ENS + Turno rules | 5 | 17 | 340 | 0.98 | -0.27 | 340 | 4 | 1.2% | 0.9% | 0.18 | 0.49 |
| heavy | RAL | ECMWF IFS (single) | 1 | 17 | 340 | 1.03 | -0.47 | 340 | 17 | 5.0% | 0.0% | 0.75 | 0.13 |
| heavy | RAL | ECMWF IFS (single) | 2 | 17 | 340 | 1.03 | -0.44 | 340 | 26 | 7.6% | 0.0% | 1.24 | 0.09 |
| heavy | RAL | ECMWF IFS (single) | 3 | 17 | 340 | 0.95 | -0.35 | 340 | 20 | 5.9% | 0.0% | 0.97 | 0.31 |
| heavy | RAL | ECMWF IFS (single) | 4 | 17 | 340 | 1.09 | -0.20 | 340 | 20 | 5.9% | 0.0% | 0.88 | 0.35 |
| heavy | RAL | ECMWF IFS (single) | 5 | 17 | 340 | 0.99 | -0.15 | 340 | 17 | 5.0% | 0.0% | 0.75 | 0.26 |
| heavy | REL | ECMWF ENS + Turno rules | 1 | 17 | 340 | 0.98 | -0.54 | 334 | 20 | 6.0% | 7.6% | 0.97 | 1.99 |
| heavy | REL | ECMWF ENS + Turno rules | 2 | 17 | 340 | 1.00 | -0.53 | 333 | 26 | 7.8% | 9.1% | 1.32 | 2.03 |
| heavy | REL | ECMWF ENS + Turno rules | 3 | 17 | 340 | 0.91 | -0.40 | 332 | 22 | 6.6% | 12.1% | 0.97 | 2.29 |
| heavy | REL | ECMWF ENS + Turno rules | 4 | 17 | 340 | 1.09 | -0.19 | 331 | 14 | 4.2% | 12.9% | 0.62 | 3.49 |
| heavy | REL | ECMWF ENS + Turno rules | 5 | 17 | 340 | 0.98 | -0.27 | 335 | 15 | 4.5% | 13.8% | 0.75 | 3.13 |
| heavy | REL | ECMWF IFS (single) | 1 | 17 | 340 | 1.03 | -0.47 | 334 | 36 | 10.8% | 0.0% | 1.94 | 1.01 |
| heavy | REL | ECMWF IFS (single) | 2 | 17 | 340 | 1.03 | -0.44 | 333 | 52 | 15.6% | 0.0% | 2.82 | 1.19 |
| heavy | REL | ECMWF IFS (single) | 3 | 17 | 340 | 0.95 | -0.35 | 332 | 47 | 14.2% | 0.0% | 2.78 | 0.93 |
| heavy | REL | ECMWF IFS (single) | 4 | 17 | 340 | 1.09 | -0.20 | 331 | 46 | 13.9% | 0.0% | 2.56 | 1.76 |
| heavy | REL | ECMWF IFS (single) | 5 | 17 | 340 | 0.99 | -0.15 | 335 | 46 | 13.7% | 0.0% | 2.56 | 1.54 |
| moderate | RAL | ECMWF ENS + Turno rules | 1 | 17 | 340 | 0.98 | -0.54 | 340 | 9 | 2.6% | 2.1% | 0.40 | 0.79 |
| moderate | RAL | ECMWF ENS + Turno rules | 2 | 17 | 340 | 1.00 | -0.53 | 339 | 18 | 5.3% | 3.8% | 0.84 | 0.79 |
| moderate | RAL | ECMWF ENS + Turno rules | 3 | 17 | 340 | 0.91 | -0.40 | 339 | 13 | 3.8% | 5.0% | 0.62 | 0.93 |
| moderate | RAL | ECMWF ENS + Turno rules | 4 | 17 | 340 | 1.09 | -0.19 | 339 | 8 | 2.4% | 5.9% | 0.35 | 1.63 |
| moderate | RAL | ECMWF ENS + Turno rules | 5 | 17 | 340 | 0.98 | -0.27 | 340 | 11 | 3.2% | 3.8% | 0.53 | 1.28 |
| moderate | RAL | ECMWF IFS (single) | 1 | 17 | 340 | 1.03 | -0.47 | 340 | 19 | 5.6% | 0.0% | 0.93 | 0.53 |
| moderate | RAL | ECMWF IFS (single) | 2 | 17 | 340 | 1.03 | -0.44 | 339 | 29 | 8.6% | 0.0% | 1.54 | 0.35 |
| moderate | RAL | ECMWF IFS (single) | 3 | 17 | 340 | 0.95 | -0.35 | 339 | 32 | 9.4% | 0.0% | 1.59 | 0.44 |
| moderate | RAL | ECMWF IFS (single) | 4 | 17 | 340 | 1.09 | -0.20 | 339 | 30 | 8.8% | 0.0% | 1.37 | 0.62 |
| moderate | RAL | ECMWF IFS (single) | 5 | 17 | 340 | 0.99 | -0.15 | 340 | 27 | 7.9% | 0.0% | 1.46 | 0.57 |
| moderate | REL | ECMWF ENS + Turno rules | 1 | 17 | 340 | 0.98 | -0.54 | 318 | 22 | 6.9% | 15.0% | 1.24 | 3.49 |
| moderate | REL | ECMWF ENS + Turno rules | 2 | 17 | 340 | 1.00 | -0.53 | 317 | 31 | 9.8% | 16.5% | 1.63 | 3.35 |
| moderate | REL | ECMWF ENS + Turno rules | 3 | 17 | 340 | 0.91 | -0.40 | 313 | 21 | 6.7% | 17.4% | 1.10 | 3.13 |
| moderate | REL | ECMWF ENS + Turno rules | 4 | 17 | 340 | 1.09 | -0.19 | 309 | 19 | 6.1% | 19.7% | 0.93 | 5.47 |
| moderate | REL | ECMWF ENS + Turno rules | 5 | 17 | 340 | 0.98 | -0.27 | 311 | 16 | 5.1% | 21.8% | 1.06 | 4.94 |
| moderate | REL | ECMWF IFS (single) | 1 | 17 | 340 | 1.03 | -0.47 | 318 | 48 | 15.1% | 0.0% | 2.65 | 1.59 |
| moderate | REL | ECMWF IFS (single) | 2 | 17 | 340 | 1.03 | -0.44 | 317 | 66 | 20.8% | 0.0% | 3.66 | 1.68 |
| moderate | REL | ECMWF IFS (single) | 3 | 17 | 340 | 0.95 | -0.35 | 313 | 53 | 16.9% | 0.0% | 3.26 | 1.41 |
| moderate | REL | ECMWF IFS (single) | 4 | 17 | 340 | 1.09 | -0.20 | 309 | 48 | 15.5% | 0.0% | 2.96 | 2.74 |
| moderate | REL | ECMWF IFS (single) | 5 | 17 | 340 | 0.99 | -0.15 | 311 | 48 | 15.4% | 0.0% | 2.87 | 2.47 |

## Per site (heavy work, unacclimatized, leads 1 to 3 pooled)

| Site | Arm | Times | Restricted share | Missed | Miss rate | Handed over |
|---|---|---|---|---|---|---|
| hyderabad | ECMWF ENS + Turno rules | 204 | 100.0% | 11 | 5.4% | 0.0% |
| hyderabad | ECMWF IFS (single) | 204 | 100.0% | 15 | 7.4% | 0.0% |
| jacobabad | ECMWF ENS + Turno rules | 204 | 100.0% | 8 | 3.9% | 0.5% |
| jacobabad | ECMWF IFS (single) | 204 | 100.0% | 12 | 5.9% | 0.0% |
| karachi | ECMWF ENS + Turno rules | 204 | 100.0% | 8 | 3.9% | 0.0% |
| karachi | ECMWF IFS (single) | 204 | 100.0% | 12 | 5.9% | 0.0% |
| lahore | ECMWF ENS + Turno rules | 204 | 100.0% | 1 | 0.5% | 4.4% |
| lahore | ECMWF IFS (single) | 204 | 100.0% | 11 | 5.4% | 0.0% |
| multan | ECMWF ENS + Turno rules | 204 | 100.0% | 5 | 2.5% | 2.5% |
| multan | ECMWF IFS (single) | 204 | 100.0% | 13 | 6.4% | 0.0% |
