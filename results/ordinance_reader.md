# Ordinance reader against the verified 2026 records

Run 2026-10-15. Model DeepSeek-V4-Flash on AMD Token Factory. 10 single-act regions scored on valid_to, ban_start, ban_end; 5 multi-act regions reported for amendment detection.

| Field | Accepted | Accepted and correct | **Accepted and wrong** | Sent to a person |
|---|---|---|---|---|
| valid_to | 8 | 8 | **0** | 2 |
| ban_start | 9 | 9 | **0** | 1 |
| ban_end | 9 | 9 | **0** | 1 |

| Region | Source | Multi-act | Flags amendment | Fields sent to a person | Latency s |
|---|---|---|---|---|---|
| Lazio | saved primary text | yes | True | valid_from | 33.651 |
| Liguria | MinerU2.5-Pro OCR on AMD of the region's PDF | no | False | valid_from, trigger | 24.497 |
| Lombardia | MinerU2.5-Pro OCR on AMD of the region's PDF | no | False | none | 20.677 |
| Puglia | MinerU2.5-Pro OCR on AMD of the region's PDF | no | True | valid_from | 60.289 |
| Campania | saved primary text | yes | True | exemptions | 18.566 |
| Sicilia | saved primary text (MinerU failed: Server error '502 Bad Gateway' for url 'https://developer.am) | yes | True | valid_from | 28.144 |
| Toscana | saved primary text | no | True | valid_from, valid_to | 110.728 |
| Emilia-Romagna | saved primary text | no | False | none | 21.066 |
| Calabria | MinerU2.5-Pro OCR on AMD of the region's PDF | no | False | valid_from, valid_to, ban_start, ban_end | 16.133 |
| Sardegna | MinerU2.5-Pro OCR on AMD of the region's PDF | yes | True | valid_from | 30.423 |
| Umbria | MinerU2.5-Pro OCR on AMD of the region's PDF | no | True | valid_from | 62.66 |
| Veneto | saved primary text | yes | True | none | 30.098 |
| Piemonte | saved primary text | no | True | none | 34.508 |
| Abruzzo | saved primary text | no | False | valid_from | 26.764 |
| Marche | saved primary text | no | False | none | 25.045 |
