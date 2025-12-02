import json
from collections import Counter
import os

INPUT = "schedule_sanitized.json"

def normalize_allowed(allowed):
    # Represent AllowedTailTypes as tuple of (AircraftTypeName, Penalty) for stable hashing
    if not allowed:
        return ()
    return tuple((a.get('AircraftTypeName'), a.get('Penalty')) for a in allowed)


def main():
    if not os.path.exists(INPUT):
        print(f"File not found: {INPUT}")
        return

    with open(INPUT, 'r', encoding='utf-8') as f:
        j = json.load(f)

    fr = j.get('FlightRequests') or []
    counter = Counter()
    examples = {}
    total = 0
    for r in fr:
        if r.get('requestedAircraftTypeName') == 'CE-680AS':
            total += 1
            allowed = r.get('AllowedTailTypes')
            key = normalize_allowed(allowed)
            counter[key] += 1
            if key not in examples:
                examples[key] = allowed

    print(f"Found {total} FlightRequests with requestedAircraftTypeName == 'CE-680AS'\n")
    if total == 0:
        return

    print("Distinct AllowedTailTypes combinations and counts:\n")
    for key, cnt in counter.most_common():
        print(f"Count: {cnt}")
        # pretty print the example
        print(json.dumps(examples[key], indent=2))
        print('-' * 60)

    # Also print a flattened set of AircraftTypeNames seen in AllowedTailTypes
    types = Counter()
    for key in counter:
        for name, penalty in key:
            types[name] += counter[key]
    print('\nAggregated Allowed AircraftTypeName frequencies:')
    for t, c in types.most_common():
        print(f"{t}: {c}")

if __name__ == '__main__':
    main()
