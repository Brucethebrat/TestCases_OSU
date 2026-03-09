import json
from collections import Counter
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap

# ===== read schedule / real data =====
INPUT_FILE = "DOE_run3.json"
INPUT_ENCODING = "utf-8"   # change to "utf-8" if needed

with open(INPUT_FILE, "r", encoding=INPUT_ENCODING) as f:
    data = json.load(f)

tails = data.get("Tails", [])
print("Total tails:", len(tails))

# ===== read airport coordinates =====
with open("srd.json", "r", encoding="utf-8") as f:
    airport_data = json.load(f)

airports_list = airport_data["StaticRoutingData"]["Airports"]
airport_coords = {
    a["AirportID"]: (a["Latitude"], a["Longitude"])
    for a in airports_list
}

# ===== Count tails by current location =====
tail_counter = Counter()
missing_loc = 0

for t in tails:
    loc = t.get("CurrentLocation")
    if not loc:
        missing_loc += 1
        continue
    tail_counter[loc] += 1

print("Tails with missing CurrentLocation:", missing_loc)
print("Unique airports with tails:", len(tail_counter))

# ===== build plotting data =====
lats, lons, sizes = [], [], []
missing_coord = 0

for airport, count in tail_counter.items():
    if airport in airport_coords:
        lat, lon = airport_coords[airport]
        lats.append(lat)
        lons.append(lon)
        sizes.append(count * 40)  
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

m.scatter(x, y, s=sizes, alpha=0.6, color="green", edgecolors="k")

plt.title("Tails Currently at Airports (by CurrentLocation)")
plt.tight_layout()
plt.show()