import json
import random
from datetime import datetime, timedelta
from collections import Counter
from math import radians, sin, cos, sqrt, atan2
import time

# === Step 1. read in all airports latitude and longtitude ===
with open("srd.json", "r", encoding="utf-8") as f:
    full_data = json.load(f)
all_airport_coords = {}
us_airports = []
us_airports_dict = {}
for a in full_data["StaticRoutingData"]["Airports"]:
    if "Latitude" in a and "Longitude" in a:
        all_airport_coords[a["ICAOCode"]] = (a["Latitude"], a["Longitude"])
        if a.get("CountryID") == "US":
            us_airports.append(a["ICAOCode"])
            us_airports_dict[a["ICAOCode"]] = (a["Latitude"], a["Longitude"])

# === Step 2. define 3 hubs and distance function ===
geo_centers = {
    "KTEB": (40.85, -74.0608),
    "KPBI": (26.6831, -80.0956),
    "KIAD": (38.9472, -77.4597)
}

global crewID_start, flightID_start, mxID_start, tailID_start, legIDstart
crewID_start = 700000
flightID_start = 50000
mxID_start = 800000
tailID_start = 1000000
legID_start = 2000000




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
def generate_crewmembers(crewmember_level, allowed_tailtypes, airports, start_time, time_window_days):
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
        crew_id = crewID_start + cid
        roster_length = random.randint(5,8) # days
        # Start time is randomly set within the time window minus the roster length
        tour_start_time = start_time + timedelta(hours=random.randint(-roster_length * 24, time_window_days * 24))
        tour_end_time = tour_start_time + timedelta(minutes=roster_length * 24 * 60 + 13 * 60 - 1)      # add 13 hours because found schedule_sanitized crew pattern
        airport_domicile = random.choice(airports)
        current_loc = airport_domicile if random.random() < 0.9 else random.choice(airports)
        qualified_types = generate_allowed_tailtypes(allowed_tailtypes)

        crews.append({
            "CrewmemberID": crew_id,
            "CurrentLocation": current_loc,
            "AirportIDDomicile": airport_domicile,    # base airport
            "tourStartDate": tour_start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tourEndDate": tour_end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "CrewmemberQualifications": qualified_types
        })
    
    # ====================== Vivian ======================
    FAnum = int(0.1 * num_crews)

    for FAid in range(1, FAnum + 1):
        crew_id = crewID_start + num_crews + FAid     #ensure no overlap with previous section
        roster_length = random.randint(5, 8)
        tour_start_time = start_time + timedelta(hours=random.randint(-roster_length * 24, time_window_days * 24))
        tour_end_time = tour_start_time + timedelta(minutes=roster_length * 24 * 60 + 13 * 60 - 1)
        airport_domicile = random.choice(airports)
        current_loc = airport_domicile if random.random() < 0.9 else random.choice(airports)
        qualified_types = generate_allowed_tailtypes(allowed_tailtypes)

        crews.append({
            "CrewmemberID": crew_id,
            "QualificationCode": "FA",  
            "CurrentLocation": current_loc,
            "AirportIDDomicile": airport_domicile,
            "tourStartDate": tour_start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tourEndDate": tour_end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "CrewmemberQualifications": qualified_types
        })

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


def pick_2_random_airports_for_req(pool1, pool2):
    dep = random.choice(pool1)
    arr = random.choice(pool2)
    while arr == dep:
        arr = random.choice(pool2)
    return dep, arr


# === DOE factors ===
def generate_scenario(
    area="US",
    arrival_rate="low",
    substitutes=0,
    tail_scale="low",    
    maintenance_scale="low",
    maintenance_airport_distribution ="east",
    geo_density="low",
    time_window_days=1,
    weather=False,
    event=False,
    maintenance_cycle="low",
    start_time=datetime(2025, 4, 1, 6, 0, 0),
    season="Winter",     # input season is more intuitive
    hub_pattern = "fly_out"
):
    
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
    else: 
        airports = list(all_airport_coords.keys())
        airport_coords = all_airport_coords       # ICAO to (lat, lon) dict
    
    crew_included = True
    crewmember_level = "low"      # low / mid / high = 1500 / 2000 / 2500 crews


    # ========== Bruce: don't need this once we have season input ==========
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

    print(f"🍂 Auto season={season} (month={month}): 30% bias toward {bias_direction}")


    # === numerical setting ===
    tail_scale_map = {"low": 500, "high": 1000}
    num_tails = tail_scale_map[tail_scale]
    num_requests = num_tails * (2 if arrival_rate == "low" else 4) * time_window_days
    
    mx_scale_map = {"low": 0.1, "high": 0.3}
    mx_num = mx_scale_map[maintenance_scale] * num_tails * time_window_days

    # ====== Vivian ======
    mx_airport = []

    # split airports by longtitude
    east_airports = [a for a, (_, lon) in airport_coords.items() if lon > -95]
    west_airports = [a for a, (_, lon) in airport_coords.items() if lon <= -95]

    # control directions 
    if maintenance_airport_distribution == "east":
        num_east = int(0.7 * len(east_airports))
        num_west = int(0.3 * len(west_airports))
        selected_east = random.sample(east_airports, num_east)
        selected_west = random.sample(west_airports, num_west)
        mx_airport = selected_east + selected_west

    elif maintenance_airport_distribution == "west":
        num_west = int(0.7 * len(west_airports))
        num_east = int(0.3 * len(east_airports))
        selected_west = random.sample(west_airports, num_west)
        selected_east = random.sample(east_airports, num_east)
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

    # === Step 3. select airports based on geo_density ===
    nearby_airports = []
    for cname, (clat, clon) in geo_centers.items():
        for icao, (alat, alon) in airport_coords.items():
            if haversine(clat, clon, alat, alon) <= 50:
                nearby_airports.append(icao)
    print(f"🗺️ Found {len(nearby_airports)} airports within 50 miles of 3 hubs.")
        # 🌍 10% of airports concentrated near hubs, remaining are randomly choose 
    
        

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
    else:
        min_left_range = (1200, 2000)
        cycle_left_range = (40, 60)


    
    # ====================== Bruce ======================

    # === generate crew members if crew_included ===
    tails = []
    legs = []
    if crew_included:
        crews = generate_crewmembers(crewmember_level, allowed_tailtypes, airports, start_time, time_window_days)
        crew_activities, crew_fly_together = generate_crew_activities(crews, airports, airport_coords, start_time, legs, tails)

    # ====================== Bruce ======================



    # === generate tails ===
    # tails is defined 
    for i in range(len(tails), num_tails):
        chosen_type = random.choice(allowed_tailtypes)["AircraftTypeName"]
        tail_number = str(tailID_start + i)
        tails.append({
            "TailNumber": tail_number,
            "AircraftTypeName": chosen_type,
            # "OriginalAircraftTypeName": chosen_type,
            "AvailableTime": "2025-03-31T01:48:00Z",        # modify to random, or make it difficult to schedule
            "CurrentLocation": random.choice(airports),
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

    if geo_density == "high":
        num_hub_reqs = int(0.1 * num_requests)
        num_random_reqs = num_requests - num_hub_reqs
        print(f"📍 High density mode: {num_hub_reqs} requests near hubs, {num_random_reqs} random across US.")
    else:
        num_hub_reqs = 0
        num_random_reqs = num_requests
        print(f"🌎 Low density mode: All {num_random_reqs} requests randomly distributed across US.")

    
    print(f"🧭 Hub traffic pattern: {hub_pattern}")

    for rid in range(1, num_requests + 1):
        # --- Determine if request belongs to hub or random region ---
        is_hub_request = (geo_density == "high" and rid <= num_hub_reqs and nearby_airports)

        # --- Generate departure & arrival based on hub pattern ---
        if is_hub_request:
            if hub_pattern == "fly_out":
                dep, arr = pick_2_random_airports_for_req(nearby_airports, airports)

            elif hub_pattern == "fly_in":
                arr, dep = pick_2_random_airports_for_req(nearby_airports, airports)
                
            else:  # "fly_io" = fly between hubs (hub↔hub)
                rd_num = random.random()
                # 1/3 chance for each of the 3 patterns
                if rd_num < 1/3.0:
                    dep, arr = pick_2_random_airports_for_req(nearby_airports, airports)
                elif rd_num < 2/3.0:
                    arr, dep = pick_2_random_airports_for_req(nearby_airports, airports)
                else:
                    dep, arr = random.sample(nearby_airports,2)
                    

        else:
            # Random region (low density or 10% random in high density)
            arr, dep = pick_2_random_airports_for_req(airports, airports)

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

        req_time = start_time + timedelta(minutes=random.randint(0, time_window_days * 24 * 60))
        req_id = flightID_start + rid
        jet_type = random.choice(allowed_tailtypes)["AircraftTypeName"]

        # AllowedTailTypes
        if substitutes == 0:
            allowed_types = [{"AircraftTypeName": jet_type, "Penalty": 0}]
        else:
            other_types = [t for t in allowed_tailtypes if t["AircraftTypeName"] != jet_type]
            sampled_types = random.sample(other_types, 4)
            allowed_types = [{"AircraftTypeName": jet_type, "Penalty": 0}] + sampled_types

        # === Required FA crewmember positions ===
        big_planes = ["CL-650S", "GL5500", "CE-700", "GL6000S", "CE-680AS"]

        # base crew positions (always PIC + SIC)
        crewmember_req = [
            {"PositionInCrew": "PIC", "CrewmemberRequiredProperties": [], "CrewmemberRestrictedProperties": []},
            {"PositionInCrew": "SIC", "CrewmemberRequiredProperties": [], "CrewmemberRestrictedProperties": []},
        ]

        # 20% chance to add FA if jet is a big plane
        if jet_type in big_planes and random.random() < 0.2:
            crewmember_req.append(
                {"PositionInCrew": "FA", "CrewmemberRequiredProperties": [], "CrewmemberRestrictedProperties": []},
            )

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



    # === generate mx requests ===
    for mx_id in range(int(mx_num)):
        dep = random.choice(mx_airport)
        arr = dep
        req_time = start_time + timedelta(minutes=random.randint(0, time_window_days * 24 * 60))
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
        epicenter_event = random.choice(airports)
        event_airports = airports_inside_circle(epicenter_event, 30.0, airport_coords)
        print(f"🎪 Event at {epicenter_event}: {len(event_airports)} airports within 30mi have surge demand")

        # extra_requests = []
        for ea in event_airports:
        # each airport generates 10 requests
            for j in range(10):
                dep = ea
                arr = random.choice([a for a in airports if a != dep])
                req_time = start_time + timedelta(minutes=random.randint(0, time_window_days * 24 * 60))
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
                })

        extra_count = len(event_airports) * 10
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
    else:
        weather_legs = []

    # === save scenario ===
    scenario = {
        "DOE_Factors": {
            "arrival_rate": arrival_rate,
            "substitutes": substitutes,
            "tail_scale": tail_scale,
            "geo_density": geo_density,
            "time_window_days": time_window_days,
            "weather": weather,
            "event": event,
            "maintenance_cycle": maintenance_cycle,
        },
        "Tails": tails,
        "FlightRequests": requests,
    }

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
            "AffectedAirports": sorted(list(weather_affected_airports)) if weather else [],
        },
        
        # ====================== Bruce ======================
        "CrewFlyingTogether": crew_fly_together if crew_included else [],
        "Configuration": {
            "PlanningHorizon": {
                "BeginTime": (start_time + timedelta(days=-1)).strftime("%Y-%m-%dT%H:%M:%SZ"),  # positioning start 1 day before
                "EndTime": (start_time + timedelta(days=time_window_days)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        },
        # ====================== Bruce ======================
        
        "Description": "DOE Run #11 with Weather disruption",
    }

    filename = f"scenario_{arrival_rate}_{geo_density}_{tail_scale}_{maintenance_cycle}.json"
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
experiments = [
    {"arrival_rate": "low", "substitutes": 0, "tail_scale": "low", "geo_density": "high", "hub_pattern": "fly_out", "time_window_days": 1, "weather": True, "event": False, "maintenance_cycle": "low"},
    {"arrival_rate": "high", "substitutes": 1, "tail_scale": "high", "geo_density": "low", "hub_pattern": "fly_in", "time_window_days": 1, "weather": False, "event": True, "maintenance_cycle": "high"},
]

for exp in experiments:
    generate_scenario(**exp)
    print("--------------------------------------------------")