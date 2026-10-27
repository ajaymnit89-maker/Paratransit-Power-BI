// =====================================================================================
// QUERY NAME: Trips
// Needs the parameters from Clients.m plus:
//   pDataStart (Date) 2025-10-01      pDataEnd (Date) 2026-09-30
// This query reads the cleaned Clients query only to flag unmatched ClientIDs (ClientMatched).
// It does not add a third table: Clients is already one of the two loaded tables.
// If you see "Formula.Firewall", set File > Options > Privacy to "Ignore privacy levels" for this local project.
// =====================================================================================
let
    // ------------------------------- helper functions --------------------------------
    CleanText = (t as nullable text) as nullable text =>
        let s = if t = null then null else Text.Trim(Text.Clean(t))
        in if s = null or List.Contains({"", "n/a", "null", "-"}, Text.Lower(s)) then null else s,
    Lc = (t as nullable text) as text => if t = null then "" else Text.Lower(t),
    ParseNum = (t as nullable text) as nullable number =>
        if t = null then null else try Number.FromText(t, "en-US") otherwise null,
    ParseDT = (t as nullable text) as nullable datetime =>
        if t = null then null else try DateTime.FromText(t, [Format = "yyyy-MM-dd HH:mm:ss", Culture = "en-US"]) otherwise null,
    ParseDate = (t as nullable text) as nullable date =>
        if t = null then null else try Date.FromText(t, [Format = "yyyy-MM-dd", Culture = "en-US"]) otherwise null,
    Minutes = (a as nullable datetime, b as nullable datetime) as nullable number =>
        if a = null or b = null then null else Duration.TotalMinutes(a - b),

    MapStatus = (t as nullable text) as text =>
        let l = Lc(t) in
        if Text.StartsWith(l, "comp") or l = "cmpltd" then "Completed"
        else if Text.Contains(l, "canc") or Text.Contains(l, "cxl") then "Cancelled"
        else if l = "ns" or Text.Contains(l, "show") then "No-Show"
        else if List.AnyTrue(List.Transform({"miss", "brkdwn", "breakdown", "incomplete", "fail"}, (k) => Text.Contains(l, k))) then "Failed/Other"
        else "Unresolved",

    MapReason = (t as nullable text, status as text) as nullable text =>
        let l = Lc(t) in
        if status = "Completed" then null
        else if t = null then (if List.Contains({"Cancelled", "No-Show", "Failed/Other"}, status) then "Not Recorded" else null)
        else if Text.Contains(l, "client req") then "Client Request"
        else if Text.Contains(l, "same") then "Same-Day Cancellation"
        else if Text.Contains(l, "weather") then "Weather"
        else if Text.Contains(l, "appt") or Text.Contains(l, "medical appointment") then "Medical Appointment Changed"
        else if Text.Contains(l, "dup") then "Duplicate Booking"
        else if Text.Contains(l, "agency") then "Agency Cancelled"
        else if Text.Contains(l, "sched") then "Schedule Change"
        else if Text.Contains(l, "not at") then "Not at Pickup Location"
        else if Text.Contains(l, "not ready") then "Not Ready at Window"
        else if Text.Contains(l, "no answer") then "No Answer at Door"
        else if Text.Contains(l, "unreachable") then "Client Unreachable"
        else if Text.Contains(l, "miss") then "Provider Missed Trip"
        else if Text.Contains(l, "breakdown") or Text.Contains(l, "brkdwn") then "Vehicle Breakdown"
        else if Text.Contains(l, "unable") or Text.Contains(l, "utl") then "Unable to Locate Client"
        else if Text.Contains(l, "driver") then "Driver Unavailable"
        else "Other",

    MapBorough = (t as nullable text) as text =>
        let l = Lc(t) in
        if List.Contains({"mn", "manhattan"}, l) then "Manhattan"
        else if List.Contains({"bx", "bronx", "the bronx"}, l) then "Bronx"
        else if List.Contains({"bk", "bklyn", "brooklyn"}, l) then "Brooklyn"
        else if List.Contains({"qns", "queens"}, l) then "Queens"
        else if List.Contains({"si", "staten is.", "staten island"}, l) then "Staten Island"
        else if Text.Contains(l, "nassau") then "Nassau County"
        else if Text.Contains(l, "hudson") then "Hudson County NJ"
        else "Unknown",

    MapPurpose = (t as nullable text) as text =>
        let l = Lc(t) in
        if t = null then "Unknown"
        else if Text.StartsWith(l, "med") then "Medical"
        else if Text.StartsWith(l, "dial") then "Dialysis"
        else if Text.StartsWith(l, "work") or Text.StartsWith(l, "employ") then "Work"
        else if Text.StartsWith(l, "edu") then "Education/Training"
        else if Text.StartsWith(l, "shop") or Text.StartsWith(l, "errand") then "Shopping/Errand"
        else if Text.StartsWith(l, "soc") or Text.StartsWith(l, "rec") then "Social/Recreation"
        else if Text.StartsWith(l, "senior") then "Senior Center"
        else if Text.StartsWith(l, "other") or Text.StartsWith(l, "misc") then "Other"
        else "Unknown",

    MapVehicle = (t as nullable text) as text =>
        let l = Lc(t) in
        if t = null then "Unknown"
        else if Text.Contains(l, "lift") or Text.Contains(l, "wheelchair") then "Lift Van"
        else if Text.Contains(l, "mini") then "Minivan"
        else if Text.Contains(l, "sedan") then "Sedan"
        else if Text.Contains(l, "taxi") or l = "cab" then "Taxi"
        else "Other",

    MapChannel = (t as nullable text) as text =>
        let l = Lc(t) in
        if t = null then "Unknown"
        else if Text.Contains(l, "phone") then "Phone"
        else if Text.Contains(l, "web") or Text.Contains(l, "online") then "Web"
        else if Text.Contains(l, "app") then "App"
        else if Text.Contains(l, "ivr") or Text.Contains(l, "automated") then "IVR"
        else "Other",

    MapRegion = (t as nullable text) as text =>
        let l = Lc(t) in
        if Text.StartsWith(l, "n") then "North" else if Text.StartsWith(l, "e") then "East" else if Text.StartsWith(l, "s") then "South" else "Unknown",

    MapRawMode = (t as nullable text) as text =>
        let l = Lc(t) in
        if Text.StartsWith(l, "prim") then "Primary" else if Text.StartsWith(l, "brk") or Text.StartsWith(l, "brok") then "Broker"
        else if Text.StartsWith(l, "supp") then "Supplemental" else "Unknown",

    // Route: strip spaces and hyphens, remove the longest prefix first (ROUTE, RT, R), keep digits only
    RouteNumberOf = (t as nullable text) as nullable number =>
        if t = null then null else
        let
            u = Text.Upper(Text.Remove(t, {" ", "-"})),
            noPrefix = if Text.StartsWith(u, "ROUTE") then Text.Middle(u, 5)
                       else if Text.StartsWith(u, "RT") then Text.Middle(u, 2)
                       else if Text.StartsWith(u, "R") then Text.Middle(u, 1) else u,
            allDigits = noPrefix <> "" and Text.Length(Text.Select(noPrefix, {"0".."9"})) = Text.Length(noPrefix)
        in if allDigits then Number.FromText(noPrefix) else null,

    CleanZip = (t as nullable text) as record =>
        let
            s0 = if t = null then null else Text.Trim(t),
            s1 = if s0 <> null and Text.EndsWith(s0, ".0") then Text.Start(s0, Text.Length(s0) - 2) else s0,
            s2 = if s1 <> null and Text.Length(s1) = 10 and Text.At(s1, 5) = "-" then Text.Start(s1, 5) else s1,
            s3 = if s2 <> null and Text.Length(s2) = 4 and Text.StartsWith(s2, "7") then Text.PadStart(s2, 5, "0") else s2,
            isDigits = s3 <> null and Text.Length(Text.Select(s3, {"0".."9"})) = Text.Length(s3),
            ok = s3 <> null and Text.Length(s3) = 5 and isDigits and List.Contains({"07", "10", "11"}, Text.Start(s3, 2))
        in [Zip = if ok then s3 else null, Valid = ok],

    CleanCoords = (latT as nullable text, lonT as nullable text) as record =>
        let
            la0 = ParseNum(latT), lo0 = ParseNum(lonT),
            swapped = la0 <> null and lo0 <> null and la0 >= -74.30 and la0 <= -73.50 and lo0 >= 40.45 and lo0 <= 41.05,
            la = if swapped then lo0 else la0, lo = if swapped then la0 else lo0,
            ok = la <> null and lo <> null and la >= 40.45 and la <= 41.05 and lo >= -74.30 and lo <= -73.50
        in [Lat = if ok then la else null, Lon = if ok then lo else null, Valid = ok],

    // Money: remove $ and commas; null when blank or not numeric
    ParseMoney = (t as nullable text) as nullable number =>
        if t = null then null else ParseNum(Text.Remove(t, {"$", ","})),
    // Distance / duration: remove unit words; null when not numeric
    ParseWithUnits = (t as nullable text, units as list) as nullable number =>
        if t = null then null else
        let s = List.Accumulate(units, Text.Lower(t), (acc, u) => Text.Replace(acc, u, ""))
        in ParseNum(Text.Trim(s)),

    // ------------------------------- load and type ----------------------------------
    Source = Csv.Document(File.Contents(pFolder & "Trips.csv"), [Delimiter = ",", Columns = 43, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    AllText = Table.TransformColumnTypes(Promoted, List.Transform(Table.ColumnNames(Promoted), each {_, type text})),
    Trimmed = Table.TransformColumns(AllText, List.Transform(Table.ColumnNames(AllText), each {_, CleanText, type nullable text})),
    WithIdx = Table.AddIndexColumn(Trimmed, "RowIdx", 0, 1, Int64.Type),

    // ------------------------------- parse timestamps (keep invalid as null) --------
    TsCols = {"ScheduledPickupTime", "ScheduledDropoffTime", "PromiseTime", "ActualPickupTime", "ActualDropoffTime", "DriverArrivalTime", "VehicleArrivalTime"},
    Stamps = Table.TransformColumns(WithIdx, List.Transform(TsCols, each {_, ParseDT, type nullable datetime})),

    // ------------------------------- status ranking for duplicate resolution --------
    WithStatus = Table.AddColumn(Stamps, "TripStatus", each MapStatus([RawTripStatus]), type text),
    Scored = Table.AddColumn(WithStatus, "CompletenessScore", each
        List.NonNullCount({[ScheduledPickupTime], [ScheduledDropoffTime], [PromiseTime], [ActualPickupTime], [ActualDropoffTime], [DriverArrivalTime], [VehicleArrivalTime],
                           ParseMoney([RawFareAmount]), ParseWithUnits([RawDistanceMiles], {"miles", "mi"}), ParseWithUnits([RawTripDuration], {"min"})}), Int64.Type),
    RankCol = Table.AddColumn(Scored, "StatusRank", each if [TripStatus] = "Unresolved" then 0 else 1, Int64.Type),
    Sorted = Table.Sort(RankCol, {{"TripID", Order.Ascending}, {"StatusRank", Order.Descending}, {"CompletenessScore", Order.Descending}, {"RowIdx", Order.Ascending}}),
    Buffered = Table.Buffer(Sorted),
    Deduped = Table.Distinct(Buffered, {"TripID"}),

    // ------------------------------- ClientID and referential integrity -------------
    ClientFix = Table.TransformColumns(Deduped, {{"ClientID", each if _ = null then null else Text.Upper(_), type nullable text}}),
    // Merge (hash join) is far faster than List.Contains over 100,000 rows x 5,000 clients.
    ValidClients = Table.Buffer(Table.SelectColumns(Clients, {"ClientID"})),
    MergedCl = Table.NestedJoin(ClientFix, {"ClientID"}, ValidClients, {"ClientID"}, "CM", JoinKind.LeftOuter),
    ClientMatchedCol = Table.AddColumn(MergedCl, "ClientMatched", each [ClientID] <> null and Table.RowCount([CM]) > 0, type logical),
    ClientMatched = Table.RemoveColumns(ClientMatchedCol, {"CM"}),

    // ------------------------------- dates ------------------------------------------
    TripDateParsed = Table.AddColumn(ClientMatched, "TripDateParsed", each ParseDate([TripDate]), type nullable date),
    TripDateFinal = Table.AddColumn(TripDateParsed, "TripDateClean", each
        let inWin = (d as nullable date) => d <> null and d >= pDataStart and d <= pDataEnd,
            fb = if [ScheduledPickupTime] = null then null else DateTime.Date([ScheduledPickupTime])
        in if inWin([TripDateParsed]) then [TripDateParsed] else if inWin(fb) then fb else null, type nullable date),
    TripDateRepaired = Table.AddColumn(TripDateFinal, "TripDateWasRepaired", each [TripDateClean] <> null and [TripDateClean] <> [TripDateParsed], type logical),
    DropOldDate = Table.RemoveColumns(TripDateRepaired, {"TripDate", "TripDateParsed"}),
    RenDate = Table.RenameColumns(DropOldDate, {{"TripDateClean", "TripDate"}}),
    Booking = Table.TransformColumns(RenDate, {{"BookingDate", ParseDate, type nullable date}}),

    // ------------------------------- route -> RouteNumber -> Mode --------------------
    RouteNum = Table.AddColumn(Booking, "RouteNumber", each RouteNumberOf([RouteID]), Int64.Type),
    // CUSTOM-M version of the Conditional Column. Mode is derived from the cleaned route; RawServiceMode is NOT trusted.
    ModeCol = Table.AddColumn(RouteNum, "Mode", each
        if [RouteNumber] = null then "Unknown"
        else if [RouteNumber] >= 1000 and [RouteNumber] <= 1999 then "Primary"
        else if [RouteNumber] >= 2000 and [RouteNumber] <= 2999 then "Broker"
        else if [RouteNumber] >= 3000 and [RouteNumber] <= 3999 then "Supplemental"
        else "Unknown", type text),
    RouteLabel = Table.AddColumn(ModeCol, "RouteIDClean", each if [RouteNumber] = null then null else "R-" & Text.From([RouteNumber]), type nullable text),
    RouteDrop = Table.RemoveColumns(RouteLabel, {"RouteID"}),
    RouteRen = Table.RenameColumns(RouteDrop, {{"RouteIDClean", "RouteID"}, {"RawServiceMode", "RawServiceModeNorm0"}}),
    RawModeNorm = Table.TransformColumns(RouteRen, {{"RawServiceModeNorm0", MapRawMode, type text}}),
    RawModeRen = Table.RenameColumns(RawModeNorm, {{"RawServiceModeNorm0", "RawServiceModeNorm"}}),

    // ------------------------------- categorical cleanup ----------------------------
    Cats = Table.TransformColumns(RawModeRen, {
        {"Borough", MapBorough, type text}, {"TripPurpose", MapPurpose, type text}, {"VehicleType", MapVehicle, type text},
        {"BookingChannel", MapChannel, type text}, {"ServiceRegion", MapRegion, type text},
        {"ServiceProviderID", each if _ = null then "Unknown" else Text.Upper(_), type text}}),
    Reason = Table.AddColumn(Cats, "OutcomeReason", each MapReason([CancellationReason], [TripStatus]), type nullable text),
    NoShowInd = Table.AddColumn(Reason, "NoShowIndicator", each
        let l = Lc([NoShowIndicatorRaw]) in
        if List.Contains({"y", "1", "true", "yes"}, l) then true else if List.Contains({"n", "0", "false", "no"}, l) then false else null, type nullable logical),
    Conflict = Table.AddColumn(NoShowInd, "StatusIndicatorConflict", each
        ([TripStatus] = "No-Show" and [NoShowIndicator] = false) or ([TripStatus] <> "No-Show" and [NoShowIndicator] = true), type logical),

    // ------------------------------- ZIP and coordinates ----------------------------
    PZ = Table.AddColumn(Conflict, "PZ", each CleanZip([PickupZipCode])),
    PZx = Table.ExpandRecordColumn(PZ, "PZ", {"Zip", "Valid"}, {"PickupZip", "PickupZipIsValid"}),
    DZ = Table.AddColumn(PZx, "DZ", each CleanZip([DropoffZipCode])),
    DZx = Table.ExpandRecordColumn(DZ, "DZ", {"Zip", "Valid"}, {"DropoffZip", "DropoffZipIsValid"}),
    PC = Table.AddColumn(DZx, "PC", each CleanCoords([PickupLatitude], [PickupLongitude])),
    PCx = Table.ExpandRecordColumn(PC, "PC", {"Lat", "Lon", "Valid"}, {"PickupLat", "PickupLon", "PickupCoordsAreValid"}),
    DC = Table.AddColumn(PCx, "DC", each CleanCoords([DropoffLatitude], [DropoffLongitude])),
    DCx = Table.ExpandRecordColumn(DC, "DC", {"Lat", "Lon", "Valid"}, {"DropoffLat", "DropoffLon", "DropoffCoordsAreValid"}),
    GeoDrop = Table.RemoveColumns(DCx, {"PickupZipCode", "DropoffZipCode", "PickupLatitude", "PickupLongitude", "DropoffLatitude", "DropoffLongitude"}),
    GeoRen = Table.RenameColumns(GeoDrop, {{"PickupZip", "PickupZipCode"}, {"DropoffZip", "DropoffZipCode"}, {"PickupLat", "PickupLatitude"},
        {"PickupLon", "PickupLongitude"}, {"DropoffLat", "DropoffLatitude"}, {"DropoffLon", "DropoffLongitude"}}),

    // Privacy-safe coordinates for PUBLIC maps: 2 decimals is roughly 1 km. Use these on the map visuals.
    R1 = Table.AddColumn(GeoRen, "PickupLatitudeRounded", each if [PickupLatitude] = null then null else Number.Round([PickupLatitude], 2), type nullable number),
    R2 = Table.AddColumn(R1, "PickupLongitudeRounded", each if [PickupLongitude] = null then null else Number.Round([PickupLongitude], 2), type nullable number),
    R3 = Table.AddColumn(R2, "DropoffLatitudeRounded", each if [DropoffLatitude] = null then null else Number.Round([DropoffLatitude], 2), type nullable number),
    GeoRound = Table.AddColumn(R3, "DropoffLongitudeRounded", each if [DropoffLongitude] = null then null else Number.Round([DropoffLongitude], 2), type nullable number),

    // ------------------------------- money, distance, duration ----------------------
    Money = Table.AddColumn(GeoRound, "FareParsed", each ParseMoney([RawFareAmount]), type nullable number),
    FareOk = Table.AddColumn(Money, "FareIsValid", each [FareParsed] <> null and [FareParsed] >= 0 and [FareParsed] <= 150, type logical),
    RefParsed = Table.AddColumn(FareOk, "RefundParsed", each let r = ParseMoney([RawRefundAmount]) in if r = null then 0 else r, type number),
    RefOk = Table.AddColumn(RefParsed, "RefundIsValid", each [FareIsValid] and [RefundParsed] >= 0 and [RefundParsed] <= [FareParsed], type logical),
    EligFare = Table.AddColumn(RefOk, "EligibleFare", each if [TripStatus] = "Completed" and [FareIsValid] then [FareParsed] else 0, type number),
    EligRef = Table.AddColumn(EligFare, "EligibleRefund", each if [TripStatus] = "Completed" and [FareIsValid] and [RefundIsValid] then [RefundParsed] else 0, type number),
    Dist = Table.AddColumn(EligRef, "DistParsed", each ParseWithUnits([RawDistanceMiles], {"miles", "mi"}), type nullable number),
    DistOk = Table.AddColumn(Dist, "DistanceIsValid", each [DistParsed] <> null and [DistParsed] > 0 and [DistParsed] <= 100, type logical),
    DistFinal = Table.AddColumn(DistOk, "DistanceMiles", each if [DistanceIsValid] then [DistParsed] else null, type nullable number),
    Dur = Table.AddColumn(DistFinal, "DurParsed", each ParseWithUnits([RawTripDuration], {"min"}), type nullable number),
    DurTs = Table.AddColumn(Dur, "DurFromTs", each
        let m = Minutes([ActualDropoffTime], [ActualPickupTime]) in if m <> null and m > 0 and m <= 240 then m else null, type nullable number),
    DurOk = Table.AddColumn(DurTs, "DurationIsValid", each [DurParsed] <> null and [DurParsed] > 0 and [DurParsed] <= 240, type logical),
    DurFinal = Table.AddColumn(DurOk, "TripDurationMinutes", each if [DurationIsValid] then [DurParsed] else [DurFromTs], type nullable number),
    DurSrc = Table.AddColumn(DurFinal, "TripDurationSource", each if [DurationIsValid] then "Raw field" else if [DurFromTs] <> null then "From timestamps" else "Unavailable", type text),
    PaxFix = Table.TransformColumns(DurSrc, {
        {"ScheduledPassengerCount", each let n = ParseNum(_) in if n <> null and n >= 1 and n <= 8 then n else null, Int64.Type},
        {"ActualPassengerCount", each let n = ParseNum(_) in if n <> null and n >= 0 and n <= 8 then n else null, Int64.Type},
        {"ScheduledDurationMinutes", each ParseNum(_), Int64.Type}}),

    // ------------------------------- PICKUP DELAY (full timestamps) -----------------
    // PickupDelayMinutes = ActualPickupTime - PromiseTime, in minutes. Positive = late. Negative = early.
    Delay = Table.AddColumn(PaxFix, "PickupDelayMinutes", each Minutes([ActualPickupTime], [PromiseTime]), type nullable number),
    DelayOk = Table.AddColumn(Delay, "PickupDelayIsValid", each [PickupDelayMinutes] <> null and [PickupDelayMinutes] >= -180 and [PickupDelayMinutes] <= 360, type logical),
    DropDelay = Table.AddColumn(DelayOk, "DropoffDelayMinutes", each
        if [TripStatus] = "Completed" then Minutes([ActualDropoffTime], [ScheduledDropoffTime]) else null, type nullable number),
    OtpElig = Table.AddColumn(DropDelay, "OTPEligibility", each
        if [TripStatus] <> "Completed" then "Not a completed trip"
        else if [PromiseTime] = null then "Missing/invalid PromiseTime"
        else if [ActualPickupTime] = null then "Missing/invalid ActualPickupTime"
        else if not [PickupDelayIsValid] then "Pickup delay out of valid range"
        else "Eligible", type text),
    OtpFlag = Table.AddColumn(OtpElig, "IsPickupOTPEligible", each [OTPEligibility] = "Eligible", type logical),
    DelayBand = Table.AddColumn(OtpFlag, "PickupDelayBand", each
        if not [IsPickupOTPEligible] then "Not Measured"
        else if [PickupDelayMinutes] < -15 then "More than 15 min early"
        else if [PickupDelayMinutes] <= 0 then "Early / on time"
        else if [PickupDelayMinutes] <= 15 then "1-15 min late"
        else if [PickupDelayMinutes] <= 20 then "16-20 min late"
        else if [PickupDelayMinutes] <= 45 then "21-45 min late"
        else "More than 45 min late", type text),
    DelayBandSort = Table.AddColumn(DelayBand, "PickupDelayBandSort", each
        if not [IsPickupOTPEligible] then 9 else if [PickupDelayMinutes] < -15 then 1 else if [PickupDelayMinutes] <= 0 then 2
        else if [PickupDelayMinutes] <= 15 then 3 else if [PickupDelayMinutes] <= 20 then 4 else if [PickupDelayMinutes] <= 45 then 5 else 6, Int64.Type),

    // ------------------------------- calendar attributes ----------------------------
    Dow = Table.AddColumn(DelayBandSort, "DayOfWeekNumber", each if [TripDate] = null then null else Date.DayOfWeek([TripDate], Day.Monday) + 1, Int64.Type),
    DowName = Table.AddColumn(Dow, "DayOfWeekName", each if [TripDate] = null then null else Date.DayOfWeekName([TripDate], "en-US"), type nullable text),
    Wknd = Table.AddColumn(DowName, "IsWeekend", each [DayOfWeekNumber] <> null and [DayOfWeekNumber] >= 6, type logical),
    Hr = Table.AddColumn(Wknd, "PickupHour", each if [ScheduledPickupTime] = null then null else Time.Hour(DateTime.Time([ScheduledPickupTime])), Int64.Type),
    Period = Table.AddColumn(Hr, "TimePeriod", each
        if [PickupHour] = null then "Unknown"
        else if not [IsWeekend] and (([PickupHour] >= 6 and [PickupHour] <= 9) or ([PickupHour] >= 15 and [PickupHour] <= 18)) then "Peak"
        else "Off-Peak", type text),
    MonthStart = Table.AddColumn(Period, "MonthStart", each if [TripDate] = null then null else Date.StartOfMonth([TripDate]), type nullable date),
    MonthLbl = Table.AddColumn(MonthStart, "MonthLabel", each if [MonthStart] = null then null else Date.ToText([MonthStart], "yyyy-MM"), type nullable text),

    // ------------------------------- validity and outcome classification ------------
    Valid = Table.AddColumn(MonthLbl, "IsValidScheduledTrip", each [TripDate] <> null and [TripStatus] <> "Unresolved", type logical),
    Outcome = Table.AddColumn(Valid, "ServiceOutcome", each
        if [TripStatus] = "Completed" then (if [IsPickupOTPEligible] and [PickupDelayMinutes] <= 15 then "Served - On Time" else if [IsPickupOTPEligible] then "Served - Late" else "Served - Timing Unknown")
        else if [TripStatus] = "No-Show" then "Passenger No-Show"
        else if [TripStatus] = "Cancelled" then "Cancelled"
        else if [TripStatus] = "Failed/Other" then "Service Failure"
        else "Unresolved", type text),
    Anomaly = Table.AddColumn(Outcome, "AnomalyFlags", each
        let r = Text.Combine(List.Select({
            if [TripStatus] = "Completed" and [DistParsed] <> null and not [DistanceIsValid] then "Distance" else null,
            if [TripStatus] = "Completed" and [DurParsed] <> null and not [DurationIsValid] then "Duration" else null,
            if [PickupDelayMinutes] <> null and not [PickupDelayIsValid] then "PickupDelay" else null,
            if [FareParsed] <> null and not [FareIsValid] then "Fare" else null,
            if [FareIsValid] and not [RefundIsValid] then "Refund" else null}, each _ <> null), "; ")
        in if r = "" then null else r, type nullable text),

    // ------------------------------- final shape ------------------------------------
    Selected = Table.SelectColumns(Anomaly, {
        "TripID", "ClientID", "BookingID", "TripDate", "MonthStart", "MonthLabel", "BookingDate",
        "ScheduledPickupTime", "ScheduledDropoffTime", "PromiseTime", "ActualPickupTime", "ActualDropoffTime", "VehicleArrivalTime", "DriverArrivalTime",
        "ScheduledDurationMinutes", "TripPurpose", "TripStatus", "OutcomeReason", "NoShowIndicator", "StatusIndicatorConflict",
        "RouteID", "RouteNumber", "Mode", "RouteDescription", "RawServiceModeNorm", "ServiceProviderID", "VehicleType", "ServiceRegion", "Borough", "BookingChannel",
        "PickupAddress", "PickupZipCode", "PickupLatitude", "PickupLongitude", "DropoffAddress", "DropoffZipCode", "DropoffLatitude", "DropoffLongitude",
        "PickupLatitudeRounded", "PickupLongitudeRounded", "DropoffLatitudeRounded", "DropoffLongitudeRounded",
        "PickupZipIsValid", "DropoffZipIsValid", "PickupCoordsAreValid", "DropoffCoordsAreValid",
        "ScheduledPassengerCount", "ActualPassengerCount", "FareParsed", "RefundParsed", "FareIsValid", "RefundIsValid", "EligibleFare", "EligibleRefund",
        "DistanceMiles", "DistanceIsValid", "TripDurationMinutes", "DurationIsValid", "TripDurationSource",
        "PickupDelayMinutes", "PickupDelayIsValid", "DropoffDelayMinutes", "OTPEligibility", "IsPickupOTPEligible", "PickupDelayBand", "PickupDelayBandSort",
        "DayOfWeekNumber", "DayOfWeekName", "IsWeekend", "PickupHour", "TimePeriod",
        "ClientMatched", "TripDateWasRepaired", "IsValidScheduledTrip", "ServiceOutcome", "AnomalyFlags"}),
    Renamed = Table.RenameColumns(Selected, {{"FareParsed", "FareAmount"}, {"RefundParsed", "RefundAmount"}}),
    // ServiceDayType is recomputed from TripDate (DayOfWeekName / IsWeekend), so the raw column is dropped.
    Typed = Table.TransformColumnTypes(Renamed, {
        {"TripDate", type date}, {"MonthStart", type date}, {"BookingDate", type date}, {"ScheduledPickupTime", type datetime}, {"ScheduledDropoffTime", type datetime},
        {"PromiseTime", type datetime}, {"ActualPickupTime", type datetime}, {"ActualDropoffTime", type datetime}, {"VehicleArrivalTime", type datetime}, {"DriverArrivalTime", type datetime},
        {"PickupZipCode", type text}, {"DropoffZipCode", type text}, {"PickupLatitude", type number}, {"PickupLongitude", type number}, {"DropoffLatitude", type number}, {"DropoffLongitude", type number},
        {"FareAmount", Currency.Type}, {"RefundAmount", Currency.Type}, {"EligibleFare", Currency.Type}, {"EligibleRefund", Currency.Type},
        {"DistanceMiles", type number}, {"TripDurationMinutes", type number}, {"PickupDelayMinutes", type number}, {"DropoffDelayMinutes", type number}, {"RouteNumber", Int64.Type}})
in
    Typed
