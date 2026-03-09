import json
from collections import Counter
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
from datetime import datetime, timezone
import math

# =========================
# Config
# =========================
INPUT_FILE = "DOE_run3.json"
INPUT_ENCODING = "utf-8"   # change to "utf-8" if needed
SRD_FILE = "srd.json"

TIME_COL = "RequestedTime"
DEP_COL = "DepartureAirport"
ARR_COL = "ArrivalAirport"

# =========================
# Helper: parse time safely (UTC-aware)
# =========================
def parse_dt_utc(s: str):
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:
        pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None

# =========================
# Load main data
# =========================
with open(INPUT_FILE, "r", encoding=INPUT_ENCODING) as f:
    data = json.load(f)

flight_requests = data.get("FlightRequests", [])
crewmembers = data.get("Crewmembers", [])
tails = data.get("Tails", [])

# =========================
# Planning horizon (from Configuration)
# =========================
cfg = data.get("Configuration", {})
ph = cfg.get("PlanningHorizon", {})
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
# Load airport coords
# =========================
with open(SRD_FILE, "r", encoding="utf-8") as f:
    airport_data = json.load(f)

airports_list = airport_data["StaticRoutingData"]["Airports"]
airport_coords = {a["AirportID"]: (a["Latitude"], a["Longitude"]) for a in airports_list}

# =========================
# 1) Requests traffic within PlanningHorizon
#    (counts both dep + arr)
# =========================
req_counter = Counter()
bad_time = 0
kept_req = 0

for r in flight_requests:
    rt = parse_dt_utc(r.get(TIME_COL))
    if rt is None:
        bad_time += 1
        continue
    if not (begin_dt <= rt <= end_dt):
        continue

    kept_req += 1
    dep = r.get(DEP_COL)
    arr = r.get(ARR_COL)
    if dep:
        req_counter[dep] += 1
    if arr:
        req_counter[arr] += 1

print("FlightRequests total:", len(flight_requests))
print("Requests kept within horizon:", kept_req)
print("Bad RequestedTime dropped:", bad_time)
print("Unique airports in requests:", len(req_counter))

# =========================
# 2) Crew currently at airports
# =========================
crew_counter = Counter()
for c in crewmembers:
    loc = c.get("CurrentLocation")
    if loc:
        crew_counter[loc] += 1
print("Crewmembers total:", len(crewmembers))
print("Unique airports with crew:", len(crew_counter))

# =========================
# 3) Tails currently at airports
# =========================
tail_counter = Counter()
for t in tails:
    loc = t.get("CurrentLocation")
    if loc:
        tail_counter[loc] += 1
print("Tails total:", len(tails))
print("Unique airports with tails:", len(tail_counter))

# =========================
# Helper: build scatter arrays with log-size scaling
# =========================
def build_scatter(counter: Counter, size_mult: float):
    lats, lons, sizes = [], [], []
    missing_coord = 0

    for airport, count in counter.items():
        if airport not in airport_coords:
            missing_coord += 1
            continue
        lat, lon = airport_coords[airport]
        lats.append(lat)
        lons.append(lon)

        # log scaling so huge counts don't dominate
        sizes.append(size_mult * math.log1p(count))

    return lats, lons, sizes, missing_coord

req_lats, req_lons, req_sizes, miss_req = build_scatter(req_counter, size_mult=120)
crew_lats, crew_lons, crew_sizes, miss_crew = build_scatter(crew_counter, size_mult=220)
tail_lats, tail_lons, tail_sizes, miss_tail = build_scatter(tail_counter, size_mult=260)

print("Missing coords - requests:", miss_req, "crew:", miss_crew, "tails:", miss_tail)

# =========================
# Plot overlay on ONE map
# =========================
plt.figure(figsize=(14, 9))

m = Basemap(
    projection="lcc",
    resolution="l",
    lat_0=37, lon_0=-95,
    width=5E6, height=3E6
)

m.drawcoastlines()
m.drawcountries()
m.drawstates()

# Convert coords
req_x, req_y = m(req_lons, req_lats)
crew_x, crew_y = m(crew_lons, crew_lats)
tail_x, tail_y = m(tail_lons, tail_lats)

# Layer order: tails + crew first, requests last (or reverse) — I prefer requests last so demand is visible
# Tails (green squares)
m.scatter(tail_x, tail_y, s=tail_sizes, alpha=0.45, marker="s",
          color="green", edgecolors="k", linewidths=0.4, label="Tails (CurrentLocation)")

# Crew (blue triangles)
m.scatter(crew_x, crew_y, s=crew_sizes, alpha=0.45, marker="^",
          color="blue", edgecolors="k", linewidths=0.4, label="Crew (CurrentLocation)")

# Requests (red circles)
m.scatter(req_x, req_y, s=req_sizes, alpha=0.35, marker="o",
          color="red", edgecolors="k", linewidths=0.3, label="Requests (dep+arr within PlanningHorizon)")

plt.title(
    "Overlay: Requests (PlanningHorizon) vs Crew & Tails (CurrentLocation)\n"
    f"{begin_str} to {end_str}  |  Bubble size ~ log(1 + count)"
)
plt.legend(loc="lower left", frameon=True)
plt.tight_layout()
plt.show()