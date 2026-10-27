#!/usr/bin/env python3
"""
Synthetic paratransit raw-data generator (all data fictional).

Usage:  python3 generate_data.py [output_dir]
Output: Clients.csv, Trips.csv  (RAW, deliberately dirty)

Everything is seeded, so re-running reproduces identical files.
Addresses are fictional; coordinates are ZIP-centroid + random jitter and are NOT real residences.
"""
import sys, os
import numpy as np
import pandas as pd

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
SEED = 20261026
rng = np.random.default_rng(SEED)

AS_OF = pd.Timestamp("2026-09-30")          # documented reporting date for Age
START, END = pd.Timestamp("2025-10-01"), pd.Timestamp("2026-09-30")
N_CLIENTS, N_TRIPS = 5000, 100000

# ----------------------------------------------------------------------------------
# Geography: (zip, borough, city, state, lat, lon, home_weight, dest_weight)
# Centroids are approximate; synthetic points are jittered around them.
# ----------------------------------------------------------------------------------
BOR = ["Manhattan", "Bronx", "Brooklyn", "Queens", "Staten Island", "Nassau County", "Hudson County NJ"]
Z = [
    ("10001", 0, "New York", "NY", 40.7506, -73.9972, 1.0, 2.0),
    ("10002", 0, "New York", "NY", 40.7157, -73.9863, 1.0, 1.0),
    ("10016", 0, "New York", "NY", 40.7459, -73.9781, 0.8, 3.0),
    ("10025", 0, "New York", "NY", 40.7989, -73.9684, 1.2, 2.0),
    ("10027", 0, "New York", "NY", 40.8116, -73.9535, 1.1, 1.0),
    ("10029", 0, "New York", "NY", 40.7917, -73.9439, 1.2, 1.5),
    ("10031", 0, "New York", "NY", 40.8250, -73.9500, 1.0, 1.0),
    ("10032", 0, "New York", "NY", 40.8395, -73.9427, 1.3, 3.0),
    ("10451", 1, "Bronx", "NY", 40.8208, -73.9238, 1.2, 1.2),
    ("10457", 1, "Bronx", "NY", 40.8470, -73.8999, 1.3, 1.5),
    ("10458", 1, "Bronx", "NY", 40.8620, -73.8890, 1.1, 1.0),
    ("10460", 1, "Bronx", "NY", 40.8403, -73.8795, 1.1, 1.0),
    ("10467", 1, "Bronx", "NY", 40.8730, -73.8680, 1.3, 1.5),
    ("10472", 1, "Bronx", "NY", 40.8293, -73.8689, 1.0, 0.8),
    ("11201", 2, "Brooklyn", "NY", 40.6940, -73.9906, 1.0, 2.5),
    ("11206", 2, "Brooklyn", "NY", 40.7032, -73.9427, 1.1, 1.0),
    ("11211", 2, "Brooklyn", "NY", 40.7127, -73.9535, 0.9, 1.0),
    ("11212", 2, "Brooklyn", "NY", 40.6628, -73.9139, 1.2, 1.2),
    ("11216", 2, "Brooklyn", "NY", 40.6767, -73.9482, 1.0, 1.0),
    ("11220", 2, "Brooklyn", "NY", 40.6417, -74.0166, 1.2, 1.0),
    ("11226", 2, "Brooklyn", "NY", 40.6463, -73.9560, 1.4, 1.2),
    ("11230", 2, "Brooklyn", "NY", 40.6218, -73.9667, 1.1, 1.0),
    ("11235", 2, "Brooklyn", "NY", 40.5842, -73.9482, 1.1, 1.2),
    ("11101", 3, "Long Island City", "NY", 40.7448, -73.9381, 0.8, 2.0),
    ("11354", 3, "Flushing", "NY", 40.7642, -73.8272, 1.2, 1.5),
    ("11368", 3, "Corona", "NY", 40.7491, -73.8606, 1.3, 1.2),
    ("11373", 3, "Elmhurst", "NY", 40.7387, -73.8788, 1.2, 1.5),
    ("11375", 3, "Forest Hills", "NY", 40.7206, -73.8448, 1.0, 1.0),
    ("11385", 3, "Ridgewood", "NY", 40.7040, -73.9010, 1.0, 0.8),
    ("11432", 3, "Jamaica", "NY", 40.7145, -73.7931, 1.2, 1.5),
    ("11434", 3, "Jamaica", "NY", 40.6791, -73.7771, 1.1, 1.0),
    ("11691", 3, "Far Rockaway", "NY", 40.6058, -73.7456, 0.9, 0.8),
    ("10301", 4, "Staten Island", "NY", 40.6430, -74.0938, 1.0, 1.2),
    ("10305", 4, "Staten Island", "NY", 40.5968, -74.0763, 1.0, 1.5),
    ("10312", 4, "Staten Island", "NY", 40.5456, -74.1665, 1.0, 1.0),
    ("10314", 4, "Staten Island", "NY", 40.6040, -74.1479, 1.2, 1.0),
    ("11550", 5, "Hempstead", "NY", 40.7064, -73.6008, 1.0, 1.0),
    ("11010", 5, "Franklin Square", "NY", 40.7013, -73.6747, 1.0, 0.8),
    ("07030", 6, "Hoboken", "NJ", 40.7440, -74.0324, 0.3, 0.6),
    ("07302", 6, "Jersey City", "NJ", 40.7178, -74.0431, 0.3, 0.8),
    ("07093", 6, "West New York", "NJ", 40.7879, -74.0143, 0.3, 0.4),
]
ZIP = np.array([z[0] for z in Z]); ZB = np.array([z[1] for z in Z]); ZCITY = np.array([z[2] for z in Z])
ZST = np.array([z[3] for z in Z]); ZLAT = np.array([z[4] for z in Z]); ZLON = np.array([z[5] for z in Z])
BOR_HOME_W = np.array([0.17, 0.18, 0.28, 0.24, 0.07, 0.035, 0.005])
home_w = np.array([z[6] for z in Z]) * BOR_HOME_W[ZB]
home_w = home_w / home_w.sum()
dest_w = np.array([z[7] for z in Z]); dest_w = dest_w / dest_w.sum()

STREETS = ["Maplecrest", "Harborlight", "Willowmere", "Stonebridge", "Fairhaven", "Oakridge", "Larkspur",
           "Pinecrest", "Ridgemont", "Silverbrook", "Thornfield", "Winterhaven", "Amberley", "Birchwood",
           "Copperfield", "Driftwood", "Evergreen", "Foxglove", "Glenmere", "Hawkstone", "Ironwood",
           "Juniper", "Kestrel", "Lindenfield", "Meadowlark", "Northgate", "Orchardview", "Pebblebrook",
           "Quailrun", "Rosemont", "Sandpiper", "Tamarack", "Underhill", "Violetta", "Westbrook", "Yarrow"]
SUFFIX = ["Street", "Avenue", "Road", "Place", "Boulevard", "Lane", "Court"]
SUFFIX_ABBR = {"Street": ["St", "St.", "ST"], "Avenue": ["Ave", "Ave.", "AVE"], "Road": ["Rd", "Rd.", "RD"],
               "Place": ["Pl", "Pl."], "Boulevard": ["Blvd", "Blvd."], "Lane": ["Ln", "Ln."], "Court": ["Ct", "Ct."]}


def hav_miles(la1, lo1, la2, lo2):
    p = np.pi / 180
    a = (np.sin((la2 - la1) * p / 2) ** 2 +
         np.cos(la1 * p) * np.cos(la2 * p) * np.sin((lo2 - lo1) * p / 2) ** 2)
    return 3958.8 * 2 * np.arcsin(np.sqrt(a))


def make_addresses(n, apt_rate=0.0):
    num = rng.integers(10, 9990, n)
    st = rng.choice(STREETS, n)
    sf = rng.choice(SUFFIX, n)
    out = []
    for i in range(n):
        s = f"{num[i]} {st[i]} {sf[i]}"
        if apt_rate and rng.random() < apt_rate:
            s += f" Apt {rng.integers(1, 20)}{rng.choice(list('ABCDEF'))}"
        out.append(s)
    return np.array(out, dtype=object)


def messy_address(addr, p_abbr=0.45, p_upper=0.08, p_space=0.04):
    out = addr.copy()
    for i in range(len(out)):
        s = out[i]
        r = rng.random()
        if r < p_abbr:
            for full, abbs in SUFFIX_ABBR.items():
                if s.split(" ")[2:3] == [full]:
                    s = s.replace(f" {full}", " " + rng.choice(abbs), 1)
                    break
        r = rng.random()
        if r < p_upper:
            s = s.upper()
        elif r < p_upper + p_space:
            s = "  " + s.replace(" ", "  ", 1) + " "
        out[i] = s
    return out


def apply_variants(canon, vmap, p_first=0.62):
    """canon: object array of canonical values -> raw variants. vmap: canon -> [variants...]."""
    out = np.array(canon, dtype=object)
    for c, variants in vmap.items():
        m = np.array([x == c for x in canon])
        k = m.sum()
        if k == 0:
            continue
        w = np.array([p_first] + [(1 - p_first) / (len(variants) - 1)] * (len(variants) - 1)) if len(variants) > 1 else np.array([1.0])
        out[m] = rng.choice(variants, size=k, p=w)
    return out


def noise_text(arr, p_space=0.05, p_upper=0.04, p_lower=0.04):
    out = np.array(arr, dtype=object)
    n = len(out)
    u = rng.random(n)
    for i in range(n):
        v = out[i]
        if not isinstance(v, str) or v == "":
            continue
        if u[i] < p_space:
            out[i] = " " + v + " " if rng.random() < 0.5 else v + " "
        elif u[i] < p_space + p_upper:
            out[i] = v.upper()
        elif u[i] < p_space + p_upper + p_lower:
            out[i] = v.lower()
    return out


BLANKS = np.array(["", "", "", " ", "N/A", "NULL", "-"], dtype=object)


def blankify(arr, rate):
    out = np.array(arr, dtype=object)
    m = rng.random(len(out)) < rate
    out[m] = rng.choice(BLANKS, size=m.sum())
    return out


# ==================================================================================
# CLIENTS
# ==================================================================================
n = N_CLIENTS
client_ids = np.array([f"C{i:05d}" for i in range(1, n + 1)], dtype=object)
cz = rng.choice(len(Z), size=n, p=home_w)

age_groups = [(8, 17, .03), (18, 24, .04), (25, 44, .12), (45, 64, .24), (65, 74, .24), (75, 84, .21), (85, 95, .12)]
g = rng.choice(len(age_groups), size=n, p=[a[2] for a in age_groups])
age_years = np.array([rng.uniform(age_groups[i][0], age_groups[i][1] + 0.99) for i in g])
dob = AS_OF - pd.to_timedelta((age_years * 365.25).astype(int), unit="D")

# registration (true)
reg = []
for i in range(n):
    lo_i = max(pd.Timestamp("2012-03-01"), dob[i] + pd.DateOffset(years=5))
    hi_i = pd.Timestamp("2025-09-30")
    in_window = rng.random() < 0.08 or lo_i > hi_i
    if in_window:
        reg.append(START + pd.Timedelta(days=int(rng.integers(0, 300))))
    else:
        reg.append(lo_i + pd.Timedelta(days=int(rng.integers(0, (hi_i - lo_i).days + 1))))
reg = pd.to_datetime(reg)

ctype = rng.choice(["ADA Paratransit", "Medicaid", "Senior Program", "Visitor"], size=n, p=[.75, .12, .09, .04])
elig = np.empty(n, dtype=object)
for i in range(n):
    if ctype[i] == "Visitor":
        elig[i] = "Visitor"
    else:
        elig[i] = rng.choice(["Unconditional", "Conditional", "Temporary"], p=[.70, .25, .05])
gender = rng.choice(["Male", "Female", "Non-binary", "Unknown"], size=n, p=[.43, .52, .01, .04])
mob = rng.choice(["Wheelchair", "Walker", "Cane", "None", "Other"], size=n, p=[.30, .22, .15, .25, .08])
lang = rng.choice(["English", "Spanish", "Chinese", "Russian", "Haitian Creole", "Bengali", "Korean", "Arabic", "Other"],
                  size=n, p=[.62, .18, .06, .04, .03, .025, .015, .015, .015])
contact = rng.choice(["Phone", "SMS", "Email", "Mail"], size=n, p=[.55, .25, .12, .08])
status = rng.choice(["Active", "Inactive", "Suspended"], size=n, p=[.88, .09, .03])

home_addr_true = make_addresses(n, apt_rate=0.18)
hlat = ZLAT[cz] + rng.normal(0, 0.008, n)
hlon = ZLON[cz] + rng.normal(0, 0.008, n)

# ---- raw corruption: Clients ----
V_TYPE = {"ADA Paratransit": ["ADA Paratransit", "ADA", "ada", "A.D.A.", "Ada Paratransit"],
          "Medicaid": ["Medicaid", "MEDICAID", "Medicaid ", "Medicaid Transport"],
          "Senior Program": ["Senior Program", "SENIOR", "Senior Prog", "senior"],
          "Visitor": ["Visitor", "VISITOR", "visitor "]}
V_ELIG = {"Unconditional": ["Unconditional", "UNCOND", "Unconditional ", "unconditional eligibility", "ADA - Unconditional"],
          "Conditional": ["Conditional", "COND", "Conditional Eligible", "conditional", "ADA - Conditional"],
          "Temporary": ["Temporary", "TEMP", "temp. eligibility", "Temporary Eligibility"],
          "Visitor": ["Visitor", "VISITOR (21-day)", "Visitor Eligibility"]}
V_GENDER = {"Male": ["Male", "M", "male", "MALE"], "Female": ["Female", "F", "female", "FEMALE"],
            "Non-binary": ["Non-binary", "NB", "X"], "Unknown": ["Unknown", "U", "Prefer not to say"]}
V_MOB = {"Wheelchair": ["Wheelchair", "WHEELCHAIR", "W/C", "Power Chair", "wheelchair "],
         "Walker": ["Walker", "walker", "Rollator", "WALKER"],
         "Cane": ["Cane", "cane", "White Cane", "CANE"],
         "None": ["None", "NONE", "none", "No Aid", "N/A"],
         "Other": ["Other", "OTHER", "Other Aid"]}
V_LANG = {"English": ["English", "ENG", "english", "EN"], "Spanish": ["Spanish", "ESP", "Español", "spanish ", "ES"],
          "Chinese": ["Chinese", "Mandarin", "Cantonese", "CHI"], "Russian": ["Russian", "RUS", "russian"],
          "Haitian Creole": ["Haitian Creole", "Creole", "HAI"], "Bengali": ["Bengali", "Bangla", "BEN"],
          "Korean": ["Korean", "KOR"], "Arabic": ["Arabic", "ARA"], "Other": ["Other", "OTHER"]}
V_CONTACT = {"Phone": ["Phone", "PHONE", "Call", "phone call"], "SMS": ["SMS", "Text", "Text Message", "sms"],
             "Email": ["Email", "e-mail", "EMAIL"], "Mail": ["Mail", "US Mail", "Postal"]}
V_STATUS = {"Active": ["Active", "A", "ACT", "active ", "1"], "Inactive": ["Inactive", "I", "INACT", "0"],
            "Suspended": ["Suspended", "S", "SUSP", "suspended"]}

c_type = apply_variants(ctype, V_TYPE)
c_elig = apply_variants(elig, V_ELIG)
c_gender = blankify(apply_variants(gender, V_GENDER), 0.06)
c_mob = blankify(apply_variants(mob, V_MOB), 0.05)
c_lang = blankify(apply_variants(lang, V_LANG), 0.04)
c_contact = blankify(apply_variants(contact, V_CONTACT), 0.06)
c_status = apply_variants(status, V_STATUS)
# a few unknown status codes
unk = rng.choice(n, 25, replace=False); c_status[unk] = rng.choice(["X", "?", "PEND"], 25)
for a in (c_type, c_elig, c_gender, c_mob, c_lang, c_contact, c_status):
    a[:] = noise_text(a)

# city / state labels
V_CITY = {"New York": ["New York", "NEW YORK", "new york", "New York City", "NYC", "Manhattan"],
          "Bronx": ["Bronx", "The Bronx", "BRONX", "bronx"],
          "Brooklyn": ["Brooklyn", "BROOKLYN", "Bklyn", "brooklyn"],
          "Staten Island": ["Staten Island", "Staten Is.", "S.I.", "STATEN ISLAND"]}
c_city = apply_variants(ZCITY[cz], V_CITY)
c_city = noise_text(c_city, 0.04, 0.02, 0.02)
c_city = blankify(c_city, 0.01)
V_STATE = {"NY": ["NY", "ny", "New York", "N.Y.", "NY "], "NJ": ["NJ", "nj", "New Jersey", "N.J."]}
c_state = blankify(apply_variants(ZST[cz], V_STATE, p_first=0.72), 0.02)

# addresses
c_addr = messy_address(home_addr_true)
c_addr = blankify(c_addr, 0.012)

# zip
c_zip = ZIP[cz].astype(object)
for i in range(n):
    r = rng.random()
    z = c_zip[i]
    if r < 0.020:
        c_zip[i] = z + "-" + f"{rng.integers(1000, 9999)}"
    elif r < 0.032:
        c_zip[i] = " " + z + " "
    elif r < 0.042:
        c_zip[i] = z + ".0"
    if z.startswith("0") and rng.random() < 0.20:
        c_zip[i] = z.lstrip("0")                      # leading zero dropped (NJ)
bad = rng.choice(n, 15, replace=False)
c_zip[bad] = rng.choice(["00000", "ABCDE", "1003", "99999", "N/A"], 15)
miss = rng.choice(n, 25, replace=False); c_zip[miss] = ""

# coordinates
c_lat = np.array([f"{v:.6f}" for v in hlat], dtype=object)
c_lon = np.array([f"{v:.6f}" for v in hlon], dtype=object)
m = rng.choice(n, 75, replace=False); c_lat[m] = ""; c_lon[m] = ""                     # missing
m2 = rng.choice(n, 50, replace=False)
for j, i in enumerate(m2):
    k = j % 5
    if k == 0: c_lat[i], c_lon[i] = "0", "0"
    elif k == 1: c_lat[i], c_lon[i] = "91.2345", c_lon[i]
    elif k == 2: c_lat[i], c_lon[i] = c_lon[i], c_lat[i]                              # swapped
    elif k == 3: c_lat[i], c_lon[i] = "N/A", "N/A"
    else: c_lat[i], c_lon[i] = c_lat[i], "-181.5"

# dates of birth / registration
c_dob = np.array([d.strftime("%Y-%m-%d") for d in dob], dtype=object)
c_reg = np.array([d.strftime("%Y-%m-%d") for d in reg], dtype=object)
idx = rng.choice(n, 40, replace=False)
bad_dobs = ["2031-02-14", "1900-01-01", "1850-05-12", "0000-00-00", "unknown", "2030-13-45", "2027-06-01", "1899-12-31"]
for j, i in enumerate(idx):
    c_dob[i] = bad_dobs[j % len(bad_dobs)]
c_dob[rng.choice(n, 50, replace=False)] = ""
# registration before DOB (valid DOB rows only)
valid_dob_idx = [i for i in range(n) if c_dob[i][:2] in ("19", "20") and c_dob[i] not in bad_dobs and c_dob[i] != ""]
for i in rng.choice(valid_dob_idx, 40, replace=False):
    c_reg[i] = (dob[i] - pd.Timedelta(days=int(rng.integers(30, 1500)))).strftime("%Y-%m-%d")
for i in rng.choice(n, 20, replace=False):
    c_reg[i] = (AS_OF + pd.Timedelta(days=int(rng.integers(30, 400)))).strftime("%Y-%m-%d")      # future registration
c_reg[rng.choice(n, 30, replace=False)] = ""
c_reg[rng.choice(n, 10, replace=False)] = "not recorded"

clients = pd.DataFrame({
    "ClientID": client_ids, "DateOfBirth": c_dob, "RegistrationDate": c_reg, "ClientType": c_type,
    "EligibilityCategory": c_elig, "Gender": c_gender, "HomeAddressLine": c_addr, "HomeCity": c_city,
    "HomeState": c_state, "HomeZipCode": c_zip, "HomeLatitude": c_lat, "HomeLongitude": c_lon,
    "PreferredLanguage": c_lang, "MobilityAid": c_mob, "ClientStatus": c_status,
    "PreferredContactMethod": c_contact})

# duplicates: 30 exact + 30 conflicting (second copy has different status / missing attributes / reformatted ZIP)
exact = clients.iloc[rng.choice(n, 30, replace=False)].copy()
conf_src = rng.choice(n, 30, replace=False)
conf = clients.iloc[conf_src].copy()
for j, (ix, row) in enumerate(conf.iterrows()):
    k = j % 3
    if k == 0:
        conf.at[ix, "ClientStatus"] = rng.choice(["Inactive", "I", "Suspended"])
    elif k == 1:
        for col in ("Gender", "MobilityAid", "PreferredContactMethod", "HomeCity"):
            conf.at[ix, col] = ""
    else:
        conf.at[ix, "HomeZipCode"] = ""
        conf.at[ix, "HomeLatitude"] = ""
        conf.at[ix, "HomeLongitude"] = ""
clients_raw = pd.concat([clients, exact, conf], ignore_index=True)
# scatter duplicates near the originals
order = np.concatenate([np.arange(n) + 0.0, np.array([clients.index.get_loc(i) for i in exact.index]) + rng.random(30) * 40,
                        conf_src + rng.random(30) * 40])
clients_raw = clients_raw.iloc[np.argsort(order, kind="stable")].reset_index(drop=True)

# ==================================================================================
# TRIPS (truth first, then raw corruption)
# ==================================================================================
recurring = rng.random(n) < 0.06
w = rng.lognormal(0, 0.85, n) * np.where(recurring, 7.0, 1.0)
w *= np.where(status == "Inactive", 0.15, np.where(status == "Suspended", 0.3, 1.0))
w *= np.where(ctype == "Visitor", 0.15, 1.0)
w *= np.where(rng.random(n) < 0.12, 0.0, 1.0)             # ~12% of clients never ride
cp = w / w.sum()

days = pd.date_range(START, END)
holidays = pd.to_datetime(["2025-10-13", "2025-11-11", "2025-11-27", "2025-12-25", "2026-01-01", "2026-01-19",
                           "2026-02-16", "2026-05-25", "2026-06-19", "2026-07-03", "2026-07-04", "2026-09-07"])
dw = np.where(days.dayofweek == 6, 0.48, np.where(days.dayofweek == 5, 0.62, 1.0))
dw = np.where(days.isin(holidays), 0.55, dw) * (1 + 0.12 * np.arange(len(days)) / (len(days) - 1))
dw = dw / dw.sum()

N_RET = int(round(N_TRIPS * 0.12 / 1.12))
N_OUT = N_TRIPS - N_RET
date_i = rng.choice(len(days), size=N_OUT, p=dw)
tdate = days[date_i]
cli = rng.choice(n, size=N_OUT, p=cp)
for _ in range(40):
    bad_m = reg.values[cli] > tdate.values
    if not bad_m.any():
        break
    cli[bad_m] = rng.choice(n, size=bad_m.sum(), p=cp)
else:
    raise SystemExit("could not place all trips after registration")

HOUR_W = np.array([.05, .05, .05, .05, .08, .3, 1.0, 1.7, 2.2, 2.0, 1.7, 1.5, 1.4, 1.5, 1.7, 2.0, 2.1, 1.8, 1.3, .9, .6, .4, .25, .15])
HOUR_W = HOUR_W / HOUR_W.sum()
hour = rng.choice(24, size=N_OUT, p=HOUR_W)
minute = rng.choice(np.arange(0, 60, 5), size=N_OUT)
sched_pu = tdate + pd.to_timedelta(hour * 60 + minute, unit="m")

# pickup/dropoff locations
home_pickup = rng.random(N_OUT) < 0.82
pz = np.where(home_pickup, cz[cli], rng.choice(len(Z), size=N_OUT, p=dest_w))
dz = rng.choice(len(Z), size=N_OUT, p=dest_w)
same = rng.random(N_OUT) < 0.14
dz = np.where(same, pz, dz)

# append returns
ret_src = rng.choice(N_OUT, size=N_RET, replace=False)
stay = rng.integers(90, 421, size=N_RET)
ret_min = np.minimum(hour[ret_src] * 60 + minute[ret_src] + stay, 23 * 60 + 55)
ret_min = (ret_min // 5) * 5

def cat(a, b): return np.concatenate([a, b])

is_ret = cat(np.zeros(N_OUT, bool), np.ones(N_RET, bool))
cli_all = cat(cli, cli[ret_src])
tdate_all = tdate.append(tdate[ret_src])
sched_pu_all = pd.DatetimeIndex(cat(sched_pu.values, (tdate[ret_src] + pd.to_timedelta(ret_min, unit="m")).values))
pz_all = cat(pz, dz[ret_src]); dz_all = cat(dz, pz[ret_src])
pick_home = cat(home_pickup, np.zeros(N_RET, bool))                  # pickup at client's home
drop_home = cat(np.zeros(N_OUT, bool), home_pickup[ret_src])         # drop-off at client's home
booking_key = cat(np.arange(N_OUT), ret_src)                         # outbound + return share a booking
N = len(cli_all)
assert N == N_TRIPS

# order chronologically -> IDs
o = np.lexsort((np.arange(N), sched_pu_all.values))
def take(a): return a[o] if not isinstance(a, pd.DatetimeIndex) else a[o]
cli_all, tdate_all, sched_pu_all, pz_all, dz_all, pick_home, drop_home, booking_key, is_ret = [
    take(x) for x in (cli_all, tdate_all, sched_pu_all, pz_all, dz_all, pick_home, drop_home, booking_key, is_ret)]
trip_id = np.array([f"T{i:07d}" for i in range(1, N + 1)], dtype=object)
# booking IDs in order of first appearance
bk_map = {}
bk = np.empty(N, dtype=object)
for i, key in enumerate(booking_key):
    if key not in bk_map:
        bk_map[key] = f"BK{len(bk_map) + 1:07d}"
    bk[i] = bk_map[key]

# geography (truth)
def pt(zidx, is_home, cl, jitter=0.007):
    lat = ZLAT[zidx] + rng.normal(0, jitter, N); lon = ZLON[zidx] + rng.normal(0, jitter, N)
    lat = np.where(is_home, hlat[cl] + rng.normal(0, 0.0004, N), lat)
    lon = np.where(is_home, hlon[cl] + rng.normal(0, 0.0004, N), lon)
    return lat, lon
plat, plon = pt(pz_all, pick_home, cli_all)
dlat, dlon = pt(dz_all, drop_home, cli_all)
p_addr = make_addresses(N); d_addr = make_addresses(N)
ph = np.where(pick_home)[0]; p_addr[ph] = home_addr_true[cli_all[ph]]
dh = np.where(drop_home)[0]; d_addr[dh] = home_addr_true[cli_all[dh]]

pb = ZB[pz_all]
dist = np.maximum(0.5, hav_miles(plat, plon, dlat, dlon) * 1.3 + rng.normal(0, 0.25, N))
same_loc = pz_all == dz_all
dist = np.where(same_loc, np.maximum(0.5, rng.gamma(2.0, 0.9, N)), dist)

# mode / route
modes = np.array(["Primary", "Broker", "Supplemental"])
P_MODE = {0: (.55, .33, .12), 1: (.55, .33, .12), 2: (.55, .33, .12), 3: (.55, .33, .12),
          4: (.45, .40, .15), 5: (.10, .60, .30), 6: (.10, .60, .30)}
pP = np.array([P_MODE[b][0] for b in pb]); pB = np.array([P_MODE[b][1] for b in pb]); pS = np.array([P_MODE[b][2] for b in pb])
wc = mob[cli_all] == "Wheelchair"
pP = np.where(wc, pP + .7 * pS, pP); pS = np.where(wc, .3 * pS, pS)
u = rng.random(N)
mode_t = np.where(u < pP, 0, np.where(u < pP + pB, 1, 2))
BASE = [1000, 2000, 3000]
ROUTES = {}   # (mode, borough) -> (numbers, weights)
for m_ in range(3):
    for b_ in range(7):
        k = 3 if b_ <= 4 else (2 if b_ == 5 else 1)
        nums = [BASE[m_] + b_ * 100 + kk * 10 + 5 for kk in range(k)]
        wts = {3: [.5, .3, .2], 2: [.65, .35], 1: [1.0]}[k]
        if m_ == 2 and k == 3: wts = [.7, .25, .05]
        ROUTES[(m_, b_)] = (nums, wts)
route_num = np.zeros(N, dtype=int)
for (m_, b_), (nums, wts) in ROUTES.items():
    mk = (mode_t == m_) & (pb == b_)
    if mk.sum():
        route_num[mk] = rng.choice(nums, size=mk.sum(), p=wts)
all_routes = sorted(set(route_num))
rq = {r: float(rng.lognormal(0, 0.22)) for r in all_routes}
rq[2105] = 1.9; rq[1405] = 0.5; rq[3105] = 1.5
route_mult = np.array([rq[r] for r in route_num])
DESC = ["Local Loop", "Crosstown", "Medical Corridor"]
BSHORT = ["Manhattan", "Bronx", "Brooklyn", "Queens", "Staten Island", "Nassau", "Hudson NJ"]
route_desc_t = np.array([f"{BSHORT[(r // 100) % 10]} {DESC[(r // 10) % 10]} #{r}" for r in route_num], dtype=object)

# service attributes
sdt = np.where(tdate_all.isin(holidays), "Holiday",
               np.where(tdate_all.dayofweek == 5, "Saturday", np.where(tdate_all.dayofweek == 6, "Sunday", "Weekday")))
lead = np.where(rng.random(N) < .03, rng.integers(14, 90, N),
                np.where(rng.random(N) < .45, 1, np.where(rng.random(N) < .55, rng.integers(2, 4, N), rng.integers(4, 15, N))))
book_date = tdate_all - pd.to_timedelta(lead, unit="D")
region = np.where(np.isin(pb, [0, 1]), "North", np.where(np.isin(pb, [3, 5, 6]), "East", "South"))

# lateness
promise = sched_pu_all + pd.Timedelta(minutes=15)
BASE_Q = np.array([.15, .26, .36])
hr_all = np.asarray(sched_pu_all.hour)
peak = ((hr_all >= 7) & (hr_all <= 9)) | ((hr_all >= 15) & (hr_all <= 18))
month = tdate_all.month
bor_mult = np.array([1.0, 1.15, 1.10, 1.0, .90, .95, 1.0])[pb]
q = BASE_Q[mode_t] * route_mult * np.where(peak, 1.25, 1.0) * np.where(np.isin(month, [1, 2]), 1.3, 1.0) * bor_mult
q = np.clip(q, 0, .8)
late_event = rng.random(N) < q
delay = rng.normal(-4, 8, N) + late_event * (8 + rng.exponential(18, N))
delay = np.clip(np.round(delay), -35, 240).astype(int)

# outcomes
dow = tdate_all.dayofweek
mobt = mob[cli_all]
f_ns = (np.array([1.0, 1.25, 1.05, 1.0, .8, .9, 1.0])[pb] * np.array([.9, 1.2, 1.4])[mode_t]
        * np.where(mobt == "Wheelchair", .8, np.where(mobt == "None", 1.2, 1.0))
        * np.where(np.isin(dow, [0, 4]), 1.15, np.where(dow >= 5, .85, 1.0))
        * np.where(hr_all < 7, 1.3, 1.0) * np.where(route_num == 2105, 1.6, 1.0) * np.where(route_num == 3105, 1.4, 1.0))
p_ns = .040 * f_ns
p_ca = .065 * np.where(np.isin(month, [1, 2]), 1.35, 1.0) * np.where(is_ret, .8, 1.0)
p_ot = .035 * np.array([.9, 1.4, .8])[mode_t]
u = rng.random(N)
outcome = np.where(u < p_ns, "No-Show", np.where(u < p_ns + p_ca, "Cancelled", np.where(u < p_ns + p_ca + p_ot, "Other", "Completed")))
unres = rng.random(N) < .0005
outcome = np.where(unres, "Unresolved", outcome)
comp = outcome == "Completed"; nsm = outcome == "No-Show"; cam = outcome == "Cancelled"; otm = outcome == "Other"; unm = outcome == "Unresolved"

# times (truth)
dwell = np.clip(np.round(rng.gamma(2, 1.0, N)), 1, 5).astype(int)
actual_pu = promise + pd.to_timedelta(delay, unit="m")
veh_arr = actual_pu - pd.to_timedelta(dwell, unit="m")
speed = np.clip(rng.normal(12.5, 2.2, N), 7, 20)
sched_dur = (np.ceil((dist / speed * 60 + 5) / 5) * 5).astype(int)
sched_do = sched_pu_all + pd.to_timedelta(sched_dur, unit="m")
act_dur = np.maximum(5, np.round(dist / np.clip(rng.normal(12.0, 2.5, N), 6, 22) * 60 * rng.lognormal(0, .12, N) + 3)).astype(int)
actual_do = actual_pu + pd.to_timedelta(act_dur, unit="m")
ns_arr = promise + pd.to_timedelta(np.round(rng.normal(0, 6, N)).astype(int), unit="m")
drv_arr = pd.DatetimeIndex(np.where(nsm, ns_arr.values, veh_arr.values)) + pd.to_timedelta(rng.integers(0, 4, N), unit="m")

# fare / refund (truth)
fare = np.where(mode_t == 2, 3.5 + 1.1 * dist, 2.75 + 0.85 * dist).round(2)
refund = np.zeros(N)
ref_flag = comp & (((delay > 45) & (rng.random(N) < .6)) | (rng.random(N) < .012))
refund[ref_flag] = np.where(rng.random(ref_flag.sum()) < .5, fare[ref_flag], (fare[ref_flag] * .5).round(2))

sched_pax = rng.choice([1, 2, 3], size=N, p=[.84, .12, .04])
act_pax = np.where(comp, np.where(rng.random(N) < .93, sched_pax, np.maximum(1, sched_pax - 1)), 0)

# ---- RAW: convert to strings & corrupt ----
def ts(x): return pd.Series(x).dt.strftime("%Y-%m-%d %H:%M:%S").astype(object).values
def dstr(x): return pd.Series(x).dt.strftime("%Y-%m-%d").astype(object).values

BAD_TS = np.array(["NULL", "N/A", "0000-00-00 00:00:00", "2025-02-30 08:15:00", "25:61:00", "TBD"], dtype=object)
def corrupt_ts(arr, rate, mask=None):
    out = np.array(arr, dtype=object)
    hit = rng.random(N) < rate
    if mask is not None: hit &= mask
    k = hit.sum()
    kind = rng.random(k)
    vals = np.where(kind < .5, "", rng.choice(BAD_TS, size=k))
    out[hit] = vals
    return out

R = {}
R["TripID"] = trip_id
cid = np.array([f"C{c + 1:05d}" for c in cli_all], dtype=object)
r_ = rng.random(N)
cid = np.where(r_ < .008, np.char.lower(cid.astype(str)), cid)
cid = np.where((r_ >= .008) & (r_ < .015), np.array([" " + x + " " for x in cid]), cid)
orph = (r_ >= .015) & (r_ < .023)
cid = np.where(orph, np.array([f"C{rng.integers(5200, 9999):05d}" for _ in range(N)]), cid)
cid = np.where((r_ >= .023) & (r_ < .025), "", cid)
R["ClientID"] = cid
R["BookingID"] = bk
td = dstr(tdate_all).astype(object)
r2 = rng.random(N)
td = np.where(r2 < .001, "", td)
off = (r2 >= .001) & (r2 < .0014)
td = np.where(off, np.array([x.replace("2025", "2024").replace("2026", "2025") for x in dstr(tdate_all)], dtype=object), td)
R["TripDate"] = td
bd = dstr(book_date).astype(object)
bd = np.where(rng.random(N) < .002, dstr(tdate_all + pd.to_timedelta(rng.integers(1, 5, N), unit="D")), bd)   # booking after trip
bd = np.where(rng.random(N) < .004, "", bd)
R["BookingDate"] = bd
R["ScheduledPickupTime"] = corrupt_ts(ts(sched_pu_all), .003)
R["ScheduledDropoffTime"] = corrupt_ts(ts(sched_do), .005)
R["PromiseTime"] = corrupt_ts(ts(promise), .010)

# actual pickup: expected null for cancel / no-show / other; defects only on completed
ap = ts(actual_pu).astype(object)
ap = np.where(comp, ap, "")
shift = comp & (rng.random(N) < .0015)
ap_shift = ts(actual_pu + pd.to_timedelta(np.where(rng.random(N) < .5, 1440, -1440), unit="m")).astype(object)
ap = np.where(shift, ap_shift, ap)
ap = corrupt_ts(ap, .015, mask=comp)
R["ActualPickupTime"] = ap
ad = np.where(comp, ts(actual_do), "").astype(object)
ad = corrupt_ts(ad, .015, mask=comp)
R["ActualDropoffTime"] = ad
R["ScheduledDurationMinutes"] = sched_dur.astype(object)

PURP = ["Medical", "Dialysis", "Work", "Education/Training", "Shopping/Errand", "Social/Recreation", "Senior Center", "Other"]
pur = rng.choice(PURP, size=N, p=[.30, .08, .14, .06, .12, .12, .08, .10])
rec_c = recurring[cli_all]
pur = np.where(rec_c & (rng.random(N) < .55), "Dialysis", pur)
V_PURP = {"Medical": ["Medical", "MED", "Med Appt", "medical"], "Dialysis": ["Dialysis", "DIAL", "Dialysis Tx"],
          "Work": ["Work", "Employment", "WORK"], "Education/Training": ["Education/Training", "Education", "EDU"],
          "Shopping/Errand": ["Shopping/Errand", "Shopping", "Errand"], "Social/Recreation": ["Social/Recreation", "Social", "Rec"],
          "Senior Center": ["Senior Center", "Senior Ctr", "SENIOR CENTER"], "Other": ["Other", "OTHER", "Misc"]}
pur_raw = blankify(noise_text(apply_variants(pur, V_PURP), .02, .02, .02), .03)
R["TripPurpose"] = pur_raw

V_STAT = {"Completed": ["Completed", "COMP", "comp", "Complete", "Cmpltd", "COMPLETED"],
          "Cancelled": ["Cancelled", "CXL", "Canceled", "cancelled ", "CANC", "Cancelled - Client"],
          "No-Show": ["No Show", "NS", "No-Show", "NOSHOW", "noshow", "No Show "],
          "Other": ["Missed Trip", "MISS", "Vehicle Breakdown", "BRKDWN", "Incomplete", "Failed", "FAIL"],
          "Unresolved": ["Scheduled", "SCHED", "UNK", "???", ""]}
R["RawTripStatus"] = apply_variants(outcome, V_STAT, p_first=.55)

V_CXL = {"Client Request": ["Client Request", "client request", "CLIENT REQ", "Client Req."],
         "Same-Day Cancellation": ["Same-Day Cancellation", "Same Day Cxl", "same day cancel"],
         "Weather": ["Weather", "WEATHER", "weather/snow"],
         "Medical Appointment Changed": ["Medical Appointment Changed", "Appt Changed", "Med Appt Chg"],
         "Duplicate Booking": ["Duplicate Booking", "Dup Booking", "Duplicate"],
         "Agency Cancelled": ["Agency Cancelled", "Agency Cxl"], "Schedule Change": ["Schedule Change", "Schedule Chg", "SCHED CHANGE"]}
V_NS = {"Not at Pickup Location": ["Not at Pickup Location", "Not at location", "NOT AT LOC"],
        "Not Ready at Window": ["Not Ready at Window", "Not Ready", "NOT READY"],
        "No Answer at Door": ["No Answer at Door", "No Answer/Door", "no answer"],
        "Client Unreachable": ["Client Unreachable", "Unreachable", "UNREACHABLE"]}
V_OT = {"Provider Missed Trip": ["Provider Missed Trip", "Missed Trip", "PROVIDER MISS"],
        "Vehicle Breakdown": ["Vehicle Breakdown", "Breakdown", "BRKDWN"],
        "Unable to Locate Client": ["Unable to Locate Client", "Unable to Locate", "UTL"],
        "Driver Unavailable": ["Driver Unavailable", "No Driver", "DRIVER N/A"]}
reason = np.full(N, "", dtype=object)
def fill_reason(mk, vmap, weights):
    keys = list(vmap.keys())
    ch = rng.choice(keys, size=mk.sum(), p=weights)
    reason[mk] = apply_variants(ch, vmap)
fill_reason(cam, V_CXL, [.34, .18, .10, .12, .08, .08, .10])
fill_reason(nsm, V_NS, [.35, .30, .20, .15])
fill_reason(otm, V_OT, [.30, .25, .25, .20])
reason = noise_text(reason, .03, .02, .02)
reason[(cam | nsm | otm) & (rng.random(N) < .08)] = ""
stray = comp & (rng.random(N) < .004); reason[stray] = "Client Request"
R["CancellationReason"] = reason

ns_raw = np.empty(N, dtype=object)
yes = ["Y", "1", "TRUE", "Yes"]; no = ["N", "0", "FALSE", "No"]
for i in range(N):
    if nsm[i]:
        r = rng.random()
        ns_raw[i] = "" if r < .04 else ("N" if r < .05 else rng.choice(yes))
    else:
        r = rng.random()
        ns_raw[i] = "" if r < .25 else ("Y" if r < .253 else rng.choice(no))
R["NoShowIndicatorRaw"] = ns_raw

# route / service info
def route_raw(r):
    f = rng.random()
    if f < .30: return f"R-{r}"
    if f < .60: return f"{r}"
    if f < .72: return f"r {r}"
    if f < .84: return f"Route {r}"
    if f < .90: return f" R-{r} "
    if f < .95: return f"R{r}"
    return f"RT-{r}"
rr = np.array([route_raw(r) for r in route_num], dtype=object)
oor = rng.random(N)
bad_routes = np.array(["4050", "R-999", "R-0", "Route 5010", "R-XX99", "r 9999"], dtype=object)
rr = np.where(oor < .004, rng.choice(bad_routes, size=N), rr)
rr = np.where((oor >= .004) & (oor < .0055), "", rr)
R["RouteID"] = rr
R["RouteDescription"] = noise_text(route_desc_t, .03, .03, .02)
V_MODE = {"Primary": ["Primary", "PRIM", "primary", "Prim."], "Broker": ["Broker", "BROKER", "Brkr", "broker"],
          "Supplemental": ["Supplemental", "SUPP", "Suppl.", "supplemental"]}
mode_names = modes[mode_t]
mode_lab = mode_names.copy().astype(object)
wrong = rng.random(N) < .07
mode_lab[wrong] = rng.choice(modes, size=wrong.sum())
R["RawServiceMode"] = apply_variants(mode_lab, V_MODE)
prov = np.where(mode_t == 0, rng.choice(["SP-01", "SP-02"], N), np.where(mode_t == 1, rng.choice(["SP-11", "SP-12", "SP-13"], N), "SP-21")).astype(object)
prov = np.where(rng.random(N) < .01, "", prov)
prov = np.where(rng.random(N) < .01, np.char.lower(prov.astype(str)), prov)
R["ServiceProviderID"] = prov
veh = np.where(wc, np.where(rng.random(N) < .85, "Lift Van", "Minivan"),
               rng.choice(["Sedan", "Minivan", "Lift Van"], size=N, p=[.45, .38, .17])).astype(object)
veh = np.where(mode_t == 2, np.where(wc, "Lift Van", "Taxi"), veh)
V_VEH = {"Sedan": ["Sedan", "SEDAN", "sedan"], "Minivan": ["Minivan", "Mini Van", "MINIVAN"],
         "Lift Van": ["Lift Van", "LIFT VAN", "lift-van", "Wheelchair Van"], "Taxi": ["Taxi", "TAXI", "Cab"]}
R["VehicleType"] = blankify(apply_variants(veh, V_VEH), .01)
V_REG = {"North": ["North", "NORTH", "N"], "East": ["East", "EAST", "E"], "South": ["South", "SOUTH", "S"]}
R["ServiceRegion"] = apply_variants(region.astype(object), V_REG)
V_BOR = {"Manhattan": ["Manhattan", "MN", "MANHATTAN", "manhattan "], "Bronx": ["Bronx", "The Bronx", "BX", "BRONX"],
         "Brooklyn": ["Brooklyn", "Bklyn", "BK", "BROOKLYN"], "Queens": ["Queens", "QNS", "QUEENS", "queens "],
         "Staten Island": ["Staten Island", "SI", "Staten Is."], "Nassau County": ["Nassau County", "Nassau", "NASSAU"],
         "Hudson County NJ": ["Hudson County NJ", "Hudson Co. NJ", "HUDSON NJ"]}
R["Borough"] = blankify(apply_variants(np.array(BOR, dtype=object)[pb], V_BOR), .005)
sdt_raw = sdt.astype(object)
mis = rng.random(N) < .01
sdt_raw[mis] = rng.choice(["Weekday", "Saturday", "Sunday"], size=mis.sum())
V_SDT = {"Weekday": ["Weekday", "WKDY", "weekday"], "Saturday": ["Saturday", "SAT", "Sat"], "Sunday": ["Sunday", "SUN", "Sun"],
         "Holiday": ["Holiday", "HOL", "holiday"]}
R["ServiceDayType"] = apply_variants(sdt_raw, V_SDT)
ch = rng.choice(["Phone", "Web", "App", "IVR"], size=N, p=[.40, .22, .28, .10]).astype(object)
V_CH = {"Phone": ["Phone", "PHONE", "phone"], "Web": ["Web", "Online", "web"], "App": ["App", "Mobile App", "APP"], "IVR": ["IVR", "Automated"]}
R["BookingChannel"] = blankify(apply_variants(ch, V_CH), .02)

# geography raw
def zip_raw(zidx):
    z = ZIP[zidx].astype(object)
    out = z.copy()
    r = rng.random(N)
    out = np.where(r < .02, np.array([a + "-" + f"{rng.integers(1000, 9999)}" for a in z], dtype=object), out)
    out = np.where((r >= .02) & (r < .032), np.array([" " + a + " " for a in z], dtype=object), out)
    out = np.where((r >= .032) & (r < .040), np.array([a + ".0" for a in z], dtype=object), out)
    lead0 = np.array([a.startswith("0") for a in z]) & (rng.random(N) < .20)
    out = np.where(lead0, np.array([a.lstrip("0") for a in z], dtype=object), out)
    out = np.where((r >= .040) & (r < .0425), rng.choice(["00000", "ABCDE", "1003", "N/A"], size=N), out)
    out = np.where((r >= .0425) & (r < .0475), "", out)
    return out
R["PickupAddress"] = blankify(messy_address(p_addr), .008)
R["PickupZipCode"] = zip_raw(pz_all)
R["DropoffAddress"] = blankify(messy_address(d_addr), .008)
R["DropoffZipCode"] = zip_raw(dz_all)

def coord_raw(lat, lon):
    la = np.array([f"{v:.6f}" for v in lat], dtype=object); lo_ = np.array([f"{v:.6f}" for v in lon], dtype=object)
    r = rng.random(N)
    miss_ = r < .012
    la[miss_] = ""; lo_[miss_] = ""
    k = (r >= .012) & (r < .0145); la[k], lo_[k] = lo_[k].copy(), la[k].copy()           # swapped
    k = (r >= .0145) & (r < .0155); la[k] = "0"; lo_[k] = "0"
    k = (r >= .0155) & (r < .0165); la[k] = "91.2345"
    k = (r >= .0165) & (r < .0185); la[k] = "N/A"; lo_[k] = "N/A"
    k = (r >= .0185) & (r < .0195); lo_[k] = "-181.5"
    k = (r >= .0195) & (r < .0225)                                                          # plausible range but far from ZIP
    la[k] = [f"{v:.6f}" for v in np.array(lat)[k] + rng.choice([-.25, .25], k.sum())]
    return la, lo_
R["PickupLatitude"], R["PickupLongitude"] = coord_raw(plat, plon)
R["DropoffLatitude"], R["DropoffLongitude"] = coord_raw(dlat, dlon)

# outcomes / metrics
V_PO = {"Picked Up": ["Picked Up", "PU", "Arrived", "picked up"], "No Show": ["No Show", "NS", "No-Show"],
        "Cancelled": ["Cancelled", "CXL", "N/A"], "Missed": ["Missed", "Not Served", "N/A"], "Unknown": ["", "N/A"]}
po = np.where(comp, "Picked Up", np.where(nsm, "No Show", np.where(cam, "Cancelled", np.where(otm, "Missed", "Unknown")))).astype(object)
po[rng.random(N) < .01] = "Picked Up"
R["RawPickupOutcome"] = apply_variants(po, V_PO)
V_DO = {"Dropped Off": ["Dropped Off", "DO", "Completed", "dropped off"], "Not Applicable": ["N/A", "", "NA"]}
do_ = np.where(comp, "Dropped Off", "Not Applicable").astype(object)
R["RawDropoffOutcome"] = apply_variants(do_, V_DO)
R["ScheduledPassengerCount"] = sched_pax.astype(object)
apx = act_pax.astype(object)
r3 = rng.random(N)
apx = np.where(r3 < .001, -1, np.where(r3 < .002, 15, apx)).astype(object)
apx = np.where(rng.random(N) < .004, "", apx)
R["ActualPassengerCount"] = apx

def fmt_money(v, r):
    if r < .15: return f"${v:.2f}"
    if r < .18: return f"{v:.1f}"
    return f"{v:.2f}"
fare_raw = np.empty(N, dtype=object)
rf = rng.random(N)
for i in range(N):
    if comp[i]:
        v = fare[i]
        if rf[i] < .003: fare_raw[i] = f"-{v:.2f}"
        elif rf[i] < .0035: fare_raw[i] = "999.99"
        elif rf[i] < .006: fare_raw[i] = "N/A"
        elif rf[i] < .016: fare_raw[i] = ""
        else: fare_raw[i] = fmt_money(v, rng.random())
    else:
        r = rng.random()
        fare_raw[i] = fmt_money(fare[i], .5) if r < .004 else ("0.00" if r < .55 else "")
R["RawFareAmount"] = fare_raw
ref_raw = np.empty(N, dtype=object)
over = comp & (rng.random(N) < .0025)
for i in range(N):
    if over[i]:
        ref_raw[i] = f"{fare[i] * 1.5 + 1:.2f}"
    elif refund[i] > 0:
        ref_raw[i] = fmt_money(refund[i], rng.random())
    else:
        r = rng.random()
        ref_raw[i] = "0.00" if r < .5 else ("0" if r < .7 else "")
R["RawRefundAmount"] = ref_raw

dist_raw = np.empty(N, dtype=object)
rd = rng.random(N)
for i in range(N):
    v = dist[i]; r = rd[i]
    if r < .0015: dist_raw[i] = f"-{v:.1f}"
    elif r < .0055: dist_raw[i] = "0"
    elif r < .0060: dist_raw[i] = "999"
    elif r < .0100: dist_raw[i] = "N/A"
    elif r < .0200: dist_raw[i] = ""
    elif r < .20: dist_raw[i] = f"{v:.1f} mi"
    elif r < .27: dist_raw[i] = f"{v:.2f} miles"
    else: dist_raw[i] = f"{v:.1f}"
R["RawDistanceMiles"] = dist_raw
dur_raw = np.empty(N, dtype=object)
rd = rng.random(N)
for i in range(N):
    if not comp[i]:
        dur_raw[i] = ""; continue
    v = act_dur[i]; r = rd[i]
    if r < .005: dur_raw[i] = "0"
    elif r < .007: dur_raw[i] = f"-{v}"
    elif r < .008: dur_raw[i] = f"{v + 600}"
    elif r < .012: dur_raw[i] = "n/a"
    elif r < .022: dur_raw[i] = ""
    elif r < .20: dur_raw[i] = f"{v} min"
    elif r < .25: dur_raw[i] = f"{v}.0"
    else: dur_raw[i] = f"{v}"
R["RawTripDuration"] = dur_raw
dl_raw = np.empty(N, dtype=object)
rd = rng.random(N)
for i in range(N):
    if not comp[i]:
        dl_raw[i] = ""; continue
    v = delay[i]; r = rd[i]
    if r < .12: dl_raw[i] = ""
    elif r < .20: dl_raw[i] = f"{-v}"                              # sign flipped
    elif r < .30: dl_raw[i] = f"{abs(v)} min {'late' if v > 0 else 'early'}"
    else: dl_raw[i] = f"{v}"
R["RawDelayMinutes"] = dl_raw
da = ts(drv_arr).astype(object); da = np.where(cam | otm | unm, "", da)
da = corrupt_ts(da, .05, mask=comp | nsm)
R["DriverArrivalTime"] = da
va = np.where(comp, ts(veh_arr), np.where(nsm, ts(ns_arr), "")).astype(object)
va = corrupt_ts(va, .045, mask=comp | nsm)
R["VehicleArrivalTime"] = va

cols = ["TripID", "ClientID", "BookingID", "TripDate", "BookingDate", "ScheduledPickupTime", "ScheduledDropoffTime",
        "PromiseTime", "ActualPickupTime", "ActualDropoffTime", "ScheduledDurationMinutes", "TripPurpose", "RawTripStatus",
        "CancellationReason", "NoShowIndicatorRaw", "RouteID", "RouteDescription", "RawServiceMode", "ServiceProviderID",
        "VehicleType", "ServiceRegion", "Borough", "ServiceDayType", "BookingChannel", "PickupAddress", "PickupZipCode",
        "PickupLatitude", "PickupLongitude", "DropoffAddress", "DropoffZipCode", "DropoffLatitude", "DropoffLongitude",
        "RawPickupOutcome", "RawDropoffOutcome", "ScheduledPassengerCount", "ActualPassengerCount", "RawFareAmount",
        "RawRefundAmount", "RawDistanceMiles", "RawTripDuration", "RawDelayMinutes", "DriverArrivalTime", "VehicleArrivalTime"]
trips = pd.DataFrame({c: R[c] for c in cols})
for c in cols:
    trips[c] = trips[c].astype(str).replace({"nan": ""})

# duplicates: 250 exact, 100 stale ("Scheduled", no actuals), 50 partial (missing actual pickup/dropoff)
exact_ix = rng.choice(N, 250, replace=False)
comp_ix = np.where(comp)[0]
stale_ix = rng.choice(comp_ix, 100, replace=False)
part_ix = rng.choice(np.setdiff1d(comp_ix, stale_ix), 50, replace=False)
d_exact = trips.iloc[exact_ix].copy()
d_stale = trips.iloc[stale_ix].copy()
for c_ in ["ActualPickupTime", "ActualDropoffTime", "VehicleArrivalTime", "DriverArrivalTime", "RawFareAmount",
           "RawRefundAmount", "RawTripDuration", "RawDelayMinutes", "ActualPassengerCount", "RawDropoffOutcome", "NoShowIndicatorRaw"]:
    d_stale[c_] = ""
d_stale["RawTripStatus"] = rng.choice(["Scheduled", "SCHED"], 100)
d_stale["RawPickupOutcome"] = ""
d_part = trips.iloc[part_ix].copy()
d_part["ActualPickupTime"] = ""; d_part["ActualDropoffTime"] = ""
pos = np.concatenate([np.arange(N), exact_ix + rng.random(250) * 3000, stale_ix + rng.random(100) * 3000, part_ix + rng.random(50) * 3000])
trips_raw = pd.concat([trips, d_exact, d_stale, d_part], ignore_index=True)
trips_raw = trips_raw.iloc[np.argsort(pos, kind="stable")].reset_index(drop=True)

os.makedirs(OUT, exist_ok=True)
clients_raw.to_csv(os.path.join(OUT, "Clients.csv"), index=False, encoding="utf-8-sig")
trips_raw.to_csv(os.path.join(OUT, "Trips.csv"), index=False, encoding="utf-8-sig")
print("Clients rows:", len(clients_raw), " Trips rows:", len(trips_raw))
