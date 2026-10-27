// =====================================================================================
// QUERY NAME: Clients
// Needs these Power Query parameters (Home > Manage Parameters):
//   pFolder   (Text)  e.g.  C:\Paratransit\      (keep the trailing backslash)
//   pAsOfDate (Date)  2026-09-30                 (age reference date)
// Paste into: Home > Advanced Editor (replace everything), then Done.
// =====================================================================================
let
    // ------------------------------- helper functions --------------------------------
    // Trim, remove control characters, turn blank tokens into null
    CleanText = (t as nullable text) as nullable text =>
        let s = if t = null then null else Text.Trim(Text.Clean(t))
        in if s = null or List.Contains({"", "n/a", "null", "-"}, Text.Lower(s)) then null else s,

    Lc = (t as nullable text) as text => if t = null then "" else Text.Lower(t),

    ParseDate = (t as nullable text) as nullable date =>
        if t = null then null
        else try Date.FromText(t, [Format = "yyyy-MM-dd", Culture = "en-US"]) otherwise null,

    ParseNum = (t as nullable text) as nullable number =>
        if t = null then null else try Number.FromText(t, "en-US") otherwise null,

    // Completed years as of a reference date (accounts for whether the birthday has happened yet)
    AgeAsOf = (dob as date, asOf as date) as number =>
        Date.Year(asOf) - Date.Year(dob)
        - (if Date.Month(asOf) * 100 + Date.Day(asOf) < Date.Month(dob) * 100 + Date.Day(dob) then 1 else 0),

    MapClientType = (t as nullable text) as text =>
        let l = Lc(t) in
        if l = "" then "Unknown"
        else if Text.Contains(l, "ada") or Text.Contains(l, "a.d.a") then "ADA Paratransit"
        else if Text.Contains(l, "medicaid") then "Medicaid"
        else if Text.Contains(l, "senior") then "Senior Program"
        else if Text.Contains(l, "visitor") then "Visitor"
        else "Unknown",

    // "uncond" must be tested before "cond" because "unconditional" contains "cond"
    MapEligibility = (t as nullable text) as text =>
        let l = Lc(t) in
        if l = "" then "Unknown"
        else if Text.Contains(l, "uncond") then "Unconditional"
        else if Text.Contains(l, "cond") then "Conditional"
        else if Text.Contains(l, "temp") then "Temporary"
        else if Text.Contains(l, "visitor") then "Visitor"
        else "Unknown",

    MapClientStatus = (t as nullable text) as text =>
        let l = Lc(t) in
        if List.Contains({"active", "a", "act", "1"}, l) then "Active"
        else if List.Contains({"inactive", "i", "inact", "0"}, l) then "Inactive"
        else if List.Contains({"suspended", "s", "susp"}, l) then "Suspended"
        else "Unknown",

    MapGender = (t as nullable text) as text =>
        let l = Lc(t) in
        if t = null then "Not Provided"
        else if List.Contains({"m", "male"}, l) then "Male"
        else if List.Contains({"f", "female"}, l) then "Female"
        else if List.Contains({"nb", "non-binary", "x"}, l) then "Non-binary"
        else "Unknown",

    MapMobility = (t as nullable text) as text =>
        let l = Lc(t) in
        if t = null then "Not Provided"
        else if Text.Contains(l, "wheel") or Text.Contains(l, "w/c") or Text.Contains(l, "power chair") then "Wheelchair"
        else if Text.Contains(l, "walker") or Text.Contains(l, "rollator") then "Walker"
        else if Text.Contains(l, "cane") then "Cane"
        else if List.Contains({"none", "no aid"}, l) then "None"
        else "Other",

    MapLanguage = (t as nullable text) as text =>
        let l = Lc(t) in
        if t = null then "Not Provided"
        else if Text.StartsWith(l, "en") then "English"
        else if Text.StartsWith(l, "es") then "Spanish"
        else if Text.StartsWith(l, "chi") or List.Contains({"mandarin", "cantonese"}, l) then "Chinese"
        else if Text.StartsWith(l, "rus") then "Russian"
        else if Text.StartsWith(l, "hai") or Text.Contains(l, "creole") then "Haitian Creole"
        else if Text.StartsWith(l, "ben") or Text.Contains(l, "bangla") then "Bengali"
        else if Text.StartsWith(l, "kor") then "Korean"
        else if Text.StartsWith(l, "ara") then "Arabic"
        else "Other",

    MapContact = (t as nullable text) as text =>
        let l = Lc(t) in
        if t = null then "Not Provided"
        else if Text.Contains(l, "phone") or Text.Contains(l, "call") then "Phone"
        else if Text.Contains(l, "sms") or Text.Contains(l, "text") then "SMS"
        else if Text.Contains(l, "e-mail") or Text.Contains(l, "email") then "Email"
        else if Text.Contains(l, "mail") or Text.Contains(l, "postal") then "Mail"
        else "Other",

    MapCity = (t as nullable text) as nullable text =>
        let l = Lc(t) in
        if t = null then null
        else if List.Contains({"new york", "new york city", "nyc", "manhattan"}, l) then "New York"
        else if List.Contains({"bronx", "the bronx"}, l) then "Bronx"
        else if List.Contains({"brooklyn", "bklyn"}, l) then "Brooklyn"
        else if List.Contains({"staten island", "staten is.", "s.i."}, l) then "Staten Island"
        else Text.Proper(t),

    MapState = (t as nullable text) as nullable text =>
        let l = Lc(t) in
        if List.Contains({"ny", "new york", "n.y."}, l) then "NY"
        else if List.Contains({"nj", "new jersey", "n.j."}, l) then "NJ"
        else null,

    SuffixMap = {{"st", "Street"}, {"ave", "Avenue"}, {"rd", "Road"}, {"pl", "Place"}, {"blvd", "Boulevard"}, {"ln", "Lane"}, {"ct", "Court"}},
    CleanAddress = (t as nullable text) as nullable text =>
        if t = null then null else
        let
            tokens = List.Select(Text.Split(t, " "), each _ <> ""),
            fixedTokens = List.Transform(tokens, (tok) =>
                let k = Text.Lower(Text.Remove(tok, {"."})),
                    hit = List.First(List.Select(SuffixMap, (p) => p{0} = k), null)
                in if hit = null then Text.Proper(tok) else hit{1})
        in Text.Combine(fixedTokens, " "),

    // ZIP stays TEXT. Returns [Zip, Valid]
    CleanZip = (t as nullable text) as record =>
        let
            s0 = if t = null then null else Text.Trim(t),
            s1 = if s0 <> null and Text.EndsWith(s0, ".0") then Text.Start(s0, Text.Length(s0) - 2) else s0,
            s2 = if s1 <> null and Text.Length(s1) = 10 and Text.At(s1, 5) = "-" then Text.Start(s1, 5) else s1,
            s3 = if s2 <> null and Text.Length(s2) = 4 and Text.StartsWith(s2, "7") then Text.PadStart(s2, 5, "0") else s2,
            isDigits = s3 <> null and Text.Length(Text.Select(s3, {"0".."9"})) = Text.Length(s3),
            ok = s3 <> null and Text.Length(s3) = 5 and isDigits and List.Contains({"07", "10", "11"}, Text.Start(s3, 2))
        in [Zip = if ok then s3 else null, Valid = ok],

    // Coordinates: numeric parse, auto-fix obviously swapped lat/lon, validate against the NYC-area box
    CleanCoords = (latT as nullable text, lonT as nullable text) as record =>
        let
            la0 = ParseNum(latT),
            lo0 = ParseNum(lonT),
            swapped = la0 <> null and lo0 <> null and la0 >= -74.30 and la0 <= -73.50 and lo0 >= 40.45 and lo0 <= 41.05,
            la = if swapped then lo0 else la0,
            lo = if swapped then la0 else lo0,
            ok = la <> null and lo <> null and la >= 40.45 and la <= 41.05 and lo >= -74.30 and lo <= -73.50
        in [Lat = if ok then la else null, Lon = if ok then lo else null, Valid = ok],

    // ------------------------------- load and type ----------------------------------
    Source = Csv.Document(File.Contents(pFolder & "Clients.csv"), [Delimiter = ",", Columns = 16, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    AllText = Table.TransformColumnTypes(Promoted, List.Transform(Table.ColumnNames(Promoted), each {_, type text})),

    // ------------------------------- text hygiene -----------------------------------
    Trimmed = Table.TransformColumns(AllText, List.Transform(Table.ColumnNames(AllText), each {_, CleanText, type nullable text})),
    WithIdx = Table.AddIndexColumn(Trimmed, "RowIdx", 0, 1, Int64.Type),
    KeyUpper = Table.TransformColumns(WithIdx, {{"ClientID", each if _ = null then null else Text.Upper(_), type text}}),

    // ------------------------------- duplicate ClientIDs ----------------------------
    AttrCols = List.RemoveItems(Table.ColumnNames(AllText), {"ClientID"}),
    Scored = Table.AddColumn(KeyUpper, "CompletenessScore", each List.NonNullCount(Record.FieldValues(Record.SelectFields(_, AttrCols))), Int64.Type),
    Sorted = Table.Sort(Scored, {{"ClientID", Order.Ascending}, {"CompletenessScore", Order.Descending}, {"RowIdx", Order.Ascending}}),
    Buffered = Table.Buffer(Sorted),
    SourceCounts = Table.Group(Buffered, {"ClientID"}, {{"SourceRowCount", each Table.RowCount(_), Int64.Type}}),
    Deduped = Table.Distinct(Buffered, {"ClientID"}),
    Joined = Table.NestedJoin(Deduped, {"ClientID"}, SourceCounts, {"ClientID"}, "Cnt", JoinKind.LeftOuter),
    WithCount = Table.ExpandTableColumn(Joined, "Cnt", {"SourceRowCount"}),

    // ------------------------------- standardise categories -------------------------
    Mapped = Table.TransformColumns(WithCount, {
        {"ClientType", MapClientType, type text},
        {"EligibilityCategory", MapEligibility, type text},
        {"Gender", MapGender, type text},
        {"MobilityAid", MapMobility, type text},
        {"PreferredLanguage", MapLanguage, type text},
        {"PreferredContactMethod", MapContact, type text},
        {"ClientStatus", MapClientStatus, type text},
        {"HomeCity", MapCity, type nullable text},
        {"HomeState", MapState, type nullable text},
        {"HomeAddressLine", CleanAddress, type nullable text}}),

    // ------------------------------- ZIP and coordinates ----------------------------
    ZipRec = Table.AddColumn(Mapped, "ZipRec", each CleanZip([HomeZipCode])),
    ZipExp = Table.ExpandRecordColumn(ZipRec, "ZipRec", {"Zip", "Valid"}, {"HomeZipClean", "HomeZipIsValid"}),
    ZipDrop = Table.RemoveColumns(ZipExp, {"HomeZipCode"}),
    ZipRen = Table.RenameColumns(ZipDrop, {{"HomeZipClean", "HomeZipCode"}}),
    CoRec = Table.AddColumn(ZipRen, "CoRec", each CleanCoords([HomeLatitude], [HomeLongitude])),
    CoExp = Table.ExpandRecordColumn(CoRec, "CoRec", {"Lat", "Lon", "Valid"}, {"LatClean", "LonClean", "HomeCoordsAreValid"}),
    CoDrop = Table.RemoveColumns(CoExp, {"HomeLatitude", "HomeLongitude"}),
    CoRen = Table.RenameColumns(CoDrop, {{"LatClean", "HomeLatitude"}, {"LonClean", "HomeLongitude"}}),

    // ------------------------------- dates, Age, AgeGroup ---------------------------
    DobParsed = Table.AddColumn(CoRen, "DobParsed", each ParseDate([DateOfBirth]), type nullable date),
    RegParsed = Table.AddColumn(DobParsed, "RegParsed", each ParseDate([RegistrationDate]), type nullable date),
    AgeRaw = Table.AddColumn(RegParsed, "AgeRaw", each if [DobParsed] = null then null else AgeAsOf([DobParsed], pAsOfDate), type nullable number),
    DobOk = Table.AddColumn(AgeRaw, "DateOfBirthIsValid",
        each [DobParsed] <> null and [DobParsed] <= pAsOfDate and [AgeRaw] <= 110 and [AgeRaw] >= 0, type logical),
    RegOk = Table.AddColumn(DobOk, "RegistrationDateIsValid",
        each [RegParsed] <> null and [RegParsed] <= pAsOfDate and not ([DateOfBirthIsValid] and [RegParsed] < [DobParsed]), type logical),

    // data-quality flags (built while the raw text columns still exist)
    Flags = Table.AddColumn(RegOk, "DataQualityFlags", each
        let r = Text.Combine(List.Select({
            if [DateOfBirth] = null then "DOB missing" else if [DobParsed] = null then "DOB unparseable" else if not [DateOfBirthIsValid] then "DOB implausible" else null,
            if [RegistrationDate] = null then "Registration missing" else if [RegParsed] = null then "Registration unparseable" else if not [RegistrationDateIsValid] then "Registration invalid" else null,
            if not [HomeZipIsValid] then "ZIP invalid" else null,
            if not [HomeCoordsAreValid] then "Coordinates invalid" else null,
            if [ClientStatus] = "Unknown" then "Status unknown" else null}, each _ <> null), "; ")
        in if r = "" then null else r, type nullable text),

    DropRawDates = Table.RemoveColumns(Flags, {"DateOfBirth", "RegistrationDate"}),
    AddDob = Table.AddColumn(DropRawDates, "DateOfBirth", each if [DateOfBirthIsValid] then [DobParsed] else null, type nullable date),
    AddReg = Table.AddColumn(AddDob, "RegistrationDate", each if [RegistrationDateIsValid] then [RegParsed] else null, type nullable date),
    AddAge = Table.AddColumn(AddReg, "Age", each if [DateOfBirthIsValid] then [AgeRaw] else null, Int64.Type),
    AddGroup = Table.AddColumn(AddAge, "AgeGroup", each
        if [Age] = null then "Unknown"
        else if [Age] < 18 then "Under 18"
        else if [Age] <= 24 then "18-24"
        else if [Age] <= 44 then "25-44"
        else if [Age] <= 64 then "45-64"
        else "65+", type text),
    AddSort = Table.AddColumn(AddGroup, "AgeGroupSort", each
        if [Age] = null then 9 else if [Age] < 18 then 1 else if [Age] <= 24 then 2 else if [Age] <= 44 then 3 else if [Age] <= 64 then 4 else 5, Int64.Type),

    // ------------------------------- final shape ------------------------------------
    Selected = Table.SelectColumns(AddSort, {
        "ClientID", "DateOfBirth", "Age", "AgeGroup", "AgeGroupSort", "RegistrationDate", "ClientType", "EligibilityCategory",
        "Gender", "HomeAddressLine", "HomeCity", "HomeState", "HomeZipCode", "HomeLatitude", "HomeLongitude",
        "PreferredLanguage", "MobilityAid", "ClientStatus", "PreferredContactMethod",
        "DateOfBirthIsValid", "RegistrationDateIsValid", "HomeZipIsValid", "HomeCoordsAreValid", "DataQualityFlags", "SourceRowCount"}),
    Typed = Table.TransformColumnTypes(Selected, {
        {"ClientID", type text}, {"DateOfBirth", type date}, {"Age", Int64.Type}, {"AgeGroup", type text}, {"AgeGroupSort", Int64.Type},
        {"RegistrationDate", type date}, {"HomeLatitude", type number}, {"HomeLongitude", type number}, {"HomeZipCode", type text},
        {"DateOfBirthIsValid", type logical}, {"RegistrationDateIsValid", type logical}, {"HomeZipIsValid", type logical},
        {"HomeCoordsAreValid", type logical}, {"SourceRowCount", Int64.Type}})
in
    Typed
