"""Build the P9 proposal and its numbered bibliography in the school format."""
from copy import deepcopy
from itertools import groupby
import json
import csv
from lxml import etree
import argparse
import base64
import os
import re
import subprocess
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
import word_layout as shared
from school_math import display

OUTPUT = ROOT / "p9/交付稿"


CITATION = re.compile(r"\[([1-9]\d*(?:[,–-][1-9]\d*)*)\]")
FIGURE = re.compile(r"!\[(图 \d+\.\d+)　(.+)\]\(([^)]+)\)$")
TABLE = re.compile(r"(表 \d+\.\d+)　([^。]+)(?:。(.*))?$")
SHORT = {}

def read(path):
    return path.read_text(encoding="utf-8-sig")


def compose():
    body = read(ROOT / "p9/revision_text/report.md")
    with (ROOT / "p9/evidence/ordering_stress.csv").open(encoding="utf-8-sig") as f:
        stress = [r for r in csv.DictReader(f) if float(r["factor"]) in (1.02, 1.05, 1.10, 1.20)]
    rows = [f"| {float(r['factor']):.2f} | {r['forced_directions']} | {r['overlapping_directions']} | {r['possible_maxima_x']} |" for r in stress]
    margins = read(ROOT / "p9/evidence/ordering_insert.md").replace("@@MARGINROWS@@", "\n".join(rows))
    body = body.replace("@@MARGINS@@", margins.strip())
    result = read(ROOT / "simulation/redesign/results.md").strip()
    body = body.replace("@@SIMRESULTS@@", result)
    manifest = json.loads(read(ROOT / "p9/revision_visuals/manifest.json"))
    equations = json.loads(read(ROOT / "p9/revision_text/equations.json"))
    figure_names = {}
    equation_names = {}
    chapter = None
    nfigure, neq = 0, 0
    rendered = []
    for line in body.splitlines():
        heading = re.match(r"^## 第\s*(\d+)\s*章", line)
        if heading:
            chapter = heading[1]
            nfigure, neq = 0, 0
        if marker := re.fullmatch(r"@@(FIG|EQ):([\w-]+)@@", line.strip()):
            kind, key = marker.groups()
            if not chapter:
                raise ValueError(f"{key} precedes chapter 1")
            if kind == "FIG":
                if key in figure_names:
                    raise ValueError(f"Duplicate figure {key}")
                nfigure += 1
                label = f"图 {chapter}.{nfigure}"
                figure_names[key] = label
                caption = manifest[key]["caption"]
                path = f"p9/revision_visuals/{key}.png"
                if not (ROOT / path).exists():
                    raise FileNotFoundError(path)
                line = f"![{label}　{caption}]({path})"
            else:
                if key in equation_names:
                    raise ValueError(f"Duplicate equation {key}")
                neq += 1
                number = f"{chapter}.{neq}"
                equation_names[key] = f"式（{number}）"
                line = f"@@MATH {number} {equations[key]}@@"
        rendered.append(line)
    body = "\n".join(rendered)
    crossrefs = {**figure_names, **equation_names}
    body = re.sub(r"@@REF:([\w-]+)@@", lambda m: crossrefs[m[1]], body)
    if re.search(r"@@(?!MATH\b|REFERENCES@@)[A-Za-z][A-Za-z_:.-]+@@", body):
        raise ValueError("Unresolved authoring marker in manuscript")
    raw_refs = read(ROOT / "p9/revision_text/references.md")
    refs = {int(k): v for k, v in re.findall(r"(?m)^\[(\d+)\] (.+)$", raw_refs)}
    order = {}

    def renumber(hit):
        ids = []
        for part in hit[1].split(","):
            start, *end = map(int, re.split(r"[–-]", part))
            for key in range(start, (end[0] if end else start) + 1):
                if key not in refs:
                    raise ValueError(f"Missing source {key}")
                ids.append(order.setdefault(key, len(order) + 1))
        numbers = sorted(set(ids))
        grouped = []
        for _, consecutive in groupby(enumerate(numbers), lambda item: item[1] - item[0]):
            v = [b for _, b in consecutive]
            grouped.extend([f"{v[0]}–{v[-1]}"] if len(v) > 2 else map(str, v))
        return "[" + ",".join(grouped) + "]"

    body = CITATION.sub(renumber, body)
    bibliography = "## 参考文献\n" + "\n".join(f"[{new}] {refs[old]}" for old, new in order.items())
    if "@@REFERENCES@@" in body:
        body = body.replace("@@REFERENCES@@", bibliography)
    elif "## 参考文献" in body:
        body = body.replace("## 参考文献", bibliography, 1)
    else:
        m = re.search(r"^## 附录", body, re.M)
        ix = m.start() if m else len(body)
        body = body[:ix].rstrip() + "\n\n" + bibliography + "\n\n" + body[ix:]
    return body.rstrip() + "\n"


def locate_template(explicit, existing):
    if explicit:
        return Path(explicit)
    # Use the checked-in P9 cover on a fresh clone; a new school template
    # may be supplied with --template without changing the repository.
    for saved in (OUTPUT / "开题报告_P9.docx", existing):
        if saved.is_file():
            return saved
    raise FileNotFoundError("Pass --template with the Tsinghua proposal template.")


def template_cover(template, title, adviser):
    """Retain the original school wordmark, layout, styles and cover metadata table."""
    doc = Document(template)
    body = doc._element.body
    boundary = next(p for p in body if p.find("./" + qn("w:pPr") + "/" + qn("w:sectPr")) is not None)
    section = deepcopy(boundary.find("./" + qn("w:pPr") + "/" + qn("w:sectPr")))
    for el in list(body)[list(body).index(boundary):]:
        body.remove(el)
    body.append(section)
    for node in list(body.iter()):
        if etree.QName(node).localname in ("AlternateContent","bookmarkStart","bookmarkEnd"):
            node.getparent().remove(node)
    cover_title = [p for p in doc.paragraphs if p.style.name == "封面论文题目"]
    if not cover_title:
        raise ValueError("School cover title style was not found")
    for p in cover_title:
        p.clear()
        p.paragraph_format.line_spacing = 1.25
    # The school's cover provides two title lines.
    points = [title.find(k) for k in ("与资源", "与研发", "与序贯", "与诊断", "的序贯")]
    split = next((i for i in points if i > 4), None)
    if split and len(cover_title) >= 2:
        parts = [(cover_title[-2], title[:split]), (cover_title[-1], title[split:])]
    else:
        parts = [(cover_title[-1], title)]
    for p, part in parts:
        shared.font(p.add_run(part), "SimHei", "SimHei", 26)
    for row, content in zip(doc.tables[0].rows, ("工业工程系", "工业工程", "张 皓 轩", adviser)):
        p = row.cells[-1].paragraphs[0]
        p.clear()
        shared.font(p.add_run(content), "仿宋", "Times New Roman", 16)
    dates = [p for p in doc.paragraphs if p.text.strip().endswith("月") and "年" in p.text]
    if dates:
        p = dates[-1]
        p.clear()
        shared.font(p.add_run("二〇二六年十一月"), "宋体", "Times New Roman", 16)
        for extra in list(p._p.itersiblings()):
            if extra.tag == qn("w:p") and not list(extra.iter(qn("w:t"))):
                extra.getparent().remove(extra)
    for st in ("Heading 1", "Heading 2", "Heading 3"):
        pr = doc.styles[st].element.get_or_add_pPr()
        for el in list(pr):
            if el.tag in (qn("w:numPr"), qn("w:pBdr")):
                pr.remove(el)
    return doc



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
    make_style(doc, "P9 body", "宋体", "Times New Roman", 12, Align.JUSTIFY, first=24)
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
    for style in ("P9 table", "P9 table header"):
        make_style(doc, style, "宋体", "Times New Roman", 11, centered, before=3, after=3, line=0)
    ref = make_style(doc, "P9 reference", "宋体", "Times New Roman", 11, left, before=3, line=16)
    ref.paragraph_format.keep_together = True
    ref.paragraph_format.left_indent = Cm(1)
    ref.paragraph_format.first_line_indent = Cm(-1)
    for node in list(doc.styles["Title"].element.iter(qn("w:pBdr"))):
        node.getparent().remove(node)
    shared.secsetup(doc.sections[0], True)
    for st in ("P9 body","Heading 1","Heading 2","Heading 3","P9 table","P9 table header"):
        pr = doc.styles[st].element.get_or_add_pPr()
        prop = pr.find(qn("w:snapToGrid"))
        if prop is None:
            prop = shared.xml("snapToGrid")
            pr.append(prop)
        prop.set(qn("w:val"), "0")
    doc.core_properties.author = "张皓轩"
    doc.core_properties.subject = "清华大学综合论文训练开题报告 P9"


def academic_table(doc, data):
    from math import sqrt
    # Allocate width by text content, while keeping brief numeric columns legible.
    if any(len(row) != len(data[0]) for row in data):
        raise ValueError("Inconsistent Markdown table width")
    weights = [sqrt(max(6, max(sum(1 if ord(c) < 128 else 2 for c in x) for x in col)))
               for col in zip(*data)]
    fractions = [w / sum(weights) for w in weights]
    tb = shared.table(doc, data, fractions)
    for margins in tb._tbl.iter(qn("w:tblCellMar")):
        for side in ("top","bottom"):
            node = margins.find(qn("w:"+side))
            if node is not None:
                node.set(qn("w:w"), "0")
    for row in tb.rows[1:]:
        for cell in row.cells:
            if re.fullmatch(r"[\d.,% −–+]+", cell.text.strip()):
                cell.paragraphs[0].alignment = Align.CENTER
    for node in tb._tbl.iter(qn("w:top")):
        if node.get(qn("w:val")) == "single":
            node.set(qn("w:sz"), "12")
    for cell in tb.rows[0].cells:
        for node in cell._tc.iter(qn("w:bottom")):
            node.set(qn("w:sz"), "8")
    if len(data) <= 12:
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
    image = p.add_run().add_picture(str(path), width=Cm(min(15, 11.5*w/h)))
    image._inline.docPr.set("descr", caption)
    cp = doc.add_paragraph(style="P9 figure")
    shared.text(cp, f"{key}　{caption}")
    shared.bmark(cp, shared.bookmark(key), index)
    item = json.loads(read(ROOT / "p9/revision_visuals/manifest.json"))[path.stem]
    if item.get("source"):
        cp.paragraph_format.keep_with_next = True
        cp.paragraph_format.space_after = Pt(2)
        note = doc.add_paragraph(style="P9 source")
        note.paragraph_format.space_before = Pt(0)
        note.paragraph_format.keep_together = True
        shared.text(note, "图注　" + item["source"])


def front(doc, lines):
    # Cover is single-sided. Reserve its unnumbered reverse for duplex printing.
    doc.add_page_break()
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
    glossary = [
        ("$x$", "富氯程度，对应七个名义组成"),
        ("$C_i$，$w_i$", "同一组成内的第 i 个结构族及其条件权重"),
        ("$F_i$，$T_f$", "同口径整胞自由能和有效冻结温度"),
        ("$I_t$", "时刻 t 已正式发布的证据及当前可用资源"),
        (r"$S$，$\delta$", "随机结构族的晶内对数输运量及最小可行动差"),
        ("$p^+$，$p^-$，$p^0$", "配方对的优势、反向优势及近似并列概率"),
        ("$q_{AB}$", "同工艺新粉体平均效应超过实验阈值的概率"),
        ("DPA4", "原子势模型，用于预测原子体系的能量、力和维里量"),
        ("DFT / MD", "密度泛函理论 / 分子动力学"),
        ("XRD / EIS", "X 射线衍射 / 电化学阻抗谱"),
        ("BME / ESS", "贝叶斯最大熵重加权 / 有效样本大小"),
        ("EVSI / DES", "样本信息期望价值 / 离散事件仿真"),
        ("RMST", "至首份可见独立阳性报告的限制平均时间"),
    ]
    for symbol, description in glossary:
        item = doc.add_paragraph(style="P9 entry")
        item.paragraph_format.tab_stops.add_tab_stop(Cm(3.5))
        shared.text(item, symbol)
        item.add_run("\t")
        shared.text(item, description)



def chapter_title(value):
    return re.sub(r"^第\s*(\d+)\s*章\s*", r"第 \1 章　", value)


def build(out, adviser="", template=None):
    source = compose()
    lines = [s.strip() for s in source.splitlines() if s.strip()]
    file = out / "开题报告_P9.docx"
    doc = template_cover(locate_template(template, file), lines[0][2:], adviser)
    configure(doc)
    doc.core_properties.title = lines[0][2:]
    doc.core_properties.last_modified_by = "张皓轩"
    front(doc, lines)
    index, mode, i = 100, "", 1
    while i < len(lines):
        s = lines[i]
        if s.startswith("## "):
            mode = s[3:]
            first = bool(re.match(r"第\s*1\s*章", mode))
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
        elif match := re.fullmatch(r"@@MATH ([\d.]+) (.+)@@", s):
            display(doc, match[2], match[1])
        else:
            shared.text(doc.add_paragraph(style="P9 body"), s)
        i += 1
    out.mkdir(parents=True, exist_ok=True)
    doc.save(file)
    markdown = re.sub(r"^@@MATH ([\d.]+) (.+)@@$", lambda m: "$$\n" + m[2] + r"\tag{" + m[1] + "}\n$$", source, flags=re.M)
    markdown_dir = HERE if out.resolve() == OUTPUT.resolve() else out
    def relative_image(match):
        relative = Path(os.path.relpath(ROOT / match[2], markdown_dir)).as_posix()
        return f"![{match[1]}]({relative})"
    markdown = re.sub(r"!\[([^\n]+)\]\((p9/[^)]+)\)", relative_image, markdown)
    (markdown_dir / "开题报告_P9_文稿.md").write_text(markdown, encoding="utf-8")
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
    parser.add_argument("--out", type=Path, default=OUTPUT)
    parser.add_argument("--adviser", default="")
    parser.add_argument("--docx-only", action="store_true")
    parser.add_argument("--template", type=Path)
    args = parser.parse_args()
    path = build(args.out, args.adviser, args.template)
    if not args.docx_only:
        export(path)
