import json
import random
from datetime import datetime, timedelta
from collections import Counter
from math import radians, sin, cos, sqrt, atan2
import time

# === Step 1. read in all airports latitude and longtitude ===
with open("srd.json", "r", encoding="utf-8") as f:
    full_data = json.load(f)
airport_coords = {}
us_airports = []
for a in full_data["StaticRoutingData"]["Airports"]:
    if "Latitude" in a and "Longitude" in a:
        airport_coords[a["ICAOCode"]] = (a["Latitude"], a["Longitude"])
        if a.get("CountryID") == "US":
            us_airports.append(a["ICAOCode"])

# === Step 2. define 3 hubs and distance function ===
geo_centers = {
    "KTEB": (40.85, -74.0608),
    "KPBI": (26.6831, -80.0956),
    "KIAD": (38.9472, -77.4597)
}

# distance function between 2 coordinates on sphere
def haversine(lat1, lon1, lat2, lon2):
    """return the distance of 2 cooridnates"""
    R = 3958.8  # earth radius (miles)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

def compute_weather_shutdown_airports(epicenter_icao: str, radius_miles: float,
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
def generate_allowed_tailtypes(allowed_tailtypes):
    rand_allowed_tailtypes = []
    temp_types = random.sample(allowed_tailtypes, k=random.randint(1, min(len(allowed_tailtypes), 4)))
    for t in temp_types:
        rand_allowed_tailtypes.append({
            "AircraftTypeName": t["AircraftTypeName"],
            "QualificationCode": "PIC",
            "dayCurrencyExpiration": "2026-06-19T23:59:00Z",
            "nightCurrencyExpiration": "2026-06-19T23:59:00Z",
            "qualificationStartDate": "1900-01-01T00:00:00Z"
        })
        rand_allowed_tailtypes.append({
            "AircraftTypeName": t["AircraftTypeName"],
            "QualificationCode": "SIC",
            "qualificationStartDate": "1900-01-01T00:00:00Z"
        })
    return rand_allowed_tailtypes


# ====================== Bruce ======================
def generate_crewmembers(crewmember_level, allowed_tailtypes, us_airports, start_time, time_window_days):
    crews = []
    # positions = ["PIC", "SIC"]
    if crewmember_level == "low":
        num_crews = 1500
    elif crewmember_level == "mid":
        num_crews = 2000
    elif crewmember_level == "high":
        num_crews = 2500
    else:
        print("Invalid crewmember_level, defaulting to low (2000 crews)")
        num_crews = 2000
    
    for cid in range(1, num_crews + 1):
        crew_id = 700000 + cid
        roster_length = random.randint(5,8) # days
        # Start time is randomly set within the time window minus the roster length
        tour_start_time = start_time + timedelta(hours=random.randint(-roster_length * 24, time_window_days * 24))
        tour_end_time = tour_start_time + timedelta(minutes=roster_length * 24 * 60 + 13 * 60 - 1)      # add 13 hours because found schedule_sanitized crew pattern
        airport_domicile = random.choice(us_airports)
        current_loc = current_loc if random.random() < 0.9 else random.choice(us_airports)
        qualified_types = generate_allowed_tailtypes(allowed_tailtypes)

        crews.append({
            "CrewmemberID": crew_id,
            "CurrentLocation": current_loc,
            "AirportIDDomicile": airport_domicile,    # base airport
            "tourStartDate": tour_start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tourEndDate": tour_end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "QualifiedAircraftTypes": qualified_types
        })
    return crews


# ====================== Bruce ======================
def generate_crew_activities(crews, us_airports, start_time, time_window_days):
    crew_activities = []
    activity_types = ["MOVEMENT", "REST", "OPERATE_REVENUE_FLIGHT", "OPERATE_FERRY_FLIGHT", "STATIC_STANDBY"]  # Example activity type codes
    for crew in crews:
        if random.random() < 0.9:
            continue  # 20% chance to skip adding activities for this crew
        crew_id = crew["CrewmemberID"]
        # num_activities = random.randint(3, 6)  # Number of activities per crew
        # for _ in range(num_activities):
        #     # activity_type = random.choice(activity_types)
        activity_type = "REST"  # For simplicity, set all activities to REST
        rest_airport = random.choice(us_airports)
        activity_start = start_time + timedelta(minutes=random.randint(0, time_window_days * 24 * 60 - 60))
        duration = random.randint(30, 300)
        crew_activities.append({
            "CrewmemberID": crew_id,
            "ActivityType": activity_type,
            "OriginAirport": rest_airport,
            "DestinationAirport": rest_airport,
            "StartTime": activity_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "Duration": duration,
        })
    return crew_activities


def generate_scenario11_full(seed=42):
    #random.seed(seed)
    random.seed(time.time())

    # === DOE factors ===
    arrival_rate = "low"      # requests = high: tails * 4 / low: tails * 2
    substitutes = 0           # 0 fleet types allowed
    scale = "low"             # 500 planes
    geo_density = "high"       # high = dense / low = dispersed
    time_window_days = 1
    weather = True            # weather issue
    event = True              # event (superbowl...)
    start_time = datetime(2025, 4, 1, 6, 0, 0)
    
    # ====================== Bruce ======================
    crew_included = True
    crewmember_level = "low"      # low / mid / high = 1500 / 2000 / 2500 crews
    # ====================== Bruce ======================


    # === numerical setting ===
    scale_map = {"low": 500, "high": 1000}
    num_tails = scale_map[scale]
    num_requests = num_tails * (2 if arrival_rate == "low" else 4) * time_window_days

    # === Step 3. select airports based on geo_density ===
    if geo_density == "high":
        nearby_airports = set()
        for cname, (clat, clon) in geo_centers.items():
            for icao, (alat, alon) in airport_coords.items():
                if haversine(clat, clon, alat, alon) <= 50:
                    nearby_airports.add(icao)
        airports = list(nearby_airports)
        print(f"🌍 High density: {len(airports)} airports within 50 miles of 3 hubs")
    else:
        airports = random.sample(list(airport_coords.keys()), 200)
        print(f"🌎 Low density: Randomly selected {len(airports)} airports")

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

    # === generate tails ===
    tails = []
    for i in range(num_tails):
        chosen_type = random.choice(allowed_tailtypes)["AircraftTypeName"]
        tail_number = str(1000000 + i)
        tails.append({
            "TailNumber": tail_number,
            "AircraftTypeName": chosen_type,
            # "OriginalAircraftTypeName": chosen_type,
            "AvailableTime": "2025-03-31T01:48:00Z",
            "CurrentLocation": random.choice(airports),
            # "BeginTimeForNextMaintenanceAfterPlanningHorizon": "2026-04-01T09:26:48Z",
            "AssignedProperties": [
                tail_number, chosen_type
                # str(1000000 + i), chosen_type, "ELT_406MHZ_FLAG", "TCAS7.1", "NO_DOUBLE_BUNK"
            ],
            "MinutesLeftForNextMaintenance": random.randint(200, 400),
            "CyclesLeftForNextMaintenance": random.randint(20, 40),
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
    for rid in range(1, num_requests + 1):
        dep = random.choice(airports)
        arr = random.choice([a for a in airports if a != dep])
        req_time = start_time + timedelta(minutes=random.randint(0, time_window_days * 24 * 60))
        req_id = 50000 + rid
        jet_type = random.choice(allowed_tailtypes)["AircraftTypeName"]

        # AllowedTailTypes
        if substitutes == 0:
            allowed_types = [{"AircraftTypeName": jet_type, "Penalty": 0}]
        else:
            other_types = [t for t in allowed_tailtypes if t["AircraftTypeName"] != jet_type]
            sampled_types = random.sample(other_types, 4)
            allowed_types = [{"AircraftTypeName": jet_type, "Penalty": 0}] + sampled_types

        req = {
            "RequestID": req_id,
            "ArrivalAirport": arr,
            "DepartureAirport": dep,
            "ActivityType": "OPERATE_REVENUE_FLIGHT",
            "RequestedTime": req_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "RequiredCrewmemberPositions": [
                {"PositionInCrew": "PIC", "CrewmemberRequiredProperties": [], "CrewmemberRestrictedProperties": []},
                {"PositionInCrew": "SIC", "CrewmemberRequiredProperties": [], "CrewmemberRestrictedProperties": []},
            ],
            "AllowedTailTypes": allowed_types,
            "requestedAircraftTypeName": jet_type,
            "TailRequiredProperties": []
        }
        requests.append(req)
        base_dep_counter[dep] += 1

    
    # ====================== Bruce ======================

    # === generate crew members if crew_included ===
    if crew_included:
        crews = generate_crewmembers(crewmember_level, allowed_tailtypes, us_airports, start_time, time_window_days)
        crew_activities = generate_crew_activities(crews, us_airports, start_time, time_window_days)

    # ====================== Bruce ======================


    # ===== Event factor =====
    baseline_count = len(requests)

    if event:
        epicenter_event = random.choice(us_airports)
        event_airports = compute_weather_shutdown_airports(epicenter_event, 30.0, airport_coords)
        print(f"🎪 Event at {epicenter_event}: {len(event_airports)} airports within 30mi have surge demand")

        extra_requests = []
        for ea in event_airports:
        # each airport generates 10 times requests
            for j in range(10):
                dep = ea
                arr = random.choice([a for a in airports if a != dep])
                req_time = start_time + timedelta(minutes=random.randint(0, time_window_days * 24 * 60))
                req_id = 900000 + len(extra_requests)
                jet_type = random.choice(allowed_tailtypes)["AircraftTypeName"]

                extra_requests.append({
                    "RequestID": req_id,
                    "ArrivalAirport": arr,
                    "DepartureAirport": dep,
                    "ActivityType": "OPERATE_REVENUE_FLIGHT",
                    "RequestedTime": req_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "ServiceTime": 0,
                    "SlidingTime": 0,
                    "AllowedTailTypes": [{"AircraftTypeName": jet_type, "Penalty": 0}],
                    "requestedAircraftTypeName": jet_type,
                })

    extra_count = len(extra_requests)          
    requests += extra_requests                 
    print(f"📈 Event extra requests: {extra_count}")


    # === Weather event ===
    legs = []
    if weather:
        # 1. randomly choose a weather affected airport in US as a center
        epicenter = random.choice(us_airports)

        # 2. find out all the affected airport within 30 miles 
        affected_airports = compute_weather_shutdown_airports(epicenter, 30.0, airport_coords)

        # 3. find all tails located at the affected airports  
        affected_tails = [t for t in tails if t["CurrentLocation"] in affected_airports]

        print(f"🌩️ Weather at {epicenter} (US only): shutdown {len(affected_airports)} airports within 30mi, affecting {len(affected_tails)} tails")

        # 4. generate locked legs for the affected tails (grounded for the entire planning window)
        weather_legs = build_grounding_legs_for_tails(
            tails=tails,
            affected_airports=affected_airports,
            start_time_dt=start_time,
            time_window_days=time_window_days,
            starting_leg_id=50_000_000
        )
    else:
        weather_legs = []



    # === Scenario output ===
    scenario = {
        "Tails": tails,
        "FlightRequests": requests + extra_requests,
        # only when weather=True add Legs
        **({"Legs": legs} if weather else {}),
        **({"Crewmembers": crews} if crew_included else {}),    # ====================== Bruce ======================
        **({"CrewActivities": crew_activities} if crew_included else {}),    # ====================== Bruce ======================
        "Weather": {
            "Enabled": weather,
            "Epicenter": epicenter if weather else None,
            "AffectedAirports": sorted(list(affected_airports)) if weather else [],
        },
        
        # ====================== Bruce ======================
        "Configuration": {
            "PlanningHorizon": {
                "BeginTime": (start_time + timedelta(days=-1)).strftime("%Y-%m-%dT%H:%M:%SZ"),  # positioning start 1 day before
                "EndTime": (start_time + timedelta(days=time_window_days)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        },
        # ====================== Bruce ======================
        
        "Description": "DOE Run #11 with Weather disruption",
    }

    with open("scenario11_full_with_crew.json", "w") as f:
        json.dump(scenario, f, indent=2)

    print(f"✅ scenario11_full.json generated ({len(legs)} weather legs)" if weather else "✅ scenario11_full.json generated (no weather)")
    return scenario




# === Generate Scenario 11 JSON ===
scenario11 = generate_scenario11_full()

# ======================= Vivian Read this ========================
# # === Generate multiple scenarios based on DOE factors ===
# exps = [{f1:"low",f2:0,f3:"low",f4:"high",f5:1,f6:1}, {f1:"high",f2:1,f3:"low",f4:"high",f5:1,f6:1}, ]
# for exp in exps:
#     generate_scenario11_full(exp.values())