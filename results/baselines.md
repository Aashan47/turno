# Non-AI baselines against ERA5 WBGT

Run 2026-10-06. Workload: heavy, acclimatized. A miss is an hour planned as more work than ERA5 allows. Truth is ERA5, itself a 0.25 degree reanalysis, not a site measurement; every arm is read at the same ERA5 land cell, at the cell's mean height. Scoring against ERA5 favours models on ERA5's own grid, so the 2 km ICON-2I is disadvantaged here.

| Site | Arm | Lead (days) | Hours | WBGT MAE C | Bias C | Restricted hours | Missed | Miss rate | False restrictions |
|---|---|---|---|---|---|---|---|---|---|
| Roma | persistence | 1 | 2184 | 1.26 | -0.03 | 880 | 268 | 30.5% | 85 |
| Roma | ecmwf_ifs025 | 1 | 2208 | 0.93 | +0.20 | 880 | 209 | 23.8% | 53 |
| Roma | italia_meteo_arpae_icon_2i | 1 | 2040 | 1.15 | -0.45 | 868 | 291 | 33.5% | 34 |
| Roma | persistence | 2 | 2160 | 1.43 | -0.07 | 879 | 305 | 34.7% | 104 |
| Roma | ecmwf_ifs025 | 2 | 2208 | 1.01 | +0.08 | 880 | 248 | 28.2% | 50 |
| Roma | italia_meteo_arpae_icon_2i | 2 | 2029 | 1.23 | -0.61 | 863 | 325 | 37.7% | 34 |
| Roma | persistence | 3 | 2136 | 1.54 | -0.12 | 879 | 341 | 38.8% | 107 |
| Roma | ecmwf_ifs025 | 3 | 2208 | 1.02 | +0.08 | 880 | 234 | 26.6% | 55 |
| Roma | persistence | 4 | 2112 | 1.72 | -0.19 | 874 | 342 | 39.1% | 105 |
| Roma | ecmwf_ifs025 | 4 | 2208 | 1.10 | +0.13 | 880 | 239 | 27.2% | 66 |
| Roma | persistence | 5 | 2088 | 1.79 | -0.26 | 874 | 378 | 43.2% | 101 |
| Roma | ecmwf_ifs025 | 5 | 2208 | 1.19 | +0.05 | 880 | 267 | 30.3% | 69 |
| Borgo Piave, Latina | persistence | 1 | 2184 | 1.10 | -0.04 | 945 | 272 | 28.8% | 80 |
| Borgo Piave, Latina | ecmwf_ifs025 | 1 | 2208 | 1.18 | -0.81 | 949 | 508 | 53.5% | 41 |
| Borgo Piave, Latina | italia_meteo_arpae_icon_2i | 1 | 2040 | 1.15 | -0.62 | 925 | 454 | 49.1% | 29 |
| Borgo Piave, Latina | persistence | 2 | 2160 | 1.26 | -0.09 | 945 | 320 | 33.9% | 91 |
| Borgo Piave, Latina | ecmwf_ifs025 | 2 | 2208 | 1.21 | -0.88 | 949 | 498 | 52.5% | 35 |
| Borgo Piave, Latina | italia_meteo_arpae_icon_2i | 2 | 2029 | 1.22 | -0.66 | 920 | 466 | 50.7% | 41 |
| Borgo Piave, Latina | persistence | 3 | 2136 | 1.35 | -0.14 | 945 | 347 | 36.7% | 84 |
| Borgo Piave, Latina | ecmwf_ifs025 | 3 | 2208 | 1.27 | -0.88 | 949 | 497 | 52.4% | 37 |
| Borgo Piave, Latina | persistence | 4 | 2112 | 1.48 | -0.19 | 937 | 363 | 38.7% | 87 |
| Borgo Piave, Latina | ecmwf_ifs025 | 4 | 2208 | 1.32 | -0.90 | 949 | 506 | 53.3% | 40 |
| Borgo Piave, Latina | persistence | 5 | 2088 | 1.61 | -0.25 | 934 | 391 | 41.9% | 94 |
| Borgo Piave, Latina | ecmwf_ifs025 | 5 | 2208 | 1.38 | -0.96 | 949 | 524 | 55.2% | 37 |
| Imperia | persistence | 1 | 2184 | 1.18 | -0.02 | 554 | 239 | 43.1% | 78 |
| Imperia | ecmwf_ifs025 | 1 | 2208 | 1.22 | -0.24 | 554 | 150 | 27.1% | 104 |
| Imperia | italia_meteo_arpae_icon_2i | 1 | 2040 | 1.41 | -1.18 | 554 | 409 | 73.8% | 18 |
| Imperia | persistence | 2 | 2160 | 1.44 | -0.05 | 554 | 257 | 46.4% | 100 |
| Imperia | ecmwf_ifs025 | 2 | 2208 | 1.24 | -0.28 | 554 | 165 | 29.8% | 94 |
| Imperia | italia_meteo_arpae_icon_2i | 2 | 2029 | 1.41 | -1.14 | 551 | 402 | 73.0% | 28 |
| Imperia | persistence | 3 | 2136 | 1.73 | -0.09 | 554 | 261 | 47.1% | 122 |
| Imperia | ecmwf_ifs025 | 3 | 2208 | 1.25 | -0.21 | 554 | 161 | 29.1% | 105 |
| Imperia | persistence | 4 | 2112 | 1.90 | -0.15 | 554 | 298 | 53.8% | 138 |
| Imperia | ecmwf_ifs025 | 4 | 2208 | 1.31 | -0.15 | 554 | 160 | 28.9% | 118 |
| Imperia | persistence | 5 | 2088 | 2.02 | -0.22 | 554 | 304 | 54.9% | 149 |
| Imperia | ecmwf_ifs025 | 5 | 2208 | 1.35 | -0.23 | 554 | 171 | 30.9% | 110 |
| Milano | persistence | 1 | 2184 | 1.56 | -0.00 | 799 | 302 | 37.8% | 93 |
| Milano | ecmwf_ifs025 | 1 | 2208 | 1.13 | +0.42 | 807 | 211 | 26.1% | 77 |
| Milano | italia_meteo_arpae_icon_2i | 1 | 2040 | 1.22 | -0.50 | 788 | 431 | 54.7% | 38 |
| Milano | persistence | 2 | 2160 | 1.82 | -0.06 | 799 | 330 | 41.3% | 102 |
| Milano | ecmwf_ifs025 | 2 | 2208 | 1.15 | +0.40 | 807 | 213 | 26.4% | 70 |
| Milano | italia_meteo_arpae_icon_2i | 2 | 2029 | 1.27 | -0.52 | 783 | 440 | 56.2% | 37 |
| Milano | persistence | 3 | 2136 | 2.04 | -0.09 | 799 | 365 | 45.7% | 116 |
| Milano | ecmwf_ifs025 | 3 | 2208 | 1.15 | +0.40 | 807 | 213 | 26.4% | 87 |
| Milano | persistence | 4 | 2112 | 2.13 | -0.15 | 799 | 377 | 47.2% | 116 |
| Milano | ecmwf_ifs025 | 4 | 2208 | 1.21 | +0.41 | 807 | 229 | 28.4% | 89 |
| Milano | persistence | 5 | 2088 | 2.37 | -0.19 | 798 | 379 | 47.5% | 124 |
| Milano | ecmwf_ifs025 | 5 | 2208 | 1.28 | +0.32 | 807 | 261 | 32.3% | 80 |
| Foggia | persistence | 1 | 2184 | 1.46 | -0.06 | 711 | 275 | 38.7% | 88 |
| Foggia | ecmwf_ifs025 | 1 | 2208 | 1.16 | +0.79 | 716 | 153 | 21.4% | 112 |
| Foggia | italia_meteo_arpae_icon_2i | 1 | 2040 | 1.29 | +0.15 | 703 | 346 | 49.2% | 62 |
| Foggia | persistence | 2 | 2160 | 1.87 | -0.11 | 711 | 329 | 46.3% | 106 |
| Foggia | ecmwf_ifs025 | 2 | 2208 | 1.17 | +0.80 | 716 | 153 | 21.4% | 124 |
| Foggia | italia_meteo_arpae_icon_2i | 2 | 2029 | 1.30 | +0.10 | 699 | 360 | 51.5% | 51 |
| Foggia | persistence | 3 | 2136 | 1.96 | -0.16 | 711 | 355 | 49.9% | 117 |
| Foggia | ecmwf_ifs025 | 3 | 2208 | 1.21 | +0.79 | 716 | 162 | 22.6% | 109 |
| Foggia | persistence | 4 | 2112 | 2.10 | -0.24 | 711 | 373 | 52.5% | 122 |
| Foggia | ecmwf_ifs025 | 4 | 2208 | 1.19 | +0.64 | 716 | 202 | 28.2% | 101 |
| Foggia | persistence | 5 | 2088 | 2.24 | -0.30 | 709 | 380 | 53.6% | 130 |
| Foggia | ecmwf_ifs025 | 5 | 2208 | 1.30 | +0.67 | 716 | 198 | 27.7% | 128 |
