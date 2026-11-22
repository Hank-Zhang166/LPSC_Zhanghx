"""Read original public archives in place. Python >=3.9, standard library only.

Each command prints JSON. Keep downloaded archives outside the research repository.
Manifest URLs and upstream checksums are in ../configs/dataset_manifest.csv.
"""
import argparse
import ast
import collections
import csv
import hashlib
import json
import math
import re
import tarfile
import zipfile
from pathlib import Path


def file_digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def formula(elements):
    counts = collections.Counter(elements)
    divisor = math.gcd(*counts.values())
    order = ["Li", "P", "S", "Cl", *sorted(set(counts) - {"Li", "P", "S", "Cl"})]
    return "".join(e + (str(counts[e] // divisor) if counts[e] // divisor > 1 else "")
                   for e in order if counts[e])


def oxford(path):
    target = "230923_PBEsol_28100.extxyz"
    formulations = collections.Counter()
    sizes = collections.Counter()
    keys = collections.Counter()
    distinct = set()
    with zipfile.ZipFile(path) as archive, archive.open(target) as stream:
        while line := stream.readline():
            n = int(line)
            header = stream.readline()
            keys.update(k.decode() for k in re.findall(br"(\w+)=", header))
            atoms = [stream.readline() for _ in range(n)]
            if not all(len(row.split()) == 7 for row in atoms):
                raise ValueError("Unexpected atom fields")
            formulations[formula(row.split(None, 1)[0].decode() for row in atoms)] += 1
            sizes[n] += 1
            distinct.add(hashlib.sha256(line + header + b"".join(atoms)).digest())
    return dict(member=target, frames=sum(sizes.values()), atom_counts=sizes,
                frames_by_reduced_formula=formulations, header_key_counts=keys,
                unique_full_frame_bytes=len(distinct))


def obelix(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    entries = []
    for row in rows:
        if set(re.findall("[A-Z][a-z]?", row["Reduced Composition"])) == {"Li", "P", "S", "Cl"}:
            entries.append({k:row[k] for k in ("ID","Reduced Composition","Ionic conductivity (S cm-1)",
                                               "IC (Total)","IC (Bulk)","Cif ID","close match","DOI")})
    return dict(rows=len(rows), cif_id=collections.Counter(r["Cif ID"] for r in rows),
                distinct_reduced_formula_strings=len(set(r["Reduced Composition"] for r in rows)),
                only_Li_P_S_Cl=entries)


def darus(path):
    unique = set()
    cfg_counts = {}
    with zipfile.ZipFile(path) as archive:
        for key in archive.namelist():
            if key.endswith("/training_set"):
                records = re.findall(br"BEGIN_CFG\s*(.*?)\s*END_CFG", archive.read(key), re.S)
                cfg_counts[key] = len(records)
                unique.update(hashlib.sha256(cfg).digest() for cfg in records)
    return dict(frames_in_each_file=cfg_counts, total_occurrences=sum(cfg_counts.values()),
                unique_identical_cfg_blocks=len(unique))


def numpy_shape(handle):
    if handle.read(6) != b"\x93NUMPY":
        raise ValueError("Invalid NumPy signature")
    major, _minor = handle.read(2)
    hlen = int.from_bytes(handle.read(2 if major == 1 else 4), "little")
    return ast.literal_eval(handle.read(hlen).decode("latin1").strip())["shape"]


def deepmd_archive(path):
    shapes = collections.defaultdict(dict)
    types = {}
    maps = {}

    def collect(name, handle):
        directory, _, leaf = name.rpartition("/")
        if leaf in ("type.raw", "type_map.raw"):
            mapping = maps if leaf == "type_map.raw" else types
            mapping[directory] = handle.read().decode().split()
        elif leaf in {"energy.npy","force.npy","coord.npy","box.npy","virial.npy"}:
            shapes[directory][leaf] = numpy_shape(handle)

    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if name.startswith("00.data/") and name.endswith((".npy",".raw")):
                    with archive.open(name) as handle:
                        collect(name, handle)
    else:
        with tarfile.open(path, "r|gz") as archive:
            for member in archive:
                if member.isfile() and member.name.endswith((".npy",".raw")):
                    with archive.extractfile(member) as handle:
                        collect(member.name, handle)
    groups = {}
    for name, files in shapes.items():
        if "energy.npy" not in files:
            continue
        group = "train" if "00.data/train-data/" in name else "validation" if "00.data/valid-data/" in name else "archive"
        stats = groups.setdefault(group, dict(sets=0, energy_frames=0, consistent_EF=0, consistent_EFV=0,
                     strict_4element_formula_frames=collections.Counter(), unique_reduced_formulas=set(),
                     distinct_elements=set()))
        n = files["energy.npy"][0]
        system = name.rsplit("/",1)[0]
        elements = [maps[system][int(idx)] for idx in types[system]]
        stats["sets"] += 1
        stats["energy_frames"] += n
        stats["consistent_EF"] += n * int(files.get("force.npy",(None,))[0] == n)
        stats["consistent_EFV"] += n * int(files.get("force.npy",(None,))[0] == n and files.get("virial.npy",(None,))[0] == n)
        fr = formula(elements)
        stats["unique_reduced_formulas"].add(fr)
        stats["distinct_elements"].update(elements)
        if set(elements) == {"Li","P","S","Cl"}:
            stats["strict_4element_formula_frames"][fr] += n
    for s in groups.values():
        s["unique_reduced_formulas"] = len(s["unique_reduced_formulas"])
        s["distinct_elements"] = sorted(s["distinct_elements"])
    return groups


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("kind", choices=["oxford", "obelix", "darus4510", "deepmd"])
    ap.add_argument("archive", type=Path)
    args = ap.parse_args()
    read = {"oxford": oxford, "obelix": obelix, "darus4510": darus, "deepmd": deepmd_archive}
    print(json.dumps({"sha256":file_digest(args.archive), "result":read[args.kind](args.archive)},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
