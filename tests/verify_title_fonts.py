"""Compare manuscript title and table-header text with actual exported PDF fonts.

Run with PyMuPDF and fontTools after generating the manuscript with Word.
"""
import io
import re
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

import pymupdf
from fontTools.ttLib import TTFont


PAPER = Path(__file__).resolve().parents[1] / "paper"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def normalize(text):
    # Word tab leaders are rendered as dots, but not stored as text in the DOCX.
    return "".join(c for c in unicodedata.normalize("NFKC", text)
                   if not c.isspace() and c not in ".…\u200b\u00ad\ufeff")


def word_text(element):
    return normalize("".join(n.text or "" for n in element.iter(W + "t")))


def pdf_text_and_fonts(page):
    text, fonts = [], []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                value = normalize(span["text"])
                text.append(value)
                fonts.extend([span["font"]] * len(value))
    return "".join(text), fonts


def check_face(value, pages):
    found = False
    for text, fonts in pages:
        for match in re.finditer(re.escape(value), text):
            faces = set(fonts[match.start():match.end()])
            assert faces == {"SimHei"}, (value, faces)
            found = True
    assert found, ("PDF title missing", value)


def main():
    with zipfile.ZipFile(PAPER / "开题报告_P8.docx") as source:
        doc = ET.fromstring(source.read("word/document.xml"))
        styles = ET.fromstring(source.read("word/styles.xml"))
    names = {s.get(W + "styleId"): s.find(W + "name").get(W + "val").lower()
             for s in styles.findall(W + "style") if s.find(W + "name") is not None}
    counts = Counter()
    with pymupdf.open(PAPER / "开题报告_P8.pdf") as pdf:
        pages = [pdf_text_and_fonts(page) for page in pdf]
        chapter_start = pdf.get_toc()[0][2] - 1
        for p in doc.find(W + "body").findall(W + "p"):
            value = word_text(p)
            if not value:
                continue
            style = p.find(f"{W}pPr/{W}pStyle")
            name = names.get(style.get(W + "val"), "") if style is not None else ""
            if name == "title" or value in {"综合论文训练", "开题报告"}:
                category, search = "cover", pages[:1]
            elif name.startswith("toc ") or name in {"p8 entry", "p8 front"}:
                category, search = name, pages[1:chapter_start]
            elif name.startswith("heading ") or name == "p8 cap":
                category, search = name, pages[chapter_start:]
            else:
                continue
            check_face(value, search)
            counts[category] += 1
        print("Verified Word headings, captions and contents entries:", sum(counts.values()))

        cells = 0
        for row in doc.iter(W + "tr"):
            if row.find(f"{W}trPr/{W}tblHeader") is None:
                continue
            headers = row.findall(W + "tc")
            # Use the full header row so common cell text cannot match prose.
            check_face("".join(word_text(cell) for cell in headers), pages)
            cells += len(headers)
        print("Verified table header cells:", cells)

        font_ids = {f[0] for page in pdf for f in page.get_fonts()
                    if f[3].split("+")[-1] == "SimHei"}
        assert font_ids, "Missing embedded SimHei"
        for xref in font_ids:
            with TTFont(io.BytesIO(pdf.extract_font(xref)[3])) as font:
                assert font["name"].getDebugName(6).endswith("SimHei")
                assert font["OS/2"].usWeightClass == 400
        for i, page in enumerate(pdf, 1):
            for span in page.get_texttrace():
                if span["font"] == "SimHei" and span["type"] == 1:
                    assert not any(not chr(c[0]).isspace() for c in span["chars"]), (
                        "Simulated bold stroke", i)
        print("Verified embedded SimHei Regular with no synthetic bold strokes.")


if __name__ == "__main__":
    main()
