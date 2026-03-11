import json
import pandas as pd
from pathlib import Path

# =========================
# Config
# =========================
# INPUT_JSON = Path("formatted_021826.json")
INPUT_JSON = Path("RealData/schedule_LikeOrUpgrade02-18-2026Input.json")
output_file = "OD_total_0218_undirected.csv"

# OUTPUT_XLSX = Path("OD_by_date_revenue_only_0218.xlsx")

TIME_COL = "RequestedTime"
DEP_COL = "DepartureAirport"
ARR_COL = "ArrivalAirport"
ACT_COL = "ActivityType"

# =========================
# Load JSON
# =========================
with open(INPUT_JSON, "r", encoding="utf-16") as f:
    data = json.load(f)

df = pd.DataFrame(data["FlightRequests"])

# =========================
# 1) Filter revenue flights
# =========================
if ACT_COL not in df.columns:
    raise KeyError(f"Column '{ACT_COL}' not found in FlightRequests")

df = df[df[ACT_COL] == "OPERATE_REVENUE_FLIGHT"].copy()
print("Total revenue reservations:", len(df))

# =========================
# 2) Required columns check
# =========================
missing_cols = [c for c in [TIME_COL, DEP_COL, ARR_COL] if c not in df.columns]
if missing_cols:
    raise KeyError(f"Missing required columns: {missing_cols}")

# =========================
# 3) Parse time + create Date
# =========================
df[TIME_COL] = pd.to_datetime(df[TIME_COL], errors="coerce")
bad_time = df[TIME_COL].isna().sum()
if bad_time > 0:
    print(f"[Warning] {bad_time} rows have invalid {TIME_COL} and will be dropped.")
df = df.dropna(subset=[TIME_COL])

df["Date"] = df[TIME_COL].dt.date

# =========================
# 4) Group by Date + OD
# =========================
od_by_date = (
    df.groupby(["Date", DEP_COL, ARR_COL])
      .size()
      .reset_index(name="ReservationCount")
      .sort_values(["Date", "ReservationCount"], ascending=[True, False])
)

print("Date range:", od_by_date["Date"].min(), "to", od_by_date["Date"].max())
print("Total OD-Date combinations:", len(od_by_date))

# =========================
# 5) Daily summary
# =========================
daily_summary = (
    df.groupby("Date")
      .size()
      .reset_index(name="TotalReservations")
      .sort_values("Date")
)

# =========================
# 6) OD total (ignore Date)
#    IMPORTANT: sum ReservationCount across dates
# =========================
od_total = (
    od_by_date.groupby([DEP_COL, ARR_COL])["ReservationCount"]
      .sum()
      .reset_index(name="TotalReservations")
      .sort_values("TotalReservations", ascending=False)
)

print("Total unique OD pairs (ignore Date):", len(od_total))

# =========================
# 7) Export to Excel (3 sheets)
# =========================
# with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as writer:
#     od_by_date.to_excel(writer, sheet_name="OD_by_date", index=False)
#     daily_summary.to_excel(writer, sheet_name="Daily_summary", index=False)
#     od_total.to_excel(writer, sheet_name="OD_total_no_date", index=False)

# print(f"✅ Excel exported: {OUTPUT_XLSX.resolve()}")


od_total.to_csv(output_file, index=False, encoding="utf-8")
print(f"✅ CSV exported: {Path(output_file).resolve()}")