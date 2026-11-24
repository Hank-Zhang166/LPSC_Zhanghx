"""Partially identify the historical ordering under bounded multiplicative perturbations.

The factor is a user-specified stress radius, not an estimated batch error or
confidence level. Every point may vary independently within [value/f, value*f].
"""
import csv
import math
from itertools import combinations
from pathlib import Path


HERE = Path(__file__).resolve().parent


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def calculate(points, factors):
    ranked = sorted(points, key=lambda p: -p[1])
    if len({item[0] for item in ranked}) != len(ranked):
        raise ValueError("Composition IDs must be unique")
    pairs = []
    for (a, high), (b, low) in combinations(ranked, 2):
        if low <= 0:
            raise ValueError("Conductivity must be positive")
        pairs.append({"higher_x": a, "lower_x": b, "nominal_ratio": high / low,
                      "first_overlap_factor": math.sqrt(high / low)})
    rows = []
    for factor in factors:
        if factor < 1:
            raise ValueError("Multiplicative radius must be at least one")
        forced = sum(pair["first_overlap_factor"] > factor for pair in pairs)
        possible = [x for x, value in ranked if value * factor >= ranked[0][1] / factor]
        rows.append({"factor": factor, "forced_directions": forced,
                     "overlapping_directions": len(pairs) - forced,
                     "possible_maxima_x": ", ".join(possible)})
    return pairs, rows


def main():
    with (HERE / "mo_s1.csv").open(encoding="utf-8-sig") as source:
        points = [(row["x"], float(row["sigma_mS_cm"])) for row in csv.DictReader(source)]
    pairs, rows = calculate(points, [1, 1.02, 1.05, 1.10, 1.15, 1.20])
    assert len(pairs) == 21 and rows[0]["forced_directions"] == 21
    check, at_touch = calculate([("A", 4.0), ("B", 1.0)], [1.99, 2, 2.01])
    assert check[0]["first_overlap_factor"] == 2
    assert [r["forced_directions"] for r in at_touch] == [1, 0, 0]
    write_csv(HERE / "ordering_margins.csv", pairs)
    write_csv(HERE / "ordering_stress.csv", rows)


if __name__ == "__main__":
    main()
