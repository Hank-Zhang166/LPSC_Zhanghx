"""Check the supplied source documents and reproduce mo_s1.csv in stdout.

python audit_mo_inputs.py PAPER.pdf SI.docx > mo_s1.csv
All other conductivity/activation-energy comparisons require the separately cited main-text checks.
"""
import argparse
import csv
import hashlib
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

PAPER_HASH = "cde4ab03c52d0cf1ef2327ef9b2e958560a0787cb71a3e52707e794c8f186c3a"
SUPP_HASH = "3c8621d928a9d4bb31badee1c69f6777fc48fc827115b03a9414b03113e73194"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paper", type=Path)
    parser.add_argument("supplement", type=Path)
    args = parser.parse_args()
    for path, expected in [(args.paper,PAPER_HASH),(args.supplement,SUPP_HASH)]:
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit(f"Source revision differs: {path.name}")
    with zipfile.ZipFile(args.supplement) as f:
        doc = ET.fromstring(f.read("word/document.xml"))
    ns = {"w":"http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    table = doc.find(".//w:tbl", ns)
    vals = [["".join(t.text or "" for t in c.findall(".//w:t",ns))
             for c in row.findall("w:tc",ns)] for row in table.findall("w:tr",ns)]
    if len(vals)!=8 or "mS" not in vals[0][1]:
        raise ValueError("Unexpected S1 structure")
    entries = vals[1:]
    descending = sorted((float(v) for _,v in entries),reverse=True)
    out = csv.writer(sys.stdout,lineterminator="\n")
    out.writerow(["x","formula","sigma_mS_cm","rank_desc","temperature_C","source","batch_uncertainty"])
    for i,(formula,v) in enumerate(entries):
        out.writerow([f"{i/10:.1f}",formula,v,descending.index(float(v))+1,25,
                     "Mo 2024 SI Table S1; main Fig.1","unreported"])


if __name__ == "__main__":
    main()
