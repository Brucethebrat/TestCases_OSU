import json
from collections import Counter
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap

# ===== read schedule / real data =====
INPUT_FILE = "DOE_run3.json"
INPUT_ENCODING = "utf-8"   # change to "utf-8" if needed

with open(INPUT_FILE, "r", encoding=INPUT_ENCODING) as f:
    data = json.load(f)

crewmembers = data.get("Crewmembers", [])
print("Total crewmembers:", len(crewmembers))

# ===== read airport coordinates =====
with open("srd.json", "r", encoding="utf-8") as f:
    airport_data = json.load(f)

airports_list = airport_data["StaticRoutingData"]["Airports"]
airport_coords = {
    a["AirportID"]: (a["Latitude"], a["Longitude"])
    for a in airports_list
}

# ===== count crew members by current location =====
crew_counter = Counter()
missing_loc = 0

for c in crewmembers:
    loc = c.get("CurrentLocation")
    if not loc:
        missing_loc += 1
        continue
    crew_counter[loc] += 1

print("Crew with missing CurrentLocation:", missing_loc)
print("Unique airports with crew:", len(crew_counter))

# ===== build plotting data =====
lats, lons, sizes = [], [], []
missing_coord = 0

for airport, count in crew_counter.items():
    if airport in airport_coords:
        lat, lon = airport_coords[airport]
        lats.append(lat)
        lons.append(lon)
        sizes.append(count * 30) 
    else:
        missing_coord += 1

print("Airports not found in SRD coords:", missing_coord)

# ===== draw US map =====
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

# Latitude/Longitude → Map coordinates
x, y = m(lons, lats)

m.scatter(x, y, s=sizes, alpha=0.6, color="blue", edgecolors="k")

plt.title("Crewmembers Currently at Airports (by CurrentLocation)")
plt.tight_layout()
plt.show()