# Power Query Tutorial (beginner-friendly, with M code)

Two ways to follow this: **(A) Learn it** by clicking each step in the Power Query Editor (recommended once), then **(B) Paste it** using the finished queries in `PowerQuery/Clients.m` and `PowerQuery/Trips.m` (Home → Advanced Editor). Both give the same result. Every step lists: table, column(s), command, expected result, why, how to validate, and whether M is faster.

> **Honesty note.** I could not run Power BI in my environment. The M files were written to implement exactly the same rules as `reference_clean.py`, which I did run against the delivered CSVs; the numbers quoted in this tutorial come from that script. Treat the first refresh as your first test: if a row count differs from the "Expected" column, use the validation tips to find the step.

---

## 0. Set-up (once)

| # | Action | Detail |
|---|---|---|
| 0.1 | Put `Clients.csv`, `Trips.csv` in one folder, e.g. `C:\Paratransit\` | Keep the trailing `\` in the parameter below |
| 0.2 | **Get Data → Blank Query → Advanced Editor** (or Home → Manage Parameters → New Parameter) | Create four parameters |
| 0.3 | Parameters | `pFolder` (Text) = `C:\Paratransit\` · `pAsOfDate` (Date) = `2026-09-30` · `pDataStart` (Date) = `2025-10-01` · `pDataEnd` (Date) = `2026-09-30` |
| 0.4 | Create query `Clients` | Blank Query → Advanced Editor → paste `Clients.m` → Done |
| 0.5 | Create query `Trips` | Same with `Trips.m` |
| 0.6 | Right-click each of the 4 parameters → untick **Enable load** | Parameters are single values, **not tables**, so the model still has exactly **two** tables |
| 0.7 | File → Options → Privacy → **Always ignore Privacy Level settings** (this local project only) | Prevents `Formula.Firewall` when `Trips` reads `Clients` |

**Why parameters?** Changing the reporting date or folder means editing one value, not hunting through code. It also documents the as-of date.

**Why not use the raw CSV `Mode`/`Age`?** They do not exist in the raw files by design; you build them.

---

## 1. `Clients` — step by step

Select query **Clients** in the Queries pane for every step.

| Step | Column(s) | Command | Expected result | Why | Validate | M faster? |
|---|---|---|---|---|---|---|
| 1.1 Import | all | Home → New Source → Text/CSV → `Clients.csv`; Transform Data | 16 columns, **5,060** rows | Start from raw | Status bar “5060 ROWS” (Column profiling: *Based on entire data set*) | M: `Csv.Document(File.Contents(pFolder & "Clients.csv"))` |
| 1.2 Promote headers | row 1 | Home → **Use First Row as Headers** | Real column names | CSV header row arrives as data | Names match the dictionary | Same step in M (`Table.PromoteHeaders`) |
| 1.3 Everything to Text first | all | Select all columns → Transform → Data Type → **Text** | No type errors | Prevents Power BI auto-typing `HomeZipCode` as number (drops leading zero in NJ ZIPs) and hiding bad dates as errors | No red “Error” cells | Yes (`Table.TransformColumnTypes` on all names) |
| 1.4 Trim and clean | all text | Select all → Transform → Format → **Trim**, then **Clean** | No leading/trailing spaces, hidden characters | `" 11373 "` ≠ `"11373"` in joins and slicers | Column quality: distinct count falls (ClientType 56 → ~9 before mapping) | M helper `CleanText` does Trim + Clean + blank-to-null in one pass |
| 1.5 Blank strings → null | all text | Select all → Transform → **Replace Values** `""` → `null`; repeat for `N/A`, `NULL`, `-` | True nulls | `""` is not null; DAX `ISBLANK`/`COUNTBLANK` would disagree | Gender empty count = **309** | M does all four tokens at once |
| 1.6 Upper-case key | `ClientID` | Transform → Format → **UPPERCASE** | `C00025` | Case-insensitive key match | Distinct count unchanged (5,000) | trivial |
| 1.7 Index (tie-breaker) | new `RowIdx` | Add Column → **Index Column** from 0 | 0…5059 | Remembers file order for stable de-dup | First value 0 | Yes |
| 1.8 Completeness score | new `CompletenessScore` | Add Column → **Custom Column**: `List.NonNullCount(Record.FieldValues(Record.SelectFields(_, AttrCols)))` | Higher = more filled-in fields | Pick the *best* duplicate, not an arbitrary one | A duplicate pair shows different scores | M only (no UI equivalent) |
| 1.9 Resolve duplicate ClientIDs | `ClientID`, score, index | Home → **Sort** `ClientID` asc, `CompletenessScore` desc, `RowIdx` asc → wrap in **Table.Buffer** → Home → **Remove Rows → Remove Duplicates** on `ClientID` only | **5,000** rows | Duplicate keys break the one-to-many relationship. **Remove Duplicates keeps the first row it sees — so sort first** and buffer so the sort order is respected | `Table.RowCount` = 5,000; Column profile: *Distinct* = *Unique* | Buffer is M-only. Check `C00025`: kept row has ZIP and coordinates, the discarded copy had none |
| 1.10 Source row count | `SourceRowCount` | Group By on `ClientID` (count rows) then merge back | 1 or 2 | Audit trail of how many raw rows each client had | `SourceRowCount = 2` for 60 clients | M |
| 1.11 Standardise categories | `ClientType`, `EligibilityCategory`, `ClientStatus`, `Gender`, `MobilityAid`, `PreferredLanguage`, `PreferredContactMethod`, `HomeCity`, `HomeState` | Add Column → **Conditional Column** (UI), or Custom Column with `Text.Contains(Text.Lower([col]), "...")` | `ClientType`: ADA Paratransit 3,734 / Medicaid 621 / Senior Program 432 / Visitor 213 | One label per concept | Column distribution shows only the clean labels; no “Unknown” beyond the 25 odd statuses | M mapping functions `Map…` handle 9 columns in one `Table.TransformColumns` |
| 1.12 ZIP as text | `HomeZipCode` | Keep type **Text**. Steps: Trim; remove trailing `.0` (Replace Values); keep first 5 chars of `ZIP+4` (Transform → Extract → **First Characters** 5 when length 10); pad 4-digit `7xxx` with `0` (Format → *Add Prefix*, conditional) | `10001`, `07030` | ZIPs are labels not numbers; Excel/BI converts `07030` → `7030` | Valid ZIP count **4,960** of 5,000; text length is 5 for all non-null | M `CleanZip` (returns ZIP and a validity flag) |
| 1.13 Coordinates | `HomeLatitude`, `HomeLongitude` | Transform → Data Type → **Decimal Number**, with *Replace Errors* → null; then Custom Column validity test: lat 40.45–41.05 and lon −74.30 – −73.50 | Numeric or null | Range test (“coordinate validation”) catches `0`, `91.2345`, `-181.5`, `N/A` | Valid coordinates **4,886** | M `CleanCoords` also swaps reversed lat/lon (10 rows) |
| 1.14 Dates | `DateOfBirth`, `RegistrationDate` | Add Column → Custom: `try Date.FromText([DateOfBirth], [Format="yyyy-MM-dd"]) otherwise null` | Date or null (no errors) | `Change Type` would turn bad strings into **errors**, breaking the load; `try … otherwise` turns them into null | No error cells; DOB null count: 65 raw (blank+unparseable) | M (`try/otherwise` is M-only) |
| 1.15 Validate DOB | `DateOfBirthIsValid` | Custom: parsed ≤ `pAsOfDate` and 0 ≤ Age ≤ 110 | **4,911** TRUE, 89 FALSE | Future dates (2031), 1850, `0000-00-00` are impossible | Filter FALSE: all are blank/odd | M |
| 1.16 Validate registration | `RegistrationDateIsValid` | Custom: parsed, ≤ `pAsOfDate`, and not earlier than a valid DOB | **4,900** TRUE | Registration before birth is impossible | Filter FALSE: includes 41 before-DOB + 20 future + 40 missing (before dedup) | M |
| 1.17 **Age** | `Age` | Add Column → Custom Column (formula below) | Whole years; null if DOB invalid | Age must be correct on the as-of date | Examples below | M only |
| 1.18 **AgeGroup** | `AgeGroup`, `AgeGroupSort` | Add Column → **Conditional Column**: Age < 18 → “Under 18”; ≤ 24 → “18-24”; ≤ 44 → “25-44”; ≤ 64 → “45-64”; else “65+”; add rule *Age is null → “Unknown”* **first** | 65+ 2,786 · 45-64 1,161 · 25-44 613 · 18-24 214 · Under 18 137 · Unknown 89 | Segmentation slicer; the sort column makes bars order logically | Counts above (they sum to 5,000) | Conditional Column UI is fine here |
| 1.19 Quality flags | `DataQualityFlags` | Custom Column concatenating problems | Text or null | Lets analysts filter bad records | Filter non-null count | M |
| 1.20 Keep columns / types | final | Home → Choose Columns; set types | **25 columns**, 5,000 rows | Hide raw junk | Columns match dictionary | M |

### Age formula (exact)

```m
AgeAsOf = (dob as date, asOf as date) as number =>
    Date.Year(asOf) - Date.Year(dob)
    - (if Date.Month(asOf) * 100 + Date.Day(asOf) < Date.Month(dob) * 100 + Date.Day(dob) then 1 else 0)
```

UI-only version (Custom Column): 

```m
Date.Year(pAsOfDate) - Date.Year([DobParsed])
 - (if (Date.Month(pAsOfDate)*100 + Date.Day(pAsOfDate)) < (Date.Month([DobParsed])*100 + Date.Day([DobParsed])) then 1 else 0)
```

The `MMDD` comparison asks “has the birthday already happened by the as-of date?” Subtracting years alone overstates age for everyone whose birthday is later in the year.

| ClientID | DateOfBirth | As-of | Naïve year subtraction | Correct Age | Why |
|---|---|---|---|---|---|
| C00025 | 1959-09-30 | 2026-09-30 | 67 | **67** | Birthday is the as-of day → already 67 |
| C00027 | 1937-10-02 | 2026-09-30 | 89 | **88** | Birthday two days later |
| C00180 | 1999-10-02 | 2026-09-30 | 27 | **26** | Same |
| C03004 | 1976-03-25 | 2026-09-30 | 50 | **50** | Birthday passed |

### Current age vs age at trip date
- **Current age (core model):** age on the documented reporting date `pAsOfDate` (2026-09-30). Every client has one value, so segments are stable and slicers are simple. Stored in the dimension because it is a *client attribute*.
- **Age at trip:** age on each `TripDate`. A client who is 17 in November 2025 may be 18 by the as-of date. It is a *fact-level* attribute. Optional DAX calculated column on `Trips`: `AgeAtTrip = VAR dob = RELATED(Clients[DateOfBirth]) VAR d = Trips[TripDate] RETURN IF(ISBLANK(dob) || ISBLANK(d), BLANK(), YEAR(d) - YEAR(dob) - IF(MONTH(d)*100+DAY(d) < MONTH(dob)*100+DAY(dob), 1, 0))`. It adds a 100,000-row column; use only for the historical-analysis experiment.

### Why Age/AgeGroup are in Power Query but KPIs are measures
Age is a **row-level attribute** with one correct value per client regardless of filters; computing it once at refresh is cheap and lets you use it as a slicer axis. A KPI (e.g. no-show rate) is an **aggregate whose denominator changes with filters**; if you froze it in a column it would be wrong the moment someone slices by mode.

---

## 2. `Trips` — step by step

| Step | Column(s) | Command | Expected | Why | Validate | M faster? |
|---|---|---|---|---|---|---|
| 2.1 Import, headers, all-Text, Trim/Clean, blanks → null | all 43 | Same as Clients 1.1–1.5 | **100,400** rows | As above | Blank counts match the report | M helper |
| 2.2 Standard column names | various | Right-click header → Rename (or `Table.RenameColumns`) | `RawFareAmount` → `FareAmount`; `RawTripStatus` kept until `TripStatus` is built; `RawServiceMode` → `RawServiceModeNorm` | Consistent names across PQ, DAX and visuals | Names equal the dictionary | M |
| 2.3 Parse timestamps | 7 timestamp columns | Custom/`Table.TransformColumns` with `try DateTime.FromText(...) otherwise null` | Valid datetime or null | Avoid errors for `NULL`, `25:61:00`, `2025-02-30 08:15:00` | `PromiseTime` null count raw = **999** | M |
| 2.4 **TripStatus** | `RawTripStatus` | Conditional Column on `Text.Lower`: starts with “comp” / “cmpltd” → Completed; contains “canc” or “cxl” → Cancelled; “ns” or contains “show” → No-Show; contains “miss/brkdwn/breakdown/incomplete/fail” → Failed/Other; else Unresolved | Completed 85,087 · Cancelled 6,694 · No-Show 4,471 · Failed/Other 3,691 (valid, after dedup) | 30 raw labels → 5 | Group By `RawTripStatus` → `TripStatus`: no raw label maps to two statuses | M `MapStatus` |
| 2.5 Duplicate `TripID` | `TripID` | Index; add `StatusRank` (resolved = 1, Unresolved = 0) and `CompletenessScore`; Sort by `TripID`, StatusRank ↓, Score ↓, Index ↑; **Table.Buffer**; Remove Duplicates on `TripID` | **100,000** rows | Exact dupes (250) are identical; conflicting copies (150) are stale “Scheduled” rows or rows missing actual times — keeping the *wrong* copy would lose a completed trip | Distinct = Unique. Trip `T0000753` keeps the completed record, not its “Scheduled” copy | M |
| 2.6 Clean ClientID | `ClientID` | Upper-case (Trim done) | `C00025` | Case/space mismatches (1,500 rows) | After fix, unmatched 934 | trivial |
| 2.7 Referential flag | `ClientMatched` | Custom: `List.Contains(ClientList, [ClientID])` where `ClientList = List.Buffer(Clients[ClientID])` | TRUE for 99,066; **FALSE 934** (745 not in Clients + 189 blank) | Keep orphan trips for operational KPIs but exclude them from client analytics | Filter FALSE and look at IDs like `C05221` | M only. (UI alternative: Merge Queries, Left Outer, expand one column, test null.) |
| 2.8 TripDate repair | `TripDate` | Parse; if blank or outside window, fall back to `DateTime.Date([ScheduledPickupTime])` if that is in window | 135 repaired, **1** unrepairable | A blank `TripDate` would hide a real trip from time charts | `TripDateWasRepaired` = TRUE count 135 | M |
| 2.9 RouteID cleaning | `RouteID` | Transform → Format → Trim; Replace Values: `-`→``, ` `→``; Extract/Replace prefix `ROUTE`, `RT`, `R` (longest first); Change type Whole Number | `RouteNumber` e.g. 1215 | Seven formats of the same route (`R-1050`, `1050`, `r 2050`, `Route 3050`, ` R-1050 `, `R1050`, `RT-1050`) | Distinct RouteNumber = **59** (including odd ones) | M `RouteNumberOf` |
| 2.10 **Mode** (UI) | `RouteNumber` | Add Column → **Conditional Column** → New column `Mode`: *If* `RouteNumber` *is greater than or equal to* 1000 **and**… the dialog allows **one** condition per clause, so use nested clauses: *If RouteNumber is less than 1000 then “Unknown”; else if less than 2000 then “Primary”; else if less than 3000 then “Broker”; else if less than 4000 then “Supplemental”; else “Unknown”*; add a first clause *If RouteNumber equals null then “Unknown”* | Primary / Broker / Supplemental / Unknown | Ordered `less than` clauses avoid needing AND in the dialog | Group By `Mode`: Primary 56,033 · Broker 33,516 · Supplemental 9,823 · Unknown 571 (valid trips) | — |
| 2.10b **Mode** (M, preferred) | same | Add Column → Custom Column | same | One readable rule table | Same counts | Yes |
| 2.11 RouteID label | `RouteID` | `"R-" & Text.From([RouteNumber])` | `R-1215` | One canonical label for visuals | No leading spaces | M |
| 2.12 ZIPs | `PickupZipCode`, `DropoffZipCode` | Text type; same ZIP rules as Clients | 5-char text, `07030` kept | Leading zeros, ZIP+4, `.0`, spaces | Invalid/missing after clean: pickup **737**, drop-off **727** (raw rows) | M `CleanZip` |
| 2.13 Coordinates | 4 columns | Decimal; validity flags; swap fix | Numeric or null | See Clients 1.13 | Invalid/missing pickup **1,759**, drop-off **1,850** (raw rows) | M `CleanCoords` |
| 2.14 Fare / refund | `RawFareAmount`, `RawRefundAmount` | Replace `$`, `,` → Decimal; `FareIsValid` = 0 ≤ fare ≤ 150; `RefundIsValid` = fare valid and 0 ≤ refund ≤ fare; `EligibleFare`, `EligibleRefund` (Completed only) | Gross eligible fare **$990,020.22**; refunds **$21,621.00**; net **$968,399.22** | Negative fares (244), 999.99 (52), refund > fare (527 raw) must not inflate revenue; refunds on unusable fares are ignored, never silently capped | Total EligibleFare before/after | M |
| 2.15 Distance / duration | `RawDistanceMiles`, `RawTripDuration` | Replace `mi`, `miles`, `min`; Decimal; validity 0 < x ≤ 100 miles / ≤ 240 min; duration falls back to `ActualDropoffTime − ActualPickupTime` | Avg distance **10.30 mi**, avg duration **56.96 min** (completed, valid rows) | Text units and impossible values | `TripDurationSource` counts | M |
| 2.16 **PickupDelayMinutes** | new | Add Column → Custom: `Duration.TotalMinutes([ActualPickupTime] - [PromiseTime])` (null if either null) | −35…+240 typical | Full timestamps handle midnight and cross-date correctly | `T0000295`: promise 2025-10-01 23:30, actual 2025-10-02 00:42 → **72**; `T0000297`: promise 00:10 on 10-02, actual 23:57 on 10-01 → **−13** | Use M; UI “Subtract” on two datetimes gives a Duration you must then convert |
| 2.17 Delay validity | `PickupDelayIsValid` | Custom: between −180 and +360 | 123 completed trips are ±24h typos | A date typo creates −1,450 or +1,439-minute “delays” that would wreck averages | `T0000343` (−1450) and `T0002686` (+1439) are FALSE | M |
| 2.18 OTP eligibility | `OTPEligibility`, `IsPickupOTPEligible` | Custom ordered rules: not Completed → “Not a completed trip”; missing Promise; missing ActualPickup; delay invalid; else Eligible | Eligible **82,830**; excl. not completed 14,856 · missing Promise 854 · missing ActualPickup 1,280 · out of range 123 | Reports excluded counts as required | Sum = 99,943 valid trips | M |
| 2.19 Drop-off delay | `DropoffDelayMinutes` | Completed only: `ActualDropoffTime − ScheduledDropoffTime` | decimal | Separate drop-off performance | Null when either is null | M |
| 2.20 Calendar attributes | `DayOfWeekNumber/Name`, `IsWeekend`, `PickupHour`, `TimePeriod`, `MonthStart` | Add Column → Date → Day → *Name of Day*; or `Date.DayOfWeek(date, Day.Monday)+1` | Mon=1 … Sun=7 | Needed by Day-of-week/hour visuals; no Date table required | Counts per weekday | M |
| 2.21 Peak/off-peak | `TimePeriod` | Conditional: weekday and hour 6–9 or 15–18 → Peak | Peak vs Off-Peak | Rule documented as fictional | Peak OTP 15-min ≈ 82.6% vs 85.6% | M |
| 2.22 Reasons | `OutcomeReason` | Mapping on `CancellationReason`; blank on non-completed → “Not Recorded”; ignore on completed | 15 reasons + Not Recorded | 196 raw spellings | Distinct ≤ 16 | M |
| 2.23 No-show indicator | `NoShowIndicator`, `StatusIndicatorConflict` | Y/1/TRUE/Yes → true; N/0/FALSE/No → false; else null | 328 conflicts | **Status is the source of truth**; the indicator is only a cross-check | Filter conflict = TRUE | M |
| 2.24 Validity & anomaly flags | `IsValidScheduledTrip`, `ServiceOutcome`, `AnomalyFlags` | Custom | **99,943** valid | Single switch used by every DAX measure | Count TRUE | M |
| 2.25 Final shape | — | Choose Columns; set types; **Close & Apply** | `Trips` ≈ 70 columns, 100,000 rows; `Clients` 25 columns, 5,000 rows | Hide helper columns later in Model view | Row counts | — |

### Which work goes where
| Work | Power Query | DAX | Reason |
|---|---|---|---|
| Parsing, trimming, mapping, de-duplication | ✔ | | Done once at refresh; cleans the stored data |
| Age, AgeGroup, Mode, RouteNumber | ✔ | | Row-level attributes, same answer in every filter |
| PickupDelayMinutes, eligibility flags | ✔ | | One value per trip |
| OTP %, No-show rate, revenue, counts, medians | | ✔ | Aggregates must react to slicers; denominators change |
| Month-over-month, rolling windows | | ✔ | Depend on the filter context |

### Query dependency check
`Clients` loads first; `Trips` reads it for `ClientMatched`. **Close & Apply** loads exactly two tables.
