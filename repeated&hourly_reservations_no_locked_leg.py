import json
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
FILES = [
    "./RealData/schedule_LikeOrUpgrade02-18-2026Input.json",
]
output_file = "./RealData/OD_total_0218_undirected_locked_filtered.csv"
TIME_COL = "RequestedTime"
DEP_COL = "DepartureAirport"
ARR_COL = "ArrivalAirport"
ACT_COL = "ActivityType"
REQ_COL = "RequestID"
all_data = []

# =========================
# Function: safe JSON reader
# =========================
def load_json_auto_encoding(file_name):
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            return json.load(f)
    except UnicodeDecodeError:
        with open(file_name, "r", encoding="utf-16") as f:
            return json.load(f)

# =========================
# Build locked_legs_by_start_time
# following schedule_maker logic style
# =========================
def build_locked_legs_by_start_time(data):
    locked_legs_by_start_time = defaultdict(list)
    locked_legs_by_tail = defaultdict(list)
    last_locked_time_by_tail = {}
    legs = data.get("Legs", [])
    # Step 1: find last locked time for each tail
    for leg in legs:
        tail = leg.get("TailNumber")
        start_time = leg.get("StartTime")
        duration = leg.get("Duration", 0)
        if tail is None or start_time is None:
            continue
        if leg.get("IsLocked", False):
            leg_start_dt = pd.to_datetime(start_time)
            leg_end_dt = leg_start_dt + pd.Timedelta(minutes=duration)
            if tail not in last_locked_time_by_tail or leg_end_dt > last_locked_time_by_tail[tail]:
                last_locked_time_by_tail[tail] = leg_end_dt
    # Step 2: mimic driver lock_legs logic
    for leg in legs:
        tail = leg.get("TailNumber")
        start_time = leg.get("StartTime")
        if tail is None or start_time is None:
            continue
        leg_start_dt = pd.to_datetime(start_time)
        if leg.get("IsLocked", False):
            locked_legs_by_start_time[start_time].append(leg)
            locked_legs_by_tail[tail].append(leg)
        elif tail in last_locked_time_by_tail and leg_start_dt < last_locked_time_by_tail[tail]:
            locked_legs_by_start_time[start_time].append(leg)
            locked_legs_by_tail[tail].append(leg)
    return locked_legs_by_start_time

# =========================
# Check whether a request should be skipped
# using the same matching logic as schedule_maker
# =========================
def is_locked_request(res, locked_legs_by_start_time):
    req_time = res.get("RequestedTime")
    if req_time not in locked_legs_by_start_time:
        return False
    for locked_leg in locked_legs_by_start_time[req_time]:
        if (
            res.get("DepartureAirport") == locked_leg.get("OriginAirport")
            and res.get("ArrivalAirport") == locked_leg.get("DestinationAirport")
            and res.get("RequestID") == locked_leg.get("RequestID")
        ):
            return True
    return False

# =========================
# 1) Load all files
# =========================
for file_name in FILES:
    print(f"Reading {file_name}...")
    data = load_json_auto_encoding(file_name)
    ac_type_names = {
        "CE-680AS", "GL5000S", "CE-700", "CL-3500", "CL-650S", "CL-350S",
        "CE-680", "CE-560XLS", "EMB-505S", "EMB-505E", "EMB-545-MOD",
        "GL6000S", "GL7500", "GL5500"
    }
    # build locked leg lookup from Legs
    locked_legs_by_start_time = build_locked_legs_by_start_time(data)
    df = pd.DataFrame(data["FlightRequests"])
    # filter revenue only
    df = df[df[ACT_COL] == "OPERATE_REVENUE_FLIGHT"].copy()
    # =========================
    # mimic schedule_maker time window filtering
    # =========================
    start_planning = "2026-02-17T17:00:00Z"
    end_planning = "2026-02-19T07:59:00Z"
    df = df[
        (df[TIME_COL] >= start_planning) &
        (df[TIME_COL] <= end_planning)
    ].copy()
    def request_matches_scheduler_fleet_rules(res):
        requested_type = res.get("requestedAircraftTypeName")
        if requested_type not in ac_type_names:
            return False
        allowed_tail_types = res.get("AllowedTailTypes", [])
        found = False
        for allowed_type in allowed_tail_types:
            if allowed_type.get("AircraftTypeName") in ac_type_names:
                found = True
                break
        return found
    df = df[df.apply(lambda row: request_matches_scheduler_fleet_rules(row.to_dict()), axis=1)].copy()
    before_count = len(df)
    # apply schedule_maker-style filtering
    keep_mask = []
    skipped_records = []
    for _, row in df.iterrows():
        res = row.to_dict()
        if is_locked_request(res, locked_legs_by_start_time):
            skipped_records.append({
                "RequestID": res.get("RequestID"),
                "RequestedTime": res.get("RequestedTime"),
                "DepartureAirport": res.get("DepartureAirport"),
                "ArrivalAirport": res.get("ArrivalAirport"),
            })
            keep_mask.append(False)
        else:
            keep_mask.append(True)
    df = df[keep_mask].copy()
    after_count = len(df)
    print(f"Revenue requests before locked-leg filter: {before_count}")
    print(f"Revenue requests after locked-leg filter:  {after_count}")
    print(f"Skipped locked-leg requests:              {before_count - after_count}")
    if skipped_records:
        skipped_df = pd.DataFrame(skipped_records)
        skipped_output = "./RealData/skipped_locked_leg_requests_0218.csv"
        skipped_df.to_csv(skipped_output, index=False, encoding="utf-8")
        print(f"Saved skipped locked-leg requests to: {skipped_output}")
    all_data.append(df)

# =========================
# Combine all
# =========================
df_all = pd.concat(all_data, ignore_index=True)
print("Total revenue reservations after locked-leg filter:", len(df_all))

# =========================
# Hourly reservation counts after locked-leg filter
# =========================
df_all["RequestedTime_dt"] = pd.to_datetime(df_all[TIME_COL], utc=True)
df_all["Hour"] = df_all["RequestedTime_dt"].dt.floor("h")

hourly_counts = (
    df_all.groupby("Hour")
    .size()
    .reset_index(name="ReservationCount")
    .sort_values("Hour")
)

hourly_counts["Hour"] = hourly_counts["Hour"].astype(str)

hourly_output_file = "./RealData/hourly_reservation_counts_021826_no_locked_leg.csv"
hourly_counts.to_csv(hourly_output_file, index=False, encoding="utf-8-sig")

print(f"✅ Exported hourly counts after locked-leg filter to {hourly_output_file}")
print(hourly_counts.head(10))

# =========================
# 2) Undirected OD
# =========================
df_all["OD_pair"] = df_all.apply(
    lambda x: tuple(sorted([x[DEP_COL], x[ARR_COL]])),
    axis=1
)

# =========================
# 3) Aggregate (ignore direction & date)
# =========================
od_total = (
    df_all.groupby("OD_pair")
    .size()
    .reset_index(name="TotalReservations")
    .sort_values("TotalReservations", ascending=False)
)
# split tuple back
od_total[["Airport1", "Airport2"]] = pd.DataFrame(
    od_total["OD_pair"].tolist(),
    index=od_total.index
)
od_total = od_total[["Airport1", "Airport2", "TotalReservations"]]

# =========================
# 4) Single vs Repeated counts (corridor-level)
# =========================
single_corridors = (od_total["TotalReservations"] == 1).sum()
repeated_corridors = (od_total["TotalReservations"] >= 2).sum()
total_corridors = len(od_total)
print("Unique undirected corridors:", total_corridors)
print("Single corridors:", single_corridors)
print("Repeated corridors:", repeated_corridors)
print("Repeated share:", repeated_corridors / total_corridors if total_corridors else 0)

# =========================
# 5) Plot: Single vs Repeated ratio
# =========================
ratio_df = pd.DataFrame(
    {"Single": [single_corridors], "Repeated": [repeated_corridors]},
    index=["Locked-filtered (undirected)"]
)
ratio_share = ratio_df.div(ratio_df.sum(axis=1), axis=0)
ax = ratio_share.plot(kind="bar", stacked=True)
ax.set_title("Single vs Repeated Corridors (Undirected, Locked Requests Filtered)")
ax.set_xlabel("")
ax.set_ylabel("Share of Corridors")
plt.xticks(rotation=0)
plt.tight_layout()
plt.show()
plt.figure()
plt.pie(
    [single_corridors, repeated_corridors],
    labels=["Single", "Repeated"],
    autopct="%1.1f%%"
)
plt.title("Single vs Repeated Corridors (Undirected, Locked Requests Filtered)")
plt.tight_layout()
plt.show()

# =========================
# 6) Export to CSV
# =========================
od_total.to_csv(output_file, index=False, encoding="utf-8")
print(f"\n✅ Exported to {output_file}")
