"""Compute reference Li force magnitudes, weighting all Li atom occurrences alike.

Usage: python refs/oxford_force_profile.py path/to/datasets.zip
This is a reference-label distribution, with no model predictions.
"""
import collections
import hashlib
import json
import math
from pathlib import Path
import sys
import zipfile

from audit_public_files import formula


def quantile(sorted_values, probability):
    location = (len(sorted_values) - 1) * probability
    low = math.floor(location)
    high = math.ceil(location)
    return sorted_values[low] + (location - low) * (sorted_values[high] - sorted_values[low])


def main():
    values = collections.defaultdict(list)
    frame_counts = collections.Counter()
    digest = hashlib.sha256()
    member = "230923_PBEsol_28100.extxyz"
    with zipfile.ZipFile(Path(sys.argv[1])) as z, z.open(member) as stream:
        while first := stream.readline():
            header = stream.readline()
            if b"Properties=species:S:1:pos:R:3:forces:R:3" not in header:
                raise ValueError("Unexpected order of atomic columns")
            raw = [stream.readline() for _ in range(int(first))]
            digest.update(first + header + b"".join(raw))
            rows = [line.split() for line in raw]
            comp = formula(row[0].decode() for row in rows)
            frame_counts[comp] += 1
            for row in rows:
                if row[0] == b"Li":
                    f = math.hypot(*(float(c) for c in row[4:7]))
                    if not math.isfinite(f):
                        raise ValueError("Nonfinite force component")
                    values[comp].append(f)
    result = {}
    for comp, occurrences in values.items():
        occurrences.sort()
        result[comp] = dict(frames=frame_counts[comp], li_atom_occurrences=len(occurrences),
                 median=quantile(occurrences, 0.5), p90=quantile(occurrences, 0.9))
    print(json.dumps(dict(member=member, member_sha256=digest.hexdigest(),
          statistic="Per-occurrence Euclidean norm of reference forces; linear order-statistic interpolation",
          units="raw extxyz forces; conventional ASE interpretation eV/Angstrom; header has no explicit unit field",
          compositions=result), indent=2))


if __name__ == "__main__":
    main()
