# this file is branched from test_doe_filter_airport.py, but the airport pool will be filtered by RoutingCache



import json
import csv
import random
from datetime import datetime, timedelta
from collections import Counter
from math import radians, sin, cos, sqrt, atan2
import time
import sys
from pathlib import Path
import pandas as pd

from Get_airport_pool import get_airport_pool

# =======================================================================================
# srd["StaticRoutingData"]["Airports"] has all airport ICAOCodes and their coordinates, 
# but not all of them are in the routingCache["Airports"] that we use for generation. 
# So we need to filter out the airports that are not in the routingCache["Airports"].
# =======================================================================================

# === Step 1. read in all airports latitude and longtitude ===
# with open("srd.json", "r", encoding="utf-8") as f:
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

# airports_ICAO_and_coord_dict = full_data["StaticRoutingData"]["Airports"]
# airports_ICAO_dict = [a["ICAOCode"] for a in airports_ICAO_and_coord_dict]

# Filtering out the airports that are not in the real data
routingCache = full_data["StaticRoutingData"]["RoutingCache"]
airports_in_RoutingCache = routingCache["Airports"]
# aircrafts = routingCache["AircraftTypeNames"]
# routes = routingCache["Routes"]
pre_airports = get_airport_pool()
airports = pre_airports.copy()   # make a copy to modify, keep pre_airports unchanged for later use



cache_airport_coords = {}
us_airports = []
us_airports_dict = {}

print(f"[+] There are {len(pre_airports)} airports.")
# print(f"first 5 airports: {airports[:5]}")
# exit()
for a_ICAO in pre_airports:
    if a_ICAO not in all_airport_coords.keys():
        airports.remove(a_ICAO)
        print(f"[-] Removed airport {a_ICAO} as it has no coordinates.")
        continue
    if a_ICAO not in airports_in_RoutingCache:
        airports.remove(a_ICAO)
        print(f"[-] Removed airport {a_ICAO} as it is not in RoutingCache.")
        continue

    cache_airport_coords[a_ICAO] = all_airport_coords[a_ICAO]
    if a_ICAO in all_us_airports:
        us_airports.append(a_ICAO)
        us_airports_dict[a_ICAO] = all_airport_coords[a_ICAO]

# check_ap = ["2A0", "KSLE"]

# print(f"[+] Checking if {check_ap} is in the filtered airport list.")
# print([ap for ap in check_ap if ap in [airport for airport in full_data["StaticRoutingData"]["RoutingCache"]["Airports"]]])
# print([ap for ap in check_ap if ap in airports_in_RoutingCache])
# print([ap for ap in check_ap if ap in airports])
# sys.exit()

'''# === Step 2. define 3 hubs and distance function ===
geo_centers = {
    "KTEB": (40.85, -74.0608),
    "KPBI": (26.6831, -80.0956),
    "KIAD": (38.9472, -77.4597)
}'''

global crewID_start, flightID_start, mxID_start, tailID_start, legIDstart
crewID_start = 700000
flightID_start = 50000
mxID_start = 800000
tailID_start = 1000000
legID_start = 2000000


weighted_routes_csv_path = Path(__file__).resolve().parent / "RealData" / "OD_total_0218_undirected.csv"
weighted_airport_tail_csv_path = Path(__file__).resolve().parent / "RealData" / "airport_supply_demand_0218.csv"



def load_weighted_airport_for_Tail_Crew(csv_path: Path):
    weighted_airports_for_tail = set()
    weighted_airports_for_crew = set()
    # with csv_path.open("r", encoding="utf-8", newline="") as f:
    #     reader = csv.DictReader(f)
    ap_df = pd.read_csv(csv_path)
    for _, row in ap_df.iterrows():
        airport = row["airport_name"].strip()
        tail_count = int(row["tails_num"])
        crew_count = int(row["crewmembers_num"])

        weighted_airports_for_tail.add((airport, tail_count))
        weighted_airports_for_crew.add((airport, crew_count))


    # print(f"[+] Loaded {len(weighted_airports_for_tail)} weighted airports for tail from {csv_path.name}.")
    # print(f"[+] First 5 weighted airports for tail: {list(weighted_airports_for_tail)[:5]}")
    # print(f"[+] Loaded {len(weighted_airports_for_crew)} weighted airports for crew from {csv_path.name}.")
    # print(f"[+] First 5 weighted airports for crew: {list(weighted_airports_for_crew)[:5]}")
    # sys.exit()
    return weighted_airports_for_tail, weighted_airports_for_crew   # return 2 same sets for now, can be different later if we want different distribution for tail and crew


def load_weighted_airport_routes(csv_path: Path):
    routes = []
    
    # with csv_path.open("r", encoding="utf-8", newline="") as f:
    #     reader = csv.DictReader(f)
    ap_df = pd.read_csv(csv_path)
    for _, row in ap_df.iterrows():
        airport1 = row["Airport1"].strip()
        airport2 = row["Airport2"].strip()
        count = int(row["TotalReservations"])

        # In OD_total_3days_undirected.csv
        # Total unique airports from combinations: 761
        # Total unique airports from combinations with count > 1: 515
        # Total unique airports from combinations with count > 2: 225
        

        if count <= 1:
            continue
        if airport1 == airport2:
            continue

        routes.append((airport1, airport2, count))

    # print(f"[+] Loaded {len(routes)} weighted routes from {csv_path.name}.")
    # print(f"first 5 routes: {routes[:5]}")
    # sys.exit()
    return routes


def load_hourly_request_profile(csv_path: Path):
    df = pd.read_csv(csv_path)

    # Hour -> datetime
    df["Hour"] = pd.to_datetime(df["Hour"], utc=True)
    df["HourOfDay"] = df["Hour"].dt.hour

    # take average hour-of-day requests
    hourly_avg = (
        df.groupby("HourOfDay")["ReservationCount"]
          .mean()
          .round()
          .astype(int)
          .to_dict()
    )

    # ensure contains 0~23 
    hour_counts = {h: 0 for h in range(24)}
    hour_counts.update(hourly_avg)

    # print("[+] Using averaged 24-slot hourly request profile")
    for h in range(24):
        print(f"    Hour {h:02d}: {hour_counts[h]}")

    return hour_counts


weighted_airport_routes = load_weighted_airport_routes(weighted_routes_csv_path)

weighted_airports_for_tail, weighted_airports_for_crew = load_weighted_airport_for_Tail_Crew(weighted_airport_tail_csv_path)


hourly_profile_csv_path = Path(__file__).resolve().parent / "RealData" / "hourly_reservation_counts_021826.csv"
hourly_request_profile = load_hourly_request_profile(hourly_profile_csv_path)








def pick_2_random_airports_for_req(pool1, pool2, weighted_airport_routes=[], use_real_route=False):
    if use_real_route:
        pool1_set = set(pool1)
        pool2_set = set(pool2)

        eligible_routes = []
        eligible_weights = []

        for a1, a2, count in weighted_airport_routes:
            '''forward_ok = (a1 in pool1_set and a2 in pool2_set)
            reverse_ok = (a2 in pool1_set and a1 in pool2_set)

            if forward_ok and reverse_ok:
                eligible_routes.append((a1, a2))
                eligible_weights.append(count)
                eligible_routes.append((a2, a1))
                eligible_weights.append(count)
            elif forward_ok:
                eligible_routes.append((a1, a2))
                eligible_weights.append(count)
            elif reverse_ok:
                eligible_routes.append((a2, a1))
                eligible_weights.append(count)'''

            eligible_routes.append((a1, a2))
            eligible_weights.append(count)
            eligible_routes.append((a2, a1))
            eligible_weights.append(count)

        if eligible_routes:
            return random.choices(eligible_routes, weights=eligible_weights, k=1)[0]
    else:
        dep = random.choice(pool1)
        arr = random.choice(pool2)
        while arr == dep:
            arr = random.choice(pool2)
    return dep, arr


def pick_weighted_random_airport(pool, weighted_airports):
    pool_set = set(pool)
    eligible_airports = []
    eligible_weights = []

    for airport, weight in weighted_airports:
        if airport in pool_set:
            eligible_airports.append(airport)
            eligible_weights.append(weight)

    if eligible_airports:
        return random.choices(eligible_airports, weights=eligible_weights, k=1)[0]
    else:
        return random.choice(pool)



def pick_request_time_from_hour_profile(horizon_begin, horizon_end, hourly_profile):
    """
    In planning horizon, based on 24-slot hourly profile sample request time.
    """
    # generate horizon each hour slot
    candidate_hours = []
    candidate_weights = []

    current = horizon_begin.replace(minute=0, second=0, microsecond=0)
    if current < horizon_begin:
        current += timedelta(hours=1)

    while current <= horizon_end:
        candidate_hours.append(current)
        candidate_weights.append(hourly_profile.get(current.hour, 0))
        current += timedelta(hours=1)

    if not candidate_hours:
        return horizon_begin

    if sum(candidate_weights) == 0:
        chosen_hour_start = random.choice(candidate_hours)
    else:
        chosen_hour_start = random.choices(candidate_hours, weights=candidate_weights, k=1)[0]

    chosen_minute = random.randint(0, 59)
    chosen_second = random.randint(0, 59)

    req_time = chosen_hour_start + timedelta(minutes=chosen_minute, seconds=chosen_second)

    # ensure not exceed horizon end
    if req_time > horizon_end:
        req_time = horizon_end - timedelta(seconds=random.randint(0, 59))

    return req_time




# distance function between 2 coordinates on sphere
def haversine(lat1, lon1, lat2, lon2):
    """return the distance of 2 cooridnates"""
    R = 3958.8  # earth radius (miles)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def airports_inside_circle(epicenter_icao: str, radius_miles: float,
                                      airport_coords: dict) -> set:
    """retrun epicenter radius radius_miles all affected airports in ICAO set。"""
    if epicenter_icao not in airport_coords:
        return set()
    clat, clon = airport_coords[epicenter_icao]
    affected = set()
    for icao, (alat, alon) in airport_coords.items():
        if haversine(clat, clon, alat, alon) <= radius_miles:
            affected.add(icao)
    return affected

# ====season factor====

def build_grounding_legs_for_tails(tails: list, affected_airports: set,
                                   start_time_dt, time_window_days: int,
                                   starting_leg_id: int = 10_000_000) -> list:
    """
    Create locked leg covering the entire planning window for all tails whose CurrentLocation is in affected_airports.
    Return the newly added legs.
    """
    legs = []
    dur_minutes = time_window_days * 24 * 60
    start_iso = start_time_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    leg_id = starting_leg_id
    for t in tails:
        loc = t.get("CurrentLocation")
        if loc in affected_airports:
            legs.append({
                "TailNumber": t["TailNumber"],
                "LegID": leg_id,
                "RequestID": 0,
                "IsLocked": True,
                "OriginAirport": loc,
                "DestinationAirport": loc,
                "StartTime": start_iso,
                "Duration": dur_minutes,
                "ActivityType": "MAINTENANCE",          
                "AssignedCrewmembers": [],
                "CrewModel": "NO_CREW",
                "mxType": "WEATHER_GROUNDED"            # weather issue
            })
            leg_id += 1
    return legs


# ====================== Bruce ======================
def generate_allowed_tailtypes(allowed_tailtypes, start_time):
    rand_allowed_tailtypes = []
    temp_types = random.sample(allowed_tailtypes, k=random.randint(1, min(len(allowed_tailtypes), 4)))
    
    day_exp = (start_time + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    night_exp = (start_time + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    qual_start = (start_time + timedelta(days=-365)).strftime("%Y-%m-%dT%H:%M:%SZ")

    for t in temp_types:
        rand_allowed_tailtypes.append({
            "AircraftTypeName": t["AircraftTypeName"],
            "QualificationCode": "PIC",
            "dayCurrencyExpiration": day_exp,
            "nightCurrencyExpiration": night_exp,
            "qualificationStartDate": qual_start
        })
        rand_allowed_tailtypes.append({
            "AircraftTypeName": t["AircraftTypeName"],
            "QualificationCode": "SIC",
            "qualificationStartDate": qual_start
        })
    return rand_allowed_tailtypes

# ====================== Vivian ======================
def generate_allowed_tailtypes_FA(allowed_tailtypes):
    rand_allowed_tailtypes = []
    big_planes = ["CL-650S", "GL5500", "CE-700", "GL6000S", "CE-680AS"]
    # filter allowed_tailtypes to only big planes
    big_plane_types = [t for t in allowed_tailtypes if t["AircraftTypeName"] in big_planes]

    if not big_plane_types:
        # fallback if none
        big_plane_types = allowed_tailtypes

    # Randomly sample 1–4 from big planes only
    temp_types = random.sample(big_plane_types, k=random.randint(1, min(len(big_plane_types), 4)))

    for t in temp_types:
        rand_allowed_tailtypes.append({
            "AircraftTypeName": t["AircraftTypeName"],
            "QualificationCode": "FA"
        })
    return rand_allowed_tailtypes

# ====================== Bruce ======================
def generate_crewmembers(num_crews, allowed_tailtypes, real_route_level, airports, start_time, time_window_days):
    num_crews = int(num_crews)
    crews = []
    '''positions = ["PIC", "SIC"]
    if crewmember_level == "low":
        num_crews = 800
    elif crewmember_level == "mid":
        num_crews = 1000
    elif crewmember_level == "high":
        num_crews = 1200
    else:
        print("Invalid crewmember_level, defaulting to low (2000 crews)")
        num_crews = 2000'''

    for cid in range(1, num_crews + 1):
        crew_id = crewID_start + cid
        roster_length = random.randint(5,8) # days
        # Start time is randomly set within the time window minus the roster length
        tour_start_time = start_time + timedelta(hours=random.randint(-roster_length * 24, time_window_days * 24))
        tour_end_time = tour_start_time + timedelta(minutes=roster_length * 24 * 60 + 13 * 60 - 1)      # add 13 hours because found schedule_sanitized crew pattern
        if real_route_level == "high":
            airport_domicile = pick_weighted_random_airport(airports, weighted_airports_for_crew)
        else:
            airport_domicile = random.choice(airports)
        current_loc = airport_domicile if random.random() < 0.9 else random.choice(airports)
        qualified_types = generate_allowed_tailtypes(allowed_tailtypes, start_time)

        crews.append({
            "CrewmemberID": crew_id,
            "CurrentLocation": current_loc,
            "AirportIDDomicile": airport_domicile,    # base airport
            "tourStartDate": tour_start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tourEndDate": tour_end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "CrewmemberQualifications": qualified_types
        })
    
    # # ====================== Vivian ======================
    # FAnum = int(0.1 * num_crews)

    # for FAid in range(1, FAnum + 1):
    #     crew_id = crewID_start + num_crews + FAid     #ensure no overlap with previous section
    #     roster_length = random.randint(5, 8)
    #     tour_start_time = start_time + timedelta(hours=random.randint(-roster_length * 24, time_window_days * 24))
    #     tour_end_time = tour_start_time + timedelta(minutes=roster_length * 24 * 60 + 13 * 60 - 1)
    #     airport_domicile = random.choice(airports)
    #     current_loc = airport_domicile if random.random() < 0.9 else random.choice(airports)
    #     qualified_types = generate_allowed_tailtypes_FA(allowed_tailtypes)

    #     crews.append({
    #         "CrewmemberID": crew_id,
    #         "CurrentLocation": current_loc,
    #         "AirportIDDomicile": airport_domicile,
    #         "tourStartDate": tour_start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    #         "tourEndDate": tour_end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    #         "CrewmemberQualifications": qualified_types
    #     })

    return crews


def pair_2_members_with_rev_flight(crew1, crew2, rev_start_time, airport_coords, crew_activities, legs, tails):
    crew1_id = crew1["CrewmemberID"]
    crew2_id = crew2["CrewmemberID"]
            
    activity_type = "OPERATE_REVENUE_FLIGHT"
    arr_airport = crew1["CurrentLocation"]
    # ===== find a departure airport within 100 miles =====
    radius_miles = 100.0
    clat, clon = airport_coords[arr_airport]
    for icao, (alat, alon) in airport_coords.items():
        if haversine(clat, clon, alat, alon) <= radius_miles:
            dep_airport = icao
            break
    # ===== ========================================= =====

    activity_start = rev_start_time

    # Tail attributes
    tailID = str(tailID_start + len(tails) + 1)
    chosen_type = random.choice(crew1["CrewmemberQualifications"])["AircraftTypeName"]
    tail_avai_time = (activity_start - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")  # available 1 day before activity start

    # Leg attributes
    LegID = legID_start + len(legs) + 1


    tails.append({
        "TailNumber": tailID,
        "AircraftTypeName": chosen_type,
        "AvailableTime": tail_avai_time,        # modify to random, or make it difficult to schedule
        "CurrentLocation": arr_airport,
        "AssignedProperties": [
            tailID, chosen_type
            # str(1000000 + i), chosen_type, "ELT_406MHZ_FLAG", "TCAS7.1", "NO_DOUBLE_BUNK"
        ],
        "MinutesLeftForNextMaintenance": random.randint(*min_left_range),
        "CyclesLeftForNextMaintenance": random.randint(*cycle_left_range),
        "TailCost": 6304,
        "TailLegCost": 1173
    })

    legs.append({
        "ActivityType": activity_type,
        "TailNumber": tailID,
        "LegID": LegID,
        "RequestID": 0,
        "IsLocked": False,
        "OriginAirport": dep_airport,
        "DestinationAirport": arr_airport,
        "StartTime": activity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Duration": 120,  # assume 2 hours flight
        "AssignedCrewmembers": [
            {
                "CrewmemberID": crew1_id,
                "CrewmemberPosition": "PIC"
            },
            {
                "CrewmemberID": crew2_id,
                "CrewmemberPosition": "SIC"
            }
        ]
    })

    # crew1 Rev Flight
    crew_activities.append({
        "CrewmemberID": crew1_id,
        "ActivityType": activity_type,
        "TailNumber": tailID,
        "CrewmemberPosition": "PIC",
        "IsLocked": False,
        "LegID": LegID,
        "OriginAirport": dep_airport,
        "DestinationAirport": arr_airport,
        "StartTime": activity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Duration": 120
    })
    # crew2 Rev Flight
    crew_activities.append({
        "CrewmemberID": crew2_id,
        "ActivityType": activity_type,
        "TailNumber": tailID,
        "CrewmemberPosition": "SIC",
        "IsLocked": False,
        "LegID": LegID,
        "OriginAirport": dep_airport,
        "DestinationAirport": arr_airport,
        "StartTime": activity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Duration": 120
    })

    # list doesn't have to be returned
    # return legs, tails, crew_activities


def crew_rest(crew, rest_airport, start_rest_time, duty_duration, crew_activities):
    crew_id = crew["CrewmemberID"]
    activity_type = "REST"
    dep_airport = rest_airport
    arr_airport = dep_airport
    rest_duration = (24 - duty_duration) * 60
    activity_start = start_rest_time
    crew_activities.append({
        "CrewmemberID": crew_id,
        "ActivityType": activity_type,
        "OriginAirport": dep_airport,
        "DestinationAirport": arr_airport,
        "StartTime": activity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Duration": rest_duration
    })

# ====================== Bruce ======================
def generate_crew_activities(crews, airports, airport_coords, start_time, legs=[], tails=[]):
    crew_activities = []
    crew_fly_together = []


    first_half_crews = crews[:len(crews)//2]
    second_half_crews = crews[len(crews)//2:]
    
    # First half crewmem don't have partner during the planning window
    for crew in first_half_crews:
        # if random.random() < 0.9:
        #     continue  # 20% chance to skip adding activities for this crew

        tour_start_dt = datetime.strptime(crew["tourStartDate"], "%Y-%m-%dT%H:%M:%SZ")
        # tour_end_dt = datetime.strptime(crew["tourEndDate"], "%Y-%m-%dT%H:%M:%SZ")
        ps_ts_diff_24 = (start_time - tour_start_dt) % (24 * timedelta(hours=1))
        duty_duration = random.randint(10,14)  # duty duration in hours

        # print(f"tour start: {tour_start_dt}, planning start: {start_time} for crew {crew['CrewmemberID']}")
        # print(f"ps - ts / 24hrs : {ps_ts_diff_24}")
        # print(f"ps_ts_diff_24 >= timedelta(hours=duty_duration): {ps_ts_diff_24 <= timedelta(hours=duty_duration)}")
        # exit()
        
        # Crewmember shift starts after "2hrs before planning window" -> no activity
        # keep 2 hrs buffer to put in an leg before planning window
        if tour_start_dt > start_time - timedelta(hours=2):
            continue
        
        # Crewmember duty still ongoing at the beginning of planning window -> "revenue flight" activity
        elif ps_ts_diff_24 <= timedelta(hours=duty_duration):
            # Dummy SIC crewmember
            dummy_crew_id = crewID_start + len(crews) + 1
            qualified_types = crew["CrewmemberQualifications"]
            dummy_crew_tour_end = start_time
            dummy_crew_tour_start = (dummy_crew_tour_end - timedelta(days=7, hours=12, minutes=59))
            dummy_arr_airport = crew["CurrentLocation"]

            crews.append({
                "CrewmemberID": dummy_crew_id,
                "CurrentLocation": dummy_arr_airport,
                "AirportIDDomicile": random.choice(airports),    # base airport
                "tourStartDate": dummy_crew_tour_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "tourEndDate": dummy_crew_tour_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "CrewmemberQualifications": qualified_types
            })

            dummy_crew = crews[-1]
            
            pair_2_members_with_rev_flight(crew1=crew, crew2=dummy_crew, 
                                           rev_start_time=start_time - timedelta(hours=2),
                                           airport_coords=airport_coords,
                                           crew_activities=crew_activities, 
                                           legs=legs, tails=tails)
            
            '''crew_id = crew["CrewmemberID"]
            
            activity_type = "OPERATE_REVENUE_FLIGHT"
            arr_airport = crew["CurrentLocation"]
            # ===== find a departure airport within 100 miles =====
            radius_miles = 100.0
            clat, clon = airport_coords[arr_airport]
            for icao, (alat, alon) in airport_coords.items():
                if haversine(clat, clon, alat, alon) <= radius_miles:
                    dep_airport = icao
                    break
            # ===== ========================================= =====

            activity_start = start_time - timedelta(hours=2)

            # Tail attributes
            tailID = tailID_start + len(tails) + 1
            chosen_type = random.choice(crew["CrewmemberQualifications"])["AircraftTypeName"]
            tail_avai_time = activity_start.strftime("%Y-%m-%dT%H:%M:%SZ") - timedelta(days=1)  # available 1 day before activity start


            # Leg attributes
            LegID = legIDstart + len(legs) + 1


            tails.append({
                "TailNumber": tailID,
                "AircraftTypeName": chosen_type,
                "AvailableTime": tail_avai_time,        # modify to random, or make it difficult to schedule
                "CurrentLocation": arr_airport,
                "AssignedProperties": [
                    tailID, chosen_type
                    # str(1000000 + i), chosen_type, "ELT_406MHZ_FLAG", "TCAS7.1", "NO_DOUBLE_BUNK"
                ],
                "MinutesLeftForNextMaintenance": random.randint(*min_left_range),
                "CyclesLeftForNextMaintenance": random.randint(*cycle_left_range),
                "TailCost": 6304,
                "TailLegCost": 1173
            })

            legs.append({
                "ActivityType": activity_type,
                "TailNumber": tailID,
                "LegID": LegID,
                "RequestID": 0,
                "IsLocked": False,
                "OriginAirport": dep_airport,
                "DestinationAirport": arr_airport,
                "StartTime": activity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "Duration": 120,  # assume 2 hours flight
                "AssignedCrewmembers": [
                    {
                        "CrewmemberID": crew_id,
                        "CrewmemberPosition": "PIC"
                    },
                    {
                        "CrewmemberID": dummy_crew_id,
                        "CrewmemberPosition": "SIC"
                    }
                ]
            })

            crew_activities.append({
                "CrewmemberID": crew_id,
                "ActivityType": activity_type,
                "TailNumber": tailID,
                "CrewmemberPosition": "PIC",
                "IsLocked": False,
                "LegID": LegID,
                "OriginAirport": dep_airport,
                "DestinationAirport": arr_airport,
                "StartTime": activity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "Duration": 0   # unknown duration
            })
            '''

            rest_airport = crew["CurrentLocation"]
            start_rest_time = start_time - ps_ts_diff_24 + duty_duration * timedelta(hours=1)
            crew_rest(crew, rest_airport, start_rest_time, duty_duration, crew_activities)

        # Crewmember still RESTING at the beginning of planning window -> "REST" activity
        else:
            rest_airport = crew["CurrentLocation"]
            activity_start = start_time - ps_ts_diff_24 + duty_duration * timedelta(hours=1)
            crew_rest(crew, rest_airport, activity_start, duty_duration, crew_activities)

    get_2_crew_members = False
    for crew in second_half_crews:
        # ==== get 2 crewmembers at a time ====
        if not get_2_crew_members:
            crew1 = crew
            get_2_crew_members = True
            continue
        crew2 = crew
        get_2_crew_members = False
        # =====================================


        # ==== Replacing some crwe2's attr with crew1's ====
        crew2["tourStartDate"] = crew1["tourStartDate"]
        crew2["tourEndDate"] = crew1["tourEndDate"]
        crew2["CurrentLocation"] = crew1["CurrentLocation"]
        crew2["CrewmemberQualifications"] = crew1["CrewmemberQualifications"]
        # ==== ======================================== ====

        
        tour_start_dt_1 = datetime.strptime(crew1["tourStartDate"], "%Y-%m-%dT%H:%M:%SZ")
        # tour_end_dt_1 = datetime.strptime(crew1["tourEndDate"], "%Y-%m-%dT%H:%M:%SZ")
        # curr_loc_1 = crew1["CurrentLocation"]
        ps_ts_diff_24_1 = (start_time - tour_start_dt_1) % (24 * timedelta(hours=1))
        duty_duration = random.randint(10,14)  # duty duration in hours



        # Crewmember shift starts after "2hrs before planning window" -> no activity
        # keep 2 hrs buffer to put in an leg before planning window
        # !!!!!!!! These 2 mem is not paired together !!!!!!!!
        if tour_start_dt_1 > start_time - timedelta(hours=2):
            continue
        
        # Crewmember duty still ongoing at the beginning of planning window -> "revenue flight" activity
        elif ps_ts_diff_24_1 <= timedelta(hours=duty_duration):
            rev_start_time = start_time - timedelta(hours=2)
            pair_2_members_with_rev_flight(crew1, crew2, rev_start_time, airport_coords, crew_activities, legs, tails)
            
            rest_airport = crew1["CurrentLocation"]
            start_rest_time = start_time - ps_ts_diff_24_1 + duty_duration * timedelta(hours=1)
            crew_rest(crew1, rest_airport, start_rest_time, duty_duration, crew_activities)
            crew_rest(crew2, rest_airport, start_rest_time, duty_duration, crew_activities)

            crew_fly_together.append({
                "Crewmembers": [
                    crew1["CrewmemberID"],
                    crew2["CrewmemberID"]
                ]
            })

        # Crewmember still RESTING at the beginning of planning window -> "REST" & "revenue flight" that pairs 2 members
        else:
            rest_airport = crew["CurrentLocation"]
            activity_start = start_time - ps_ts_diff_24 + duty_duration * timedelta(hours=1)
            crew_rest(crew1, rest_airport, activity_start, duty_duration, crew_activities)
            crew_rest(crew2, rest_airport, activity_start, duty_duration, crew_activities)

            # assign rev flight to pair 2 members
            # start 2 hrs b4 "rest" start
            rev_start_time = activity_start - timedelta(hours=2)
            pair_2_members_with_rev_flight(crew1, crew2, rev_start_time, airport_coords, crew_activities, legs, tails)

            crew_fly_together.append({
                "Crewmembers": [
                    crew1["CrewmemberID"],
                    crew2["CrewmemberID"]
                ]
            })

    return crew_activities, crew_fly_together





# === DOE factors ===
def generate_scenario(
    area="US",
    arrival_rate="low",
    substitutes=0,          # change to low / high later
    tail_scale="low",
    crew_included = True,
    crewmember_level = "low",      # low / mid / high = 1500 / 2000 / 2500 crews
    maintenance_scale="low",
    maintenance_airport_distribution ="east",
    # geo_density="low",
    real_route_level="high",     # low: random route; high: weighted route based on real data # controdict with geo_density
    round_trip_ratio=0.2,          # only for real_route_level = high, % of routes that are round trip
    time_window_days=1,
    weather=False,
    event=False,
    maintenance_cycle="low",
    start_time="2026-02-18T17:00:00Z",
    season="Winter",        # removed for now
    hub_pattern = "fly_out",
    exp_id=0
):
    
    if start_time is None:
        start_time = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
        print(f"⏰ start_time not provided → default = {start_time}")
    elif isinstance(start_time, str):
        start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")

    random.seed(time.time())

    weather_affected_airports = set()
    # remove weather airports at the beginning, so that no one request to/from there
    if weather:
        # randomly choose a weather affected airport in US as a center
        epicenter = random.choice(us_airports)
        # find out all the affected airport within 30 miles 
        weather_affected_airports = airports_inside_circle(epicenter, 30.0, us_airports_dict)

    # designate available airports
    if area == "US":
        airports = [airport for airport in us_airports if airport not in weather_affected_airports]     # list of ICAO codes
        # Build a dict of coords for only the airports in `airports` (safe subset copy)
        airport_coords = {icao: all_airport_coords[icao] for icao in airports if icao in all_airport_coords}
        # The `airports` list already excludes weather-affected airports, so no deletion needed
    elif area == "Global": 
        airports = list(all_airport_coords.keys())
        airport_coords = all_airport_coords       # ICAO to (lat, lon) dict
    else:
        raise ValueError(f"Invalid area: {area}, must be 'US' or 'Global'.")
    


    '''# ========== Bruce: don't need this once we have season input ==========
    # === derive season from time window ===
    month = start_time.month
    if month in [12, 1, 2]:
        season = "winter"
    elif month in [3, 4, 5]:
        season = "spring"
    elif month in [6, 7, 8]:
        season = "summer"
    else:
        season = "fall"
    # ========== Bruce: don't need this once we have season input ==========


    # === seasonal demand bias ===
    prob_bias = 0.3  # 30% flights biased toward seasonal direction

    if season in ["winter", "fall"]:
        # 30% more flights go south, others random
        prob_south_bias = prob_bias
        prob_north_bias = 0
        bias_direction = "south"
    else:  # spring/summer
        # 30% more flights go north, others random
        prob_south_bias = 0
        prob_north_bias = prob_bias
        bias_direction = "north"

    print(f"🍂 Auto season={season} (month={month}): 30% bias toward {bias_direction}")'''


    # === numerical setting ===
    tail_scale_map = {"low": 400, "high": 600}
    num_tails = tail_scale_map[tail_scale]
    num_requests = int(num_tails * (0.9 if arrival_rate == "low" else 1.2) * time_window_days)
    
    mx_scale_map = {"low": 0.1, "high": 0.2}
    mx_num = mx_scale_map[maintenance_scale] * num_tails * time_window_days

    # ====== Vivian ======
    mx_airport = []

    # split airports by longtitude
    east_airports = [a for a, (_, lon) in airport_coords.items() if lon > -95]
    west_airports = [a for a, (_, lon) in airport_coords.items() if lon <= -95]
    mx_airport_num = 50

    # control directions 
    if maintenance_airport_distribution == "east":
        # num_east = int(0.7 * len(east_airports))
        # num_west = int(0.3 * len(west_airports))
        num_east = int(0.7 * mx_airport_num)
        num_west = int(0.3 * mx_airport_num)
        selected_east = random.sample(east_airports, num_east)
        selected_west = random.sample(west_airports, num_west)
        mx_airport = selected_east + selected_west

    elif maintenance_airport_distribution == "west":
        # num_west = int(0.7 * len(west_airports))
        # num_east = int(0.3 * len(east_airports))
        num_east = int(0.3 * mx_airport_num)
        num_west = int(0.7 * mx_airport_num)
        selected_west = random.sample(west_airports, num_west)
        selected_east = random.sample(east_airports, num_east)
        mx_airport = selected_east + selected_west

    elif maintenance_airport_distribution == "balanced":
        num_east = int(0.5 * mx_airport_num)
        num_west = int(0.5 * mx_airport_num)
        selected_east = random.sample(east_airports, num_east)
        selected_west = random.sample(west_airports, num_west)
        mx_airport = selected_east + selected_west

    else:
        raise ValueError(f"Invalid maintenance_airport_distribution: {maintenance_airport_distribution}")   
    
    # mx_airport_map = {"low": 20, "mid": 50, "high": 100}
    # mx_airport_num = mx_airport_map[maintenance_airport_number]
    # mx_airport = []
    # for _ in range(mx_airport_num):
    #     mx_airport.append(random.choice(list(airport_coords.keys())))


    # === classify airports into north/south (based on latitude 37°N) ===
    north_airports = [icao for icao, (lat, lon) in airport_coords.items() if lat > 37]
    south_airports = [icao for icao, (lat, lon) in airport_coords.items() if lat <= 37]

    # # === Step 3. select airports based on geo_density ===
    # nearby_airports = []
    # for cname, (clat, clon) in geo_centers.items():
    #     for icao, (alat, alon) in airport_coords.items():
    #         if haversine(clat, clon, alat, alon) <= 50:
    #             nearby_airports.append(icao)
    # print(f"🗺️ Found {len(nearby_airports)} airports within 50 miles of 3 hubs.")
    #     # 🌍 10% of airports concentrated near hubs, remaining are randomly choose 
    
        

    # === tail types ===
    allowed_tailtypes = [
        {"AircraftTypeName": "CL-650S", "Penalty": 0},
        {"AircraftTypeName": "CE-700", "Penalty": 0},
        {"AircraftTypeName": "CL-350S", "Penalty": 0},
        {"AircraftTypeName": "CE-680AS", "Penalty": 0},
        {"AircraftTypeName": "EMB-545-MOD", "Penalty": 0},
        {"AircraftTypeName": "GL5000S", "Penalty": 0},
        {"AircraftTypeName": "CE-680", "Penalty": 0},
        {"AircraftTypeName": "CE-560XLS", "Penalty": 0},
        {"AircraftTypeName": "EMB-505S", "Penalty": 0},
        {"AircraftTypeName": "EMB-505E", "Penalty": 0},
        {"AircraftTypeName": "GL6000S", "Penalty": 0},
        {"AircraftTypeName": "GL7500", "Penalty": 0},
        {"AircraftTypeName": "GL5500", "Penalty": 0},
    ]
    
    # === set maintenance parameters based on DOE factor ===
    global min_left_range, cycle_left_range
    if maintenance_cycle == "low":
        min_left_range = (200, 400)
        cycle_left_range = (2, 5)
    elif maintenance_cycle == "high":
        min_left_range = (1200, 2000)
        cycle_left_range = (40, 60)
    else:
        print("[-] Invalid maintenance_cycle, defaulting to low")
        min_left_range = (200, 400)
        cycle_left_range = (2, 5)


    
    # ====================== Bruce ======================

    # === generate crew members if crew_included ===
    tails = []
    legs = []
    if crew_included:
        num_crewmembers = num_tails * {"low": 2.2, "high": 2.8}[crewmember_level]
        crews = generate_crewmembers(num_crewmembers, allowed_tailtypes, real_route_level, airports, start_time, time_window_days)
        crewmember_count = len(crews)
        crew_activities, crew_fly_together = generate_crew_activities(crews, airports, airport_coords, start_time, legs, tails)

    # ====================== Bruce ======================



    # === generate tails ===
    # tails is defined 
    for i in range(len(tails), num_tails):
        chosen_type = random.choice(allowed_tailtypes)["AircraftTypeName"]
        tail_number = str(tailID_start + i)

        if real_route_level == "high":
            current_loc = pick_weighted_random_airport(airports, weighted_airports_for_tail)
        elif real_route_level == "low":
            current_loc = random.choice(airports)

        tails.append({
            "TailNumber": tail_number,
            "AircraftTypeName": chosen_type,
            # "OriginalAircraftTypeName": chosen_type,
            "AvailableTime": (start_time - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),        # modify to random, or make it difficult to schedule
            "CurrentLocation": current_loc,
            # "BeginTimeForNextMaintenanceAfterPlanningHorizon": "2026-04-01T09:26:48Z",
            "AssignedProperties": [
                tail_number, chosen_type
                # str(1000000 + i), chosen_type, "ELT_406MHZ_FLAG", "TCAS7.1", "NO_DOUBLE_BUNK"
            ],
            "MinutesLeftForNextMaintenance": random.randint(*min_left_range),
            "CyclesLeftForNextMaintenance": random.randint(*cycle_left_range),  
            # "UseAdditionalRouteTime": False,
            # "IsVendor": False,
            # "AutoPilotInoperative": False,
            "TailCost": 6304,
            # "TailBaseAirport": "KCMH",
            "TailLegCost": 1173
            # "ServiceRequested": True,
            # "TailCostForFerry": 6304,
            # "TailCostForNonFerry": 6304,
            # "tailId": 1000000 + i,
            # "paxSeats": random.choice([8, 10, 12]),
            # "lavSeats": random.choice([0, 1]),
        })




    # === generate flight requests ===
    requests = []
    base_dep_counter = Counter() 
    num_hub_reqs = 0
    num_random_reqs = num_requests

    # if geo_density == "high":
    #     num_hub_reqs = int(0.1 * num_requests)
    #     num_random_reqs = num_requests - num_hub_reqs
    #     print(f"📍 High density mode: {num_hub_reqs} requests near hubs, {num_random_reqs} random across US.")
    # elif geo_density == "low":        
    #     num_hub_reqs = 0
    #     num_random_reqs = num_requests
    #     print(f"🌎 Low density mode: All {num_random_reqs} requests randomly distributed across US.")
    # else:
    #     raise ValueError(f"Invalid geo_density: {geo_density}")
    
    # print(f"🧭 Hub traffic pattern: {hub_pattern}")

    if real_route_level == "high":
        print(f"🛫 Route pattern: HIGH realism based on real weighted routes.")
        # real_route_counter = 0
        REAL_ROUTE_PERCENTAGE = 0.9   # 90% requests follow real route distribution, 10% are random

    elif real_route_level == "low":
        print(f"🛫 Route pattern: LOW realism with random routes.")

    rid = 0
    adjustable_num_requests = num_requests
    # for rid in range(1, num_requests + 1):
    while len(requests) < adjustable_num_requests:
        '''# --- Determine if request belongs to hub or random region ---
        is_hub_request = (geo_density == "high" and rid <= num_hub_reqs and nearby_airports)

        # --- Generate departure & arrival based on hub pattern ---
        if is_hub_request:
            if hub_pattern == "fly_out":
                dep, arr = pick_2_random_airports_for_req(nearby_airports, airports)

            elif hub_pattern == "fly_in":
                arr, dep = pick_2_random_airports_for_req(nearby_airports, airports)
                
            elif hub_pattern == " fly_io":  # "fly_io" = fly between hubs (hub↔hub)
                rd_num = random.random()
                # 1/3 chance for each of the 3 patterns
                if rd_num < 1/3.0:
                    dep, arr = pick_2_random_airports_for_req(nearby_airports, airports)
                elif rd_num < 2/3.0:
                    arr, dep = pick_2_random_airports_for_req(nearby_airports, airports)
                else:
                    dep, arr = random.sample(nearby_airports,2)
                    
            else:
                raise ValueError(f"Invalid hub_pattern: {hub_pattern}")'''

        rid += 1
        # else:
        # Random region (low density or 10% random in high density)
        if real_route_level == "high" and rid < adjustable_num_requests * REAL_ROUTE_PERCENTAGE:
            arr, dep = pick_2_random_airports_for_req(airports, airports, weighted_airport_routes, use_real_route=True)
        elif real_route_level == "low":
            arr, dep = pick_2_random_airports_for_req(airports, airports, use_real_route=False)

        '''Season conflict with geo density, skip for now, fix in future version
        # === choose arrival airport with seasonal bias ===
        if season in ["winter", "fall"]:
            if random.random() < prob_south_bias and south_airports:  # 30% chance to go south
                candidate_pool = [a for a in south_airports if a in airports and a != dep]
            else:  # 70% random
                candidate_pool = [a for a in airports if a != dep]
        else:  # spring/summer
            if random.random() < prob_north_bias and north_airports:  # 30% chance to go north
                candidate_pool = [a for a in north_airports if a in airports and a != dep]
            else:
                candidate_pool = [a for a in airports if a != dep]

        if not candidate_pool:
            candidate_pool = [a for a in airports if a != dep]

        arr = random.choice(candidate_pool)'''

        # any start_time within the day, it will start the previous day 17:00, ends 7:59 the day after
        planning_begin = (start_time - timedelta(days=1)).replace(hour=17, minute=0, second=0)
        planning_end = (start_time + timedelta(days=time_window_days)).replace(hour=7, minute=59, second=0)
        req_time = pick_request_time_from_hour_profile(
            horizon_begin=planning_begin,
            horizon_end=planning_end,
            hourly_profile=hourly_request_profile
        )
        req_id = flightID_start + rid
        jet_type = random.choice(allowed_tailtypes)["AircraftTypeName"]

        # AllowedTailTypes
        if substitutes == 0:
            allowed_types = [{"AircraftTypeName": jet_type, "Penalty": 0}]
        elif substitutes > 0 and substitutes < len(allowed_tailtypes) and type(substitutes) == int:
            other_types = [t for t in allowed_tailtypes if t["AircraftTypeName"] != jet_type]
            sampled_types = random.sample(other_types, substitutes)
            allowed_types = [{"AircraftTypeName": jet_type, "Penalty": 0}] + sampled_types
        else:
            raise ValueError(f"Invalid substitutes: {substitutes}")


        # === Required FA crewmember positions ===
        big_planes = ["CL-650S", "GL5500", "CE-700", "GL6000S", "CE-680AS"]

        # base crew positions (always PIC + SIC)
        crewmember_req = [
            {"PositionInCrew": "PIC", "CrewmemberRequiredProperties": [], "CrewmemberRestrictedProperties": []},
            {"PositionInCrew": "SIC", "CrewmemberRequiredProperties": [], "CrewmemberRestrictedProperties": []},
        ]

        # # 20% chance to add FA if jet is a big plane
        # if jet_type in big_planes and random.random() < 0.2:
        #     crewmember_req.append(
        #         {"PositionInCrew": "FA", "CrewmemberRequiredProperties": [], "CrewmemberRestrictedProperties": []},
        #     )

        # === consruct request ===  
        req = {
            "RequestID": req_id,
            "ArrivalAirport": arr,
            "DepartureAirport": dep,
            "ActivityType": "OPERATE_REVENUE_FLIGHT",
            "RequestedTime": req_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "RequiredCrewmemberPositions": crewmember_req,
            "AllowedTailTypes": allowed_types,
            "requestedAircraftTypeName": jet_type,
            "TailRequiredProperties": []
        }
        requests.append(req)
        base_dep_counter[dep] += 1

        if round_trip_ratio > 0 and random.random() < round_trip_ratio:
            # generate a return request with same dep/arr reversed, same jet type, within the time window
            return_req_time = req_time + timedelta(hours=random.randint(1, 6))
            if return_req_time < start_time + timedelta(days=time_window_days):
                rid += 1
                return_req_id = flightID_start + rid
                return_req = {
                    "RequestID": return_req_id,
                    "ArrivalAirport": dep,
                    "DepartureAirport": arr,
                    "ActivityType": "OPERATE_REVENUE_FLIGHT",
                    "RequestedTime": return_req_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "RequiredCrewmemberPositions": crewmember_req,
                    "AllowedTailTypes": allowed_types,
                    "requestedAircraftTypeName": jet_type,
                    "TailRequiredProperties": []
                }
                requests.append(return_req)
                base_dep_counter[arr] += 1


    # === generate mx requests ===
    for mx_id in range(int(mx_num)):
        dep = random.choice(mx_airport)
        arr = dep
        req_time = start_time + timedelta(minutes=random.randint(0, time_window_days * 24 * 60 - 2))
        service_time = random.randint(4, 24)*60  # maintenance time between 4 hours to 24 hours
        req_id = mxID_start + mx_id
        required_tail_obj = random.choice(tails)
        required_tail = required_tail_obj["TailNumber"]
        jet_type = required_tail_obj["AircraftTypeName"]

        requests.append({
            "RequestID": req_id,
            "RequiredTail": required_tail,
            "ArrivalAirport": arr,
            "DepartureAirport": dep,
            "ActivityType": "MAINTENANCE",
            "RequestedTime": req_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ServiceTime": service_time,
            "AllowedTailTypes": [{"AircraftTypeName": jet_type, "Penalty": 0}],
            "requestedAircraftTypeName": jet_type,
            "TailRequiredProperties": []
        })



    



    # ===== Event factor =====
    baseline_count = len(requests)
    extra_requests = []
    if event:
        EVENT_RANGE_MILES = 100
        epicenter_event = random.choice(airports)
        event_airports = airports_inside_circle(epicenter_event, EVENT_RANGE_MILES, airport_coords)
        Extra_request_number_standard = int(max(100, 0.05 * baseline_count))   # 10% extra requests
        extra_request_per_airport = max(1, Extra_request_number_standard // len(event_airports))
        Extra_request_number = extra_request_per_airport * len(event_airports)
        print(f"🎯 Target extra requests: {Extra_request_number} (~{extra_request_per_airport} per airport)")
        print(f"🎪 Event at {epicenter_event}: {len(event_airports)} airports within {EVENT_RANGE_MILES}mi have surge demand")

        extra_count = 0

        # extra_requests = []
        for ea in event_airports:
        # each airport generates 10 requests
            for j in range(extra_request_per_airport):
                dep = ea
                arr = random.choice([a for a in airports if a != dep])
                req_time = start_time + timedelta(minutes=random.randint(0, time_window_days * 24 * 60 - 2))
                req_id = flightID_start + len(requests)
                jet_type = random.choice(allowed_tailtypes)["AircraftTypeName"]

                requests.append({
                    "RequestID": req_id,
                    "ArrivalAirport": arr,
                    "DepartureAirport": dep,
                    "ActivityType": "OPERATE_REVENUE_FLIGHT",
                    "RequestedTime": req_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "ServiceTime": 0,
                    "SlidingTime": 0,
                    "AllowedTailTypes": [{"AircraftTypeName": jet_type, "Penalty": 0}],
                    "requestedAircraftTypeName": jet_type,
                    "TailRequiredProperties": []
                })

                extra_count += 1
        # extra_count = len(extra_requests)
        # requests += extra_requests                 
        print(f"📈 Event extra requests: {extra_count}")



    # === Weather event ===
    if weather:
        # 3. find all tails located at the affected airports  
        affected_tails = [t for t in tails if t["CurrentLocation"] in weather_affected_airports]

        print(f"🌩️ Weather at {epicenter} (US only): shutdown {len(weather_affected_airports)} airports within 30mi, affecting {len(affected_tails)} tails")

        # 4. generate locked legs for the affected tails (grounded for the entire planning window)
        starting_leg_id=legID_start + len(legs)
        weather_legs = build_grounding_legs_for_tails(
            tails=tails,
            affected_airports=weather_affected_airports,
            start_time_dt=start_time,
            time_window_days=time_window_days,
            starting_leg_id=starting_leg_id
        )

        # combined weather legs to legs
        legs.extend(weather_legs)

    else:
        weather_legs = []

    # print(f"[DEBUG] Crew-generated legs: {len(legs) - len(weather_legs)}")
    # print(f"[DEBUG] Weather legs: {len(weather_legs)}")
    # print(f"[DEBUG] Final total legs: {len(legs)}")



    # ==================== summary ====================     # not finished yet
    tail_count = len(tails)
    request_count = len(requests)
    maintenance_count = int(mx_num)
    total_mx_minutes = sum([r.get("ServiceTime",0) for r in requests if r["ActivityType"] == "MAINTENANCE"])
    # total_rev_flights_duration = sum([r.get("Duration",0) for r in legs if r["ActivityType"] == "OPERATE_REVENUE_FLIGHT"])
    total_cycles_left = sum([t["CyclesLeftForNextMaintenance"] for t in tails])
    total_minutes_left = sum([t["MinutesLeftForNextMaintenance"] for t in tails])
    mx_minutes_by_type = {}
    rev_minutes_by_type = {}
    cycels_left_by_type = {}
    minutes_left_by_type = {}
    for fleet_type in allowed_tailtypes:
        atype = fleet_type["AircraftTypeName"]
        mx_minutes_by_type[atype] = sum([r.get("ServiceTime",0) for r in requests if r["ActivityType"] == "MAINTENANCE" and any(at["AircraftTypeName"]==atype for at in r["AllowedTailTypes"])])
        # rev_minutes_by_type[atype] = sum([r.get("Duration",0) for r in legs if r["ActivityType"] == "OPERATE_REVENUE_FLIGHT" and any(at["AircraftTypeName"]==atype for at in r["AllowedTailTypes"])])
        cycels_left_by_type[atype] = sum([t["CyclesLeftForNextMaintenance"] for t in tails if t["AircraftTypeName"] == atype])
        minutes_left_by_type[atype] = sum([t["MinutesLeftForNextMaintenance"] for t in tails if t["AircraftTypeName"] == atype])

    # ==================== summary ====================



    # === Scenario output ===
    scenario = {
        "Tails": tails,
        "FlightRequests": requests,
        # always output legs
        "Legs": legs,
        **({"Crewmembers": crews} if crew_included else {}),    # ====================== Bruce ======================
        **({"CrewActivities": crew_activities} if crew_included else {}),    # ====================== Bruce ======================
        "Weather": {
            "Enabled": weather,
            "Epicenter": epicenter if weather else None,
            "AffectedAirports": sorted(list(weather_affected_airports)) if weather else [],
        },
        
        # ====================== Bruce ======================
        "CrewFlyingTogether": crew_fly_together if crew_included else [],
        "Configuration": {
            "PlanningHorizon": {
                "BeginTime": planning_begin.strftime("%Y-%m-%dT%H:%M:%SZ"),  # positioning start 1 day before
                "EndTime": planning_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        },
        # ====================== Bruce ======================
        
        "Factors": {
            "DOE Run ID": exp_id,
            "Area": area,
            "Arrival Rate": arrival_rate,
            "substitutes": substitutes,
            "tail_scale": tail_scale,
            "crew_included": crew_included,
            "crewmember_level": crewmember_level,
            "maintenance_scale": maintenance_scale,
            "maintenance_airport_distribution": maintenance_airport_distribution,
            # "geo_density": geo_density,
            "time_window_days": time_window_days,
            "weather": weather,
            "event": event,
            "maintenance_cycle": maintenance_cycle,
            "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ") if start_time else None,
            "season": season,
            "hub_pattern": hub_pattern
        },
        
        "Summary": {        # not finished yet
            "tail_scale": tail_count,
            "request_count": request_count,
            "maintenance_count": maintenance_count,
            "crewmember_count": crewmember_count if crew_included else 0,
            "total_maintenance_minutes": total_mx_minutes,
            # "total_revenue_flight_minutes": total_rev_flights_duration,
            "total_cycles_left": total_cycles_left,
            "total_minutes_left": total_minutes_left,
            "maintenance_minutes_by_type": mx_minutes_by_type,
            # "revenue_flight_minutes_by_type": rev_minutes_by_type,
            "cycles_left_by_type": cycels_left_by_type,
        }
    }

    # filename = f"scenario_{arrival_rate}_{geo_density}_{tail_scale}_{maintenance_cycle}.json"
    filename = f"./TestCases/DOE_FilterAirport/DOE_run{exp_id}.json"
    with open(filename, "w") as f:
        json.dump(scenario, f, indent=2)
    print()
    print(f"✅ {filename} generated with {len(requests)} requests and {len(tails)} tails")





# === Generate Scenario 11 JSON ===
# scenario11 = generate_scenario11_full()

# ======================= Vivian Read this ========================
# # === Generate multiple scenarios based on DOE factors ===
# exps = [{f1:"low",f2:0,f3:"low",f4:"high",f5:1,f6:1}, {f1:"high",f2:1,f3:"low",f4:"high",f5:1,f6:1}, ]
# for exp in exps:
#     generate_scenario11_full(exp.values())
# === Generate multiple scenarios ===

arrival_rates = ["low", "high"]
substitutes_options = [0, 2]
tail_scales = ["low", "high"]
crewmember_levels = ["low", "high"] # "mid",
maintenance_scales = ["low", "high"]
maintenance_airport_distributions = ["balanced", "east"] # "west",
# geo_densities = ["low", "high"]
real_route_levels = ["low", "high"]
hub_patterns = ["fly_out", "fly_in"] # "fly_io",
time_window_days_options = [1, 3]
weather_options = [False, True]
event_options = [False, True]
maintenance_cycles = ["low", "high"]

# experiments = [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 
#                [1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1]]  # total 12 factors

# DOE1 experiments matrix ( 30 runs )
'''experiments = [
    [1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0], # [0, 1, 1]
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], # [0, 0, 0]
    [1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1], # [0, 1, 0]
    [1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0], # [1, 0, 1]
    [1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 0], # [1, 1, 0]
    [1, 1, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1], # [1, 0, 1]
    [1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1], # [0, 1, 1]
    [1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1], # [1, 1, 0]
    [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0], # [1, 1, 0]
    [1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1], # [0, 0, 0]
    [1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0], # [1, 1, 1]
    [1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0], # [0, 1, 0]
    [1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0], # [0, 0, 1]
    [1, 0, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1], # [1, 0, 0]
    [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1], # [0, 0, 1]
    [0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1], # [0, 0, 1]
    [0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1], # [0, 1, 1]
    [0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0], # [1, 0, 0]
    [0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1], # [0, 0, 1]
    [0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0], # [1, 1, 1]
    [0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0], # [0, 1, 0]
    [0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1], # [1, 1, 0]
    [0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 1, 0], # [0, 0, 0]
    [0, 0, 1, 1, 0, 1, 1, 1, 0, 0, 1, 0], # [1, 0, 0]
    [0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0], # [1, 1, 1]
    [0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1], # [1, 0, 0]
    [0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0], # [0, 1, 0]
    [0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1], # [1, 1, 1]
    [0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0], # [0, 1, 1]
    [0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1], # [1, 1, 1]
]


experiments = [
    {"arrival_rate": "low", 
     "substitutes": 0, 
     "tail_scale": "low",
     "crewmember_level": "low", 
     "maintenance_scale": "high",
     "maintenance_airport_distribution": "west",
     "geo_density": "high", 
     "hub_pattern": "fly_out", 
     "time_window_days": 1, 
     "weather": True, 
     "event": False, 
     "maintenance_cycle": "low",
     "experiment_id": 1},
    {"arrival_rate": "high", 
     "substitutes": 4, 
     "tail_scale": "high",
     "crewmember_level": "low", 
     "maintenance_scale": "high",
     "maintenance_airport_distribution": "west",
     "geo_density": "low", 
     "hub_pattern": "fly_in", 
     "time_window_days": 1, 
     "weather": False, 
     "event": True, 
     "maintenance_cycle": "high",
     "experiment_id": 2},
]'''


# DOE1 experiments, test on 1010 model
'''for idx, exp in enumerate(experiments):
    generate_scenario(arrival_rate=arrival_rates[exp[0]],
                      substitutes=substitutes_options[exp[1]],
                      tail_scale=tail_scales[exp[2]],
                      crewmember_level=crewmember_levels[exp[3]],
                      maintenance_scale=maintenance_scales[exp[4]],
                      maintenance_airport_distribution=maintenance_airport_distributions[exp[5]],
                      geo_density=geo_densities[exp[6]],
                      hub_pattern=hub_patterns[exp[7]],
                      time_window_days=time_window_days_options[exp[8]],
                      weather=weather_options[exp[9]],
                      event=event_options[exp[10]],
                      maintenance_cycle=maintenance_cycles[exp[11]],
                      exp_id=idx+1
                      )
    # generate_scenario(**exp)
    print("--------------------------------------------------")
'''

# DOE3 : 32 runs with 15 factors
experiments = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], #, [0, 0, 0, 0, 0],
    [1, 1, 1, 1, 1, 1, 1, 0, 1, 1], #, [1, 1, 1, 1, 0],
    [1, 1, 1, 1, 0, 0, 0, 1, 1, 1], #, [1, 1, 0, 1, 0],
    [1, 1, 1, 0, 1, 0, 0, 1, 0, 0], #, [0, 1, 1, 1, 1],
    [1, 1, 1, 0, 0, 1, 1, 0, 1, 0], #, [0, 0, 0, 1, 0],
    [1, 1, 1, 0, 0, 1, 0, 0, 1, 0], #, [1, 1, 1, 0, 1],
    [1, 1, 1, 0, 0, 0, 1, 1, 0, 0], #, [0, 1, 1, 0, 0],
    [1, 1, 0, 1, 0, 1, 1, 0, 1, 0], #, [0, 0, 0, 1, 1],
    [1, 1, 0, 1, 0, 0, 0, 1, 1, 1], #, [0, 1, 1, 0, 1],
    [1, 1, 0, 0, 1, 1, 1, 1, 0, 0], #, [1, 1, 1, 0, 0],
    [1, 0, 1, 1, 1, 1, 0, 1, 1, 0], #, [0, 1, 0, 0, 0],
    [1, 0, 1, 1, 0, 0, 1, 0, 0, 1], #, [1, 1, 0, 1, 1],
    [1, 0, 1, 0, 0, 1, 1, 0, 0, 1], #, [0, 0, 1, 0, 1],
    [1, 0, 0, 1, 1, 1, 0, 0, 1, 0], #, [1, 0, 1, 1, 0],
    [1, 0, 0, 0, 1, 0, 1, 1, 1, 0], #, [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 1, 1, 1], #, [1, 0, 1, 1, 0],
    [0, 1, 1, 1, 1, 1, 1, 1, 0, 0], #, [1, 0, 1, 0, 1],
    [0, 1, 1, 1, 1, 0, 0, 0, 0, 1], #, [0, 0, 0, 1, 1],
    [0, 1, 1, 0, 1, 1, 0, 1, 1, 1], #, [1, 0, 0, 0, 1],
    [0, 1, 0, 1, 0, 0, 1, 1, 0, 1], #, [1, 0, 0, 0, 0],
    [0, 1, 0, 0, 1, 1, 1, 0, 0, 1], #, [0, 1, 1, 1, 0],
    [0, 1, 0, 0, 1, 0, 1, 0, 1, 0], #, [1, 1, 0, 0, 1],
    [0, 1, 0, 0, 0, 1, 1, 1, 0, 1], #, [1, 1, 0, 1, 1],
    [0, 1, 0, 0, 0, 0, 1, 1, 1, 0], #, [1, 0, 1, 1, 1],
    [0, 0, 1, 1, 1, 0, 1, 0, 1, 0], #, [1, 1, 1, 0, 0],
    [0, 0, 1, 1, 0, 1, 0, 0, 0, 0], #, [1, 1, 1, 1, 0],
    [0, 0, 1, 1, 0, 0, 1, 1, 1, 0], #, [0, 0, 1, 0, 1],
    [0, 0, 1, 0, 0, 0, 1, 1, 1, 0], #, [0, 1, 0, 1, 0],
    [0, 0, 0, 1, 1, 1, 1, 0, 1, 1], #, [0, 1, 0, 1, 1],
    [0, 0, 0, 0, 1, 1, 1, 1, 1, 1], #, [0, 1, 1, 0, 0],
    [0, 0, 0, 0, 1, 1, 0, 1, 0, 0], #, [1, 1, 0, 1, 1],
    [0, 0, 0, 0, 0, 0, 0, 0, 1, 1]  #, [1, 1, 1, 0, 0],
]

# DOE2 experiments, test on 1107 model
for idx, exp in enumerate(experiments):
    generate_scenario(arrival_rate=arrival_rates[exp[0]],
                      substitutes=substitutes_options[exp[1]],
                      tail_scale=tail_scales[exp[2]],
                      crewmember_level=crewmember_levels[exp[3]],
                      maintenance_scale=maintenance_scales[exp[4]],
                    #   maintenance_airport_distribution=maintenance_airport_distributions[exp[5]],
                    #   geo_density=geo_densities[exp[5]],
                    #   real_route_level=real_route_levels[exp[5]],
                      hub_pattern=hub_patterns[exp[6]],
                    #   time_window_days=time_window_days_options[exp[7]],
                      weather=weather_options[exp[7]],
                      event=event_options[exp[8]],
                      maintenance_cycle=maintenance_cycles[exp[9]],
                      exp_id=idx+1
                      )
    # generate_scenario(**exp)
    print("--------------------------------------------------")
    