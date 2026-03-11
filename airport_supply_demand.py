import json
import pandas as pd
from collections import Counter
from datetime import datetime, timezone

# =========================
# Config
# =========================
INPUT_FILE = "TestCases/DOE_FilterAirport/DOE_run8.json"
INPUT_ENCODING = "utf-8"      
OUTPUT_CSV = "airport_supply_demand_DOE_run8.csv"

TIME_COL = "RequestedTime"
DEP_COL = "DepartureAirport"
ARR_COL = "ArrivalAirport"
ACT_COL = "ActivityType"
REVENUE_TYPE = "OPERATE_REVENUE_FLIGHT"

# =========================
# Helper: parse datetime to UTC (robust)
# =========================
def parse_dt_utc(s: str):
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    # ISO first
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    # common formats
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None

# =========================
# Load JSON
# =========================
with open(INPUT_FILE, "r", encoding=INPUT_ENCODING) as f:
    data = json.load(f)

flight_requests = data.get("FlightRequests", [])
crewmembers = data.get("Crewmembers", [])
tails = data.get("Tails", [])

# =========================
# Planning horizon
# =========================
ph = data.get("Configuration", {}).get("PlanningHorizon", {})
begin_str = ph.get("BeginTime")
end_str = ph.get("EndTime")

begin_dt = parse_dt_utc(begin_str)
end_dt = parse_dt_utc(end_str)

if begin_dt is None or end_dt is None:
    raise ValueError(
        f"PlanningHorizon BeginTime/EndTime parse failed.\n"
        f"BeginTime={begin_str}\nEndTime={end_str}"
    )

print("PlanningHorizon:", begin_dt, "to", end_dt)

# =========================
# Count tails & crew by CurrentLocation
# =========================
tails_counter = Counter()
for t in tails:
    loc = t.get("CurrentLocation")
    if loc:
        tails_counter[loc] += 1

crew_counter = Counter()
for c in crewmembers:
    loc = c.get("CurrentLocation")
    if loc:
        crew_counter[loc] += 1

# =========================
# Count reservations by airport (dep + arr)
#   - within planning horizon
#   - revenue only
# =========================
res_counter = Counter()
bad_time = 0
kept = 0

for r in flight_requests:
    if r.get(ACT_COL) != REVENUE_TYPE:
        continue

    rt = parse_dt_utc(r.get(TIME_COL))
    if rt is None:
        bad_time += 1
        continue

    if not (begin_dt <= rt <= end_dt):
        continue

    kept += 1
    dep = r.get(DEP_COL)
    arr = r.get(ARR_COL)

    if dep:
        res_counter[dep] += 1
    if arr:
        res_counter[arr] += 1

print("Revenue requests kept within horizon:", kept)
print("Bad RequestedTime dropped:", bad_time)

# =========================
# Build airport-level table
# =========================
all_airports = set(tails_counter) | set(crew_counter) | set(res_counter)

rows = []
for ap in sorted(all_airports):
    rows.append({
        "airport_name": ap,
        "tails_num": int(tails_counter.get(ap, 0)),
        "crewmembers_num": int(crew_counter.get(ap, 0)),
        "reservations_num": int(res_counter.get(ap, 0)),
    })

df_out = pd.DataFrame(rows)

# Optional: sort so important airports appear first
df_out = df_out.sort_values(
    by=["reservations_num", "tails_num", "crewmembers_num"],
    ascending=False
).reset_index(drop=True)

df_out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
print(f"✅ CSV exported: {OUTPUT_CSV}")