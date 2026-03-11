import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timezone
from pathlib import Path

# =========================
# Config
# =========================
INPUT_DIR = Path("TestCases/DOE_FilterAirport")
INPUT_FILES = sorted(INPUT_DIR.glob("DOE_run*.json"))
OUTPUT_DIR = Path("hourly_counts_output")
OUTPUT_DIR.mkdir(exist_ok=True)

TIME_COL = "RequestedTime"
ACT_COL = "ActivityType"
REVENUE_TYPE = "OPERATE_REVENUE_FLIGHT"
INPUT_ENCODING = "utf-8"

# =========================
# Helper: parse datetime to UTC (robust)
# =========================
def parse_dt_utc(s: str):
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None

# =========================
# Process one file
# =========================
def process_file(input_file: Path):
    print(f"\n===== Processing {input_file.name} =====")

    with open(input_file, "r", encoding=INPUT_ENCODING) as f:
        data = json.load(f)

    flight_requests = data.get("FlightRequests", [])

    # =========================
    # Planning horizon
    # =========================
    ph = data.get("Configuration", {}).get("PlanningHorizon", {})
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
    # Filter + collect RequestedTime
    # =========================
    times = []
    bad_time = 0
    kept = 0

    for r in flight_requests:
        if r.get(ACT_COL) != REVENUE_TYPE:
            continue

        rt = parse_dt_utc(r.get(TIME_COL))
        if rt is None:
            bad_time += 1
            continue

        if begin_dt <= rt <= end_dt:
            times.append(rt)
            kept += 1

    print("Revenue requests kept within horizon:", kept)
    print("Bad RequestedTime dropped:", bad_time)

    if not times:
        print(f"⚠️ No reservations found within PlanningHorizon for {input_file.name}")
        return

    # =========================
    # Build hourly bins
    # =========================
    s = pd.Series(pd.to_datetime(times))
    s_hour = s.dt.floor("H")

    hour_index = pd.date_range(
        start=pd.to_datetime(begin_dt).floor("H"),
        end=pd.to_datetime(end_dt).floor("H"),
        freq="H",
        tz="UTC"
    )

    hour_counts = s_hour.value_counts().reindex(hour_index, fill_value=0).sort_index()

    # =========================
    # Export CSV
    # =========================
    output_csv = OUTPUT_DIR / f"hourly_reservation_counts_{input_file.stem}.csv"

    hour_counts_df = pd.DataFrame({
        "Hour": hour_counts.index.astype(str),
        "ReservationCount": hour_counts.values
    })

    hour_counts_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"✅ CSV exported: {output_csv}")

    # =========================
    # Plot hourly distribution
    # =========================
    plt.figure(figsize=(14, 5))
    plt.bar(hour_counts.index.astype(str), hour_counts.values)
    plt.title(f"Hourly Reservation Distribution (Revenue Only)\n{begin_str} to {end_str}")
    plt.xlabel("Hour (UTC)")
    plt.ylabel("Number of Reservations")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    output_png = OUTPUT_DIR / f"hourly_reservation_counts_{input_file.stem}.png"
    plt.savefig(output_png, dpi=150)
    plt.close()

    print(f"✅ Plot saved: {output_png}")

    # =========================
    # Peak hour info
    # =========================
    peak_hour = hour_counts.idxmax()
    peak_value = int(hour_counts.max())
    print(f"Peak hour (UTC): {peak_hour} with {peak_value} reservations")

# =========================
# Main loop
# =========================
if not INPUT_FILES:
    raise FileNotFoundError(f"No files found in {INPUT_DIR} matching DOE_run*.json")

for file_path in INPUT_FILES:
    process_file(file_path)

print("\n🎉 All files processed.")