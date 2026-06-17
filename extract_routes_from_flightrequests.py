import argparse
import csv
import importlib.util
import json
import os
from collections import Counter


ith_run = 1
root_path = f"TestCases/DOE_Jacob_list/"
DEFAULT_INPUT_FILE = f"{root_path}DOE_run{ith_run}_long.json"  # Set this to a default JSON file path if desired
DEFAULT_OUTPUT_FILE = f"{root_path}distance/DOE_run{ith_run}_route_counts.csv"  # Set this to a default CSV file path if desired

DEFAULT_HAVERSINE_PATH = os.path.join(
    os.path.dirname(__file__),
    "Functions_and_Ploting",
    "add_distance_to_undirected_route.py",
)
DEFAULT_AIRPORTS_FILE = os.path.join(
    os.path.dirname(__file__),
    "combinedStaticRoutingData02-17-2026.json",
)


def load_haversine(func_path):
    spec = importlib.util.spec_from_file_location("route_distance_module", func_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.haversine


def load_airport_coords(airports_file):
    with open(airports_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    coords = {}
    for airport in data.get("StaticRoutingData", {}).get("Airports", []):
        code = airport.get("ICAOCode")
        lat = airport.get("Latitude")
        lon = airport.get("Longitude")
        if code and lat is not None and lon is not None:
            coords[code] = (lat, lon)
    return coords


def extract_routes(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    counts = Counter()
    for request in data.get("FlightRequests", []):
        departure = request.get("DepartureAirport")
        arrival = request.get("ArrivalAirport")
        if not departure or not arrival:
            continue
        route = tuple(sorted([departure, arrival]))
        counts[route] += 1

    return counts


def write_route_counts(route_counts, airport_coords, haversine, output_file):
    fieldnames = ["Airport1", "Airport2", "TotalReservations", "Distance"]
    with open(output_file, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for route, count in sorted(route_counts.items(), key=lambda item: item[1], reverse=True):
            airport1, airport2 = route
            distance = "N/A"
            if airport1 in airport_coords and airport2 in airport_coords:
                lat1, lon1 = airport_coords[airport1]
                lat2, lon2 = airport_coords[airport2]
                distance = round(haversine(lat1, lon1, lat2, lon2), 2)

            writer.writerow(
                {
                    "Airport1": airport1,
                    "Airport2": airport2,
                    "TotalReservations": count,
                    "Distance": distance,
                }
            )


def main():
    parser = argparse.ArgumentParser(description="Extract undirected route counts from FlightRequests and compute route distances.")
    parser.add_argument(
        "json_file",
        nargs="?",
        default=DEFAULT_INPUT_FILE,
        help="JSON file containing FlightRequests",
    )
    parser.add_argument(
        "--airports-file",
        default=DEFAULT_AIRPORTS_FILE,
        help="Static routing data JSON file with airport coordinates",
    )
    parser.add_argument(
        "--haversine-file",
        default=DEFAULT_HAVERSINE_PATH,
        help="Python file that defines the haversine function",
    )
    parser.add_argument(
        "--output-file",
        default=DEFAULT_OUTPUT_FILE,
        help="Destination CSV file path",
    )
    args = parser.parse_args()

    if args.json_file is None:
        parser.error("Please provide a JSON input file or set DEFAULT_INPUT_FILE in the script.")

    haversine = load_haversine(args.haversine_file)
    airport_coords = load_airport_coords(args.airports_file)
    route_counts = extract_routes(args.json_file)

    if not args.output_file:
        base_name = os.path.splitext(os.path.basename(args.json_file))[0]
        args.output_file = f"{base_name}_route_counts.csv"

    write_route_counts(route_counts, airport_coords, haversine, args.output_file)
    print(f"Wrote {len(route_counts)} unique undirected routes to {args.output_file}")


if __name__ == "__main__":
    main()
