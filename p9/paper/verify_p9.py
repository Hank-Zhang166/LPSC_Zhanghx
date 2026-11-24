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
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
OUT = ROOT / "p9/交付稿"
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
    cited = []
    for group in re.findall(r"\[([1-9]\d*(?:[,–-][1-9]\d*)*)\]", split[0]):
        for item in group.split(","):
            nums = [int(n) for n in re.split(r"[–-]", item)]
            cited.extend(range(nums[0], nums[-1]+1))
    ids = list(dict.fromkeys(cited))
    bibliography = [int(x) for x in re.findall(r"(?m)^\[(\d+)\]", split[1])]
    assert ids == bibliography == list(range(1, len(bibliography) + 1))
    assert len(ids) >= 50
    figures = re.findall(r"!\[(图 \d+\.\d+)　[^\n]+\]\(([^)]+)\)", manuscript)
    assert len(figures) == len({k for k, _ in figures}) >= 14
    assert all((HERE / rel).is_file() for _, rel in figures)
    assert "@@" not in manuscript
    tables = re.findall(r"^表 ([0-9A-Z]+\.\d+)　", manuscript, re.M)
    assert len(tables) == len(set(tables)) and len(tables) >= 10
    eq = re.findall(r"\\tag\{([\d.]+)\}", manuscript)
    assert len(eq) == len(set(eq)) and len(eq) >= 9
    forbidden = re.compile(r"\$|@@|\\(?:frac|sigma|delta|mathrm|begin|hat|sum|tag)\b|\\\(|\\\)|Error!|错误!未|错误！未|填写说明")

    with ZipFile(OUT / "开题报告_P9.docx") as z:
        assert z.testzip() is None
        doc = ET.fromstring(z.read("word/document.xml"))
        biblio = {x.get(W+"name") for x in doc.iter(W+"bookmarkStart")}
        assert {f"Biblio{i}" for i in ids} <= biblio
        assert all(el.get(W+"anchor") in biblio for el in doc.iter(W+"hyperlink") if el.get(W+"anchor"))
        plain = tex(doc, W)
        assert not forbidden.search(plain), forbidden.search(plain)
        math_nodes = list(doc.iter(M+"oMath"))
        assert len(math_nodes) >= len(eq)
        assert list(doc.iter(M+"f")) and list(doc.iter(M+"sSub")) and list(doc.iter(M+"nary"))
        assert not forbidden.search(tex(doc, M))
        assert all(f"（{n}）" in plain for n in eq)
        styles = ET.fromstring(z.read("word/styles.xml"))
        for level in ("heading 1","heading 2","heading 3"):
            st = next(st for st in styles.findall(W+"style") if st.find(W+"name").get(W+"val").lower() == level)
            by_id = {x.get(W+"styleId"):x for x in styles.findall(W+"style")}
            for slot, allowed in (("eastAsia", {"黑体","SimHei"}), ("ascii", {"Arial"})):
                current = st
                while current is not None:
                    fonts = current.find(W+"rPr/"+W+"rFonts")
                    if fonts is not None and fonts.get(W+slot):
                        assert fonts.get(W+slot) in allowed
                        break
                    parent = current.find(W+"basedOn")
                    current = by_id.get(parent.get(W+"val")) if parent is not None else None
                else:
                    raise AssertionError(f"Missing heading font {slot}")
    report = PdfReader(OUT / "开题报告_P9.pdf")
    text = compact("".join(p.extract_text() for p in report.pages))
    assert not forbidden.search(text), forbidden.search(text)
    assert all(compact(t) in text for t in ("第 1 章","第 8 章","七组成","附录 A"))
    assert all(compact(f"（{n}）") in text for n in eq)
    # Require actual citations, not just a larger bibliography or duplicate entries.
    urls = re.findall(r"(?im)^\[\d+\].*?https://doi.org/(\S+)", split[1])
    assert len({u.lower() for u in urls}) == len(urls), "Duplicate DOI"
    assert len(list(OUT.glob("*.pdf"))) == 2
    speakers = json.loads((HERE / "speaker_script.json").read_text(encoding="utf-8"))
    slides = PdfReader(OUT / "汇报版开题报告_P9.pdf")
    assert len(slides.pages) == len(speakers) and len(speakers) > 0
    with ZipFile(OUT / "P9_逐页汇报词.docx") as z:
        assert z.testzip() is None
        notes = compact(tex(ET.fromstring(z.read("word/document.xml")), W))
    with ZipFile(OUT / "汇报版开题报告_P9.pptx") as z:
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
    policies = {r["policy"]:r for r in data(ROOT / "simulation/redesign/outputs/policy_summary.csv") if r["scenario"]=="baseline"}
    assert len({r["n"] for r in policies.values()}) == 1
    assert int(policies["tree"]["n"]) == 1024
    assert policies["tree_fit"]["fit_count"] == "0.0"
    for name in ("myopic","tree"):
        percent = float(policies[name]["success_rate"])*100
        formats = (f"{percent:.2f}%", f"{percent:.1f}%")
        assert any(x in text for x in formats), formats
    assert all(r["forced_directions"] == n for r,n in zip(data(ROOT / "p9/evidence/ordering_stress.csv"),("21","20","19","14","10","6")))
    samples = data(ROOT / "p9/protocol/powders.csv")
    assert len({r["powder_id"] for r in samples}) == 18
    assert all(r["status"] == "planned" for r in samples)
    print(f"PASS {len(report.pages)} written pages, {len(figures)} report figures, {len(bibliography)} "
          f"cited references, {len(tables)} tables, {len(eq)} display / {len(math_nodes)} total Office Math objects, "
          f"{len(slides.pages)} matching slides and notes, 49 synthetic probabilities.")


if __name__ == "__main__":
    main()
