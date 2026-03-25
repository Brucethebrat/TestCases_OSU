import json
import pandas as pd
import matplotlib.pyplot as plt

FILES = [
#    "schedule_sanitized.json",
#    "formatted_021626.json",
    # "formatted_021826.json"
    # "./RealData/schedule_LikeOrUpgrade02-18-2026Input.json",
    "./RealData/schedule_LikeOrUpgrade02-16-2026Input.json",
]

# output_file = "./RealData/OD_total_0218_undirected.csv"
output_file = "./RealData/OD_total_0216_undirected.csv"


TIME_COL = "RequestedTime"
DEP_COL = "DepartureAirport"
ARR_COL = "ArrivalAirport"
ACT_COL = "ActivityType"

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
# 1) Load all files
# =========================
for file_name in FILES:
    print(f"Reading {file_name}...")

    data = load_json_auto_encoding(file_name)
    df = pd.DataFrame(data["FlightRequests"])

    # Filter revenue only
    df = df[df[ACT_COL] == "OPERATE_REVENUE_FLIGHT"].copy()

    all_data.append(df)

# Combine all
df_all = pd.concat(all_data, ignore_index=True)
print("Total revenue reservations (3 files combined):", len(df_all))

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

# Split tuple back (for export / readability)
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
    index=["All 3 days (undirected)"]
)

ratio_share = ratio_df.div(ratio_df.sum(axis=1), axis=0)

ax = ratio_share.plot(kind="bar", stacked=True)
ax.set_title("Single vs Repeated Corridors (Undirected, All Files Combined)")
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
plt.title("Single vs Repeated Corridors (Undirected)")
plt.tight_layout()
plt.show()

# =========================
# 6) Export to CSV
# =========================


od_total.to_csv(output_file, index=False, encoding="utf-8")

print(f"\n✅ Exported to {output_file}")