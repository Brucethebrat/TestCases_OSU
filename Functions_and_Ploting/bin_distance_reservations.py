# ========================================
# This script reads a CSV file containing distance and total reservation data, 
# bins the distances into specified intervals, sums the reservations for each bin, 
# and plots the results.
# ========================================

import csv
import math
from collections import defaultdict

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

# INPUT_CSV = "RealData/OD_total_0218_undirected_with_distance.csv"
ith_run = 1
root_path = f"TestCases/DOE_Jacob_list/distance/"
INPUT_CSV = f"{root_path}DOE_run{ith_run}_long_route_counts.csv"
BIN_SIZE = 100
PLOT_FILE = f"{root_path}distance_bin_DOE_run{ith_run}_long.png"


def load_bins(filename, bin_size=100):
    bins = defaultdict(int)
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                distance = float(row['Distance'])
                reservations = int(row['TotalReservations'])
            except (ValueError, KeyError):
                continue

            bin_index = int(math.floor(distance / bin_size))
            bins[bin_index] += reservations

    return bins


def format_bin_name(bin_index, bin_size):
    start = bin_index * bin_size
    end = start + bin_size
    return f"{start}-{end}"


def plot_bins(bins, bin_size, output_file=None):
    if plt is None:
        print("matplotlib is not installed. Install it with 'pip install matplotlib' to enable plotting.")
        return

    indices = sorted(bins)
    widths = bin_size
    starts = [bin_index * bin_size for bin_index in indices]
    values = [bins[bin_index] for bin_index in indices]
    labels = [format_bin_name(bin_index, bin_size) for bin_index in indices]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(starts, values, width=widths, align='edge', edgecolor='black')
    ax.set_xlabel('Distance range')
    ax.set_ylabel('Total reservations')
    ax.set_title(f'Total reservations by {bin_size}-unit distance bin')
    ax.set_xticks(starts)
    ax.set_xticklabels(labels, rotation=90, fontsize=8)
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    plt.tight_layout()

    if output_file:
        fig.savefig(output_file)
        print(f"Saved plot to {output_file}")

    plt.show()


def main():
    bins = load_bins(INPUT_CSV, BIN_SIZE)
    print(f"Distance bins of size {BIN_SIZE}, total reservations per bin:\n")
    for bin_index in sorted(bins):
        print(f"{format_bin_name(bin_index, BIN_SIZE)}: {bins[bin_index]}")

    plot_bins(bins, BIN_SIZE, output_file=PLOT_FILE)


if __name__ == '__main__':
    main()
