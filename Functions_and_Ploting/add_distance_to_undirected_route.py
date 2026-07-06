# This script adds a distance column to the undirected route table, 
# Below is the column names of the input CSV file:
# Airport1,Airport2,TotalReservations,Distance

from math import radians, sin, cos, sqrt, atan2

import csv
import json
import sys

# distance function between 2 coordinates on sphere
def haversine(lat1, lon1, lat2, lon2):
    """return the distance of 2 cooridnates"""
    R = 3958.8  # earth radius (miles)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


with open("combinedStaticRoutingData02-17-2026.json", "r", encoding="utf-8") as f:
    full_data = json.load(f)
all_airport_coords = {}
all_us_airports = []
all_us_airports_dict = {}
for a in full_data["StaticRoutingData"]["Airports"]:
    if "Latitude" in a and "Longitude" in a:
        all_airport_coords[a["ICAOCode"]] = (a["Latitude"], a["Longitude"])
        if a.get("CountryID") == "US":
            all_us_airports.append(a["ICAOCode"])
            all_us_airports_dict[a["ICAOCode"]] = (a["Latitude"], a["Longitude"])

# Read the OD_total_0218_undirected.csv file
input_csv = "RealData/OD_total_0218_undirected.csv"
output_csv = "RealData/OD_total_0218_undirected_with_distance.csv"

# Open the input CSV file
with open(input_csv, "r", encoding="utf-8-sig") as infile:
    reader = csv.DictReader(infile)
    rows = list(reader)
# print(f"column names: {rows[0].keys()}")

# Add a new column for distance
for row in rows:
    airport1 = row["Airport1"]
    airport2 = row["Airport2"]

    if airport1 in all_airport_coords and airport2 in all_airport_coords:
        lat1, lon1 = all_airport_coords[airport1]
        lat2, lon2 = all_airport_coords[airport2]
        row["Distance"] = round(haversine(lat1, lon1, lat2, lon2), 2)
    else:
        row["Distance"] = "N/A"  # Mark as N/A if coordinates are missing

print(f"Added distance column to {len(rows)} rows.")
print(f"Sample rows with distance:")
for row in rows[:5]:  # Print the first 5 rows as a sample
    print(row)

# sys.exit(0)

# Write the updated data to a new CSV file
with open(output_csv, "w", encoding="utf-8", newline="") as outfile:
    fieldnames = reader.fieldnames + ["Distance"]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)

    writer.writeheader()
    writer.writerows(rows)

print(f"Updated CSV with distances written to {output_csv}")

