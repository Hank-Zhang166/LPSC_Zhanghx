"""Inspect a single independent Bath file in a bounded HTTP prefix, without storing the 44 GB archive.

Run: python audit_bath_prefix.py
Writes the result to stdout. The XML stresses follow VASP conventions and need conversion before training.
"""
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import io
import json
import tarfile
import urllib.request
import xml.etree.ElementTree as ET
import zlib

URL = "https://researchdata.bath.ac.uk/814/2/argyrodite_MD.tar.gz"
BLOCK = 4 * 1024**2
COUNT = 15


def download(i):
    left, right = i * BLOCK, (i + 1) * BLOCK - 1
    for attempt in range(3):
        try:
            req = urllib.request.Request(f"{URL}?p9slice={i}&trial={attempt}",
                    headers={"Range":f"bytes={left}-{right}", "User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=24) as resp:
                if resp.status != 206 or not resp.headers["Content-Range"].startswith(f"bytes {left}-{right}/"):
                    raise ValueError("Server did not honor the requested range")
                value = resp.read(BLOCK)
            if len(value) != BLOCK:
                raise ValueError("Truncated HTTP range")
            return value
        except (OSError, ValueError):
            if attempt == 2:
                raise


def main():
    with ThreadPoolExecutor(max_workers=4) as pool:
        data = b"".join(pool.map(download, range(COUNT)))
    tar_prefix = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(data)
    with tarfile.open(fileobj=io.BytesIO(tar_prefix), mode="r|") as tar:
        for member in tar:
            if not member.name.endswith("quench/config_2050/vasprun.xml.gz"):
                continue
            compressed = tar.extractfile(member).read()
            xml = ET.fromstring(gzip.decompress(compressed))
            steps = xml.findall("calculation")
            seen = {"ionic_steps": len(steps)}
            for key in ("forces", "stress"):
                arrays = [step.find(f"varray[@name='{key}']") for step in steps]
                seen[key + "_steps"] = sum(v is not None for v in arrays)
                first = next(v for v in arrays if v is not None)
                seen[key + "_first_shape"] = [len(first), len(first[0].text.split())]
            seen["energy_steps"] = sum(c.find("energy/i[@name='e_fr_energy']") is not None for c in steps)
            xc = xml.find(".//i[@name='GGA']")
            result = dict(source=URL, inclusive_bytes=[0,len(data)-1],
                   partial_archive_sha256=hashlib.sha256(data).hexdigest(),
                   complete_member=member.name, member_size=member.size,
                   compressed_member_sha256=hashlib.sha256(compressed).hexdigest(),
                   dft_GGA_tag=(xc.text or "").strip() if xc is not None else None, counts=seen)
            print(json.dumps(result, indent=2))
            return
    raise RuntimeError("Expected complete member not found in archive prefix")


if __name__ == "__main__":
    main()
