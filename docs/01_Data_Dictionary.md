# Data Dictionary — Synthetic Paratransit Analytics Project

**All data is fictional.** Addresses are invented. Coordinates are ZIP-area centroids plus random jitter; they are *not* real residences or pickup points. ZIP codes are real NYC-area ZIP codes used only as geographic labels. Route numbers, mode ranges, fares, promise windows and thresholds are project rules, not agency operating rules.

Reporting window: **2025-10-01 to 2026-09-30** (12 full months). Age reference date: **2026-09-30** (`pAsOfDate`).

---

## 1. Model summary

| Item | `Clients` | `Trips` |
|---|---|---|
| Role | Dimension | Fact |
| Source file | `Clients.csv` | `Trips.csv` |
| Grain | One row per client | One row per scheduled trip record (completed, cancelled, no-show, failed/other) |
| Primary key | `ClientID` | `TripID` |
| Foreign key | — | `ClientID` → `Clients[ClientID]` (many-to-one) |
| Raw rows | **5,060** | **100,400** |
| Rows after de-duplication | **5,000** | **100,000** |
| Rows usable for KPIs | 5,000 (some with missing Age / ZIP flags) | **99,943** (`IsValidScheduledTrip = TRUE`) |
| Raw columns | 16 | 43 |

Relationship: `Clients[ClientID]` (1) → `Trips[ClientID]` (*), single direction (Clients filters Trips).

**Two-table rule.** The core model has exactly these two imported tables. `pAsOfDate`, `pDataStart`, `pDataEnd` are Power Query *parameters* (single values, not tables). An optional calculated `Calendar` table is described in the DAX guide and is clearly marked optional.

---

## 2. `Clients.csv` — raw columns

| Raw column | Raw format in CSV | Business meaning | Final name / type after Power Query | Valid values / range | Notes |
|---|---|---|---|---|---|
| `ClientID` | text `C00001`–`C05000` | Unique client key | `ClientID` text | `C` + 5 digits, unique after de-dup | 60 rows repeat an existing ID (see quality report) |
| `DateOfBirth` | text `yyyy-MM-dd` | Birth date | `DateOfBirth` date | 1916-09-30 … 2026-09-30 (age 0–110) | Contains future, impossible, blank and non-date values. **No Age column in raw.** |
| `RegistrationDate` | text `yyyy-MM-dd` | Date client registered for service | `RegistrationDate` date | ≥ DateOfBirth, ≤ 2026-09-30 | Some earlier than DOB, some in future |
| `ClientType` | text | Program type | `ClientType` text | ADA Paratransit, Medicaid, Senior Program, Visitor, Unknown | 56 raw spellings |
| `EligibilityCategory` | text | Eligibility description | `EligibilityCategory` text | Unconditional, Conditional, Temporary, Visitor, Unknown | 67 raw spellings (e.g. `UNCOND`, `ADA - Conditional`, `temp. eligibility`) |
| `Gender` | text | Optional synthetic demographic | `Gender` text | Male, Female, Non-binary, Unknown, Not Provided | Optional; ~6% blank/placeholder |
| `HomeAddressLine` | text | Fictional street address | `HomeAddressLine` text (hide it) | free text | Mixed abbreviations (`St`, `Street`, `ST.`), double spaces, ALL CAPS. **Never display in reports.** |
| `HomeCity` | text | City / neighbourhood | `HomeCity` text | e.g. New York, Bronx, Brooklyn, Jamaica … | 103 raw spellings (`NYC`, `Bklyn`, `The Bronx`) |
| `HomeState` | text | State | `HomeState` text | NY, NJ | `ny`, `New York`, `N.Y.`, blanks |
| `HomeZipCode` | **text** | Home ZIP | `HomeZipCode` text | 5 digits, prefix 07, 10 or 11 | ZIP+4, trailing `.0`, spaces, dropped leading zero (NJ), invalid values |
| `HomeLatitude` | text (decimal) | Approx. synthetic latitude | `HomeLatitude` decimal | 40.45 – 41.05 (service box) | Blank, `0`, `N/A`, `91.2345`, swapped with longitude |
| `HomeLongitude` | text (decimal) | Approx. synthetic longitude | `HomeLongitude` decimal | −74.30 – −73.50 | Blank, `0`, `N/A`, `-181.5` |
| `PreferredLanguage` | text | Language | `PreferredLanguage` text | English, Spanish, Chinese, Russian, Haitian Creole, Bengali, Korean, Arabic, Other, Not Provided | 114 raw spellings (`ENG`, `Español`, `Mandarin`) |
| `MobilityAid` | text | Mobility aid | `MobilityAid` text | Wheelchair, Walker, Cane, None, Other, Not Provided | `W/C`, `Power Chair`, `Rollator`, `White Cane` … |
| `ClientStatus` | text | Account status | `ClientStatus` text | Active, Inactive, Suspended, Unknown | Codes `A`, `ACT`, `1`, `I`, `0`, `S`, `SUSP`, plus unknown `X`, `?`, `PEND` |
| `PreferredContactMethod` | text | Contact preference | `PreferredContactMethod` text | Phone, SMS, Email, Mail, Not Provided | `Call`, `Text`, `e-mail`, `US Mail` … |

### Columns created later in Power Query (`Clients`)

| Column | Type | Definition |
|---|---|---|
| `Age` | whole number | Completed years as of `pAsOfDate` (2026-09-30), calculated from `DateOfBirth`; null when DOB invalid |
| `AgeGroup` | text | `Under 18`, `18-24`, `25-44`, `45-64`, `65+`, `Unknown` |
| `AgeGroupSort` | whole number | 1–5 for the groups, 9 for Unknown (used as *Sort by column*) |
| `DateOfBirthIsValid` | logical | DOB parsed, not in future, age 0–110 |
| `RegistrationDateIsValid` | logical | Parsed, ≤ as-of date, not earlier than a valid DOB |
| `HomeZipIsValid` | logical | 5-digit ZIP with prefix 07/10/11 after cleanup |
| `HomeCoordsAreValid` | logical | Lat/lon numeric and inside the service-area box |
| `DataQualityFlags` | text | Semicolon-separated list of problems for that client (blank = clean) |
| `SourceRowCount` | whole number | How many raw rows carried this `ClientID` (1 = no duplicate) |

---

## 3. `Trips.csv` — raw columns

### A. Identifiers and scheduling

| Raw column | Raw format | Business meaning | Final name / type | Valid values / range | Known raw problems |
|---|---|---|---|---|---|
| `TripID` | text `T0000001`… | Unique trip key | `TripID` text | unique after de-dup | 400 repeated rows |
| `ClientID` | text | FK to `Clients` | `ClientID` text | existing client ID | lower-case, padded spaces, blanks, IDs not in `Clients` |
| `BookingID` | text `BK0000001`… | Booking; an outbound trip and its return leg share one BookingID | `BookingID` text | — | none deliberately |
| `TripDate` | text `yyyy-MM-dd` | Service date (date of scheduled pickup) | `TripDate` date | 2025-10-01 … 2026-09-30 | blank (110), outside window (26) |
| `BookingDate` | text `yyyy-MM-dd` | Date the trip was booked | `BookingDate` date | ≤ `TripDate` | blank, later than trip date |
| `ScheduledPickupTime` | text `yyyy-MM-dd HH:mm:ss` | Negotiated pickup time | `ScheduledPickupTime` datetime | valid timestamp | blank / malformed (292) |
| `ScheduledDropoffTime` | same | Planned drop-off | `ScheduledDropoffTime` datetime | ≥ scheduled pickup | blank / malformed (474) |
| `PromiseTime` | same | **Time by which the pickup is promised to occur** (project rule: `ScheduledPickupTime` + 15 minutes) | `PromiseTime` datetime | valid timestamp | blank / malformed (999) |
| `ActualPickupTime` | same | **Actual pickup (boarding) timestamp** used for OTP | `ActualPickupTime` datetime | valid timestamp, completed trips only | blank by design for cancelled/no-show/other; blank/malformed on completed trips (a defect) |
| `ActualDropoffTime` | same | Actual drop-off | `ActualDropoffTime` datetime | ≥ actual pickup | same pattern |
| `ScheduledDurationMinutes` | integer text | Planned ride length | `ScheduledDurationMinutes` whole number | 5–240 | none deliberately |
| `TripPurpose` | text | Trip purpose | `TripPurpose` text | Medical, Dialysis, Work, Education/Training, Shopping/Errand, Social/Recreation, Senior Center, Other, Unknown | variants (`MED`, `Med Appt`, `DIAL`) and blanks |
| `RawTripStatus` | text | Status as logged | `TripStatus` text | Completed, Cancelled, No-Show, Failed/Other, Unresolved | 30 raw spellings (below) |
| `CancellationReason` | text | Reason text for cancelled, no-show and failed trips (despite the name) | `OutcomeReason` text | 15 standard reasons + Not Recorded | 196 raw spellings; ~8% blank on non-completed; stray values on completed trips |
| `NoShowIndicatorRaw` | text | No-show flag as logged | `NoShowIndicator` logical (nullable) | Y/1/TRUE/Yes → true; N/0/FALSE/No → false | 24,529 blank; 328 rows disagree with status |

### B. Route and service

| Raw column | Raw format | Meaning | Final name / type | Valid values | Known raw problems |
|---|---|---|---|---|---|
| `RouteID` | text | Route identifier | `RouteID` text (`R-1050`) and `RouteNumber` whole number | number 1000–3999 | 11 formats: `R-1050`, `1050`, `r 2050`, `Route 3050`, ` R-1050 `, `R1050`, `RT-1050`; 358 numeric out-of-range; 215 blank/non-numeric |
| `RouteDescription` | text | Route label | `RouteDescription` text | — | case / spacing noise |
| `RawServiceMode` | text | Untrusted mode label | kept only for reconciliation (`RawServiceModeNorm`, hidden) | Primary, Broker, Supplemental | ~4,600 rows disagree with route-derived mode. **Never use as the final mode.** |
| *(created)* | — | Final service mode | **`Mode`** text | Primary 1000–1999, Broker 2000–2999, Supplemental 3000–3999, else Unknown | derived in Power Query from `RouteNumber` |
| `ServiceProviderID` | text | Provider | `ServiceProviderID` text | SP-01, SP-02, SP-11, SP-12, SP-13, SP-21 | lower-case, blanks (1,033) |
| `VehicleType` | text | Vehicle | `VehicleType` text | Sedan, Minivan, Lift Van, Taxi, Unknown | variants, blanks |
| `ServiceRegion` | text | Fictional region (North / East / South) | `ServiceRegion` text | North, East, South | `N`, `E`, `S`, upper-case |
| `Borough` | text | Pickup borough / county | `Borough` text | Manhattan, Bronx, Brooklyn, Queens, Staten Island, Nassau County, Hudson County NJ, Unknown | `MN`, `BX`, `Bklyn`, `QNS`, `SI` … |
| `ServiceDayType` | text | Day type as logged | `ServiceDayType` text (recomputed: Weekday/Saturday/Sunday) | — | ~1% disagree with `TripDate`; holidays not modelled |
| `BookingChannel` | text | Booking channel | `BookingChannel` text | Phone, Web, App, IVR, Unknown | variants, blanks |

### C. Geography (all fictional)

| Raw column | Meaning | Final | Valid | Known raw problems |
|---|---|---|---|---|
| `PickupAddress`, `DropoffAddress` | Fictional address text | text (hide in report) | — | abbreviations, caps, double spaces, ~360 blank each |
| `PickupZipCode`, `DropoffZipCode` | ZIP, **kept as text** | text, 5 chars | prefix 07/10/11 | ZIP+4 (~1,960 each), padded spaces (~1,240), `12345.0` (~830), dropped leading zero on NJ ZIPs, `00000`/`ABCDE`, blank (497) |
| `PickupLatitude`, `PickupLongitude`, `DropoffLatitude`, `DropoffLongitude` | Approx. synthetic coordinates | decimal | lat 40.45–41.05, lon −74.30 – −73.50 | blank (~1,190), `0`, `N/A`, lat > 90, lon < −180, swapped lat/lon (~280 pickup), plausible-range points far from their ZIP (~0.3%, **undetectable by range checks** — a deliberate limitation) |

### D. Outcome and operational metrics

| Raw column | Raw format | Meaning | Final name / type | Valid | Known raw problems |
|---|---|---|---|---|---|
| `RawPickupOutcome` | text | Pickup outcome as logged | not used in KPIs (drop or hide) | — | variants; ~1% inconsistent with status |
| `RawDropoffOutcome` | text | Drop-off outcome | not used in KPIs (drop or hide) | — | variants |
| `ScheduledPassengerCount` | integer text | Passengers booked | `ScheduledPassengerCount` whole number | 1–8 | — |
| `ActualPassengerCount` | integer text | Passengers carried | `ActualPassengerCount` whole number | 0–8 | `-1`, `15` (≈205), blank (516) |
| `RawFareAmount` | text | Fare for the trip | `FareAmount` decimal | 0–150 | `$12.40`, `12.4`, negative (244), `999.99` (52), `N/A`, blank, positive on non-completed trips (54) |
| `RawRefundAmount` | text | Refund | `RefundAmount` decimal | 0 ≤ refund ≤ fare | `$`, blank/0/0.00 variants, refund larger than fare |
| `RawDistanceMiles` | text | Trip distance | `DistanceMiles` decimal | >0 and ≤100 | `5.6 mi`, `5.60 miles`, `0`, negative, `999`, `N/A`, blank |
| `RawTripDuration` | text | Actual ride minutes | `TripDurationMinutes` decimal | >0 and ≤240 | `28 min`, `28.0`, `0`, negative, ≥600, `n/a`, blank |
| `RawDelayMinutes` | text | Provider-reported delay (**not trusted**) | `ReportedDelayMinutes` decimal (reconciliation only) | — | ~8% sign-flipped, ~10% with `min late/early` text, ~12% blank |
| `DriverArrivalTime` | timestamp text | Driver pressed "arrived" on the tablet | `DriverArrivalTime` datetime | — | blank / malformed ~5% |
| `VehicleArrivalTime` | timestamp text | GPS-detected arrival at pickup point | `VehicleArrivalTime` datetime | ≤ `ActualPickupTime` | blank / malformed ~4.5% |

### Raw status spellings → `TripStatus`

| `TripStatus` | Raw spellings in the file (case/space variants ignored) |
|---|---|
| Completed | `Completed`, `COMP`, `comp`, `Complete`, `Cmpltd`, `COMPLETED` |
| Cancelled | `Cancelled`, `CXL`, `Canceled`, `CANC`, `Cancelled - Client` |
| No-Show | `No Show`, `NS`, `No-Show`, `NOSHOW`, `noshow` |
| Failed/Other | `Missed Trip`, `MISS`, `Vehicle Breakdown`, `BRKDWN`, `Incomplete`, `Failed`, `FAIL` |
| Unresolved (excluded from KPIs) | `Scheduled`, `SCHED`, `UNK`, `???`, blank |

### Columns created later in Power Query (`Trips`)

| Column | Type | Definition |
|---|---|---|
| `TripDateWasRepaired` | logical | `TripDate` was blank/outside window and was rebuilt from `ScheduledPickupTime` |
| `ClientMatched` | logical | Cleaned `ClientID` exists in `Clients` |
| `RouteNumber` | whole number | Numeric part of `RouteID` after cleanup |
| `Mode` | text | **Derived from `RouteNumber`** (1000–1999 Primary, 2000–2999 Broker, 3000–3999 Supplemental, otherwise Unknown) |
| `IsValidScheduledTrip` | logical | De-duplicated row with a usable `TripDate` and a resolved `TripStatus` |
| `PickupDelayMinutes` | decimal | `ActualPickupTime − PromiseTime` in minutes (full timestamps); positive = late, negative = early |
| `PickupDelayIsValid` | logical | Delay exists and is between −180 and +360 minutes |
| `OTPEligibility` | text | `Eligible` or the exclusion reason (`Not a completed trip`, `Missing/invalid PromiseTime`, `Missing/invalid ActualPickupTime`, `Pickup delay out of valid range`) |
| `IsPickupOTPEligible` | logical | `OTPEligibility = "Eligible"` |
| `DropoffDelayMinutes` | decimal | `ActualDropoffTime − ScheduledDropoffTime` when both valid and trip completed |
| `DayOfWeekName` / `DayOfWeekNumber` | text / whole | Monday = 1 … Sunday = 7 |
| `IsWeekend` | logical | Saturday or Sunday |
| `PickupHour` | whole number | Hour (0–23) of `ScheduledPickupTime` |
| `TimePeriod` | text | `Peak` = weekday with scheduled pickup 06:00–09:59 or 15:00–18:59, else `Off-Peak` |
| `FareIsValid`, `RefundIsValid`, `DistanceIsValid`, `DurationIsValid` | logical | Range and format checks |
| `EligibleFare` | decimal | `FareAmount` for completed trips with a valid fare, else 0 |
| `EligibleRefund` | decimal | `RefundAmount` for completed trips with valid fare **and** valid refund, else 0 |
| `TripDurationSource` | text | `Raw field`, `From timestamps` or `Unavailable` |
| `PickupZipIsValid`, `DropoffZipIsValid` | logical | ZIP format check |
| `PickupCoordsAreValid`, `DropoffCoordsAreValid` | logical | Coordinate range check |
| `StatusIndicatorConflict` | logical | `TripStatus` and `NoShowIndicator` disagree (status wins) |

**Not created as columns on purpose:** OTP on-time flags, No-Show rates, revenue totals — these are DAX measures so they respond to filters.
