# Raw-Data Quality Report

Counts below were measured on the delivered `Clients.csv` (5,060 rows) and `Trips.csv` (100,400 rows) by an independent script (`reference_clean.py`) that applies the same rules as the Power Query guide. **Do not calculate KPIs from the raw files** — use these counts only to confirm that your cleaned tables match.

**Resolution types**
- **Correct** — the true value can be recovered with certainty (trim, case, format, sign).
- **Flag** — keep the row, mark the problem, let measures decide.
- **Exclude from measure** — row stays in the table but is left out of a specific KPI denominator.
- **Remove** — true duplicate row, deleted.

---

## 1. Row counts before and after de-duplication

| Table | Raw rows | Exact duplicate rows | Conflicting duplicate rows | Rows after de-dup | Distinct keys |
|---|---|---|---|---|---|
| `Clients` | 5,060 | 30 | 30 | **5,000** | 5,000 `ClientID` |
| `Trips` | 100,400 | 250 | 150 (100 stale "Scheduled" copies + 50 copies missing actual pickup/drop-off) | **100,000** | 100,000 `TripID` |

No valid client or trip is lost: 60 surplus client rows and 400 surplus trip rows are removed; every key survives exactly once.

### How conflicting duplicates are resolved (never "keep the first and hope")
- **Clients:** sort by `ClientID`, then *completeness score* (count of non-blank raw attribute fields, descending), then original row order. Keep the top row. The 10 conflicting copies that only differ by `ClientStatus` tie on completeness, so the first-listed record wins; in real life you would take the status from the source system's "last updated" field, which this dataset does not have. Flag it in your write-up as a known limitation.
- **Trips:** sort by `TripID`, then *status rank* (resolved status beats `Scheduled`/blank), then completeness (parsed timestamps + parsed fare/distance/duration), then original row order. Stale "Scheduled" copies lose to the final record; partial copies lose to the complete one.

---

## 2. Issue register — `Clients`

Counts are raw-row counts (5,060 rows) unless stated.

| # | Issue | Raw count | Resolution type | Power Query treatment | Result after cleaning |
|---|---|---|---|---|---|
| C1 | Duplicate `ClientID` rows | 60 rows share 60 IDs (120 rows involved) | Remove / resolve | Completeness score → sort → `Table.Buffer` → `Table.Distinct` on `ClientID` | 5,000 unique clients |
| C2 | Different labels for the same `ClientType` | 56 raw spellings | Correct | Trim/clean, `Text.Lower`, rule-based mapping | 4 values + Unknown |
| C3 | Different labels for the same `EligibilityCategory` | 67 raw spellings | Correct | Rule-based mapping (`uncond` tested *before* `cond`) | Unconditional, Conditional, Temporary, Visitor |
| C4 | Inconsistent `ClientStatus` codes | 51 raw spellings; 25 unrecognised (`X`, `?`, `PEND`) | Correct / Flag | Code table; unknown → `Unknown` | Active 4,360, Inactive 483, Suspended 132, Unknown 25 |
| C5 | Inconsistent city / state labels | 103 city and 12 state spellings; 57 blank cities, 93 blank states | Correct / Flag | Mapping + `Text.Proper`; blank → null | consistent labels |
| C6 | Optional attributes missing | Gender 309, MobilityAid 376, PreferredLanguage 213, PreferredContactMethod 282, HomeAddressLine 57 | Flag | Blank tokens (`""`, `N/A`, `NULL`, `-`) → null; null → `Not Provided` | no empty strings left |
| C7 | Inconsistent capitalisation / spacing | all text columns | Correct | `Text.Trim`, `Text.Clean`, `Text.Upper` on keys | clean text |
| C8 | ZIP stored inconsistently | 132 fixable (ZIP+4, `.0`, spaces, dropped leading zero); 50 invalid or blank | Correct / Flag | Keep as **text**; strip; pad 4-digit `7xxx` to `07xxx`; validate | `HomeZipIsValid` flag; invalid → null |
| C9 | Invalid / implausible `DateOfBirth` | 50 blank, 15 unparseable text, 24 future or older than 110 | Flag | `try Date.FromText … otherwise null`; range check | 89 clients with `Age = null` → `AgeGroup = "Unknown"` |
| C10 | `RegistrationDate` earlier than `DateOfBirth` | 41 | Flag | Compare after both parsed | `RegistrationDateIsValid = false`, date set to null |
| C11 | `RegistrationDate` in the future | 20 | Flag | Compare with `pAsOfDate` | same |
| C12 | `RegistrationDate` blank / text | 40 (30 blank, 10 `not recorded`) | Flag | parse → null | `RegistrationDateIsValid = false` |
| C13 | Missing or invalid home coordinates | 126 raw rows after repair (75 blank, 10 each of `0`/`0`, lat 91.2345, `N/A`, lon −181.5, plus blanks on duplicate copies) | Flag | Numeric parse + bounding box | `HomeCoordsAreValid = false`, lat/lon null |
| C14 | Swapped latitude / longitude | 10 | Correct | If lat is in the longitude range and lon in the latitude range → swap | fixed |

**Clients — quality summary after cleaning (5,000 clients):** Valid DOB / Age available 4,911 (98.2%); valid registration date 4,900 (98.0%); valid ZIP 4,960 (99.2%); valid coordinates 4,886 (97.7%); status Unknown 25; every `ClientID` unique.

---

## 3. Issue register — `Trips`

Counts are raw-row counts (100,400 rows) unless stated.

| # | Issue | Raw count | Resolution type | Power Query treatment | Result after cleaning |
|---|---|---|---|---|---|
| T1 | Duplicate `TripID` | 400 rows (250 exact, 100 stale, 50 partial) | Remove | Status rank → completeness → first; `Table.Distinct` | 100,000 rows |
| T2 | `ClientID` needs trim / case fix | 1,500 | Correct | `Text.Trim`, `Text.Upper` | matched |
| T3 | `ClientID` blank | 191 | Flag | null | `ClientMatched = false` |
| T4 | `ClientID` not in `Clients` (orphan) | 747 | Flag (keep for operational KPIs) | Merge/RELATED check | After de-dup: 745 orphan + 189 blank = **934 unmatched trips** |
| T5 | `TripDate` blank or outside the 12-month window | 110 blank + 26 outside | Correct | Fallback: `DateTime.Date(ScheduledPickupTime)` if it falls inside the window | 135 repaired; **1 unrepairable** (excluded) |
| T6 | `BookingDate` blank / after `TripDate` | 449 / 179 | Flag | Compare dates | not used by KPIs; flagged |
| T7 | `ScheduledPickupTime` blank / malformed | 292 | Flag | `try DateTime.FromText … otherwise null` | null |
| T8 | `ScheduledDropoffTime` blank / malformed | 474 | Flag | same | null; drop-off delay unavailable |
| T9 | `PromiseTime` blank / malformed (`NULL`, `0000-00-00 00:00:00`, `25:61:00`, `2025-02-30 08:15:00`) | 999 | Exclude from OTP | same | 854 completed trips excluded from OTP |
| T10 | `ActualPickupTime` missing on **completed** trips | 1,345 (1,280 after de-dup) | Exclude from OTP | same | counted in "excluded records" |
| T11 | `ActualPickupTime` blank on cancelled / no-show / failed trips | expected | — (not a defect) | none | not an error; excluded because not completed |
| T12 | `ActualPickupTime` off by exactly ±24 h (date typo) | 123 completed rows | Exclude from OTP | `PickupDelayIsValid` (−180…+360 min) | excluded and counted |
| T13 | `ActualDropoffTime` missing/malformed on completed trips | 1,325 | Flag | parse → null | duration falls back to raw field |
| T14 | `RawTripStatus` spelled 30 ways | 30 labels | Correct | rule-based `MapStatus` | 5 clean values |
| T15 | Unresolved status (`Scheduled`, `SCHED`, `UNK`, `???`, blank) | 157 raw → 56 after de-dup | Exclude from all KPIs | `Unresolved` | `IsValidScheduledTrip = false` |
| T16 | `NoShowIndicatorRaw` blank | 24,529 | Flag | `Y/1/TRUE/Yes` → true, `N/0/FALSE/No` → false, else null | status is the source of truth |
| T17 | Indicator contradicts status | 328 | Flag | `StatusIndicatorConflict` | status wins; measures ignore the indicator |
| T18 | `RouteID` in 11 formats | 11 formats | Correct | strip spaces/hyphens, remove `ROUTE`/`RT`/`R`, convert | `RouteNumber`, `RouteID = "R-nnnn"` |
| T19 | Route outside 1000–3999 | 358 numeric out-of-range (`999`, `0`, `4050`, `5010`, `9999`) | Flag | `Mode = "Unknown"` | 571 valid trips with Mode Unknown |
| T20 | Route blank or non-numeric (`R-XX99`) | 215 | Flag | `RouteNumber = null` → `Unknown` | same |
| T21 | `RawServiceMode` disagrees with route-derived mode | 4,585 | Flag (never use raw) | derive `Mode` from route; keep normalised raw only for reconciliation | `Mode` is trusted |
| T22 | Pickup ZIP malformed | ZIP+4 1,971; padded 1,237; `.0` 844; 4-digit 253 (NJ zero loss or invalid); `00000`/`ABCDE` 168; blank 497 | Correct / Flag | strip, pad, validate | invalid or missing after cleaning: **737** |
| T23 | Drop-off ZIP malformed | ZIP+4 1,957; padded 1,268; `.0` 807; 4-digit 591; invalid 178; blank 497 | Correct / Flag | same | invalid or missing: **727** |
| T24 | Pickup coordinates invalid or missing | blank 1,186; `0`; `N/A` 204; lat > 90; lon < −180 | Flag | numeric + bounding box | invalid/missing after repair: **1,759** |
| T25 | Drop-off coordinates invalid or missing | similar | Flag | same | **1,850** |
| T26 | Latitude/longitude swapped | pickup 278; drop-off 251 | Correct | swap if clearly reversed | fixed |
| T27 | Coordinates in plausible range but ~25 km from their ZIP | ~0.3% of each pair | Not detectable by range check | optional: compare with ZIP median | shows why validation ≠ proof |
| T28 | Fare negative | 244 | Flag / exclude from revenue | parse; valid range 0–150 | `FareIsValid = false` |
| T29 | Fare 999.99 | 52 | Flag / exclude | same | same |
| T30 | Fare `N/A` or blank on completed trips | 1,129 | Flag / exclude | same | same |
| T31 | Positive fare on cancelled / no-show / failed trips | 54 | Exclude from revenue | revenue counts completed trips only | `EligibleFare = 0` |
| T32 | Refund greater than fare (or refund with unusable fare) | 527 | Exclude refund | `RefundIsValid` requires valid fare and refund ≤ fare | refund not subtracted; never silently capped |
| T33 | Distance text / invalid | text suffix 25,091; blank/`N/A` 1,448; zero/negative/`999` 592 | Correct / Flag | strip `mi`/`miles`, parse, range 0–100 | `DistanceIsValid` |
| T34 | Duration text / invalid | `min` suffix 15,150; zero/negative/≥600/`n/a`/blank on completed 1,979 | Correct / Flag | parse; fall back to timestamp difference | `TripDurationSource` |
| T35 | `RawDelayMinutes` inconsistent signs and text | ~8% sign-flipped, 8,567 with text, blank on completed ~12% | Do not use | recompute `PickupDelayMinutes` from timestamps | reconciliation only |
| T36 | Passenger count invalid | `-1`/`15` ≈ 205; blank 516 | Flag | range 0–8 | null |
| T37 | `ServiceDayType` disagrees with `TripDate` | ~1% | Correct | recompute from `TripDate` | consistent |
| T38 | Address blank | pickup 357, drop-off 366 | Flag | trim/proper; null | hidden from report |

---

## 4. KPI-eligibility waterfall (what each KPI will see)

| Stage | Rows |
|---|---|
| Raw rows | 100,400 |
| After removing duplicate `TripID` rows | 100,000 |
| Unresolved status (excluded everywhere) | −56 |
| No usable `TripDate` | −1 |
| **Valid scheduled trips (`IsValidScheduledTrip`)** | **99,943** |
| of which Completed / No-Show / Cancelled / Failed-Other | 85,087 / 4,471 / 6,694 / 3,691 |
| No-show denominator (valid minus cancelled) | 93,249 |
| OTP candidates (completed) | 85,087 |
| Excluded — `PromiseTime` missing or invalid | −854 |
| Excluded — `ActualPickupTime` missing or invalid | −1,280 |
| Excluded — pickup delay outside −180…+360 min | −123 |
| **OTP-eligible trips** | **82,830** |
| Completed trips with unusable fare (not in revenue) | 1,419 |
| Completed trips whose refund is invalid (refund ignored) | 235 |
| Trips whose `ClientID` has no match in `Clients` | 934 (773 are completed) |

## 5. Data-quality summary by category

| Category | `Clients` | `Trips` |
|---|---|---|
| Missing values | optional attributes 57–376 per column; 89 without Age | 497 ZIPs, ~1,190 coordinates, 999 promise times, 1,345 actual pickups on completed trips |
| Duplicates | 60 rows | 400 rows |
| Invalid values | 24 impossible DOBs, 61 impossible registration dates | 244 negative fares, 52 impossible fares, 592 bad distances, 123 pickup-time date typos |
| Unmatched / orphan | — | 934 trips (0.93%) |
| Label inconsistency | 4 categorical fields with 50–114 spellings each | status 30, route 11 formats, borough, mode |

A reasonable accuracy target after cleaning is that **more than 98% of rows remain usable for every headline KPI**; this dataset meets it (99.94% of trips are valid scheduled trips; 97.3% of completed trips are OTP-eligible).
