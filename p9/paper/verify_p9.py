"""Cross-check official documents against data, links and one speaker script."""
import csv
import json
import math
import re
import unicodedata
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"


def data(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def compact(value):
    value = unicodedata.normalize("NFKC", value)
    return "".join(value.split())


def tex(el, namespace):
    return "".join(child.text or "" for child in el.iter(namespace + "t"))


def main():
    manuscript = (HERE / "开题报告_P9_文稿.md").read_text(encoding="utf-8")
    split = manuscript.split("## 参考文献\n", 1)
    ids = list(dict.fromkeys(int(x) for group in re.findall(r"\[([1-9]\d*(?:,\d+)*)\]", split[0])
                           for x in group.split(",")))
    bibliography = [int(x) for x in re.findall(r"(?m)^\[(\d+)\]", split[1])]
    assert ids == bibliography == list(range(1, len(bibliography) + 1))
    figures = re.findall(r"!\[(图 \d+\.\d+)　[^\n]+\]\(([^)]+)\)", manuscript)
    assert len(figures) == len({k for k, _ in figures}) >= 12
    assert all((ROOT / rel).is_file() for _, rel in figures)
    assert not re.search(r"@(RESULTS|REFERENCES|RANK_CASE|EVIDENCE|DES_CASE|LITERATURE)", manuscript)
    with ZipFile(HERE / "开题报告_P9.docx") as z:
        assert z.testzip() is None
        doc = ET.fromstring(z.read("word/document.xml"))
        biblio = {x.get(W+"name") for x in doc.iter(W+"bookmarkStart")}
        assert {f"Biblio{i}" for i in ids} <= biblio
        assert all(el.get(W+"anchor") in biblio for el in doc.iter(W+"hyperlink") if el.get(W+"anchor"))
    report = PdfReader(HERE / "开题报告_P9.pdf")
    assert len(report.pages) > 32
    text = compact("".join(p.extract_text() for p in report.pages))
    assert all(compact(t) in text for t in ("第 1 章", "七组成", "481184", "48.15", "0.4", "附录 A"))

    speakers = json.loads((HERE / "speaker_script.json").read_text(encoding="utf-8"))
    slides = PdfReader(HERE / "汇报版开题报告_P9.pdf")
    assert len(slides.pages) == len(speakers) == 22
    with ZipFile(HERE / "P9_逐页汇报词.docx") as z:
        assert z.testzip() is None
        notes = compact(tex(ET.fromstring(z.read("word/document.xml")), W))
    with ZipFile(HERE / "汇报版开题报告_P9.pptx") as z:
        assert z.testzip() is None
        for page, entry in enumerate(speakers, 1):
            assert entry["page"] == page
            assert compact(entry["title"]) in compact(slides.pages[page-1].extract_text())
            assert compact(entry["speech"]) in notes
            slide_notes = ET.fromstring(z.read(f"ppt/notesSlides/notesSlide{page}.xml"))
            note_shape = next(s for s in slide_notes.iter(P+"sp")
                              if s.find(f".//{P}ph[@type='body']") is not None)
            assert compact(tex(note_shape, A)) == compact(entry["speech"])
    mo = data(ROOT / "p9/evidence/mo_s1.csv")
    assert [float(r["x"]) for r in mo] == [i/10 for i in range(7)]
    assert [float(r["sigma_mS_cm"]) for r in mo] == [3.7, 4.1, 4.6, 5.1, 8.2, 5.9, 4.2]
    pairs = [r for r in data(ROOT / "p9/ranking/outputs/pairwise.csv")
             if r["method"] == "bme" and r["primary_delta"] == "true"]
    assert len(pairs) == 49
    assert all(r["synthetic_only"] == "true" and
               math.isclose(sum(float(r[key]) for key in ("p_plus", "p_minus", "p_tie")), 1)
               for r in pairs)
    samples = data(ROOT / "p9/protocol/powders.csv")
    assert len({r["powder_id"] for r in samples}) == 18
    assert all(r["status"] == "planned" for r in samples)
    print(f"PASS {len(report.pages)} written pages, {len(figures)} report figures, {len(bibliography)} "
          f"cited references, {len(slides.pages)} matching slides and notes, 49 synthetic probabilities.")


if __name__ == "__main__":
    main()
