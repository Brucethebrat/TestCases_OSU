import sys
import json
from datetime import datetime, timedelta


def parse(input_str):
    return datetime.strptime(input_str, "%Y-%m-%dT%H:%M:%SZ")


schedule_file = [
    "./RealData/schedule_LikeOrUpgrade02-18-2026Input.json",
    # "./RealData/schedule_LikeOrUpgrade02-16-2026Input.json",
    # "./RealData/schedule_sanitized.json"
]

def get_airport_pool(schedule_file=schedule_file):

    ac_type_names = ["CE-680AS", "GL5000S", "CE-700", "CL-650S", "CL-350S", "CE-680", "CE-560XLS", "EMB-505S", "EMB-505E", "EMB-545-MOD", "GL6000S", "GL7500", "GL5500"]

    fleet_seed_airports = set()

    for file in schedule_file:    
        with open(file, "r", encoding="utf-8") as f:
            fullFile = json.loads(f.read())
        
        
        config = fullFile["Configuration"]
        start_planning = config['PlanningHorizon']["BeginTime"]
        end_planning = config['PlanningHorizon']["EndTime"]    
        
        
        print(f"[+] Scheduling {start_planning} to {end_planning}.")
        # start_positioning = parse(start_positioning)
        start_planning = parse(start_planning)
        end_planning = parse(end_planning)



        if type(fullFile) == list:
            flightRequests = fullFile
        else:
            flightRequests = fullFile["FlightRequests"]
        revenue_flight_requests = []
        mx_flight_requests = []
        for fr in flightRequests:
            if fr["ActivityType"] == "OPERATE_REVENUE_FLIGHT":
                revenue_flight_requests += [fr]
            if fr["ActivityType"] == "MAINTENANCE":
                mx_flight_requests += [fr]

        # request_type_counter = {}
        # on_fleet_mx_flight_requests = []
        # rev_flight_requests = []
        # fleet_seed_airports = set()
        for rev_fr in revenue_flight_requests:
            # if rev_fr["requestedAircraftTypeName"] not in request_type_counter.keys():
            #     request_type_counter[rev_fr["requestedAircraftTypeName"]] = 1
            # else:
            #     request_type_counter[rev_fr["requestedAircraftTypeName"]] += 1
            request_time = parse(rev_fr["RequestedTime"])
            if request_time >= start_planning and request_time <= end_planning and (rev_fr["requestedAircraftTypeName"] in ac_type_names):
                found = False
                for allowed_type in rev_fr["AllowedTailTypes"]:
                    if allowed_type["AircraftTypeName"] in ac_type_names:
                        found = True
                if found:
                    # rev_flight_requests += [rev_fr]
                    fleet_seed_airports |= {rev_fr["ArrivalAirport"]}
                    fleet_seed_airports |= {rev_fr["DepartureAirport"]}

        for mx_fr in mx_flight_requests:
            try:
                request_time = parse(mx_fr["RequestedTime"])
                if request_time >= start_planning and request_time <= end_planning and mx_fr["AllowedTailTypes"][0]["AircraftTypeName"] in ac_type_names:
                    # on_fleet_mx_flight_requests += [mx_fr]
                    fleet_seed_airports |= {mx_fr["ArrivalAirport"]}
            except:
                for key in mx_fr:
                    #print(key)
                    pass
                sys.exit()

    return fleet_seed_airports

if __name__ == "__main__":
    print(get_airport_pool())
    print(f"Total number of airports in the pool: {len(get_airport_pool())}")