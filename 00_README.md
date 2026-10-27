# Synthetic Paratransit Dashboard Project — Start Here

All data is fictional. Reporting window 2025-10-01 → 2026-09-30. Age as-of date 2026-09-30.

| Order | File | Purpose |
|---|---|---|
| 1 | `Clients.csv` (5,060 raw rows), `Trips.csv` (100,400 raw rows) | Raw, deliberately dirty data |
| 2 | `01_Data_Dictionary.md` | Columns, grain, keys, valid values, created-later columns |
| 3 | `02_Raw_Data_Quality_Report.md` | Every planted issue, counts, resolution type, row waterfall |
| 4 | `03_Power_Query_Tutorial.md` + `PowerQuery/Clients.m`, `PowerQuery/Trips.m` | Step-by-step cleaning; Age, Mode, PickupDelayMinutes in M |
| 5 | `04_DAX_Model_Guide.md` | Relationship, all measures, time intelligence, ranking |
| 6 | `05_Dashboard_QA_Portfolio_Publishing.md` | 7 pages, interactivity, QA checklist, portfolio text, publishing |
| Tools | `generate_data.py` (seeded, reproducible), `reference_clean.py` (pandas answer key) | Regenerate data / verify your Power BI numbers |

Parameters to create in Power Query: pFolder, pAsOfDate, pDataStart, pDataEnd (not loaded, so the model has exactly two tables).
