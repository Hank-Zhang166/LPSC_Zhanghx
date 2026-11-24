"""Build the P9 slide deck and synchronized Word script.

Run with python-pptx, python-docx and Pillow. Export PDFs with --export-pdf
on Windows with Microsoft Office. --notes-pdf is for rendering QA.
"""
from __future__ import annotations

import argparse
from base64 import b64encode
import json
import os
from pathlib import Path
import subprocess

from PIL import Image
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement as WordElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt as WordPt, RGBColor as WordColor
from lxml import etree
from pptx.opc.constants import RELATIONSHIP_TYPE
from pptx.opc.package import Part
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt


HERE = Path(__file__).resolve().parent
P9 = HERE.parent
DELIVERY = P9 / "交付稿"
FIGURES = P9 / "revision_visuals"
TITLE = "氯富集硫银锗矿的概率排序与资源受限研发决策"
AUTHOR = "张皓轩"
PPTX_NAME = "汇报版开题报告_P9.pptx"
WORD_NAME = "P9_逐页汇报词.docx"
INK, TEAL, GRAY = "18343E", "0B7065", "526872"
NAVY, WHITE, PALE, PAPER = "24495D", "FFFFFF", "E8F4F1", "FFFFFF"


def color(value):
    return RGBColor.from_string(value)


def apply_font(run, size, fill, bold=False):
    run.font.name = "Microsoft YaHei"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color(fill)
    for tag in ("a:ea", "a:cs"):
        face = OxmlElement(tag)
        face.set("typeface", "Microsoft YaHei")
        run._r.get_or_add_rPr().append(face)


def text(slide, value, x, y, width, height, size=16, fill=INK, bold=False,
         align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(width), Inches(height))
    frame = box.text_frame
    frame.margin_left = frame.margin_right = Inches(.01)
    frame.margin_top = frame.margin_bottom = Inches(.005)
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i, line in enumerate(value.split("\n")):
        paragraph = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        paragraph.alignment = align
        paragraph.space_before = paragraph.space_after = Pt(0)
        run = paragraph.add_run()
        run.text = line
        apply_font(run, size, fill, bold)


def block(slide, x, y, width, height, fill):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y),
                                   Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = color(fill)
    shape.line.fill.background()
    default_style = shape._element.find("{http://schemas.openxmlformats.org/presentationml/2006/main}style")
    if default_style is not None:
        shape._element.remove(default_style)


def picture(slide, path, title, x, y, width, height):
    with Image.open(path) as image:
        iw, ih = image.size
    scale = min(width / iw, height / ih)
    iw, ih = iw * scale, ih * scale
    shape = slide.shapes.add_picture(str(path), Inches(x + (width - iw) / 2),
                                     Inches(y + (height - ih) / 2), Inches(iw), Inches(ih))
    shape._element.nvPicPr.cNvPr.set("descr", title)
    vector_path = path.with_suffix(".svg")
    if vector_path.is_file():
        package = slide.part.package
        part = Part(package.next_partname("/ppt/media/vector%d.svg"), "image/svg+xml",
                    package, vector_path.read_bytes())
        rel = slide.part.relate_to(part, RELATIONSHIP_TYPE.IMAGE)
        extension_list = OxmlElement("a:extLst")
        extension = OxmlElement("a:ext")
        extension.set("uri", "{96DAC541-7B7A-43D3-8B79-37D633B846F1}")
        svg_ns = "http://schemas.microsoft.com/office/drawing/2016/SVG/main"
        ref = etree.SubElement(extension, f"{{{svg_ns}}}svgBlip", nsmap={"asvg": svg_ns})
        ref.set("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed", rel)
        extension_list.append(extension)
        shape._element.blipFill.blip.append(extension_list)



def table(slide, headers, rows, widths):
    x, y, width, height = .67, 2.20, 12, 4.32
    table = slide.shapes.add_table(len(rows) + 1, len(headers), Inches(x), Inches(y),
                                   Inches(width), Inches(height)).table
    for j, fraction in enumerate(widths):
        table.columns[j].width = Inches(width * fraction)
    for i, row in enumerate([headers, *rows]):
        table.rows[i].height = Inches(.52 if i == 0 else (height - .52) / len(rows))
        for j, value in enumerate(row):
            cell = table.cell(i, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = color(NAVY if i == 0 else PALE if i % 2 else PAPER)
            cell.margin_left = cell.margin_right = Inches(.15)
            cell.margin_top = cell.margin_bottom = Inches(.045)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.text_frame.word_wrap = True
            para = cell.text_frame.paragraphs[0]
            para.space_after = Pt(0)
            run = para.add_run()
            run.text = str(value)
            apply_font(run, 15 if i == 0 or len(rows) < 5 else 14,
                       WHITE if i == 0 else TEAL if j == 0 else INK, i == 0 or j == 0)


def figure(slide, page, path):
    callouts = page.get("callouts", [])
    plot_height = 3.78 if callouts else 4.62
    picture(slide, path, page["title"], .68, 2.04, 11.98, plot_height)
    for i, (label, detail) in enumerate(callouts):
        x = .68 + 4.03 * i
        block(slide, x, 5.91, 3.89, .79, PALE)
        text(slide, label, x + .12, 5.96, 3.65, .24, 12, TEAL, True)
        text(slide, detail, x + .12, 6.21, 3.65, .38, 11, INK)


def cover(slide, page):
    block(slide, 0, 0, 13.333, 7.5, "F2F6F3")
    block(slide, .68, .75, .44, .07, TEAL)
    text(slide, page["section"], 1.22, .53, 5.7, .50, 15, TEAL, True)
    text(slide, "氯富集硫银锗矿的概率排序\n与资源受限研发决策", .67, 1.64, 7.32, 1.88, 31, INK, True)
    text(slide, page["lead"], .71, 3.78, 6.65, 1.12, 20, NAVY)
    text(slide, page["source"], .71, 6.01, 7.05, .47, 14, GRAY)
    picture(slide, FIGURES / "pellet_cutaway.png", "阻挡电极与多晶压片分解示意",
            7.20, .44, 5.72, 5.88)
    text(slide, "阻挡电极与多晶压片的分解示意", 7.20, 6.36, 5.72, .34, 11, GRAY,
         align=PP_ALIGN.CENTER)


def slide_header(slide, page):
    block(slide, 0, 0, 13.333, 7.5, PAPER)
    block(slide, .65, .43, .25, .052, TEAL)
    text(slide, page["section"], 1, .25, 8.3, .41, 12, TEAL, True)
    text(slide, page["title"], .65, .80, 12, .72, 29, INK, True)
    text(slide, page["lead"], .68, 1.53, 11.97, .49, 15, GRAY)
    block(slide, .67, 6.86, 12, .013, "CBD9D6")
    text(slide, page["source"], .67, 6.95, 11.15, .36, 10, GRAY)
    text(slide, str(page["page"]).zfill(2), 12.05, 6.94, .61, .37, 13, TEAL, True,
         align=PP_ALIGN.RIGHT)


def build_slides(pages, out):
    deck = Presentation()
    deck.slide_width, deck.slide_height = Inches(13.333), Inches(7.5)
    deck.core_properties.title = TITLE
    deck.core_properties.author = AUTHOR
    for page in pages:
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        kind = page["kind"]
        if kind == "cover":
            cover(slide, page)
        else:
            slide_header(slide, page)
            if kind == "table":
                table(slide, page["columns"], page["rows"], [.22, .38, .40])
            else:
                path = FIGURES / (page["figure"] + ".png")
                figure(slide, page, path)
        slide.notes_slide.notes_text_frame.text = page["speech"]
    path = out / PPTX_NAME
    deck.save(path)
    return path


def word_font(run, size, face, fill=INK):
    run.font.name = face
    run.font.size = WordPt(size)
    run.font.bold = False
    run.font.color.rgb = WordColor.from_string(fill)
    fonts = run._element.get_or_add_rPr().rFonts
    for script in ("ascii", "hAnsi", "eastAsia", "cs"):
        fonts.set(qn("w:" + script), face)


def build_word(pages, out):
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.left_margin = section.right_margin = Cm(2.1)
    section.top_margin = section.bottom_margin = Cm(1.8)
    section.header_distance = section.footer_distance = Cm(.78)
    word_font(section.header.paragraphs[0].add_run("综合论文训练     P9 开题汇报"),
              9, "宋体", GRAY)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    word_font(footer.add_run(AUTHOR + "    ·    "), 9, "宋体", GRAY)
    field = WordElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._element.append(field)
    for border in doc.styles["Title"]._element.xpath(".//w:pBdr"):
        border.getparent().remove(border)
    title = doc.add_paragraph(style="Title")
    word_font(title.add_run("P9 开题汇报词"), 22, "SimHei", "000000")
    title.paragraph_format.keep_with_next = True
    subtitle = doc.add_paragraph()
    subtitle.paragraph_format.keep_with_next = True
    subtitle.paragraph_format.space_after = WordPt(11)
    word_font(subtitle.add_run(TITLE), 14, "SimHei", TEAL)
    for page in pages:
        heading = doc.add_paragraph()
        heading.paragraph_format.keep_with_next = True
        heading.paragraph_format.space_before = WordPt(9)
        heading.paragraph_format.space_after = WordPt(3)
        word_font(heading.add_run(f"{page['page']:02d}　{page['title']}"), 12.5, "SimHei", TEAL)
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.keep_together = True
        paragraph.paragraph_format.space_after = WordPt(7)
        paragraph.paragraph_format.line_spacing = WordPt(19)
        word_font(paragraph.add_run(page["speech"]), 12, "宋体")
    doc.core_properties.title = "P9 开题汇报词"
    doc.core_properties.author = AUTHOR
    path = out / WORD_NAME
    doc.save(path)
    return path


def run_office(script, **paths):
    env = {**os.environ, **{key: str(value.resolve()) for key, value in paths.items()}}
    payload = b64encode(("$ErrorActionPreference = 'Stop'\n" + script).encode("utf-16-le")).decode()
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", payload],
                   check=True, env=env)


def export_slides(path):
    run_office("""
$app = New-Object -ComObject PowerPoint.Application
$doc = $app.Presentations.Open($env:P9_DECK, -1, 0, 0)
try { $doc.SaveAs($env:P9_DECK_PDF, 32) } finally { $doc.Close() }
""", P9_DECK=path, P9_DECK_PDF=path.with_suffix(".pdf"))


def render_notes(path, pdf):
    run_office("""
$app = New-Object -ComObject Word.Application
$app.Visible = $false
$app.DisplayAlerts = 0
try {
  $doc = $app.Documents.Open($env:P9_NOTES, $false, $true)
  try { $doc.ExportAsFixedFormat($env:P9_NOTES_PDF, 17) } finally { $doc.Close(0) }
} finally { $app.Quit() }
""", P9_NOTES=path, P9_NOTES_PDF=pdf)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DELIVERY)
    parser.add_argument("--export-pdf", action="store_true")
    parser.add_argument("--notes-pdf", type=Path)
    args = parser.parse_args()
    pages = json.loads((HERE / "speaker_script.json").read_text(encoding="utf-8"))
    if [p["page"] for p in pages] != list(range(1, len(pages) + 1)):
        raise ValueError("Presentation and script must have consecutive slide numbers.")
    args.out.mkdir(parents=True, exist_ok=True)
    deck = build_slides(pages, args.out)
    word = build_word(pages, args.out)
    if args.export_pdf:
        export_slides(deck)
    if args.notes_pdf:
        render_notes(word, args.notes_pdf)


if __name__ == "__main__":
    main()
