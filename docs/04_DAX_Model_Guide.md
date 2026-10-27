# Data Model and DAX Library

Tables: `Clients` (5,000 rows) and `Trips` (100,000 rows). Column names below are the **final** names produced by `Clients.m` / `Trips.m`.

## 1. Relationship

| Setting | Value |
|---|---|
| From → To | `Clients[ClientID]` (one, `1`) → `Trips[ClientID]` (many, `*`) |
| Cross-filter direction | **Single** (Clients filters Trips) |
| Active | Yes |

**Create it:** Model view → drag `Clients[ClientID]` onto `Trips[ClientID]` → check *Many to one (*:1)*, *Single* → OK.

**What the unmatched trips do.** 934 trips have a blank or unknown `ClientID`. Power BI keeps them (they sit under a *(Blank)* member of any `Clients` field). They count in trip-level KPIs (volume, OTP, no-shows, mode, route) but fall into *(Blank)* in client-segment visuals. Client-based measures below explicitly require `Trips[ClientMatched]`.

### Relationship checks (run once, as DAX queries or cards)
```DAX
Dup Client Keys = COUNTROWS(Clients) - DISTINCTCOUNT(Clients[ClientID])          -- must be 0
Dup Trip Keys   = COUNTROWS(Trips)   - DISTINCTCOUNT(Trips[TripID])              -- must be 0
Unmatched Trips = CALCULATE(COUNTROWS(Trips), Trips[ClientMatched] = FALSE())    -- expect 934
Clients Without Trips = COUNTROWS(FILTER(Clients, ISBLANK(CALCULATE(COUNTROWS(Trips)))))   -- clients with no trip rows
```
**Avoid duplicated trips / double counting revenue:** (1) `TripID` is unique after Power Query; (2) revenue measures sum `EligibleFare`, which is already zero for non-completed trips; (3) never SUM a fare on the `Clients` side; (4) a return leg is a separate trip with its own fare, not a duplicate (it shares `BookingID`).

**Test client segmentation:** put `Clients[AgeGroup]` on rows and `[Completed Trips]` as values. The total plus the *(Blank)* row must equal the unsegmented total (85,087). Repeat for `EligibilityCategory`, `ClientType`, `MobilityAid`.

### Model hygiene
- Hide `Trips[ClientID]` (use the `Clients` copy in visuals) and helper columns (`FareAmount`, `RefundAmount`, `RawServiceModeNorm`, `*IsValid`).
- Hide `Clients[HomeAddressLine]`, `HomeLatitude`, `HomeLongitude`, `Trips[PickupAddress]`, `DropoffAddress` from Report view (privacy).
- Set **Sort by column**: `Clients[AgeGroup]` by `AgeGroupSort`; `Trips[DayOfWeekName]` by `DayOfWeekNumber`; `Trips[PickupDelayBand]` by `PickupDelayBandSort`; `Trips[MonthLabel]` is `yyyy-MM` so it sorts naturally.
- Data categories: `PickupZipCode`, `DropoffZipCode`, `HomeZipCode` → **Postal Code**; lat/lon columns → **Decimal Number**, categories *Latitude* / *Longitude*.
- Create a `_Measures` display folder per section using *Display folder*.

---

## 2. Conventions used in every measure

- **Valid scheduled trip** = `Trips[IsValidScheduledTrip] = TRUE` (de-duplicated, has a trip date, resolved status).
- **OTP-eligible** = `Trips[IsPickupOTPEligible] = TRUE`.
- Measures are in the table `Trips`; helper/parameter measures in a display folder “Parameters”.
- `DIVIDE(num, den)` returns BLANK on a zero denominator, so visuals stay empty rather than erroring.

---

## 3. Trip volume

| Measure | DAX | Definition / denominator | Format | Visual |
|---|---|---|---|---|
| **Total Scheduled Trips** | `CALCULATE(COUNTROWS(Trips), Trips[IsValidScheduledTrip] = TRUE())` | Every valid de-duplicated scheduled trip record, whatever its outcome | `#,0` | Card |
| **Completed Trips** | `CALCULATE([Total Scheduled Trips], Trips[TripStatus] = "Completed")` | Trips served | `#,0` | Card, line |
| **No-Show Trips** | `CALCULATE([Total Scheduled Trips], Trips[TripStatus] = "No-Show")` | Passenger not found at pickup (operational no-show) | `#,0` | Card |
| **Cancelled Trips** | `CALCULATE([Total Scheduled Trips], Trips[TripStatus] = "Cancelled")` | Cancelled by client/agency before service | `#,0` | Card |
| **Other Failed Trips** | `CALCULATE([Total Scheduled Trips], Trips[TripStatus] = "Failed/Other")` | Service failure (missed trip, breakdown, unable to locate) | `#,0` | Card |
| **Eligible Scheduled Trips** | `[Total Scheduled Trips] - [Cancelled Trips]` | **No-show denominator**: scheduled minus cancelled | `#,0` | Hidden helper |
| **Completed Trip Rate** | `DIVIDE([Completed Trips], [Total Scheduled Trips])` | Completed ÷ all scheduled | `0.0%` | Card |
| **No-Show Rate %** | `DIVIDE([No-Show Trips], [Eligible Scheduled Trips])` | Fraction (0.048 = 4.8%) | `0.0%` | Card, bar |
| **No-Shows per 100 Trips** | `DIVIDE([No-Show Trips], [Eligible Scheduled Trips]) * 100` | Same denominator, expressed per 100 | `0.00` (label “per 100 trips”) | Card, line |
| **Cancellations per 100 Trips** | `DIVIDE([Cancelled Trips], [Total Scheduled Trips]) * 100` | Cancellations are *in* the denominator, because the question is “how many scheduled trips got cancelled” | `0.00` | Card |
| **Unique Clients Served** | `CALCULATE(DISTINCTCOUNT(Trips[ClientID]), Trips[TripStatus] = "Completed", Trips[IsValidScheduledTrip] = TRUE(), Trips[ClientMatched] = TRUE())` | Distinct matched clients with ≥1 completed trip | `#,0` | Card |
| **Trips per Client Served** | `DIVIDE(CALCULATE([Completed Trips], Trips[ClientMatched] = TRUE()), [Unique Clients Served])` | Completed trips of matched clients ÷ distinct matched clients | `0.0` | Card |
| **Average Daily Completed Trips** | `DIVIDE([Completed Trips], DISTINCTCOUNTNOBLANK(Trips[TripDate]))` | Completed ÷ number of service days in the current filter | `#,0.0` | Card |

**Label rule — three different things:** *No-Show Trips* is a **count**; *No-Show Rate %* is a **percentage** (4.8%); *No-Shows per 100 Trips* is a **rate per 100** (4.80). They use the same denominator, so per-100 = percentage × 100 numerically. Only the unit and label differ. Use per-100 on the executive page, percentage in tooltips, never mix them on one axis.

**Why a measure, not a Power Query column?** A column stores one fixed answer per row. A rate is a ratio of two counts, and *both* change with filters (mode, borough, month, client segment). A column cannot recompute its denominator; a measure re-evaluates in the current filter context. (Averaging per-row 0/1 flags would also give the wrong number whenever the denominator excludes rows.)

**Expected full-dataset results (no filters):** Total Scheduled Trips **99,943** · Completed **85,087** · No-Show **4,471** · Cancelled **6,694** · Other Failed **3,691** · Eligible Scheduled **93,249** · No-Shows per 100 **4.80** (4.795) · Cancellations per 100 **6.70** · Completed Trip Rate **85.1%**.

---

## 4. Pickup on-time performance (OTP)

`PickupDelayMinutes = ActualPickupTime − PromiseTime` is a **calculated column** (Power Query), one value per trip. The KPIs below are **measures** that aggregate it and react to filters.

| Measure | DAX | Denominator / rule | Format |
|---|---|---|---|
| **Eligible Pickup Trips** | `CALCULATE(COUNTROWS(Trips), Trips[IsPickupOTPEligible] = TRUE(), Trips[IsValidScheduledTrip] = TRUE())` | Completed, valid Promise & ActualPickup, delay in −180…+360 | `#,0` |
| **On-Time Pickup Trips — 15 Minutes** | `CALCULATE([Eligible Pickup Trips], Trips[PickupDelayMinutes] <= 15)` | delay ≤ 15 (early counts as on time) | `#,0` |
| **On-Time Pickup Trips — 20 Minutes** | `CALCULATE([Eligible Pickup Trips], Trips[PickupDelayMinutes] <= 20)` | delay ≤ 20 | `#,0` |
| **Pickup OTP % — 15 Minutes** | `DIVIDE([On-Time Pickup Trips — 15 Minutes], [Eligible Pickup Trips])` | eligible | `0.0%` |
| **Pickup OTP % — 20 Minutes** | `DIVIDE([On-Time Pickup Trips — 20 Minutes], [Eligible Pickup Trips])` | eligible | `0.0%` |
| **Late Pickup Trips — 15 Minutes** | `[Eligible Pickup Trips] - [On-Time Pickup Trips — 15 Minutes]` | delay > 15 | `#,0` |
| **Late Pickup Trips — 20 Minutes** | `[Eligible Pickup Trips] - [On-Time Pickup Trips — 20 Minutes]` | delay > 20 | `#,0` |
| **Average Pickup Delay Minutes** | `CALCULATE(AVERAGE(Trips[PickupDelayMinutes]), Trips[IsPickupOTPEligible] = TRUE(), Trips[IsValidScheduledTrip] = TRUE())` | mean (negative = early) | `0.0" min"` |
| **Median Pickup Delay Minutes** | `CALCULATE(MEDIAN(Trips[PickupDelayMinutes]), Trips[IsPickupOTPEligible] = TRUE(), Trips[IsValidScheduledTrip] = TRUE())` | median is robust to the long tail of very late pickups | `0.0" min"` |
| **Completed Trips Excluded from OTP** | `[Completed Trips] - [Eligible Pickup Trips]` | transparency measure | `#,0` |
| **Excluded — Missing PromiseTime** | `CALCULATE([Completed Trips], Trips[OTPEligibility] = "Missing/invalid PromiseTime")` | | `#,0` |
| **Excluded — Missing ActualPickupTime** | `CALCULATE([Completed Trips], Trips[OTPEligibility] = "Missing/invalid ActualPickupTime")` | | `#,0` |
| **Excluded — Delay Out of Range** | `CALCULATE([Completed Trips], Trips[OTPEligibility] = "Pickup delay out of valid range")` | | `#,0` |
| **OTP Coverage %** | `DIVIDE([Eligible Pickup Trips], [Completed Trips])` | share of completed trips that could be measured | `0.0%` |

**Cancelled and no-show trips** are excluded automatically because `IsPickupOTPEligible` is false unless `TripStatus = "Completed"`.

**Why “≤ 15” and not “< 15”?** The rule is “no later than 15 minutes after PromiseTime”: a pickup exactly 15 min late is on time (`T0000326`: promise 07:30, actual 07:45 = 15 → on time; `T0000022`: 16 → late).

**Breakdowns (no new measures needed).** Drag the base measures into visuals with the field on the axis; filter context supplies the slice. “Pickup OTP by Mode / Route / Borough / ZIP / Day of Week / Hour” = `[Pickup OTP % — 15 Minutes]` with `Trips[Mode]` / `Trips[RouteID]` / `Trips[Borough]` / `Trips[PickupZipCode]` / `Trips[DayOfWeekName]` / `Trips[PickupHour]` on the axis. Because all measures use `CALCULATE` filters on columns of `Trips`, they respect every slicer and cross-filter (they never use `ALL`).

**Expected (no filters):** Eligible **82,830** · On-time 15 **69,818** · On-time 20 **73,090** · OTP 15 **84.3%** · OTP 20 **88.2%** · Avg delay **+2.97** min · Median **−1.0** min · Excluded **2,257** (854 + 1,280 + 123).

**Row-level calculated column vs aggregated measure.**

| | Calculated column (Power Query) | Measure (DAX) |
|---|---|---|
| Evaluated | Once per row at refresh | Every time a visual renders |
| Stored | Yes, uses memory | No |
| Context | The row | The filter context (slicers, axes, cross-filter) |
| Example | `PickupDelayMinutes` | `Pickup OTP % — 15 Minutes` |

---

## 5. Fare and financial analytics

**Revenue rules (documented):**
1. Revenue counts **completed** trips only. Cancelled, no-show and failed trips earn $0 even if the raw file shows a fare (54 such rows).
2. A completed trip contributes its fare only if `FareIsValid` (0 ≤ fare ≤ 150). Negative, 999.99, `N/A` and blank fares contribute $0 (1,419 completed trips) — they are **not** imputed.
3. A refund is subtracted only if `RefundIsValid` (fare valid and 0 ≤ refund ≤ fare). Invalid refunds (235 completed trips) are ignored, not capped. Net revenue can never be negative on a trip.
4. Currency is fictional dollars; the fare formula is a project rule.

| Measure | DAX | Format |
|---|---|---|
| **Gross Eligible Fare Revenue** | `CALCULATE(SUM(Trips[EligibleFare]), Trips[IsValidScheduledTrip] = TRUE())` | `$#,0` |
| **Total Refund Amount** | `CALCULATE(SUM(Trips[EligibleRefund]), Trips[IsValidScheduledTrip] = TRUE())` | `$#,0` |
| **Net Fare Revenue** | `[Gross Eligible Fare Revenue] - [Total Refund Amount]` | `$#,0` |
| **Completed Trips With Valid Fare** | `CALCULATE([Completed Trips], Trips[FareIsValid] = TRUE())` | `#,0` |
| **Average Fare per Completed Trip** | `DIVIDE([Gross Eligible Fare Revenue], [Completed Trips With Valid Fare])` | `$0.00` |
| **Net Revenue per Client Served** | `DIVIDE(CALCULATE([Net Fare Revenue], Trips[ClientMatched] = TRUE()), [Unique Clients Served])` | `$#,0.00` |
| **Revenue by Mode / Route / Borough / Pickup ZIP / Client Age Group** | `[Net Fare Revenue]` with `Trips[Mode]`, `Trips[RouteID]`, `Trips[Borough]`, `Trips[PickupZipCode]`, `Clients[AgeGroup]` on the axis | `$#,0` |
| **Previous Month Net Fare Revenue** | see §9 | `$#,0` |
| **Month-over-Month Revenue Growth %** | see §9 | `+0.0%;-0.0%` |

Why the denominator for the average fare is “completed with *valid* fare”: dividing by all completed trips would mix real $0 fares with unusable ones and understate the average.

**Expected:** Gross **$990,020** · Refunds **$21,621** · Net **$968,399** · Avg fare **$11.83** · Net by mode: Primary **$533,959** · Broker **$309,962** · Supplemental **$118,904** · Unknown **$5,575**. By age group the net revenue for matched clients is 65+ $521,080 · 45-64 $230,731 · 25-44 $114,172 · 18-24 $47,555 · Under 18 $31,157 · Unknown $14,954 · (Blank/unmatched) $8,751.

---

## 6. Service performance (additional)

| Measure | DAX | Format |
|---|---|---|
| **Average Trip Duration** | `CALCULATE(AVERAGE(Trips[TripDurationMinutes]), Trips[TripStatus] = "Completed", Trips[IsValidScheduledTrip] = TRUE())` | `0.0" min"` |
| **Average Trip Distance** | `CALCULATE(AVERAGE(Trips[DistanceMiles]), Trips[TripStatus] = "Completed", Trips[IsValidScheduledTrip] = TRUE())` | `0.0" mi"` |
| **Average Transfers per Trip** | *Not available – no transfer data exists in this dataset.* | – |
| **Late > 45 Min Trips** | `CALCULATE([Eligible Pickup Trips], Trips[PickupDelayMinutes] > 45)` | `#,0` |
| **Avg Drop-off Delay** | `CALCULATE(AVERAGE(Trips[DropoffDelayMinutes]), Trips[TripStatus]="Completed", Trips[IsValidScheduledTrip]=TRUE())` | `0.0" min"` |

Blank distances/durations are ignored by `AVERAGE`; expect **10.3 mi** and **57.0 min**.

---

## 7. Client analytics

| Measure | DAX | Definition | Format |
|---|---|---|---|
| **Total Valid Clients** | `DISTINCTCOUNT(Clients[ClientID])` | De-duplicated clients in the current `Clients` filter (**5,000** unfiltered) | `#,0` |
| **Active Client Rate** | `DIVIDE([Unique Clients Served], [Total Valid Clients])` | Active = ≥1 completed trip in the selected period. **Expect 83.7%** (4,183 ÷ 5,000) | `0.0%` |
| **Average Trips per Client Served** | `[Trips per Client Served]` | | `0.0` (expect 20.2) |
| **High-Frequency Threshold** | `20` (a measure, so it needs no extra table) | Completed trips in the selected period | `0` |
| **High-Frequency Client Count** | `COUNTROWS(FILTER(VALUES(Clients[ClientID]), CALCULATE([Completed Trips], Trips[ClientMatched] = TRUE()) >= [High-Frequency Threshold]))` | Clients meeting the threshold *in the current filter context* (expect **1,154** over 12 months) | `#,0` |
| **High-Frequency Client Share** | `DIVIDE([High-Frequency Client Count], [Unique Clients Served])` | | `0.0%` |
| **Trips by Age Group / Eligibility / Mobility Aid / Home ZIP / Client Type** | `[Completed Trips]` with `Clients[AgeGroup]`, `Clients[EligibilityCategory]`, `Clients[MobilityAid]`, `Clients[HomeZipCode]`, `Clients[ClientType]` on the axis | Trips arrive through the relationship | `#,0` |
| **Client Utilization by Mode** | `DIVIDE([Completed Trips], [Unique Clients Served])` with `Trips[Mode]` on the axis | Completed trips per client who rode *that mode* | `0.0` |

**Filter-direction note.** `Clients` filters `Trips`, not the reverse. A slicer on `Trips[Mode]` therefore does **not** reduce `Total Valid Clients` (still 5,000) but does reduce `Unique Clients Served`. This is why *Active Client Rate* falls when you filter to one mode: it then means “share of all clients who used this mode”. Use client slicers (age, eligibility) for segment rates.

---

## 8. Geographic analytics

| Measure | DAX | Notes |
|---|---|---|
| **Pickup Trips** | `[Total Scheduled Trips]` with `Trips[PickupZipCode]` on the axis | pickups are *scheduled trip records* by ZIP |
| **Drop-off Trips** | `[Total Scheduled Trips]` with `Trips[DropoffZipCode]` on the axis | |
| **Unique Pickup ZIP Codes** | `CALCULATE(DISTINCTCOUNTNOBLANK(Trips[PickupZipCode]), Trips[IsValidScheduledTrip] = TRUE())` | `DISTINCTCOUNT` would count blank as a value |
| **Unique Drop-off ZIP Codes** | `CALCULATE(DISTINCTCOUNTNOBLANK(Trips[DropoffZipCode]), Trips[IsValidScheduledTrip] = TRUE())` | 41 each among completed trips |
| **No-Shows by Pickup ZIP / No-Show Rate by Pickup ZIP** | `[No-Show Trips]` / `[No-Show Rate %]` with `Trips[PickupZipCode]` on the axis | |
| **OTP by Pickup ZIP** | `[Pickup OTP % — 15 Minutes]` with `Trips[PickupZipCode]` | |
| **OTP by Mode and Borough** | matrix: rows `Trips[Borough]`, columns `Trips[Mode]`, values `[Pickup OTP % — 15 Minutes]` | |
| **Trips between Pickup and Drop-off ZIP Codes** | matrix: rows `PickupZipCode`, columns `DropoffZipCode`, values `[Completed Trips]` | origin–destination matrix |
| **Same-ZIP Share** | `DIVIDE(CALCULATE([Completed Trips], FILTER(Trips, Trips[PickupZipCode] = Trips[DropoffZipCode] && NOT ISBLANK(Trips[PickupZipCode]))), [Completed Trips])` | 13,792 completed trips have the same pickup and drop-off ZIP |
| **Missing Pickup ZIP Trips** | `CALCULATE([Completed Trips], ISBLANK(Trips[PickupZipCode]))` | data-quality card (618 completed) |

**Limitations with two tables and no geography dimension.** There is no ZIP table with names, boroughs, centroids or population, so you cannot (a) normalise by population, (b) draw ZIP polygons from a stored shape, (c) guarantee that the `Borough` label always agrees with the ZIP, or (d) show one row per ZIP with its own attributes. ZIP areas vary hugely in size and population, so a ZIP with more trips may simply be larger. ZIP codes also do not equal neighbourhoods, and pickups at one address share the ZIP of that address, so hot spots reflect where clients live. Add a ZIP reference table only as an **optional** third table.

---

## 9. Time-based analytics (strict two-table version)

`Trips[MonthStart]` (first day of month) and `Trips[TripDate]` are plain columns created in Power Query, so no Date table is needed.

| Measure | DAX |
|---|---|
| **Completed Trips by Month** | `[Completed Trips]` with `Trips[MonthLabel]` on the axis |
| **No-Shows by Month** | `[No-Show Trips]` with `Trips[MonthLabel]` |
| **OTP by Month** | `[Pickup OTP % — 15 Minutes]` and `[… 20 Minutes]` with `Trips[MonthLabel]` |
| **Previous Month Completed Trips** | below |
| **Month-over-Month Trip Growth %** | below |
| **Previous Month Net Fare Revenue** | below |
| **Month-over-Month Revenue Growth %** | below |
| **Rolling 7-Day Completed Trips** | below |
| **Rolling 30-Day No-Show Rate** | below |

```DAX
Previous Month Completed Trips =
VAR m = MAX(Trips[MonthStart])
RETURN
    IF(NOT ISBLANK(m),
        CALCULATE([Completed Trips],
            REMOVEFILTERS(Trips[MonthStart], Trips[MonthLabel], Trips[TripDate]),
            Trips[MonthStart] = EDATE(m, -1)))

Month-over-Month Trip Growth % =
VAR cur = [Completed Trips]
VAR prev = [Previous Month Completed Trips]
RETURN DIVIDE(cur - prev, prev)          -- format +0.0%;-0.0%

Previous Month Net Fare Revenue =
VAR m = MAX(Trips[MonthStart])
RETURN
    IF(NOT ISBLANK(m),
        CALCULATE([Net Fare Revenue],
            REMOVEFILTERS(Trips[MonthStart], Trips[MonthLabel], Trips[TripDate]),
            Trips[MonthStart] = EDATE(m, -1)))

Month-over-Month Revenue Growth % =
DIVIDE([Net Fare Revenue] - [Previous Month Net Fare Revenue], [Previous Month Net Fare Revenue])

Rolling 7-Day Completed Trips =
VAR d = MAX(Trips[TripDate])
RETURN
    CALCULATE([Completed Trips],
        REMOVEFILTERS(Trips[TripDate], Trips[MonthStart], Trips[MonthLabel]),
        Trips[TripDate] > d - 7, Trips[TripDate] <= d)

Rolling 30-Day No-Show Rate =
VAR d = MAX(Trips[TripDate])
VAR ns  = CALCULATE([No-Show Trips],
            REMOVEFILTERS(Trips[TripDate], Trips[MonthStart], Trips[MonthLabel]),
            Trips[TripDate] > d - 30, Trips[TripDate] <= d)
VAR den = CALCULATE([Eligible Scheduled Trips],
            REMOVEFILTERS(Trips[TripDate], Trips[MonthStart], Trips[MonthLabel]),
            Trips[TripDate] > d - 30, Trips[TripDate] <= d)
RETURN DIVIDE(ns, den)
```

**Use these on the right axis.** The rolling measures need `Trips[TripDate]` on the axis (turn off the automatic date hierarchy: select the field → choose `TripDate` not *Date Hierarchy*). The monthly “previous month” measures need `MonthLabel` or `MonthStart` on the axis. The rolling 30-day rate is “implemented correctly” because numerator and denominator are both recomputed over the same window (an average of daily rates would be wrong). The first 29 days contain fewer than 30 days of history; mark them as partial in a tooltip. Both rolling measures keep all non-date filters (mode, borough…) because only date columns are removed.

**Expected:** Rolling 7-day completed ending 2026-09-30 = **1,694**. Completed per month: Oct-25 6,999 · Nov 6,497 · Dec 7,082 · Jan 6,751 · Feb 6,360 · Mar 7,249 · Apr 7,080 · May 7,191 · Jun 7,142 · Jul 7,671 · Aug 7,571 · Sep 7,494. November → October growth: (6,497 − 6,999) ÷ 6,999 = **−7.2%**.

### Optional extension: a Calendar table (NOT part of the strict two-table model)
```DAX
Calendar = CALENDAR(DATE(2025,10,1), DATE(2026,9,30))
```
Add columns `Year`, `MonthStart`, `Weekday`, mark as date table, relate `Calendar[Date]` → `Trips[TripDate]` (1:*). **Benefits:** native `DATEADD`, `SAMEPERIODLASTYEAR`, `DATESINPERIOD`, no gaps on the axis when a day has no trips, one date slicer. **Costs:** a third table (breaks the “exactly two tables” rule), and with one year of data year-over-year functions have nothing to compare. For the portfolio, keep the strict version as the core and mention the Calendar as a documented trade-off.

---

## 10. Pickup-OTP and no-show breakdown measures (named as requested)

The requested names “Pickup OTP by Mode/Route/…” and “No-Shows per 100 Trips by Mode/…” are *the base measure sliced by a field*. To make them selectable, create one field parameter (§12), or build one visual per cut. No extra DAX is required, which is deliberate: duplicating a measure per dimension creates 12 measures that must be maintained identically.

**Verify filter responses.** Select each slicer and check the card:

| Filter | Expect (No-Shows per 100) |
|---|---|
| none | 4.80 |
| Mode = Primary | 4.01 |
| Mode = Broker | 5.48 |
| Mode = Supplemental | 6.85 |
| Mode = Unknown | 5.78 |
| Borough = Bronx | 6.56 |
| Borough = Manhattan | 4.45 |
| Monday | 5.57 (Sunday 3.65) |
| Month = 2026-01 | 5.18 |

---

## 11. Small-sample-safe route ranking

```DAX
Min Trips for Ranking = 200                                       -- parameter measure

Route Eligible = [Eligible Scheduled Trips]

Route NoShow per 100 (Ranked) =
IF([Eligible Scheduled Trips] >= [Min Trips for Ranking], [No-Shows per 100 Trips])

Route No-Show Rank =
VAR cur = [Route NoShow per 100 (Ranked)]
RETURN IF(NOT ISBLANK(cur),
    RANKX(
        FILTER(ALLSELECTED(Trips[RouteID]), NOT ISBLANK([Route NoShow per 100 (Ranked)])),
        [Route NoShow per 100 (Ranked)], , DESC, Dense))

Route Net Revenue Rank =
RANKX(ALLSELECTED(Trips[RouteID]), [Net Fare Revenue], , DESC, Dense)

Route OTP 15 (Ranked) =
IF([Eligible Pickup Trips] >= [Min Trips for Ranking], [Pickup OTP % — 15 Minutes])

Dynamic Top N Revenue Routes =           -- Top N slicer replacement without extra tables
VAR n = 10
RETURN IF([Route Net Revenue Rank] <= n, [Net Fare Revenue])
```

**Why:** `Route 3425` has 28 valid trips and 3 no-shows (10.7 per 100), `Route 3125` has 78 trips and 10 no-shows (13.3), while big routes sit near 4–5. With a handful of trips, one event swings the rate. The ranking measures return BLANK below the sample threshold, and the route table shows `Eligible Scheduled Trips` next to the rate. Also add a **confidence hint**: width of a 95% interval ≈ `1.96*SQRT(p*(1-p)/n)`; if the interval overlaps the system average, do not call the route “underperforming”.

```DAX
NoShow 95% Margin =
VAR p = [No-Show Rate %]  VAR n = [Eligible Scheduled Trips]
RETURN IF(n > 0, 1.96 * SQRT(p * (1 - p) / n) * 100)      -- in per-100 points
```

**Real outliers with enough volume (≥ 200 valid trips), planted in the synthetic data:** Route 3105 OTP-15 **57.6%** (11.6 no-shows per 100), Route 2105 OTP-15 **63.0%** (10.6 per 100). Everything else is near its mode’s average (Primary 89.0%, Broker 79.1%, Supplemental 74.1% OTP-15).

---

## 12. Interactivity measures

```DAX
Dynamic Title - OTP =
"Pickup OTP (≤ 15 min) – " &
IF(ISFILTERED(Trips[Mode]), CONCATENATEX(VALUES(Trips[Mode]), Trips[Mode], ", "), "All Modes") &
" | " & IF(ISFILTERED(Trips[Borough]), CONCATENATEX(VALUES(Trips[Borough]), Trips[Borough], ", "), "All Boroughs")

Selected Period Label =
VAR a = MIN(Trips[TripDate])  VAR b = MAX(Trips[TripDate])
RETURN FORMAT(a, "mmm d, yyyy") & " – " & FORMAT(b, "mmm d, yyyy")

Late Pickup Color =                         -- for conditional formatting by field value
SWITCH(TRUE(), MAX(Trips[PickupDelayMinutes]) > 20, "#C0392B",
               MAX(Trips[PickupDelayMinutes]) > 15, "#E67E22", "#2E7D32")

OTP vs Target Color =
IF([Pickup OTP % — 15 Minutes] >= 0.85, "#2E7D32", IF([Pickup OTP % — 15 Minutes] >= 0.80, "#E67E22", "#C0392B"))
```
85% is a fictional target for the demo, not an agency standard.
