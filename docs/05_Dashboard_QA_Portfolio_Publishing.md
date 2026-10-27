# Dashboard Build, Interactivity, QA, Portfolio Text and Publishing

All data, findings and thresholds are **synthetic**. Label every page footer: *“Synthetic data – illustrative project, not agency data.”*

---

## 1. Theme (transit-inspired, accessible)

| Role | Hex | Use |
|---|---|---|
| Navy (primary) | `#0B2545` | Titles, header band, Primary mode |
| Transit blue | `#0039A6` | Main series, Broker mode |
| Teal | `#13A89E` | Supplemental mode, positive |
| Amber | `#F2A900` | Warning / on-watch |
| Red | `#C8102E` | Late, no-show, below target |
| Light grey | `#F2F4F7` | Page background |
| Mid grey | `#667085` | Axis text, gridlines `#D0D5DD` |

Typography: **Segoe UI** (Power BI default, safe on every machine). Title 20 pt semibold; KPI value 28 pt bold; KPI label 11 pt grey; visual titles 12 pt; axis/legend 10 pt. Canvas 1280 × 720, 16 px outer margin, 12 px gutters, cards 150 × 90. Save as a **theme**: View → Themes → *Customize current theme* (set the colors above) → Save → `ParatransitTheme.json`.

Use **mode colors consistently on every page**: Primary = navy, Broker = blue, Supplemental = teal, Unknown = grey. Never use red/green as the only difference (add icons or labels).

---

## 2. Page-by-page build

For each visual: **type → fields**. “Axis” = category field, “Values” = measure.

### Page 1 — Executive Operations Overview
Header: title, `Selected Period Label`, navigation buttons, “Synthetic data” note.

| Visual | Type | Fields |
|---|---|---|
| 6 KPI cards | Card (new) | `[Completed Trips]`, `[No-Shows per 100 Trips]`, `[Pickup OTP % — 15 Minutes]`, `[Pickup OTP % — 20 Minutes]`, `[Net Fare Revenue]`, `[Unique Clients Served]` |
| Monthly completed trend | Line/column | Axis `Trips[MonthLabel]` · Values `[Completed Trips]` |
| Monthly no-show trend | Line | Axis `MonthLabel` · `[No-Shows per 100 Trips]` |
| 15 vs 20-min OTP | Line (2 series) | Axis `MonthLabel` · `[Pickup OTP % — 15 Minutes]`, `[… 20 Minutes]` |
| Trips by Mode | Donut or bar | Axis `Trips[Mode]` · `[Completed Trips]` |
| Trips by Borough | Bar | Axis `Trips[Borough]` · `[Completed Trips]` |
| Top routes | Bar, **Top N = 10** by `[Completed Trips]` (Filters pane → `RouteID` → Top N) | Axis `RouteID` · `[Completed Trips]` |
| No-show by mode | Clustered bar | Axis `Mode` · `[No-Shows per 100 Trips]` |
| Slicers | Date (between) `Trips[TripDate]`; dropdowns `Mode`, `RouteID`, `Borough`, `Clients[ClientType]`, `Clients[EligibilityCategory]`, `Trips[PickupZipCode]` | |

Data-quality strip (small): `[Completed Trips Excluded from OTP]` and `[OTP Coverage %]` so recruiters see you handled exclusions.

### Page 2 — Mode and Route Performance
Completed trips by Mode (bar) · No-shows per 100 by Mode (bar) · OTP-15 by Mode (bar with 85% reference line) · Completed trips by `RouteID` (bar) · OTP by `RouteID` (bar, use `[Route OTP 15 (Ranked)]`) · Route ranking by no-show rate (table: `RouteID`, `[Eligible Scheduled Trips]`, `[Route NoShow per 100 (Ranked)]`, `[Route No-Show Rank]`, sorted by rank) · Route ranking by net revenue (`[Net Fare Revenue]`, `[Route Net Revenue Rank]`) · Route performance table (`RouteID`, `Mode`, `[Completed Trips]`, `[Eligible Scheduled Trips]`, `[No-Shows per 100 Trips]`, `[NoShow 95% Margin]`, `[Pickup OTP % — 15 Minutes]`, `[Net Fare Revenue]`).
**Identify underperformers without misleading rankings:** (1) minimum sample (`Min Trips for Ranking`, 200); (2) show volume beside every rate; (3) show the 95% margin; (4) compare a route with its **mode average**, not the system average (Supplemental legitimately runs lower OTP); (5) flag “watch” only if the rate is worse than the mode average by more than the margin. In this dataset Routes 2105 and 3105 qualify; 3425 and 3125 look terrible but have 28 and 78 trips.

### Page 3 — Pickup OTP Analysis
KPI cards (OTP-15, OTP-20, `[Average Pickup Delay Minutes]`, `[Median Pickup Delay Minutes]`) · OTP trend (line by `MonthLabel`) · OTP by `RouteID` (bar) · by `Borough` (bar) · by `PickupZipCode` (bar, top 15 by eligible trips) · by `PickupHour` (column) · **Delay distribution**: column chart, Axis `Trips[PickupDelayBand]` (sorted by `PickupDelayBandSort`), Values `[Eligible Pickup Trips]` (bands: >15 early, early/on time, 1-15 late, 16-20, 21-45, >45).
Detail table: `TripID`, `TripDate`, `Mode`, `RouteID`, `PromiseTime`, `ActualPickupTime`, `PickupDelayMinutes`, `TripStatus`, `PickupZipCode`. Filter: `IsPickupOTPEligible = TRUE` (a page-level filter) plus a toggle bookmark that shows excluded rows.
**Conditional formatting (late pickups):** table → Format → Cell elements → `PickupDelayMinutes` → Background color → *Rules*: `> 20` red `#C8102E` (white text), `> 15 and ≤ 20` amber `#F2A900`, `≤ 15` none; or *Format by → Field value → `[Late Pickup Color]`*. Add *Data bars* to the delay.

### Page 4 — No-Show Analysis
Cards: `[No-Show Trips]`, `[No-Shows per 100 Trips]`, `[Cancellations per 100 Trips]`, `[Other Failed Trips]` · No-show trend (line by `MonthLabel`) · by `Mode`, `Borough`, `RouteID` (min-sample measure), `PickupZipCode` (bars) · **Day × hour** matrix: rows `DayOfWeekName`, columns `PickupHour`, values `[No-Shows per 100 Trips]`, conditional background gradient (white → red); suppress cells with `[Eligible Scheduled Trips] < 50` using a helper measure `IF([Eligible Scheduled Trips] >= 50, [No-Shows per 100 Trips])`.
**Operational no-show vs cancellation vs failure:** *No-show* = vehicle arrived, passenger not found (`TripStatus = "No-Show"`, reasons such as “Not at Pickup Location”). *Cancellation* = trip removed before service; excluded from the no-show denominator, reported on its own per 100 scheduled. *Failed/Other* = provider-side failure (breakdown, missed trip, unable to locate). A stacked bar by `OutcomeReason` coloured by `TripStatus` makes the split visible. Never add the three into one “lost trips” number without showing the parts.

### Page 5 — Geographic and ZIP Code Analysis
Setup (do once, as in Microsoft’s map guidance): set the ZIP columns to **Postal Code** data category, keep latitude/longitude as **Decimal Number**, drop latitude/longitude fields in the Latitude/Longitude wells (this avoids geocoding, so no data is sent for lookup) and use a Location field for grouping.

| Visual | Setup |
|---|---|
| Pickup map | **Azure Maps** (or Map) bubble visual; Location `PickupZipCode`, Latitude = *Average of* `PickupLatitude`, Longitude = *Average of* `PickupLongitude`, Size `[Total Scheduled Trips]` |
| Drop-off map | Same with `DropoffZipCode`, `DropoffLatitude/Longitude` |
| No-show hotspots | Bubble: Size `[No-Show Trips]`, color saturation `[No-Shows per 100 Trips]` (only ZIPs with ≥ 100 trips) |
| Mode-level comparison | Small multiples by `Mode` on the pickup map, or Legend = `Mode` |
| Volume by ZIP | Bar of `[Total Scheduled Trips]` for `PickupZipCode` and `DropoffZipCode` |
| No-shows / OTP by ZIP | Bars with `[No-Shows per 100 Trips]` and `[Pickup OTP % — 15 Minutes]` |
| Pickup vs drop-off | Clustered bar with `PickupZipCode` & `DropoffZipCode` as two series |
| Flows | **Matrix** rows `PickupZipCode` × columns `DropoffZipCode`, values `[Completed Trips]`, heat-map shading |
| Detail table | `PickupZipCode`, `DropoffZipCode`, `Borough`, `[Total Scheduled Trips]`, `[No-Show Trips]`, `[Pickup OTP % — 15 Minutes]` (no addresses) |

Why the “average of latitude” trick: the model has no ZIP-centroid table. Averaging the (jittered, synthetic) trip coordinates per ZIP puts one bubble at a plausible centroid, shows ZIP-level patterns and avoids showing individual points. **Bubble/filled maps cannot draw origin→destination lines.** Use the matrix, or an AppSource flow-map custom visual (check that it works with your tenant and its data-sharing behavior before using it), or add an *optional* ZIP-pair table (a third table) with centroids and use a Shape-map/line-layer.
**Limitations of ZIP-level analysis:** areas differ in size/population (no normalisation without a reference table); ZIPs ≠ neighbourhoods; ~0.7% of trips have missing/invalid pickup ZIPs; ~0.3% have coordinates within range but far from their ZIP (undetectable without a ZIP-centroid check); averages of coordinates misplace ZIPs that wrap water or are split by a border. **Privacy:** ~82% of synthetic pickups are home pickups, so pickup points approximate residences. Even for synthetic data practise the habit: publish only aggregated ZIP bubbles, suppress cells under 10 trips, never publish address fields or client-level coordinates, and don’t show `Clients[HomeLatitude/Longitude]` at all.

### Page 6 — Client Analytics
Cards: `[Total Valid Clients]`, `[Unique Clients Served]`, `[Active Client Rate]`, `[Trips per Client Served]` · Trips by `Clients[AgeGroup]` (column) · by `EligibilityCategory` · by `MobilityAid` · by `HomeZipCode` (top 15) · by `ClientType` · High-frequency share (donut: `[High-Frequency Client Count]` vs the rest, or card `[High-Frequency Client Share]`) · slicer for threshold? Use a bookmark between 10/20/30 only if you add a what-if parameter (it creates an extra table, so flag it as an optional extension). No ClientID lists with identifying attributes; ClientID appears only in drill-through for synthetic IDs.

### Page 7 — Trip Explorer (hidden from navigation; reached by drill-through)
Table: `TripID`, `Clients[ClientID]`, `TripDate`, `Mode`, `RouteID`, `PickupZipCode`, `DropoffZipCode`, `PromiseTime`, `ActualPickupTime`, `PickupDelayMinutes`, `TripStatus`, `FareAmount`, `RefundAmount`. Add: search (the table-level *Search* in the top-left of a slicer set to *List* with search on `TripID`), sort by clicking headers, status-based font color (`No-Show` red, `Cancelled` grey), delay formatting as on page 3, `FareIsValid = FALSE` shown in red italic with an asterisk header note. Keep it off the executive pages: heavy tables slow rendering, and detail rows are what privacy rules most want restricted.

---

## 3. Interactivity (prioritised)

| Priority | Feature | How |
|---|---|---|
| 1 | **Synchronised slicers** | View → Sync slicers; tick pages for Date, Mode, Borough; leave Route/ZIP page-specific |
| 1 | **Dynamic titles** | Visual → Format → Title → *fx* → Field value → `[Dynamic Title - OTP]` |
| 1 | **Cross-highlighting** | Default: click a mode bar to filter the others. Format → Edit interactions to turn it off for KPI cards that should stay global |
| 1 | **Drill-through** | On Page 7 drag `RouteID` (or `Mode`) to *Drill-through* well; right-click a route bar → *Drill through → Trip Explorer* |
| 1 | **Report-page tooltips** | New page 320×240, Page information → *Allow use as tooltip*; add `[Pickup OTP % — 15 Minutes]`, `[No-Shows per 100 Trips]`, `[Eligible Scheduled Trips]` and a mini monthly line; in a visual set Tooltip → Type *Report page* |
| 2 | **Top N and dynamic ranking** | Filters pane → Top N; plus `[Route No-Show Rank]` / `[Dynamic Top N Revenue Routes]` for ranking on a table |
| 2 | **Conditional formatting** | Cards: Callout value → fx → `[OTP vs Target Color]`; bars: Bars → Color → Format by Field value |
| 2 | **Bookmarks + navigation buttons** | View → Bookmarks → capture (uncheck *Data* to keep slicers dynamic); Insert → Buttons → Navigator → Page navigator (hide the Explorer page) |
| 2 | **Reset-filters button** | Bookmark “Reset” captured with all slicers cleared; button action → Bookmark |
| 3 | **Field parameters** | Modeling → New parameter → Fields → add `Mode`, `Borough`, `RouteID`, `PickupZipCode`, `DayOfWeekName`; use as the axis of one visual so users choose the cut. *Creates a calculated table; list it as an optional addition to the two-table model.* |

Show the “Selected Period Label” on each page so exported screenshots are self-explanatory.

---

## 4. Validation and QA checklist

Run on the **unfiltered** model first, then with filters. Numbers come from the independent script on the delivered CSVs.

| # | Test | How | Expected |
|---|---|---|---|
| 1 | ClientID unique | `Dup Client Keys` | 0; `COUNTROWS(Clients)` = 5,000 |
| 2 | TripID unique | `Dup Trip Keys` | 0; `COUNTROWS(Trips)` = 100,000 |
| 3 | Referential integrity | `Unmatched Trips` | 934 (745 + 189 blank); completed among them 773 |
| 4 | Route → Mode | Table of `RouteID`, `Mode` | `R-1215` Primary · `R-1025` Primary · `R-1315` (raw `r 1315`) Primary · `R-2205` (raw `Route 2205`) Broker · `R-3305` Supplemental · `R-999` Unknown · `R-XX99` blank route, Unknown. 571 valid trips Unknown |
| 5 | Age | Check 4 clients | C00025 (1959-09-30) = 67 · C00027 (1937-10-02) = 88 · C00180 (1999-10-02) = 26 · C03004 (1976-03-25) = 50. Age blank for 89 clients |
| 6 | AgeGroup | Count by group | 65+ 2,786 · 45-64 1,161 · 25-44 613 · 18-24 214 · Under 18 137 · Unknown 89 |
| 7 | ZIP format | `Trips` ZIP length | all non-blank = 5 text chars; NJ ZIPs `07030/07302/07093` start with `0` |
| 8 | Coordinates | Min/max after cleaning | lat 40.45–41.05; lon −74.30 – −73.50; no `0`, 91.2 or −181.5 |
| 9 | Pickup delay | Inspect rows | T0000295 = +72 (crosses midnight) · T0000297 = −13 · T0000326 = 15 · T0000022 = 16 · T0000005 = −16 (early) |
| 10 | Excluded delays | Filter `OTPEligibility` | T0000343 (−1,450) and T0002686 (+1,439) are “Pickup delay out of valid range” |
| 11 | OTP-15 denominator | `[Eligible Pickup Trips]` | 82,830; OTP-15 = 69,818 ÷ 82,830 = **84.29%** |
| 12 | OTP-20 denominator | | 73,090 ÷ 82,830 = **88.24%** |
| 13 | Exclusions add up | 14,856 not completed + 854 + 1,280 + 123 + 82,830 = 99,943 | ✔ |
| 14 | No-show numerator / denominator | | 4,471 ÷ 93,249 → **4.795 per 100** |
| 15 | Cancellation treatment | | 6,694 cancelled, not in the denominator of #14; cancellations/100 = 6.698 |
| 16 | Revenue reconciliation | | Gross $990,020.22 − refunds $21,621.00 = **$968,399.22**; sum of monthly net = total; by mode sums to total |
| 17 | Missing-timestamp exclusion | | `Excluded — Missing PromiseTime` = 854, `… ActualPickupTime` = 1,280 |
| 18 | Duplicate treatment | | 100,400 raw → 100,000; T0000753 keeps its completed record |
| 19 | Filter context | | Mode = Broker → OTP-15 **79.1%**, No-shows/100 **5.48**; Mode = Supplemental → **74.1%** / **6.85**; Borough = Bronx → 6.56; Month 2026-01 → OTP-15 **80.0%** |
| 20 | Route ranking | | Routes below 200 trips are blank in `[Route No-Show Rank]`; 2105 and 3105 appear at the top |
| 21 | Geographic accuracy | Compare ZIP bubbles with the matrix | 41 unique pickup ZIPs; top pickup ZIPs by completed trips: 11368 (3,701), 11206 (3,550), 11226 (3,427) |
| 22 | Client measures | | Unique Clients Served **4,183**; Active Client Rate **83.7%**; High-Frequency (≥20) **1,154**; Trips per Client Served 20.16 |
| 23 | Segmentation sums | Sum `[Completed Trips]` over `AgeGroup` incl. (Blank) | 85,087 (unmatched 773 appear under *(Blank)*) |

**Independent re-calculation.** `reference_clean.py` recomputes every number above from the raw CSVs in pandas. Run `python3 reference_clean.py <folder> audit.json` if you regenerate the data; if you change the seed, all expected values change and must be re-read from `audit.json`.

---

## 5. Portfolio package

**Project title:** *Paratransit Service Quality Analytics — On-Time Pickup, No-Shows and Equity of Service (Power BI, synthetic data)*

**Business problem.** A fictional metropolitan paratransit operator delivers ~100,000 scheduled trips a year through three delivery models (Primary, Broker, Supplemental). Leadership needs a single, trustworthy view of pickup reliability (15- and 20-minute on-time performance), no-shows per 100 trips, cancellations, revenue and client usage, on data that arrives messy from several systems.

**Objectives.** (1) Clean raw operational data reproducibly in Power Query; (2) model clients and trips as a two-table star; (3) define OTP, no-show and revenue rules explicitly; (4) deliver a 7-page interactive dashboard with trustworthy ranking and privacy-aware geography.

**Executive summary and illustrative findings (synthetic – from the generated data, including patterns that were planted for the exercise):**
- Overall pickup OTP is **84.3%** (≤15 min) and **88.2%** (≤20 min) on 82,830 measurable pickups; 2,257 completed trips (2.7%) were excluded for missing/invalid timestamps.
- **Primary** service performs best (OTP-15 89.0%, 4.0 no-shows per 100); **Supplemental** is weakest (74.1%, 6.9 per 100); Broker sits between (79.1%, 5.5).
- Two routes stand out among high-volume routes: **R-3105** (OTP-15 57.6%) and **R-2105** (63.0%), with 11.6 and 10.6 no-shows per 100. Low-volume routes with extreme rates (e.g., 28–78 trips) are not ranked.
- The **Bronx** has the highest no-show rate (6.6 per 100) versus 4.4 in Manhattan and Queens. **Mondays** (5.6) are worse than **Sundays** (3.7).
- Winter pressure: OTP-15 fell to **80.0% in January 2026** vs ~85% in most months; peak periods run ~3 points below off-peak (82.6% vs 85.6%).
- Net fare revenue is **$968K**; about 1,419 completed trips (1.7%) had unusable fares and are excluded rather than imputed.
- 83.7% of clients took at least one completed trip; 1,154 clients (28% of those served) took 20+ trips.

**Resume / LinkedIn description (≈80 words):**
> *Paratransit Operations Dashboard (Power BI, synthetic data).* Built a 7-page interactive dashboard from 100K raw trip and 5K client records. Cleaned and standardised data in Power Query (M): de-duplicated keys, parsed 11 route formats into a rule-based Mode, calculated age and pickup delay from full timestamps. Designed a two-table model and 70+ DAX measures for 15/20-minute OTP, no-shows per 100 trips, revenue and client utilisation, with small-sample-safe route rankings, drill-through and privacy-aware ZIP-level maps. All data is fictional.

**Interview talking points:** why `<=15` and early pickups count; why OTP excludes cancelled/no-show; why `Remove Duplicates` needs sort + `Table.Buffer`; why ZIPs are text; why the rate is a measure; why some routes are not ranked; what you’d add with a third table.

---

## 6. Publishing and sharing

**Import and save.** Home → Get data → Text/CSV for each file → *Transform Data* → paste `Clients.m` / `Trips.m` as described in the Power Query tutorial → Close & Apply → File → Save as `Paratransit_Trips_Dashboard.pbix`. If you move the files, change only the `pFolder` parameter (Transform data → Edit parameters).

**Publish.** Home → Publish → choose a workspace (My workspace is fine for a portfolio) → open in the Power BI service → set up a scheduled refresh only if the CSVs live in a cloud location (OneDrive/SharePoint); local files need a gateway.

**Licensing (checked against Microsoft Learn pages “Licenses and subscriptions for business users” and “Features available to free users”):**
- A **free license** gives you *My workspace* to create and view your own content. Free users **cannot** share content, publish to app workspaces, share with external users, or view content others share unless that content (report *and* its semantic model) sits in Premium/Fabric capacity (F64 or higher; smaller F SKUs still require a paid license for viewers) and they have a Viewer role.
- To **share privately** with named people outside a capacity setup, the creator and each viewer need **Power BI Pro or Premium Per User**; sharing with people outside your organisation also requires the guest to be licensed (or the content to be in suitable capacity). Prices and plans change — confirm on the Power BI pricing page before you buy.
- Creating a *Publish to web* embed code is also not available to free users.

**Publish to web — risks (Microsoft Learn):** anyone on the internet can view it without signing in; underlying detail-level data in the model can be reachable; the link can spread; no access restriction exists (only deleting the embed code); it is not supported with row-level security or certain data sources; data is cached for an hour; your admin may disable it. Never publish confidential or employer data this way. The synthetic data here is safe in principle, but keep the habit and avoid it if you reuse real employer logic.

**Safe ways to show recruiters (best to simplest):**
1. **Screenshots / PDF** of each page with the “synthetic data” footer (File → Export → PDF).
2. **Recorded walkthrough** (2–3 minutes) hosted on YouTube (unlisted) or LinkedIn; narrate the cleaning decisions and the OTP definition.
3. **Sanitised PBIX on GitHub** with the generator script, `reference_clean.py`, the two CSVs and the data dictionary. Because everything is synthetic, the PBIX can be shared as a file; remove local paths (`pFolder`) and any personal workspace names first.
4. **Live private demo**: share your screen, or add the recruiter as a licensed guest only if you have the licenses.
5. Use **Publish to web** only if you accept that the dashboard and its underlying synthetic data become public.

**Sources**
- [Licenses and subscriptions for business users – Power BI](https://learn.microsoft.com/power-bi/consumer/end-user-license)
- [Power BI features available to free users](https://learn.microsoft.com/en-us/power-bi/fundamentals/end-user-features)
- [Publish to web from Power BI](https://learn.microsoft.com/en-us/power-bi/collaborate-share/service-publish-to-web)
- [Tips and tricks for Power BI map visualizations](https://learn.microsoft.com/en-gb/power-BI/visuals/power-bi-map-tips-and-tricks)
