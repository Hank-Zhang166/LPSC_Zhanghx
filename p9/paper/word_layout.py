"""Word sections, typography, tables and numbered references for the proposal."""
import re

from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from school_math import add_inline


def xml(tag, **attributes):
    element = OxmlElement("w:" + tag)
    for name, value in attributes.items():
        element.set(qn("w:" + name), str(value))
    return element


def font(target, cn="宋体", en="Times New Roman", pt=12, bold=False):
    target.font.name = en
    target.font.size = Pt(pt)
    target.font.bold = bold
    target.font.color.rgb = RGBColor(0, 0, 0)
    props = target.element.get_or_add_rPr()
    fonts = props.find(qn("w:rFonts"))
    if fonts is None:
        fonts = xml("rFonts")
        props.append(fonts)
    for script, face in (("eastAsia", cn), ("ascii", en), ("hAnsi", en), ("cs", en)):
        fonts.set(qn("w:" + script), face)
    fonts.set(qn("w:hint"), "eastAsia")


def simhei(target):
    """Remove theme overrides to select genuine SimHei Regular."""
    props = target.element.get_or_add_rPr()
    fonts = props.rFonts
    if fonts is None:
        fonts = xml("rFonts")
        props.insert(0, fonts)
    for key in list(fonts.attrib):
        if key.rsplit("}", 1)[-1].lower().endswith("theme"):
            del fonts.attrib[key]
    for script in ("ascii", "hAnsi", "eastAsia", "cs"):
        fonts.set(qn("w:" + script), "SimHei")
    fonts.set(qn("w:hint"), "eastAsia")
    target.font.bold = target.font.cs_bold = False
    target.font.italic = target.font.cs_italic = False


def fstyle(style, align, first, before, after, line, keep):
    pf = style.paragraph_format
    pf.alignment = align
    pf.first_line_indent = Pt(first)
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = Pt(line) if line else 1.0
    pf.keep_with_next = keep
    pf.widow_control = True


def field(paragraph, code, placeholder="1"):
    run = paragraph.add_run()._r
    run.append(xml("fldChar", fldCharType="begin"))
    instruction = xml("instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " " + code + " "
    run.append(instruction)
    run.append(xml("fldChar", fldCharType="separate"))
    value = xml("t")
    value.text = placeholder
    run.append(value)
    run.append(xml("fldChar", fldCharType="end"))


def bmark(paragraph, name, index):
    node = paragraph._p
    node.insert(0 if node.pPr is None else 1, xml("bookmarkStart", id=index, name=name))
    node.append(xml("bookmarkEnd", id=index))


def bookmark(key):
    chapter, number = re.search(r"(\d+)\.(\d+)", key).groups()
    return ("Fig" if key.startswith("图") else "Tab") + chapter + "_" + number


def secsetup(section, cover=False, num=None):
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(3.8 if cover else 3)
    section.bottom_margin = Cm(3.2 if cover else 3)
    section.left_margin = section.right_margin = Cm(3)
    section.gutter = Cm(.2 if cover else 0)
    section.footer_distance = Cm(1.5)
    section.header_distance = Cm(1.7)
    if num:
        section.footer.is_linked_to_previous = False
        props = section._sectPr
        previous = props.find(qn("w:pgNumType"))
        if previous is not None:
            props.remove(previous)
        props.append(xml("pgNumType", fmt=num, start=1))
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer.paragraph_format.first_line_indent = Pt(0)
        field(footer, "PAGE")


CITATION = re.compile(r"(\[[1-9]\d*(?:[,–-][1-9]\d*)*\])")
MATH_GLYPHS = re.compile(r"([₀-₉₋₊ₓᵢ⁰¹²³⁴⁵⁶⁷⁸⁹⁻ᵀ∂ΣΞ√≥≤∝Åθ]+)")


def clean(value):
    return re.sub(r"\*\*|`", "", value.strip())


def plain_text(paragraph, value):
    for part in MATH_GLYPHS.split(clean(value)):
        if not part:
            continue
        run = paragraph.add_run(part)
        if MATH_GLYPHS.fullmatch(part):
            run.font.name = "Cambria Math"
            run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Cambria Math")


def linked_run(paragraph, label, anchor=None, url=None, raised=False):
    link = xml("hyperlink")
    if anchor:
        link.set(qn("w:anchor"), anchor)
    if url:
        link.set(qn("r:id"), paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True))
    run = paragraph.add_run(label)
    run.font.superscript = raised
    link.append(run._r)
    paragraph._p.append(link)


def citation_text(paragraph, value):
    for part in CITATION.split(clean(value)):
        if not part:
            continue
        if CITATION.fullmatch(part):
            for token in re.split(r"(\d+)", part):
                if token.isdigit():
                    linked_run(paragraph, token, anchor="Biblio" + token, raised=True)
                elif token:
                    paragraph.add_run(token).font.superscript = True
        else:
            if part[:1].isspace():
                paragraph.add_run(" ")
            plain_text(paragraph, part)
            if part[-1:].isspace():
                paragraph.add_run(" ")


def text(paragraph, value):
    add_inline(paragraph, value, citation_text)


def bibliography_entry(paragraph, entry):
    number = re.match(r"\[(\d+)\]", entry)[1]
    body, separator, suffix = entry.rpartition(" https://")
    if separator:
        plain_text(paragraph, body)
        paragraph.add_run(" ")
        url = "https://" + suffix
        label = "DOI: " + url.removeprefix("https://doi.org/") if url.startswith("https://doi.org/") else url
        linked_run(paragraph, label, url=url)
    else:
        plain_text(paragraph, entry)
    bmark(paragraph, "Biblio" + number, 1000 + int(number))


def table(doc, data, fractions):
    result = doc.add_table(rows=0, cols=len(fractions))
    result.autofit = False
    result.alignment = WD_TABLE_ALIGNMENT.CENTER
    for column, fraction in zip(result.columns, fractions):
        column.width = Cm(15 * fraction)
    borders = xml("tblBorders")
    for edge in ("top", "bottom", "insideH", "left", "right", "insideV"):
        outer = edge in ("top", "bottom")
        borders.append(xml(edge, val="single" if outer else "nil", sz=12 if outer else 0, color="253E44"))
    result._tbl.tblPr.append(borders)
    margins = xml("tblCellMar")
    for side in ("top", "bottom", "left", "right"):
        margins.append(xml(side, w=55, type="dxa"))
    result._tbl.tblPr.append(margins)
    for row_number, values in enumerate(data):
        row = result.add_row()
        props = row._tr.get_or_add_trPr()
        props.append(xml("cantSplit"))
        if row_number == 0:
            props.append(xml("tblHeader", val=1))
        for cell, value, fraction in zip(row.cells, values, fractions):
            cell.width = Cm(15 * fraction)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            paragraph = cell.paragraphs[0]
            paragraph.style = "P9 table header" if row_number == 0 else "P9 table"
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if row_number == 0 else WD_ALIGN_PARAGRAPH.LEFT
            text(paragraph, value)
            if row_number == 0:
                border = xml("tcBorders")
                border.append(xml("bottom", val="single", sz=6, color="677A7F"))
                cell._tc.get_or_add_tcPr().append(border)
    return result
