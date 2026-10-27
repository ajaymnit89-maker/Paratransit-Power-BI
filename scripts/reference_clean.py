#!/usr/bin/env python3
"""
Reference implementation (pandas) of the cleaning rules documented in the Power Query guide.
Purpose: (1) audit the RAW CSVs, (2) produce an independent "answer key" so you can check your Power BI numbers.
Usage: python3 reference_clean.py <dir containing Clients.csv and Trips.csv> [json_out]
"""
import sys, json, re
import numpy as np
import pandas as pd

D = sys.argv[1] if len(sys.argv) > 1 else "."
AS_OF = pd.Timestamp("2026-09-30")
WIN_START, WIN_END = pd.Timestamp("2025-10-01"), pd.Timestamp("2026-09-30")
BL = {"", "n/a", "null", "-"}

def tx(v):
    s = str(v).strip() if pd.notna(v) else ""
    return None if s.lower() in BL else s

def low(v):
    t = tx(v)
    return None if t is None else t.lower()

# ------------------------------------------------------------------ mappings (mirrors the M code)
def m_ctype(v):
    l = low(v)
    if l is None: return "Unknown"
    if "ada" in l or "a.d.a" in l: return "ADA Paratransit"
    if "medicaid" in l: return "Medicaid"
    if "senior" in l: return "Senior Program"
    if "visitor" in l: return "Visitor"
    return "Unknown"

def m_elig(v):
    l = low(v)
    if l is None: return "Unknown"
    if "uncond" in l: return "Unconditional"
    if "cond" in l: return "Conditional"
    if "temp" in l: return "Temporary"
    if "visitor" in l: return "Visitor"
    return "Unknown"

def m_cstatus(v):
    l = low(v)
    if l in ("active", "a", "act", "1"): return "Active"
    if l in ("inactive", "i", "inact", "0"): return "Inactive"
    if l in ("suspended", "s", "susp"): return "Suspended"
    return "Unknown"

def m_gender(v):
    l = low(v)
    if l is None: return "Not Provided"
    if l in ("m", "male"): return "Male"
    if l in ("f", "female"): return "Female"
    if l in ("nb", "non-binary", "x"): return "Non-binary"
    return "Unknown"

def m_mob(v):
    l = low(v)
    if l is None: return "Not Provided"
    if "wheel" in l or "w/c" in l or "power chair" in l: return "Wheelchair"
    if "walker" in l or "rollator" in l: return "Walker"
    if "cane" in l: return "Cane"
    if l in ("none", "no aid"): return "None"
    return "Other"

def m_lang(v):
    l = low(v)
    if l is None: return "Not Provided"
    if l.startswith("en"): return "English"
    if l.startswith("es") or l.startswith("esp"): return "Spanish"
    if l.startswith("chi") or l in ("mandarin", "cantonese"): return "Chinese"
    if l.startswith("rus"): return "Russian"
    if l.startswith("hai") or "creole" in l: return "Haitian Creole"
    if l.startswith("ben") or "bangla" in l: return "Bengali"
    if l.startswith("kor"): return "Korean"
    if l.startswith("ara"): return "Arabic"
    return "Other"

def m_contact(v):
    l = low(v)
    if l is None: return "Not Provided"
    if "phone" in l or "call" in l: return "Phone"
    if "sms" in l or "text" in l: return "SMS"
    if "e-mail" in l or "email" in l: return "Email"
    if "mail" in l or "postal" in l: return "Mail"
    return "Other"

def m_city(v):
    l = low(v)
    if l is None: return None
    if l in ("new york", "new york city", "nyc", "manhattan"): return "New York"
    if l in ("bronx", "the bronx"): return "Bronx"
    if l in ("brooklyn", "bklyn"): return "Brooklyn"
    if l in ("staten island", "staten is.", "s.i."): return "Staten Island"
    return str(tx(v)).title()

def m_state(v):
    l = low(v)
    if l in ("ny", "new york", "n.y."): return "NY"
    if l in ("nj", "new jersey", "n.j."): return "NJ"
    return None

def m_zip(v):
    s = tx(v)
    if s is None: return (None, False)
    s = s.replace(".0", "") if s.endswith(".0") else s
    if len(s) == 10 and s[5] == "-": s = s[:5]
    if len(s) == 4 and s[0] == "7": s = s.zfill(5)
    ok = len(s) == 5 and s.isdigit() and s[:2] in ("07", "10", "11")
    return (s if ok else None, ok)

def parse_date(s):
    return pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")

def num(v):
    try:
        return float(v)
    except Exception:
        return np.nan

def coords(lat, lon):
    la, lo = num(lat), num(lon)
    swapped = False
    if not np.isnan(la) and not np.isnan(lo) and -74.30 <= la <= -73.50 and 40.45 <= lo <= 41.05:
        la, lo, swapped = lo, la, True
    ok = (not np.isnan(la)) and (not np.isnan(lo)) and 40.45 <= la <= 41.05 and -74.30 <= lo <= -73.50
    return (la if ok else np.nan, lo if ok else np.nan, ok, swapped)

# ================================================================== CLIENTS
cr = pd.read_csv(f"{D}/Clients.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
out = {"clients": {}, "trips": {}}
C = out["clients"]
C["raw_rows"] = len(cr)
C["distinct_clientids_raw"] = int(cr.ClientID.nunique())
dups = cr[cr.duplicated("ClientID", keep=False)]
C["rows_with_duplicated_clientid"] = len(dups)
C["exact_duplicate_rows"] = int(cr.duplicated(keep="first").sum())
C["conflicting_duplicate_rows"] = int(cr.duplicated("ClientID", keep="first").sum() - cr.duplicated(keep="first").sum())
for col in ["Gender", "MobilityAid", "PreferredLanguage", "PreferredContactMethod", "HomeAddressLine", "HomeCity", "HomeState",
            "HomeZipCode", "DateOfBirth", "RegistrationDate", "HomeLatitude"]:
    C[f"blank_or_null_token__{col}"] = int(cr[col].map(lambda v: tx(v) is None).sum())

cr["RowIdx"] = np.arange(len(cr))
cl = pd.DataFrame({"ClientID": cr.ClientID.str.strip().str.upper(), "RowIdx": cr.RowIdx})
cl["ClientType"] = cr.ClientType.map(m_ctype)
cl["EligibilityCategory"] = cr.EligibilityCategory.map(m_elig)
cl["Gender"] = cr.Gender.map(m_gender)
cl["MobilityAid"] = cr.MobilityAid.map(m_mob)
cl["PreferredLanguage"] = cr.PreferredLanguage.map(m_lang)
cl["PreferredContactMethod"] = cr.PreferredContactMethod.map(m_contact)
cl["ClientStatus"] = cr.ClientStatus.map(m_cstatus)
cl["HomeCity"] = cr.HomeCity.map(m_city)
cl["HomeState"] = cr.HomeState.map(m_state)
z = cr.HomeZipCode.map(m_zip)
cl["HomeZipCode"] = z.map(lambda t: t[0]); cl["HomeZipValid"] = z.map(lambda t: t[1])
dob = parse_date(cr.DateOfBirth.map(lambda v: tx(v) or ""))
reg = parse_date(cr.RegistrationDate.map(lambda v: tx(v) or ""))
cl["DateOfBirthRaw_parsed"] = dob
# DOB validity: parseable, not in future, age <= 110
age = (AS_OF.year - dob.dt.year) - (((AS_OF.month * 100 + AS_OF.day) < (dob.dt.month * 100 + dob.dt.day)).astype(int))
dob_ok = dob.notna() & (dob <= AS_OF) & (age <= 110) & (age >= 0)
cl["DateOfBirth"] = dob.where(dob_ok)
cl["Age"] = age.where(dob_ok)
cl["DobValid"] = dob_ok
bins = [-1, 17, 24, 44, 64, 500]
labels = ["Under 18", "18-24", "25-44", "45-64", "65+"]
cl["AgeGroup"] = pd.cut(cl.Age, bins=bins, labels=labels).astype(object).where(cl.Age.notna(), "Unknown")
reg_before_dob = reg.notna() & dob_ok & (reg < dob)
reg_ok = reg.notna() & (reg <= AS_OF) & ~reg_before_dob
cl["RegistrationDate"] = reg.where(reg_ok)
cl["RegBeforeDOB"] = reg_before_dob
cl["RegValid"] = reg_ok
cc = [coords(a, b) for a, b in zip(cr.HomeLatitude, cr.HomeLongitude)]
cl["HomeLatitude"] = [c[0] for c in cc]; cl["HomeLongitude"] = [c[1] for c in cc]
cl["HomeCoordsValid"] = [c[2] for c in cc]; cl["HomeCoordsSwapped"] = [c[3] for c in cc]
raw_attr = [c for c in cr.columns if c not in ("ClientID", "RowIdx")]
cl["Score"] = cr[raw_attr].apply(lambda col: col.map(lambda v: tx(v) is not None)).sum(axis=1)
cl = cl.sort_values(["ClientID", "Score", "RowIdx"], ascending=[True, False, True])
cl_dedup = cl.drop_duplicates("ClientID", keep="first").copy()
cl = cl.sort_index()
# bad data counts
C["dob_missing_or_unparseable"] = int((dob.isna()).sum())
C["dob_future_or_implausible"] = int((dob.notna() & ~dob_ok).sum())
C["registration_before_dob"] = int(reg_before_dob.sum())
C["registration_future"] = int((reg.notna() & (reg > AS_OF)).sum())
C["registration_missing_or_unparseable"] = int(reg.isna().sum())
C["zip_needs_cleanup_but_fixable"] = int(((cr.HomeZipCode.str.strip() != cl.HomeZipCode.fillna("")) & cl.HomeZipValid & cr.HomeZipCode.map(lambda v: tx(v) is not None)).sum())
C["zip_invalid_or_missing_after_clean"] = int((~cl.HomeZipValid).sum())
C["coords_missing_or_invalid_after_clean"] = int((~cl.HomeCoordsValid).sum())
C["coords_swapped_autofixed"] = int(cl.HomeCoordsSwapped.sum())
C["status_unknown_after_map"] = int((cl.ClientStatus == "Unknown").sum())
C["distinct_raw_clienttype_labels"] = int(cr.ClientType.nunique())
C["distinct_raw_eligibility_labels"] = int(cr.EligibilityCategory.nunique())
C["distinct_raw_status_labels"] = int(cr.ClientStatus.nunique())
C["distinct_raw_city_labels"] = int(cr.HomeCity.nunique())
C["rows_after_dedup"] = len(cl_dedup)
C["unique_valid_clients"] = int(cl_dedup.ClientID.nunique())
C["clean_age_missing_after_dedup"] = int(cl_dedup.Age.isna().sum())
C["clean_status_counts"] = cl_dedup.ClientStatus.value_counts().to_dict()
C["clean_agegroup_counts"] = cl_dedup.AgeGroup.value_counts().to_dict()
C["clean_eligibility_counts"] = cl_dedup.EligibilityCategory.value_counts().to_dict()
C["clean_clienttype_counts"] = cl_dedup.ClientType.value_counts().to_dict()
C["clean_mobility_counts"] = cl_dedup.MobilityAid.value_counts().to_dict()

# ================================================================== TRIPS
tr = pd.read_csv(f"{D}/Trips.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
T = out["trips"]
T["raw_rows"] = len(tr)
T["distinct_tripids_raw"] = int(tr.TripID.nunique())
T["exact_duplicate_rows"] = int(tr.duplicated(keep="first").sum())
T["duplicate_tripid_rows_total"] = int(tr.duplicated("TripID", keep="first").sum())
T["conflicting_duplicate_rows"] = T["duplicate_tripid_rows_total"] - T["exact_duplicate_rows"]
tr["RowIdx"] = np.arange(len(tr))

def pts(col):
    return pd.to_datetime(tr[col].map(lambda v: str(v).strip()), format="%Y-%m-%d %H:%M:%S", errors="coerce")
for c in ["ScheduledPickupTime", "ScheduledDropoffTime", "PromiseTime", "ActualPickupTime", "ActualDropoffTime", "VehicleArrivalTime", "DriverArrivalTime"]:
    tr[c + "_p"] = pts(c)

def m_status(v):
    l = (str(v).strip().lower())
    if l.startswith("comp") or l == "cmpltd": return "Completed"
    if "canc" in l or "cxl" in l: return "Cancelled"
    if l == "ns" or "show" in l: return "No-Show"
    if any(k in l for k in ("miss", "brkdwn", "breakdown", "incomplete", "fail")): return "Failed/Other"
    return "Unresolved"
tr["TripStatus"] = tr.RawTripStatus.map(m_status)

tr["ClientID_clean"] = tr.ClientID.str.strip().str.upper().replace("", np.nan)
valid_ids = set(cl_dedup.ClientID)
tr["ClientMatched"] = tr.ClientID_clean.isin(valid_ids)

# date handling
td = parse_date(tr.TripDate.map(lambda v: tx(v) or ""))
fallback = tr.ScheduledPickupTime_p.dt.normalize()
td_in = td.notna() & (td >= WIN_START) & (td <= WIN_END)
fb_in = fallback.notna() & (fallback >= WIN_START) & (fallback <= WIN_END)
tr["TripDate_clean"] = td.where(td_in, fallback.where(fb_in))
T["tripdate_blank"] = int((tr.TripDate.str.strip() == "").sum())
T["tripdate_outside_window"] = int((td.notna() & ~td_in).sum())
T["tripdate_repaired_from_scheduled_pickup"] = int((~td_in & tr.TripDate_clean.notna()).sum())
T["tripdate_unrepairable"] = int(tr.TripDate_clean.isna().sum())
bd = parse_date(tr.BookingDate.map(lambda v: tx(v) or ""))
T["bookingdate_blank"] = int(bd.isna().sum())
T["bookingdate_after_tripdate"] = int((bd.notna() & (bd > tr.TripDate_clean)).sum())

# route
def route_num(v):
    s = str(v).strip().upper().replace(" ", "").replace("-", "")
    if s.startswith("ROUTE"): s = s[5:]
    elif s.startswith("RT"): s = s[2:]
    elif s.startswith("R"): s = s[1:]
    return int(s) if s.isdigit() and s != "" else np.nan
tr["RouteNumber"] = tr.RouteID.map(route_num)
def mode_of(n):
    if pd.isna(n): return "Unknown"
    if 1000 <= n <= 1999: return "Primary"
    if 2000 <= n <= 2999: return "Broker"
    if 3000 <= n <= 3999: return "Supplemental"
    return "Unknown"
tr["Mode"] = tr.RouteNumber.map(mode_of)
def raw_mode_norm(v):
    l = str(v).strip().lower()
    if l.startswith("prim"): return "Primary"
    if l.startswith("brk") or l.startswith("brok"): return "Broker"
    if l.startswith("supp"): return "Supplemental"
    return "Unknown"
tr["RawModeNorm"] = tr.RawServiceMode.map(raw_mode_norm)
T["raw_route_formats_distinct"] = int(tr.RouteID.str.replace(r"\d", "9", regex=True).nunique())
T["routeid_unparseable_or_blank"] = int(tr.RouteNumber.isna().sum())
T["routeid_numeric_out_of_range"] = int((tr.RouteNumber.notna() & (tr.Mode == "Unknown")).sum())
T["rawservicemode_disagrees_with_route_mode"] = int(((tr.Mode != "Unknown") & (tr.RawModeNorm != tr.Mode)).sum())

# zips / coords
for p in ("Pickup", "Dropoff"):
    z = tr[f"{p}ZipCode"].map(m_zip)
    tr[f"{p}Zip_clean"] = z.map(lambda t: t[0]); tr[f"{p}ZipValid"] = z.map(lambda t: t[1])
    cc = [coords(a, b) for a, b in zip(tr[f"{p}Latitude"], tr[f"{p}Longitude"])]
    tr[f"{p}Lat_clean"] = [c[0] for c in cc]; tr[f"{p}Lon_clean"] = [c[1] for c in cc]
    tr[f"{p}CoordsValid"] = [c[2] for c in cc]; tr[f"{p}CoordsSwapped"] = [c[3] for c in cc]
    T[f"{p.lower()}_zip_invalid_or_missing"] = int((~tr[f"{p}ZipValid"]).sum())
    T[f"{p.lower()}_coords_invalid_or_missing"] = int((~tr[f"{p}CoordsValid"]).sum())
    T[f"{p.lower()}_coords_swapped"] = int(tr[f"{p}CoordsSwapped"].sum())

# money / distance / duration
def money(v):
    s = str(v).strip().replace("$", "").replace(",", "").replace("USD", "").strip()
    return num(s) if s not in BL else np.nan
tr["Fare_p"] = tr.RawFareAmount.map(money)
tr["FareValid"] = tr.Fare_p.notna() & (tr.Fare_p >= 0) & (tr.Fare_p <= 150)
tr["Refund_p"] = tr.RawRefundAmount.map(money).fillna(0.0)
tr["RefundValid"] = (tr.Refund_p >= 0) & tr.FareValid & (tr.Refund_p <= tr.Fare_p)
def dist_p(v):
    s = str(v).lower().replace("miles", "").replace("mi", "").strip()
    return num(s) if s not in BL else np.nan
tr["Dist_p"] = tr.RawDistanceMiles.map(dist_p)
tr["DistValid"] = tr.Dist_p.notna() & (tr.Dist_p > 0) & (tr.Dist_p <= 100)
def dur_p(v):
    s = str(v).lower().replace("min", "").strip()
    return num(s) if s not in BL else np.nan
tr["Dur_p"] = tr.RawTripDuration.map(dur_p)
tr["DurValid"] = tr.Dur_p.notna() & (tr.Dur_p > 0) & (tr.Dur_p <= 240)
ts_dur = (tr.ActualDropoffTime_p - tr.ActualPickupTime_p).dt.total_seconds() / 60
tr["DurFromTs"] = ts_dur.where((ts_dur > 0) & (ts_dur <= 240))
tr["TripDurationMinutes"] = tr.Dur_p.where(tr.DurValid, tr.DurFromTs)

# pickup delay
tr["PickupDelayMinutes"] = (tr.ActualPickupTime_p - tr.PromiseTime_p).dt.total_seconds() / 60
tr["PickupDelayIsValid"] = tr.PickupDelayMinutes.notna() & tr.PickupDelayMinutes.between(-180, 360)
tr["DropoffDelayMinutes"] = (tr.ActualDropoffTime_p - tr.ScheduledDropoffTime_p).dt.total_seconds() / 60

def excl_reason(r):
    if r.TripStatus != "Completed": return "Not a completed trip"
    if pd.isna(r.PromiseTime_p): return "Missing/invalid PromiseTime"
    if pd.isna(r.ActualPickupTime_p): return "Missing/invalid ActualPickupTime"
    if not r.PickupDelayIsValid: return "Pickup delay out of valid range"
    return "Eligible"
tr["OTPStatus"] = tr.apply(excl_reason, axis=1)

# ---------------- RAW audit counts (before dedup)
T["status_raw_distinct_labels"] = int(tr.RawTripStatus.nunique())
T["clientid_needs_trim_or_case_fix"] = int(((tr.ClientID != tr.ClientID_clean.fillna("")) & tr.ClientID_clean.notna()).sum())
T["clientid_blank"] = int((tr.ClientID.str.strip() == "").sum())
T["clientid_orphan_after_clean_rows_raw"] = int((tr.ClientID_clean.notna() & ~tr.ClientMatched).sum())
T["scheduledpickup_malformed_or_blank"] = int(tr.ScheduledPickupTime_p.isna().sum())
T["promisetime_malformed_or_blank"] = int(tr.PromiseTime_p.isna().sum())
comp_raw = tr.TripStatus == "Completed"
T["completed_rows_actualpickup_missing_or_malformed_raw"] = int((comp_raw & tr.ActualPickupTime_p.isna()).sum())
T["completed_rows_actualdropoff_missing_or_malformed_raw"] = int((comp_raw & tr.ActualDropoffTime_p.isna()).sum())
T["completed_rows_pickup_delay_out_of_range_raw"] = int((comp_raw & tr.PickupDelayMinutes.notna() & ~tr.PickupDelayIsValid).sum())
T["fare_negative_raw"] = int((tr.Fare_p < 0).sum())
T["fare_over_150_raw"] = int((tr.Fare_p > 150).sum())
T["fare_missing_or_text_on_completed_raw"] = int((comp_raw & tr.Fare_p.isna()).sum())
T["noncompleted_with_positive_fare_raw"] = int((~comp_raw & (tr.Fare_p > 0)).sum())
T["refund_exceeds_fare_raw"] = int((tr.Refund_p > tr.Fare_p.fillna(0)).sum() - 0)
T["distance_nonnumeric_or_blank_raw"] = int(tr.Dist_p.isna().sum())
T["distance_zero_negative_or_over100_raw"] = int((tr.Dist_p.notna() & ~tr.DistValid).sum())
T["duration_invalid_or_blank_on_completed_raw"] = int((comp_raw & ~tr.DurValid).sum())
T["rawdelay_sign_or_text_issue_note"] = "RawDelayMinutes: ~8% sign-flipped, ~10% contain text suffix, ~12% blank (completed trips)"
ns_l = tr.NoShowIndicatorRaw.str.strip().str.lower()
tr["NoShowInd"] = ns_l.map(lambda v: True if v in ("y", "1", "true", "yes") else (False if v in ("n", "0", "false", "no") else None))
T["noshow_indicator_blank_raw"] = int((tr.NoShowIndicatorRaw.str.strip() == "").sum())
T["status_vs_indicator_conflicts_raw"] = int((((tr.TripStatus == "No-Show") & (tr.NoShowInd == False)) | ((tr.TripStatus != "No-Show") & (tr.NoShowInd == True))).sum())
T["unresolved_status_rows_raw"] = int((tr.TripStatus == "Unresolved").sum())

# ---------------- dedupe (status rank, completeness, first row)
tr["StatusRank"] = (tr.TripStatus != "Unresolved").astype(int)
tr["Score"] = (tr[["ScheduledPickupTime_p", "ScheduledDropoffTime_p", "PromiseTime_p", "ActualPickupTime_p", "ActualDropoffTime_p", "VehicleArrivalTime_p", "DriverArrivalTime_p"]].notna().sum(axis=1)
               + tr.Fare_p.notna().astype(int) + tr.Dist_p.notna().astype(int) + tr.Dur_p.notna().astype(int))
tr = tr.sort_values(["TripID", "StatusRank", "Score", "RowIdx"], ascending=[True, False, False, True])
t = tr.drop_duplicates("TripID", keep="first").copy()
T["rows_after_dedup"] = len(t)
T["distinct_tripids_after_dedup"] = int(t.TripID.nunique())

# ---------------- flags on deduped data
t["IsValidScheduledTrip"] = t.TripDate_clean.notna() & (t.TripStatus != "Unresolved")
T["excluded_from_kpis_unresolved_status"] = int((t.TripStatus == "Unresolved").sum())
T["excluded_from_kpis_no_valid_tripdate"] = int(t.TripDate_clean.isna().sum())
T["clientid_orphan_rows_after_dedup"] = int((t.ClientID_clean.notna() & ~t.ClientMatched).sum())
T["clientid_blank_rows_after_dedup"] = int(t.ClientID_clean.isna().sum())
T["clientid_unmatched_total_after_dedup"] = int((~t.ClientMatched).sum())
valid = t[t.IsValidScheduledTrip].copy()
status_counts = valid.TripStatus.value_counts().to_dict()
T["status_counts_valid"] = status_counts
comp = valid[valid.TripStatus == "Completed"]
n_total = len(valid)
n_comp = len(comp); n_ns = int((valid.TripStatus == "No-Show").sum()); n_can = int((valid.TripStatus == "Cancelled").sum()); n_oth = int((valid.TripStatus == "Failed/Other").sum())
n_elig = n_total - n_can
# OTP
oe = valid[valid.OTPStatus == "Eligible"]
otp = {
    "otp_eligible": len(oe),
    "otp_excluded_not_completed": int((valid.OTPStatus == "Not a completed trip").sum()),
    "otp_excluded_missing_promise": int((valid.OTPStatus == "Missing/invalid PromiseTime").sum()),
    "otp_excluded_missing_actual_pickup": int((valid.OTPStatus == "Missing/invalid ActualPickupTime").sum()),
    "otp_excluded_delay_out_of_range": int((valid.OTPStatus == "Pickup delay out of valid range").sum()),
    "on_time_15": int((oe.PickupDelayMinutes <= 15).sum()), "on_time_20": int((oe.PickupDelayMinutes <= 20).sum()),
}
otp["otp15_pct"] = round(100 * otp["on_time_15"] / otp["otp_eligible"], 2)
otp["otp20_pct"] = round(100 * otp["on_time_20"] / otp["otp_eligible"], 2)
otp["avg_delay"] = round(float(oe.PickupDelayMinutes.mean()), 2)
otp["median_delay"] = float(oe.PickupDelayMinutes.median())
otp["by_mode"] = {m: {"eligible": int(len(g)), "otp15": round(100 * (g.PickupDelayMinutes <= 15).mean(), 2),
                      "otp20": round(100 * (g.PickupDelayMinutes <= 20).mean(), 2)} for m, g in oe.groupby("Mode")}
T["otp"] = otp
T["volume"] = {"total_valid_scheduled": n_total, "completed": n_comp, "no_show": n_ns, "cancelled": n_can, "failed_other": n_oth,
               "eligible_scheduled_excl_cancelled": n_elig,
               "no_shows_per_100": round(100 * n_ns / n_elig, 3), "cancellations_per_100_scheduled": round(100 * n_can / n_total, 3),
               "completed_trip_rate_pct": round(100 * n_comp / n_total, 2)}
bm = {}
for m, g in valid.groupby("Mode"):
    e = (g.TripStatus != "Cancelled").sum()
    bm[m] = {"valid": int(len(g)), "completed": int((g.TripStatus == "Completed").sum()), "no_shows": int((g.TripStatus == "No-Show").sum()),
             "eligible": int(e), "ns_per_100": round(100 * (g.TripStatus == "No-Show").sum() / e, 3)}
T["by_mode"] = bm
bb = {}
BOR = {"mn": "Manhattan", "manhattan": "Manhattan", "bx": "Bronx", "bronx": "Bronx", "the bronx": "Bronx", "bk": "Brooklyn", "bklyn": "Brooklyn",
       "brooklyn": "Brooklyn", "qns": "Queens", "queens": "Queens", "si": "Staten Island", "staten is.": "Staten Island", "staten island": "Staten Island"}
def m_bor(v):
    l = str(v).strip().lower()
    if l in BOR: return BOR[l]
    if "nassau" in l: return "Nassau County"
    if "hudson" in l: return "Hudson County NJ"
    return "Unknown"
valid["Borough_clean"] = valid.Borough.map(m_bor)
for b, g in valid.groupby("Borough_clean"):
    e = (g.TripStatus != "Cancelled").sum()
    bb[b] = {"valid": int(len(g)), "completed": int((g.TripStatus == "Completed").sum()),
             "ns_per_100": round(100 * (g.TripStatus == "No-Show").sum() / e, 3)}
T["by_borough"] = bb
# revenue
comp = valid[valid.TripStatus == "Completed"].copy()
comp["EligibleFare"] = comp.Fare_p.where(comp.FareValid, 0.0).fillna(0.0)
comp["EligibleRefund"] = comp.Refund_p.where(comp.FareValid & comp.RefundValid, 0.0)
T["revenue"] = {"gross_eligible_fare": round(float(comp.EligibleFare.sum()), 2), "total_refund": round(float(comp.EligibleRefund.sum()), 2),
                "net_fare": round(float(comp.EligibleFare.sum() - comp.EligibleRefund.sum()), 2),
                "completed_with_invalid_or_missing_fare": int((~comp.FareValid).sum()),
                "completed_with_invalid_refund_excluded": int((comp.FareValid & ~comp.RefundValid).sum()),
                "avg_fare_per_completed_valid_fare": round(float(comp.EligibleFare[comp.FareValid].mean()), 4),
                "by_mode_net": {m: round(float((g.EligibleFare - g.EligibleRefund).sum()), 2) for m, g in comp.groupby("Mode")}}
# clients served
served = comp[comp.ClientMatched]
T["clients"] = {"unique_clients_served_completed": int(served.ClientID_clean.nunique()),
                "valid_clients": int(len(cl_dedup)),
                "active_client_rate_pct": round(100 * served.ClientID_clean.nunique() / len(cl_dedup), 2),
                "high_freq_clients_20plus": int((served.groupby("ClientID_clean").size() >= 20).sum()),
                "completed_trips_matched_clients": int(len(served)), "avg_trips_per_client_served": round(len(served) / served.ClientID_clean.nunique(), 3)}
# monthly
valid["Month"] = valid.TripDate_clean.dt.to_period("M").astype(str)
mon = {}
for mth, g in valid.groupby("Month"):
    e = g[g.OTPStatus == "Eligible"]
    mon[mth] = {"completed": int((g.TripStatus == "Completed").sum()), "no_shows": int((g.TripStatus == "No-Show").sum()),
                "ns_per_100": round(100 * (g.TripStatus == "No-Show").sum() / (g.TripStatus != "Cancelled").sum(), 3),
                "otp15": round(100 * (e.PickupDelayMinutes <= 15).mean(), 2)}
T["monthly"] = mon
# route-level for small-sample illustration
rg = valid.groupby("RouteNumber").agg(valid=("TripID", "size"))
rg["completed"] = valid[valid.TripStatus == "Completed"].groupby("RouteNumber").size()
rg["ns"] = valid[valid.TripStatus == "No-Show"].groupby("RouteNumber").size()
rg = rg.fillna(0)
rg["ns_per_100"] = (100 * rg.ns / (valid[valid.TripStatus != "Cancelled"].groupby("RouteNumber").size())).round(2)
rg["otp15"] = (100 * oe.groupby("RouteNumber").apply(lambda g: (g.PickupDelayMinutes <= 15).mean(), include_groups=False)).round(2)
T["route_table_head"] = rg.sort_values("valid", ascending=False).head(8).reset_index().to_dict(orient="records")
T["route_table_tail"] = rg.sort_values("valid", ascending=True).head(8).reset_index().to_dict(orient="records")
T["route_worst_otp15_min200_eligible"] = rg[rg.valid >= 200].sort_values("otp15").head(3).reset_index().to_dict(orient="records")
T["route_count"] = int(rg.shape[0])
# examples
ex = {}
ex["midnight_crossing_example"] = t[(t.OTPStatus == "Eligible") & (t.PromiseTime_p.dt.date != t.ActualPickupTime_p.dt.date)][["TripID", "PromiseTime", "ActualPickupTime", "PickupDelayMinutes", "RouteID", "Mode"]].head(3).to_dict(orient="records")
ex["exactly_15_min"] = t[(t.OTPStatus == "Eligible") & (t.PickupDelayMinutes == 15)][["TripID", "PromiseTime", "ActualPickupTime", "PickupDelayMinutes"]].head(2).to_dict(orient="records")
ex["exactly_16_min"] = t[(t.OTPStatus == "Eligible") & (t.PickupDelayMinutes == 16)][["TripID", "PromiseTime", "ActualPickupTime", "PickupDelayMinutes"]].head(1).to_dict(orient="records")
ex["early_pickup"] = t[(t.OTPStatus == "Eligible") & (t.PickupDelayMinutes <= -15)][["TripID", "PromiseTime", "ActualPickupTime", "PickupDelayMinutes"]].head(1).to_dict(orient="records")
ex["anomalous_delay"] = t[(t.OTPStatus == "Pickup delay out of valid range")][["TripID", "PromiseTime", "ActualPickupTime", "PickupDelayMinutes"]].head(2).to_dict(orient="records")
ex["route_mode_examples"] = t.drop_duplicates("RouteID").head(0).to_dict(orient="records")
rm = tr[["RouteID", "RouteNumber", "Mode"]].drop_duplicates("RouteID")
pick = []
for pat in [r"^R-1", r"^\d{4}$", r"^r \d", r"^Route 2", r"^Route 3", r"^R-9", r"^R-XX"]:
    sel = rm[rm.RouteID.str.contains(pat, regex=True)].head(1)
    pick += sel.to_dict(orient="records")
ex["route_to_mode"] = pick
ex["age_examples"] = cl_dedup[cl_dedup.DobValid].sample(5, random_state=3)[["ClientID", "DateOfBirth", "Age", "AgeGroup"]].assign(DateOfBirth=lambda d: d.DateOfBirth.dt.strftime("%Y-%m-%d")).to_dict(orient="records")
ex["age_birthday_edge"] = cl_dedup[cl_dedup.DobValid & (cl_dedup.DateOfBirth.dt.month == 10) & (cl_dedup.DateOfBirth.dt.day <= 5)][["ClientID", "DateOfBirth", "Age"]].head(2).assign(DateOfBirth=lambda d: d.DateOfBirth.dt.strftime("%Y-%m-%d")).to_dict(orient="records")
ex["age_birthday_before_asof"] = cl_dedup[cl_dedup.DobValid & (cl_dedup.DateOfBirth.dt.month == 9) & (cl_dedup.DateOfBirth.dt.day >= 25)][["ClientID", "DateOfBirth", "Age"]].head(2).assign(DateOfBirth=lambda d: d.DateOfBirth.dt.strftime("%Y-%m-%d")).to_dict(orient="records")
ex["client_dup_example"] = cr[cr.duplicated("ClientID", keep=False)].sort_values("ClientID").head(4)[["ClientID", "ClientStatus", "Gender", "HomeZipCode", "HomeLatitude"]].to_dict(orient="records")
ex["trip_dup_stale_example"] = tr[tr.duplicated("TripID", keep=False) & tr.RawTripStatus.isin(["Scheduled", "SCHED"])].sort_values("TripID").head(1)[["TripID"]].to_dict(orient="records")
out["examples"] = ex

# ---- sanity: unmapped status/variants
T["status_map_check"] = tr.groupby("RawTripStatus").TripStatus.agg(lambda s: s.iloc[0]).to_dict()
C["status_map_check"] = cr.groupby("ClientStatus").ClientStatus.first().map(m_cstatus).to_dict()
C["elig_map_check"] = cr.groupby("EligibilityCategory").EligibilityCategory.first().map(m_elig).to_dict()
C["type_map_check"] = cr.groupby("ClientType").ClientType.first().map(m_ctype).to_dict()

# ---------------- extra validation numbers
comp = comp.copy()
comp["Month"] = comp.TripDate_clean.dt.to_period("M").astype(str)
X = {}
X["avg_distance_completed_valid"] = round(float(comp.Dist_p[comp.DistValid].mean()), 3)
X["avg_duration_completed_valid"] = round(float(comp.TripDurationMinutes.dropna().mean()), 3)
X["completed_distance_valid_rows"] = int(comp.DistValid.sum()); X["completed_duration_valid_rows"] = int(comp.TripDurationMinutes.notna().sum())
X["net_by_month"] = {m: round(float((g.EligibleFare - g.EligibleRefund).sum()), 2) for m, g in comp.groupby("Month")}
last7 = comp[(comp.TripDate_clean >= "2026-09-24") & (comp.TripDate_clean <= "2026-09-30")]
X["rolling7_completed_ending_2026_09_30"] = int(len(last7))
v30 = valid[(valid.TripDate_clean >= "2026-09-01") & (valid.TripDate_clean <= "2026-09-30")]
X["avg_daily_completed"] = round(n_comp / 365, 3)
cm = comp.merge(cl_dedup[["ClientID", "AgeGroup", "EligibilityCategory", "MobilityAid", "ClientType"]], left_on="ClientID_clean", right_on="ClientID", how="left", suffixes=("", "_c"))
X["completed_by_agegroup"] = cm.AgeGroup.fillna("(unmatched)").value_counts().to_dict()
X["completed_by_eligibility"] = cm.EligibilityCategory.fillna("(unmatched)").value_counts().to_dict()
X["completed_by_clienttype"] = cm.ClientType.fillna("(unmatched)").value_counts().to_dict()
X["completed_by_mobility"] = cm.MobilityAid.fillna("(unmatched)").value_counts().to_dict()
X["net_by_agegroup"] = {k: round(float((g.EligibleFare - g.EligibleRefund).sum()), 2) for k, g in cm.groupby(cm.AgeGroup.fillna("(unmatched)"))}
X["unique_pickup_zips_valid_completed"] = int(comp.PickupZip_clean.nunique())
X["unique_dropoff_zips_valid_completed"] = int(comp.DropoffZip_clean.nunique())
X["completed_pickup_zip_missing"] = int(comp.PickupZip_clean.isna().sum())
X["same_zip_completed"] = int((comp.PickupZip_clean == comp.DropoffZip_clean).sum())
X["top_pickup_zip_completed"] = comp.PickupZip_clean.value_counts().head(3).to_dict()
X["ns_by_pickup_zip_top"] = valid.groupby("PickupZip_clean").apply(lambda g: pd.Series({"valid": len(g), "ns_per_100": round(100 * (g.TripStatus == "No-Show").sum() / (g.TripStatus != "Cancelled").sum(), 2)}), include_groups=False).sort_values("valid", ascending=False).head(3).to_dict(orient="index")
dow = valid.TripDate_clean.dt.day_name()
X["ns_per_100_by_dow"] = {k: round(100 * (g.TripStatus == "No-Show").sum() / (g.TripStatus != "Cancelled").sum(), 2) for k, g in valid.groupby(dow)}
oe2 = valid[valid.OTPStatus == "Eligible"]
X["otp15_by_hour"] = {int(k): round(100 * (g.PickupDelayMinutes <= 15).mean(), 1) for k, g in oe2.groupby(oe2.ScheduledPickupTime_p.dt.hour) if len(g) > 300}
X["peak_vs_offpeak_otp15"] = {}
wk = oe2.ScheduledPickupTime_p.dt.dayofweek < 5; hh = oe2.ScheduledPickupTime_p.dt.hour
pk = wk & (((hh >= 6) & (hh <= 9)) | ((hh >= 15) & (hh <= 18)))
X["peak_vs_offpeak_otp15"] = {"Peak": round(100 * (oe2[pk].PickupDelayMinutes <= 15).mean(), 2), "Off-Peak": round(100 * (oe2[~pk].PickupDelayMinutes <= 15).mean(), 2)}
X["trips_peak_share_pct_valid"] = None
X["unmatched_client_completed_trips"] = int((~comp.ClientMatched).sum())
X["late_over_45_completed"] = int((oe2.PickupDelayMinutes > 45).sum())
X["noshow_flag_vs_status_conflicts_valid"] = int((((valid.TripStatus == "No-Show") & (valid.NoShowInd == False)) | ((valid.TripStatus != "No-Show") & (valid.NoShowInd == True))).sum())
T["extra"] = X

# ---------------- mapping coverage for text standardisers (mirrors the M functions)
def m_reason(v, status):
    l = low(v)
    if status == "Completed": return None
    if l is None: return "Not Recorded" if status in ("Cancelled", "No-Show", "Failed/Other") else None
    for keys, out_ in [(("client req",), "Client Request"), (("same",), "Same-Day Cancellation"), (("weather",), "Weather"),
                       (("appt", "medical appointment"), "Medical Appointment Changed"), (("dup",), "Duplicate Booking"),
                       (("agency",), "Agency Cancelled"), (("sched",), "Schedule Change"), (("not at",), "Not at Pickup Location"),
                       (("not ready",), "Not Ready at Window"), (("no answer",), "No Answer at Door"), (("unreachable",), "Client Unreachable"),
                       (("miss",), "Provider Missed Trip"), (("breakdown", "brkdwn"), "Vehicle Breakdown"),
                       (("unable", "utl"), "Unable to Locate Client"), (("driver",), "Driver Unavailable")]:
        if any(k in l for k in keys): return out_
    return "Other"
def m_purpose(v):
    l = low(v)
    if l is None: return "Unknown"
    if l.startswith("med"): return "Medical"
    if l.startswith("dial"): return "Dialysis"
    if l.startswith("work") or l.startswith("employ"): return "Work"
    if l.startswith("edu"): return "Education/Training"
    if l.startswith("shop") or l.startswith("errand"): return "Shopping/Errand"
    if l.startswith("soc") or l.startswith("rec"): return "Social/Recreation"
    if l.startswith("senior"): return "Senior Center"
    if l.startswith("other") or l.startswith("misc"): return "Other"
    return "Unknown"
def m_vehicle(v):
    l = low(v)
    if l is None: return "Unknown"
    if "lift" in l or "wheelchair" in l: return "Lift Van"
    if "mini" in l: return "Minivan"
    if "sedan" in l: return "Sedan"
    if "taxi" in l or l == "cab": return "Taxi"
    return "Other"
def m_channel(v):
    l = low(v)
    if l is None: return "Unknown"
    if "phone" in l: return "Phone"
    if "web" in l or "online" in l: return "Web"
    if "app" in l: return "App"
    if "ivr" in l or "automated" in l: return "IVR"
    return "Other"
def m_region(v):
    l = low(v)
    if l is None: return "Unknown"
    if l.startswith("n"): return "North"
    if l.startswith("e"): return "East"
    if l.startswith("s"): return "South"
    return "Unknown"
cov_out = {}
x = pd.read_csv(f"{D}/Trips.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
x["TripStatus"] = x.RawTripStatus.map(m_status)
x["r"] = [m_reason(a, b) for a, b in zip(x.CancellationReason, x.TripStatus)]
cov_out["reason_distinct_raw"] = int(x.CancellationReason.nunique())
cov_out["reason_mapped_values"] = x.r.value_counts(dropna=False).to_dict()
cov_out["purpose_values"] = x.TripPurpose.map(m_purpose).value_counts().to_dict()
cov_out["vehicle_values"] = x.VehicleType.map(m_vehicle).value_counts().to_dict()
cov_out["channel_values"] = x.BookingChannel.map(m_channel).value_counts().to_dict()
cov_out["region_values"] = x.ServiceRegion.map(m_region).value_counts().to_dict()
cov_out["borough_values"] = x.Borough.map(m_bor).value_counts().to_dict()
cov_out["provider_values"] = x.ServiceProviderID.map(lambda v: (tx(v) or "").upper()).value_counts().to_dict()
cov_out["rawmode_values"] = x.RawServiceMode.map(raw_mode_norm).value_counts().to_dict()
cov_out["route_formats"] = x.RouteID.str.replace(r"\d", "9", regex=True).value_counts().to_dict()
out["coverage"] = cov_out

def conv(o):
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return None if np.isnan(o) else float(o)
    if isinstance(o, (pd.Timestamp,)): return str(o)
    if isinstance(o, float) and np.isnan(o): return None
    return str(o)
js = json.dumps(out, indent=1, default=conv)
if len(sys.argv) > 2:
    open(sys.argv[2], "w").write(js)
else:
    print(js)
