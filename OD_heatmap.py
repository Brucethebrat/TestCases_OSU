import json
from collections import Counter
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
from datetime import datetime, timezone

# =========================
# Helper: parse time safely (UTC-aware)
# =========================
def parse_dt_utc(s: str):
    """
    Parse datetime string into timezone-aware UTC datetime.
    Supports:
      - 2026-02-17T17:00:00Z
      - 2026-02-17T17:00:00+00:00
      - 2026-02-17 17:00:00
      - 2026-02-17T17:00:00
    Returns None if cannot parse.
    """
    if not s or not isinstance(s, str):
        return None
    s = s.strip()

    # Handle trailing Z
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    # Try ISO first
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:
        pass

    # Try common formats
    fmts = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue

    return None


# =========================
# Read requests
# =========================
with open("DOE_run3.json", "r", encoding="utf-8") as f:
    data = json.load(f)

flight_requests = data.get("FlightRequests", [])

# =========================
# Read planning horizon from Configuration
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
# Filter requests by RequestedTime within [BeginTime, EndTime]
# =========================
filtered_requests = []
bad_time_count = 0

for r in flight_requests:
    rt = r.get("RequestedTime")
    rt_dt = parse_dt_utc(rt)
    if rt_dt is None:
        bad_time_count += 1
        continue

    # Keep if within window (inclusive)
    if begin_dt <= rt_dt <= end_dt:
        filtered_requests.append(r)

print("Total FlightRequests:", len(flight_requests))
print("Bad RequestedTime rows dropped:", bad_time_count)
print("Requests within PlanningHorizon:", len(filtered_requests))

# =========================
# Read airport coordinates
# =========================
with open("srd.json", "r", encoding="utf-8") as f:
    airport_data = json.load(f)

airports_list = airport_data["StaticRoutingData"]["Airports"]

airport_coords = {
    a["AirportID"]: (a["Latitude"], a["Longitude"])
    for a in airports_list
}

# =========================
# Count traffic (dep + arr)
# =========================
traffic_counter = Counter()

for r in filtered_requests:
    dep = r.get("DepartureAirport")
    arr = r.get("ArrivalAirport")

    if dep:
        traffic_counter[dep] += 1
    if arr:
        traffic_counter[arr] += 1

lats, lons, sizes = [], [], []

for airport, count in traffic_counter.items():
    if airport in airport_coords:
        lat, lon = airport_coords[airport]
        lats.append(lat)
        lons.append(lon)
        sizes.append(count * 10)  

# =========================
# Plot US map
# =========================
plt.figure(figsize=(12, 8))

m = Basemap(
    projection="lcc",
    resolution="l",
    lat_0=37, lon_0=-95,
    width=5E6, height=3E6
)

m.drawcoastlines()
m.drawcountries()
m.drawstates()

x, y = m(lons, lats)
m.scatter(x, y, s=sizes, alpha=0.6, color="red", edgecolors="k")

plt.title(f"Flight Request Density (within PlanningHorizon)\n{begin_str} to {end_str}")
plt.tight_layout()
plt.show()