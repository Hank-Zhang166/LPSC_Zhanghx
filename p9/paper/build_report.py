"""Build school-format P9 Word and PDF using the shared P8 text/field helpers."""
import argparse
import base64
import os
import re
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH as Align, WD_TAB_ALIGNMENT as Tab, WD_TAB_LEADER as Leader
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "paper"))
import build_manuscript as shared

CITATION = re.compile(r"\[([1-9]\d*(?:[,–-][1-9]\d*)*)\]")
FIGURE = re.compile(r"!\[(图 \d+\.\d+)　(.+)\]\(([^)]+)\)$")
TABLE = re.compile(r"(表 \d+\.\d+)　([^。]+)(?:。(.*))?$")
SHORT = {
    "表 1.1": "研究假设、对照与终点",
    "表 2.1": "七组成公开实验基准",
    "表 2.2": "原子数据可用范围",
    "表 4.1": "观测与诊断对象",
}


def read(path):
    return path.read_text(encoding="utf-8-sig")


def compose(preview=False):
    old = read(ROOT / "paper/manuscript.md")
    review = "#### 2.1.1" + old.split("#### 2.1.1", 1)[1].split("#### 2.1.7", 1)[0]
    review = review.replace("P8 因而", "本研究因而").replace("因此 P8 采用", "因此本课题拟采用")
    review = re.sub(r"因此，P8 应给成本感知规则 B2[^\n]+。",
                    "因此需以同观测预算比较单步规则和有限前瞻，并单独验证队列因素。", review)
    review = review.replace("因此 P8 分开记录", "本课题分开记录")
    review = re.sub(r"B3 与 B4 遵守[^\n]+。", "将适配、发布与重算条件纳入策略对照。", review)
    body, tail = read(HERE / "manuscript.md").replace("@LITERATURE", review.rstrip()).split("@REFERENCES", 1)
    for marker, path in (
        ("@EVIDENCE", ROOT / "p9/evidence/report_insert.md"),
        ("@RANK_CASE", ROOT / "p9/ranking/report_insert.md"),
        ("@RESULTS", HERE / "results.md"),
        ("@DES_CASE", ROOT / "simulation/p9/report_insert.md"),
    ):
        if marker in body:
            content = "" if preview and not path.is_file() else read(path).strip()
            body = body.replace(marker, content)
    existing = read(ROOT / "paper/manuscript_des.md")
    ref_file = "\n".join((existing, read(HERE / "reference_additions.md")))
    references = {int(k): v for k, v in re.findall(r"(?m)^\[(\d+)\] (.+)$", ref_file)}
    order = {}

    def renumber(hit):
        numbers = []
        for value in hit[1].split(","):
            first, *last = (int(k) for k in re.split("[–-]", value))
            numbers.extend(range(first, (last[0] if last else first) + 1))
        for old_id in numbers:
            if old_id not in references:
                raise ValueError(f"Missing bibliographic entry {old_id}")
            order.setdefault(old_id, len(order) + 1)
        return "[" + ",".join(str(i) for i in sorted({order[n] for n in numbers})) + "]"

    body = CITATION.sub(renumber, body)
    first = "\n".join(f"[{new}] {references[old_id]}" for old_id, new in order.items())
    return body + first + "\n\n" + tail.strip() + "\n"


def make_style(doc, name, cn, western, point, align, first=0, before=0, after=0, line=20, keep=False):
    styles = doc.styles
    st = styles[name] if name in styles else styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
    if cn == "SimHei":
        shared.simhei(st)
    shared.font(st, cn, western, point)
    shared.fstyle(st, align, first, before, after, line, keep)
    return st


def configure(doc):
    left, centered = Align.LEFT, Align.CENTER
    make_style(doc, "Normal", "宋体", "Times New Roman", 12, Align.JUSTIFY, first=24)
    make_style(doc, "Title", "SimHei", "SimHei", 26, centered, line=0)
    make_style(doc, "Heading 1", "SimHei", "Arial", 16, centered, before=24, after=18, line=0, keep=True)
    make_style(doc, "Heading 2", "SimHei", "Arial", 14, left, before=24, after=6, keep=True)
    make_style(doc, "Heading 3", "SimHei", "Arial", 13, left, before=12, after=6, keep=True)
    make_style(doc, "P9 front", "SimHei", "Arial", 16, centered, before=24, after=18, line=0)
    make_style(doc, "P9 figure", "宋体", "Times New Roman", 11, centered, before=6, after=12, line=0)
    make_style(doc, "P9 table caption", "宋体", "Times New Roman", 11, centered, before=12, after=6, line=0, keep=True)
    make_style(doc, "P9 source", "宋体", "Times New Roman", 11, left, before=6, after=12, line=0)
    make_style(doc, "P9 entry", "宋体", "Times New Roman", 12, left)
    make_style(doc, "P9 equation", "Cambria Math", "Cambria Math", 12, centered, before=6, after=6, line=0)
    for style in ("P8 table", "P8 table header"):
        make_style(doc, style, "宋体", "Times New Roman", 11, centered, before=3, after=3, line=0)
    ref = make_style(doc, "P9 reference", "宋体", "Times New Roman", 11, left, before=3, line=16)
    ref.paragraph_format.keep_together = True
    ref.paragraph_format.left_indent = Cm(1)
    ref.paragraph_format.first_line_indent = Cm(-1)
    for node in list(doc.styles["Title"].element.iter(qn("w:pBdr"))):
        node.getparent().remove(node)
    shared.secsetup(doc.sections[0], True)
    doc.core_properties.author = "张皓轩"
    doc.core_properties.subject = "清华大学综合论文训练开题报告 P9"


def cover(doc, title, adviser=""):
    def line(value, face, size, before=0, after=0, style=None):
        p = doc.add_paragraph(style=style)
        p.alignment = Align.CENTER
        p.paragraph_format.first_line_indent = Pt(0)
        p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(before), Pt(after)
        p.paragraph_format.line_spacing = 1.25
        r = p.add_run(value)
        shared.font(r, face, face, size)
    line("综 合 论 文 训 练", "SimHei", 22, 16, 40)
    line(title.replace("与研发决策", "\n与研发决策"), "SimHei", 26, 0, 24, "Title")
    line("开 题 报 告", "SimHei", 21, 0, 68)
    for label, value in (("系　　别", "工业工程系"), ("专　　业", "工业工程"),
                         ("姓　　名", "张 皓 轩"), ("指导教师", adviser)):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(3.6)
        p.paragraph_format.first_line_indent = Pt(0)
        p.paragraph_format.space_after = Pt(7)
        shared.font(p.add_run(f"{label}：{value}"), "仿宋", "Times New Roman", 16)
    line("二〇二六年十一月", "宋体", 16, 40)


def academic_table(doc, data):
    cols = len(data[0])
    fractions = {2: [.28, .72], 3: [.23, .37, .40],
                 4: [.13, .42, .25, .20]}.get(cols)
    tb = shared.table(doc, data, fractions)
    for node in tb._tbl.iter(qn("w:top")):
        if node.get(qn("w:val")) == "single":
            node.set(qn("w:sz"), "12")
    for cell in tb.rows[0].cells:
        for node in cell._tc.iter(qn("w:bottom")):
            node.set(qn("w:sz"), "8")
    if len(data) <= 8:
        for row in tb.rows[:-1]:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.keep_with_next = True


def figure(doc, key, caption, relpath, index):
    path = ROOT / relpath
    with Image.open(path) as img:
        w, h = img.size
    p = doc.add_paragraph()
    p.alignment = Align.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.keep_with_next = True
    image = p.add_run().add_picture(str(path), width=Cm(min(15, 10.3*w/h)))
    image._inline.docPr.set("descr", caption)
    cp = doc.add_paragraph(style="P9 figure")
    shared.text(cp, f"{key}　{caption}")
    shared.bmark(cp, shared.bookmark(key), index)


def front(doc, lines):
    shared.secsetup(doc.add_section(WD_SECTION.NEW_PAGE), num="upperRoman")
    doc.add_paragraph("目　录", "P9 front")
    shared.field(doc.add_paragraph(style="P9 entry"), 'TOC \\o "1-3" \\h \\z', "请更新目录")
    groups = [(k, []) for k in ("插图清单", "附表清单")]
    for s in lines:
        f, t = FIGURE.fullmatch(s), TABLE.fullmatch(s)
        if f:
            groups[0][1].append((f[1], f[2].split("。", 1)[0]))
        if t:
            groups[1][1].append((t[1], SHORT.get(t[1], t[2])))
    for label, entries in groups:
        p = doc.add_paragraph(label, "P9 front")
        p.paragraph_format.page_break_before = True
        for key, name in entries:
            p = doc.add_paragraph(style="P9 entry")
            p.paragraph_format.tab_stops.add_tab_stop(Cm(14.8), Tab.RIGHT, Leader.DOTS)
            p.add_run(f"{key}　{name}\t")
            shared.field(p, "PAGEREF " + shared.bookmark(key) + " \\h")
    p = doc.add_paragraph("符号和缩略语说明", "P9 front")
    p.paragraph_format.page_break_before = True
    academic_table(doc, [["符号", "含义"], ["DFT / MD", "密度泛函理论 / 分子动力学"],
                         ["XRD / EIS", "X 射线衍射 / 电化学阻抗谱"],
                         ["BME / ESS", "贝叶斯最大熵重加权 / 有效样本大小"],
                         ["EVSI / DES", "样本信息期望价值 / 离散事件仿真"],
                         ["RMST", "到首次独立阳性确认的限制平均时间"],
                         ["λ / δ", "重加权正则强度 / 最小可行动差"]])


def chapter_title(value):
    return re.sub(r"^第(\d+)章　", r"第 \1 章　", value)


def build(out, adviser="", preview=False):
    source = compose(preview)
    lines = [s.strip() for s in source.splitlines() if s.strip()]
    doc = Document()
    configure(doc)
    doc.core_properties.title = lines[0][2:]
    cover(doc, lines[0][2:], adviser)
    front(doc, lines)
    index, mode, i = 100, "", 1
    while i < len(lines):
        s = lines[i]
        if s.startswith("## "):
            mode = s[3:]
            first = mode.startswith("第1章")
            if first:
                shared.secsetup(doc.add_section(WD_SECTION.ODD_PAGE), num="decimal")
            head = doc.add_paragraph(chapter_title(mode), "P9 front" if mode == "摘要" else "Heading 1")
            head.paragraph_format.page_break_before = not first
        elif s.startswith(("### ", "#### ")):
            prefix, heading = s.split(" ", 1)
            heading = re.sub(r"^([\d.]+) +", r"\1　", heading)
            doc.add_paragraph(heading, f"Heading {len(prefix)-1}")
        elif match := FIGURE.fullmatch(s):
            figure(doc, *match.groups(), index)
            index += 1
        elif s.startswith("|"):
            data = []
            while i < len(lines) and lines[i].startswith("|"):
                row = [v.strip() for v in lines[i].strip("|").split("|")]
                if not all(re.fullmatch(r"[- :]+", v) for v in row):
                    data.append(row)
                i += 1
            match = TABLE.fullmatch(lines[i])
            if not match:
                raise ValueError(f"Table needs a caption before {lines[i]}")
            key, long_title, note = match.groups()
            title = SHORT.get(key, long_title)
            cp = doc.add_paragraph(f"{key}　{title}", "P9 table caption")
            shared.bmark(cp, shared.bookmark(key), index)
            index += 1
            academic_table(doc, data)
            explanation = "。".join(s for s in (long_title if title != long_title else "", note) if s)
            if explanation:
                shared.text(doc.add_paragraph(style="P9 source"), explanation)
        elif s.startswith("[") and mode.startswith("参考文献"):
            shared.bibliography_entry(doc.add_paragraph(style="P9 reference"), s)
        elif s.startswith("$$ ") and s.endswith(" $$"):
            formula, number = s[3:-3].rsplit("　", 1)
            p = doc.add_paragraph(style="P9 equation")
            p.alignment = Align.LEFT
            p.paragraph_format.tab_stops.add_tab_stop(Cm(7.5), Tab.CENTER)
            p.paragraph_format.tab_stops.add_tab_stop(Cm(15), Tab.RIGHT)
            p.add_run(f"\t{formula}\t{number}")
        else:
            shared.text(doc.add_paragraph(), s)
        i += 1
    out.mkdir(parents=True, exist_ok=True)
    file = out / "开题报告_P9.docx"
    doc.save(file)
    (out / "开题报告_P9_文稿.md").write_text(source, encoding="utf-8")
    return file


def export(file):
    ps = r"""
$ErrorActionPreference='Stop'
$word=New-Object -ComObject Word.Application
$word.Visible=$false
$word.DisplayAlerts=0
try {
    $doc=$word.Documents.Open($env:P9_DOCX,$false,$false)
    foreach ($level in (1..3)) {
        $style=$doc.Styles.Item([int](-19-$level))
        $style.Font.NameFarEast=if ($level -eq 1) {'SimHei'} else {'SimSun'}
        $style.Font.NameAscii=if ($level -eq 1) {'Arial'} else {'Times New Roman'}
        $style.Font.NameOther=$style.Font.NameAscii
        $style.Font.NameBi=$style.Font.NameAscii
        $style.Font.Size=12
        $style.Font.Bold=0
        $style.ParagraphFormat.LeftIndent=12*($level-1)
        $style.ParagraphFormat.FirstLineIndent=0
        $style.ParagraphFormat.SpaceBefore=0
        $style.ParagraphFormat.SpaceAfter=0
        $style.ParagraphFormat.LineSpacingRule=4
        $style.ParagraphFormat.LineSpacing=20
    }
    $doc.Repaginate()
    $doc.Fields.Update() | Out-Null
    foreach ($toc in $doc.TablesOfContents) {$toc.Update()}
    $doc.Repaginate()
    $doc.Fields.Update() | Out-Null
    foreach ($toc in $doc.TablesOfContents) {$toc.UpdatePageNumbers()}
    $doc.Save()
    $doc.ExportAsFixedFormat($env:P9_PDF,17,$false,0,0,1,1,0,$true,$true,1,$true,$true,$false)
    $doc.Close(0)
} finally {$word.Quit()}
"""
    env = dict(os.environ, P9_DOCX=str(file.resolve()),
               P9_PDF=str(file.with_suffix(".pdf").resolve()))
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand",
                    base64.b64encode(ps.encode("utf-16-le")).decode()], env=env, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=HERE)
    parser.add_argument("--adviser", default="")
    parser.add_argument("--docx-only", action="store_true")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    path = build(args.out, args.adviser, args.preview)
    if not args.docx_only:
        export(path)
