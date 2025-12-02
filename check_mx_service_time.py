import json
from collections import Counter
from statistics import mean, median
import math
import os

INPUT = "schedule_sanitized.json"  # adjust path if needed

def percentile(sorted_vals, p):
    if not sorted_vals:
        return None
    k = (len(sorted_vals)-1) * (p/100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    d0 = sorted_vals[int(f)] * (c-k)
    d1 = sorted_vals[int(c)] * (k-f)
    return d0 + d1

def bucket_hist(values, bins):
    # bins: list of upper bounds (inclusive); last can be None for open-ended
    counter = Counter()
    for v in values:
        placed = False
        for upper in bins:
            if upper is None:
                counter[f">{bins[-2]}"] += 1
                placed = True
                break
            if v <= upper:
                counter[f"<= {upper}"] += 1
                placed = True
                break
        if not placed:
            counter["unbinned"] += 1
    return counter

def main():
    if not os.path.exists(INPUT):
        print(f"File not found: {INPUT}")
        return

    with open(INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)

    fr = data.get("FlightRequests") or data.get("FlightRequests", [])

    # Extract ServiceTime for maintenance ActivityType
    servicetimes = []
    for r in fr:
        if r.get("ActivityType") == "MAINTENANCE":
            st = r.get("ServiceTime")
            # If missing or null, treat as 0 (or skip based on your preference)
            if st is None:
                st = 0
            try:
                st = int(st)
            except Exception:
                continue
            servicetimes.append(st)

    total = len(servicetimes)
    if total == 0:
        print("No MAINTENANCE FlightRequests with ServiceTime found.")
        return

    servicetimes_sorted = sorted(servicetimes)
    stats = {
        "count": total,
        "min": servicetimes_sorted[0],
        "max": servicetimes_sorted[-1],
        "mean": mean(servicetimes_sorted),
        "median": median(servicetimes_sorted),
        "p10": percentile(servicetimes_sorted, 10),
        "p25": percentile(servicetimes_sorted, 25),
        "p75": percentile(servicetimes_sorted, 75),
        "p90": percentile(servicetimes_sorted, 90),
    }

    print("ServiceTime (minutes) distribution for ActivityType == 'MAINTENANCE'")
    print("-" * 60)
    for k, v in stats.items():
        print(f"{k:6}: {v}")
    print("-" * 60)

    # Histogram buckets (minutes). Adjust bins as needed.
    bins = [60, 240, 720, 1440, None]  # <=1h, <=4h, <=12h, <=24h, >24h
    hist = bucket_hist(servicetimes_sorted, bins)
    print("Histogram (minutes):")
    for b in ["<= 60", "<= 240", "<= 720", "<= 1440", f">{bins[-2]}" if bins[-1] is None else "<= ???"]:
        print(f"{b:10}: {hist.get(b, 0)}")
    print("-" * 60)

    # Optional: print top 10 most common exact ServiceTime values
    freq = Counter(servicetimes_sorted)
    print("Top 10 most common ServiceTime values (minutes):")
    for val, cnt in freq.most_common(10):
        print(f"{val:6} min : {cnt}")
    print("-" * 60)

if __name__ == "__main__":
    main()