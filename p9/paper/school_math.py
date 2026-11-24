"""Convert LaTeX authoring expressions to editable Office Math, including inline math."""
import os
import re
from functools import lru_cache
from pathlib import Path

from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.shared import Cm, Pt
from latex2mathml.converter import convert
from lxml import etree


@lru_cache(maxsize=1)
def office_transform():
    supplied = os.environ.get("MML2OMML_XSL")
    candidates = [Path(supplied)] if supplied else [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) /
        "Microsoft Office/root/Office16/MML2OMML.XSL",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) /
        "Microsoft Office/root/Office16/MML2OMML.XSL",
    ]
    for path in candidates:
        if path.is_file():
            return etree.XSLT(etree.parse(str(path)))
    raise FileNotFoundError("Set MML2OMML_XSL to the Office MathML to OMML stylesheet.")


def insert_math(paragraph, latex, size=12):
    mathml = etree.fromstring(convert(latex).encode("utf-8"))
    node = office_transform()(mathml).getroot()
    if node.tag != qn("m:oMath"):
        raise ValueError(f"Expected Office Math for {latex!r}")
    # Word clamps inline fractions to the surrounding line's height on some
    # templates. A floating baseline and a real math font avoid cropped limits.
    for run in node.iter(qn("m:r")):
        props = run.find(qn("w:rPr"))
        if props is None:
            props = OxmlElement("w:rPr")
            run.insert(1 if run.find(qn("m:rPr")) is not None else 0, props)
        fonts = OxmlElement("w:rFonts")
        for slot in ("ascii", "hAnsi", "eastAsia", "cs"):
            fonts.set(qn("w:" + slot), "Cambria Math")
        props.append(fonts)
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), str(round(size * 2)))
        props.append(sz)
    paragraph._p.append(node)


def add_inline(paragraph, value, plain):
    # Fail on an unpaired delimiter instead of copying markup to the reader.
    fragments = value.split("$")
    if len(fragments) % 2 == 0:
        raise ValueError(f"Unpaired inline math delimiter in {value!r}")
    for i, fragment in enumerate(fragments):
        if i % 2:
            if not fragment.strip():
                raise ValueError("Empty math or unexpected display delimiter")
            insert_math(paragraph, fragment)
            paragraph.paragraph_format.line_spacing = 1.25
        elif fragment:
            if re.search(r"\\(?:frac|sigma|delta|mathrm|hat|sum|begin)\b", fragment):
                raise ValueError(f"Unmarked TeX in prose: {fragment}")
            plain(paragraph, fragment)


def display(doc, latex, number):
    p = doc.add_paragraph(style="P9 equation")
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.tab_stops.add_tab_stop(Cm(7.5), WD_TAB_ALIGNMENT.CENTER)
    pf.tab_stops.add_tab_stop(Cm(15.0), WD_TAB_ALIGNMENT.RIGHT)
    pf.first_line_indent = Pt(0)
    pf.keep_together = True
    p.add_run("\t")
    insert_math(p, latex)
    p.add_run(f"\t（{number}）")
    return p
