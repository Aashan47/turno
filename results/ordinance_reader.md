# Ordinance reader against the verified 2026 records

Run 2026-10-15. Model DeepSeek-V4-Flash on AMD Token Factory. 10 single-act regions scored on valid_to, ban_start, ban_end; 5 multi-act regions reported for amendment detection.

| Field | Accepted | Accepted and correct | **Accepted and wrong** | Sent to a person |
|---|---|---|---|---|
| valid_to | 7 | 7 | **0** | 3 |
| ban_start | 8 | 8 | **0** | 2 |
| ban_end | 8 | 8 | **0** | 2 |

| Region | Source | Multi-act | Flags amendment | Fields sent to a person | Latency s |
|---|---|---|---|---|---|
| Lazio | saved primary text | yes | True | valid_from | 51.723 |
| Liguria | MinerU2.5-Pro OCR on AMD of the region's PDF | no | False | valid_from | 20.651 |
| Lombardia | MinerU2.5-Pro OCR on AMD of the region's PDF | no | False | none | 61.832 |
| Puglia | MinerU2.5-Pro OCR on AMD of the region's PDF | no | True | valid_from, trigger | 23.792 |
| Campania | saved primary text | yes | True | none | 46.481 |
| Sicilia | saved primary text (MinerU failed: Server error '502 Bad Gateway' for url 'https://developer.am) | yes | True | valid_from, valid_to | 31.688 |
| Toscana | saved primary text | no | True | valid_from, valid_to | 20.174 |
| Emilia-Romagna | saved primary text | no | False | none | 46.568 |
| Calabria | MinerU2.5-Pro OCR on AMD of the region's PDF | no | False | valid_from, valid_to, ban_start, ban_end, trigger, sectors, exemptions | 18.189 |
| Sardegna | MinerU2.5-Pro OCR on AMD of the region's PDF | yes | True | valid_from, trigger | 18.616 |
| Umbria | MinerU2.5-Pro OCR on AMD of the region's PDF | no | True | valid_from, valid_to, ban_start, ban_end, trigger, sectors, exemptions | 25.282 |
| Veneto | saved primary text | yes | True | none | 30.154 |
| Piemonte | saved primary text | no | True | none | 34.792 |
| Abruzzo | saved primary text | no | False | valid_from | 31.475 |
| Marche | saved primary text | no | False | trigger | 23.121 |
