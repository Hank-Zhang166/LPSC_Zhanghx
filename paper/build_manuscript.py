"""Build the editable P8 written proposal and export with Microsoft Word on Windows."""
import argparse
import base64
import csv
import os
import re
import subprocess
from pathlib import Path
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.shared import Cm, Pt, RGBColor
from docx.text.run import Run
from PIL import Image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
HEADING_FACE="SimHei"
TITLE_STYLES={"Title","Heading 1","Heading 2","Heading 3","P8 front","P8 cap","P8 entry","P8 table header"}
SHORT={
    "图 1.1":"从原子构型、晶内轨迹到压片测量",
    "图 2.1":"三个组成的 Li 参考力模分位数",
    "图 3.1":"DPA4 的输入张量、能量与力及其下游解释",
    "图 3.2":"源域与目标域的监督、梯度更新及验收",
    "图 5.1":"筛查粉体和新确认批次的事件泳道",
    "图 5.2":"五种政策的首次确认时间与召回率",
    "图 5.3":"定向适配相对固定势的敏感性",
    "表 2.1":"公开数据的组成覆盖与首轮用途",
    "表 2.2":"同名义组成的历史输运对照及其比较条件",
    "表 4.1":"实验证据与可选择的后续动作",
    "表 5.1":"五种政策的时间、费用和准确性",
    "表 5.2":"B4 相对三种基线的配对差",
    "表 5.3":"阶段门禁、队列、结构、标签和更新时机消融"}

def xml(tag,**attrs):
    node=OxmlElement("w:"+tag)
    for k,v in attrs.items(): node.set(qn("w:"+k),str(v))
    return node

def font(style,cn="宋体",en="Times New Roman",pt=12,bold=False):
    style.font.name=en
    style.font.size=Pt(pt)
    style.font.bold=bold
    style.font.color.rgb=RGBColor(0,0,0)
    prop=style.element.get_or_add_rPr()
    fonts=prop.find(qn("w:rFonts"))
    if fonts is None:
        fonts=xml("rFonts");prop.append(fonts)
    for k,v in (("eastAsia",cn),("ascii",en),("hAnsi",en),("cs",en)):
        fonts.set(qn("w:"+k),v)
    fonts.set(qn("w:hint"),"eastAsia")

def simhei(target):
    """Set every script slot to genuine SimHei Regular; theme slots override names in Word."""
    rp=target.element.get_or_add_rPr()
    fonts=rp.rFonts
    if fonts is None:
        fonts=xml("rFonts");rp.insert(0,fonts)
    for key in list(fonts.attrib):
        if key.rsplit("}",1)[-1].lower().endswith("theme"):
            del fonts.attrib[key]
    for slot in ("ascii","hAnsi","eastAsia","cs"):
        fonts.set(qn("w:"+slot),HEADING_FACE)
    fonts.set(qn("w:hint"),"eastAsia")
    target.font.bold=False
    target.font.cs_bold=False
    target.font.italic=False
    target.font.cs_italic=False

def fstyle(style,align=WD_ALIGN_PARAGRAPH.LEFT,first=0,before=0,after=0,line=20,keep=False):
    pf=style.paragraph_format
    pf.alignment=align;pf.first_line_indent=Pt(first);pf.space_before=Pt(before);pf.space_after=Pt(after)
    pf.line_spacing=Pt(line) if line else 1.;pf.keep_with_next=keep;pf.widow_control=True

def field(paragraph,code,placeholder="1"):
    r=paragraph.add_run()
    r._r.append(xml("fldChar",fldCharType="begin"))
    instr=xml("instrText");instr.set(qn("xml:space"),"preserve");instr.text=" "+code+" "
    r._r.append(instr)
    r._r.append(xml("fldChar",fldCharType="separate"))
    node=xml("t");node.text=placeholder;r._r.append(node)
    r._r.append(xml("fldChar",fldCharType="end"))

def bmark(p,name,idx):
    s=xml("bookmarkStart",id=idx,name=name)
    if p._p.pPr is None:p._p.insert(0,s)
    else:p._p.insert(1,s)
    p._p.append(xml("bookmarkEnd",id=idx))

def secsetup(s,cover=False,num=None):
    s.page_width=Cm(21);s.page_height=Cm(29.7)
    s.top_margin=Cm(3.8 if cover else 3);s.bottom_margin=Cm(3.2 if cover else 3)
    s.left_margin=s.right_margin=Cm(3);s.gutter=Cm(.2 if cover else 0.)
    s.footer_distance=Cm(1.5)
    s.header_distance=Cm(1.7)
    if num:
        s.footer.is_linked_to_previous=False
        pag=s._sectPr.find(qn("w:pgNumType"))
        if pag is not None:s._sectPr.remove(pag)
        s._sectPr.append(xml("pgNumType",fmt=num,start=1))
        p=s.footer.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent=Pt(0)
        field(p,"PAGE")

def clean(s):
    return re.sub(r"\*\*|`","",s.strip())

def plain_text(p,s):
    """Preserve uncommon scientific glyphs through explicit math-font runs."""
    for part in re.split(r"([₀-₉₋₊ₓᵢ⁰¹²³⁴⁵⁶⁷⁸⁹⁻ᵀ∂ΣΞ√≥≤∝Åθ]+)",clean(s)):
        if not part:continue
        r=p.add_run(part)
        if re.match(r"^[₀-₉₋₊ₓᵢ⁰¹²³⁴⁵⁶⁷⁸⁹⁻ᵀ∂ΣΞ√≥≤∝Åθ]",part):
            r.font.name="Cambria Math"
            r._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"),"Cambria Math")

def linked_run(p,label,anchor=None,url=None,raised=False):
    link=xml("hyperlink")
    if anchor:
        link.set(qn("w:anchor"),anchor)
    if url:
        link.set(qn("r:id"),p.part.relate_to(url,RT.HYPERLINK,is_external=True))
    run=p.add_run(label)
    run.font.superscript=raised
    link.append(run._r)
    p._p.append(link)

def text(p,s):
    # Link numbered inline citations, leaving numerical simulation intervals intact.
    pattern=r"(\[[1-9]\d*(?:[,–-][1-9]\d*)*\])"
    for part in re.split(pattern,clean(s)):
        if not part:
            continue
        if re.fullmatch(pattern,part):
            for token in re.split(r"(\d+)",part):
                if token.isdigit():
                    linked_run(p,token,anchor="Biblio"+token,raised=True)
                elif token:
                    p.add_run(token).font.superscript=True
        else:
            # This helper preserves spaces at citation boundaries.
            if part[:1].isspace(): p.add_run(" ")
            plain_text(p,part)
            if part[-1:].isspace(): p.add_run(" ")

def bibliography_entry(p,s):
    number=re.match(r"\[(\d+)\]",s)[1]
    # Publication records carry one stable resolver or official resource link.
    body,sep,url=s.rpartition(" https://")
    if sep:
        plain_text(p,body)
        p.add_run(" ")
        url="https://"+url
        label=("DOI: "+url.removeprefix("https://doi.org/")) if url.startswith("https://doi.org/") else url
        linked_run(p,label,url=url)
    else:
        plain_text(p,s)
    bmark(p,"Biblio"+number,1000+int(number))

def table(doc,data,fractions=None,compact=False):
    k=len(data[0])
    fractions=fractions or [1/k]*k
    tbl=doc.add_table(rows=0,cols=k)
    tbl.autofit=False
    tbl.alignment=WD_TABLE_ALIGNMENT.CENTER
    for i,f in enumerate(fractions):tbl.columns[i].width=Cm(15*f)
    pr=tbl._tbl.tblPr
    borders=xml("tblBorders")
    for edge,typ,sz in (("top","single",12),("bottom","single",12),("insideH","nil",0),
                       ("left","nil",0),("right","nil",0),("insideV","nil",0)):
        borders.append(xml(edge,val=typ,sz=sz,color="253E44"))
    pr.append(borders)
    mar=xml("tblCellMar")
    for a,sz in (("top",55),("bottom",55),("left",55),("right",55)):
        mar.append(xml(a,w=sz,type="dxa"))
    pr.append(mar)
    for rownum,row in enumerate(data):
        cells=tbl.add_row().cells
        rp=tbl.rows[-1]._tr.get_or_add_trPr();rp.append(xml("cantSplit"))
        if rownum==0:rp.append(xml("tblHeader",val=1))
        for i,value in enumerate(row):
            cell=cells[i];cell.width=Cm(15*fractions[i])
            cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p=cell.paragraphs[0];p.style="P8 table header" if rownum==0 else "P8 table"
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER if (compact or rownum==0) else WD_ALIGN_PARAGRAPH.LEFT
            text(p,value)
            if rownum==0:
                cp=cell._tc.get_or_add_tcPr()
                b=xml("tcBorders");b.append(xml("bottom",val="single",sz=6,color="677A7F"));cp.append(b)
    return tbl

def readcsv(name):
    with (ROOT/"simulation/outputs"/name).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def numbers():
    summary={r["policy"]:r for r in readcsv("policy_summary.csv") if r["scenario"]=="V0"}
    eff={(r["policy"],r["reference"],r["metric"]):r for r in readcsv("paired_effects.csv") if r["scenario"]=="V0"}
    base=[["政策","RMST / h\n[95% 区间]","中位数 / P90\n（h）","队列费用\n（元）","真合格\n召回率"]]
    for p in ("B0","B1","B2","B3","B4"):
        r=summary[p]
        f=lambda x:float(r[x])
        base.append([p,f"{f('restricted_h'):.2f}\n[{f('restricted_h_lo'):.2f}, {f('restricted_h_hi'):.2f}]",
                     f"{f('first_cond_median_h'):.2f} / {f('first_cond_p90_h'):.2f}",f"{f('cost_cny'):,.0f}",f"{f('recall')*100:.2f}%"])
    def val(a,b,m,digits=2,factor=1,ci=True):
        r=eff[a,b,m]
        s=f"{float(r['difference'])*factor:+,.{digits}f}"
        if ci:s+=f"\n[{float(r['diff_lo'])*factor:,.{digits}f}, {float(r['diff_hi'])*factor:,.{digits}f}]"
        return s
    delta=[["政策对照","限制平均时间差\n（h）","整队列费用差\n（元）","召回率差\n（百分点）"]]
    for b in ("B1","B2","B3"):
        delta.append([f"B4 − {b}",val("B4",b,"restricted_h",3),val("B4",b,"cost_cny",0),val("B4",b,"recall",3,100)])
    abl=[["机制与对照","时间差（h）","费用差（元）","召回差（百分点）"]]
    for a,b,n in [("B1","B0","初相门禁"),("B3","B3-no-queue","队列与截止"),("B3","B3-no-structure","追加结构复核"),
                  ("B4","B4-random-label","定向标签选择"),("B4","B4-immediate","等待合批更新")]:
        abl.append([n,val(a,b,"restricted_h",2,ci=False),val(a,b,"cost_cny",0,ci=False),val(a,b,"recall",3,100,False)])
    return {"@BASE_TABLE":(base,[.11,.27,.25,.2,.17]),"@DELTA_TABLE":(delta,[.16,.3,.28,.26]),
            "@ABLATION_TABLE":(abl,[.28,.22,.24,.26])}

def format_document(d):
    styles=d.styles
    normal=styles["Normal"];font(normal);fstyle(normal,WD_ALIGN_PARAGRAPH.JUSTIFY,24)
    for name,cn,en,pt,al,first,bef,aft,ln,bold,keep in [
      ("Title",HEADING_FACE,HEADING_FACE,26,1,0,0,12,0,False,False),
      ("Heading 1",HEADING_FACE,HEADING_FACE,16,1,0,24,18,0,False,True),
      ("Heading 2",HEADING_FACE,HEADING_FACE,14,0,0,24,6,20,False,True),
      ("Heading 3",HEADING_FACE,HEADING_FACE,12,0,0,13,4,20,False,True),
      ("P8 front",HEADING_FACE,HEADING_FACE,16,1,0,24,18,0,False,True),
      ("P8 cap",HEADING_FACE,HEADING_FACE,10.5,1,0,6,10,0,False,False),
      ("P8 table","宋体","Times New Roman",10.5,0,0,0,0,14,False,False),
      ("P8 table header",HEADING_FACE,HEADING_FACE,10.5,0,0,0,0,14,False,False),
      ("P8 reference","宋体","Times New Roman",10.5,0,0,0,4,16,False,False),
      ("P8 entry",HEADING_FACE,HEADING_FACE,12,0,0,0,0,20,False,False),
      ("P8 small","宋体","Times New Roman",11,0,0,3,5,17,False,False)]:
        st=styles[name] if name in styles else styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH)
        font(st,cn,en,pt,bold);fstyle(st,al,first,bef,aft,ln,keep)
        if name in TITLE_STYLES:simhei(st)
        for node in list(st.element.iter()):
            if node.tag==qn("w:pBdr"):
                node.getparent().remove(node)
        if name=="P8 reference":st.paragraph_format.keep_together=True
    secsetup(d.sections[0],True)
    # TOC result paragraphs are regenerated by Word when the field is updated.
    for level in (1,2):
        name=f"TOC {level}"
        st=styles[name] if name in styles else styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH)
        simhei(st)
    props=d.core_properties
    props.title="氯富集硫银锗矿的输运分歧与序贯验证"
    props.subject="综合论文训练开题报告 P8"
    props.author="张皓轩"

def cover(d,title):
    def cent(s,style="Normal",pt=18,cn="宋体",before=0,after=0,bold=False):
        p=d.add_paragraph(style=style)
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.space_before=Pt(before)
        p.paragraph_format.space_after=Pt(after);p.paragraph_format.line_spacing=1.25
        r=p.add_run(s);font(r,cn,"Times New Roman",pt,bold)
        if cn=="黑体":simhei(r)
    cent("综 合 论 文 训 练",pt=22,cn="黑体",before=16,after=40)
    cent("氯富集硫银锗矿的输运分歧\n与序贯验证",style="Title",pt=26,cn="黑体",after=24)
    cent("开 题 报 告",pt=21,cn="黑体",after=74)
    for label,name in (("系　　别","工业工程系"),("专　　业","工业工程"),("姓　　名","张皓轩"),("指导教师","")):
        p=d.add_paragraph()
        p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.left_indent=Cm(3.6)
        p.paragraph_format.space_after=Pt(7);p.paragraph_format.line_spacing=1.12
        r=p.add_run(label+"　　"+name);font(r,"仿宋","Times New Roman",16)
    cent("二〇二六年十一月",pt=16,before=42)

def front(d,lines):
    secsetup(d.add_section(WD_SECTION.NEW_PAGE),num="upperRoman")
    d.add_paragraph("目　录","P8 front")
    toc=d.add_paragraph(style="P8 entry")
    field(toc,'TOC \\o "1-2" \\h \\z','请在 Word 中更新目录')
    for label,prefix in (("插图清单","图 "),("附表清单","表 ")):
        p=d.add_paragraph(label,"P8 front");p.paragraph_format.page_break_before=True
        for key,name in SHORT.items():
            if not key.startswith(prefix):continue
            p=d.add_paragraph(style="P8 entry");p.paragraph_format.tab_stops.add_tab_stop(Cm(14.8),WD_TAB_ALIGNMENT.RIGHT,WD_TAB_LEADER.DOTS)
            text(p,key+"　"+name)
            p.add_run("\t")
            field(p,"PAGEREF "+bookmark(key)+" \\h")
    p=d.add_paragraph("符号和缩略语说明","P8 front");p.paragraph_format.page_break_before=True
    entries=[["符号或简称","本报告采用的含义"],
        ["DPA4 / SeZM","原子间势的架构及其等变描述符，须另选具体权重。"],
        ["DFT / MD","密度泛函理论 / 分子动力学。前者提供参考标签，后者给出统计轨迹。"],
        ["E / F / Ξ","构型能量 / 原子力 / virial，分别以 eV、eV/Å、eV 计。"],
        ["MSD / Dself","均方位移 / 自扩散系数，按轨迹估算并报告统计区间。"],
        ["EIS / XRD","电化学阻抗谱 / X 射线衍射，在制样和质控条件下解释。"],
        ["QC / DES","质量控制 / 离散事件仿真，区分任务完成和结果可见时点。"],
        ["RMST","截至 480 h 的首次独立阳性确认限制平均时间。"],
        ["B0–B4","系统政策对照，从固定全评价到允许定向势适配。"]]
    table(d,entries,[.24,.76])

def bookmark(key):
    n=re.search(r"(\d+)\.(\d+)",key)
    return ("Fig" if key.startswith("图") else "Tab")+n[1]+"_"+n[2]

def caption(d,s,idx,above=False):
    p=d.add_paragraph(style="P8 cap")
    if above:p.paragraph_format.keep_with_next=True
    text(p,s)
    key=re.match(r"(?:图|表) \d+\.\d+",s)[0]
    bmark(p,bookmark(key),idx)

def build(out):
    lines=[s.strip() for file in ("manuscript.md","manuscript_des.md") for s in (HERE/file).read_text(encoding="utf-8-sig").splitlines() if s.strip()]
    doc=Document();format_document(doc);cover(doc,lines[0][2:]);front(doc,lines)
    lookup=numbers()
    i=1; mode="";mark=200
    while i<len(lines):
        s=lines[i]
        if s.startswith("#### "):
            p=doc.add_paragraph(style="Heading 3");text(p,s[5:])
        elif s.startswith("### "):
            p=doc.add_paragraph(style="Heading 2");text(p,s[4:])
        elif s.startswith("## "):
            label=s[3:];mode=label
            if label.startswith("第1章"):
                secsetup(doc.add_section(WD_SECTION.NEW_PAGE),num="decimal")
            p=doc.add_paragraph(label,style="P8 front" if label=="摘要" else "Heading 1")
            if not label.startswith("第1章"):p.paragraph_format.page_break_before=True
        elif s.startswith("!["):
            m=re.match(r"!\[(.+)\]\(([^)]+)\)",s)
            path=ROOT/m[2]
            assert path.is_file(),path
            with Image.open(path) as img:w,h=img.size
            width=min(15.0,9.4*w/h)
            if path.name=="sensitivity.png":
                width=min(width,13.6)
            p=doc.add_paragraph()
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.line_spacing=1
            p.paragraph_format.space_before=Pt(7);p.paragraph_format.keep_with_next=True
            pic=p.add_run().add_picture(str(path),width=Cm(width))
            pic._inline.docPr.set("descr",m[1])
            caption(doc,m[1],mark);mark+=1
        elif s.startswith("|") or s in lookup:
            compact=s in lookup
            if compact:
                data,fractions=lookup[s]
            else:
                data=[]
                while i<len(lines) and lines[i].startswith("|"):
                    vals=[v.strip() for v in lines[i].strip("|").split("|")]
                    if not all(re.fullmatch(r"[- :]+",v) for v in vals):data.append(vals)
                    i+=1
                i-=1
                fractions=[.23,.40,.37] if len(data[0])==3 else None
            assert lines[i+1].startswith("表 ")
            i+=1;cap=lines[i]
            key=re.match(r"表 \d+\.\d+",cap)[0]
            caption(doc,key+"　"+SHORT[key],mark,above=True);mark+=1
            table(doc,data,fractions,compact)
            note=cap.split("　",1)[1]
            p=doc.add_paragraph(style="P8 small");p.add_run("注　");text(p,note)
        elif s.startswith("[") and mode.startswith("参考文献"):
            p=doc.add_paragraph(style="P8 reference")
            p.paragraph_format.left_indent=Pt(20);p.paragraph_format.first_line_indent=Pt(-20)
            bibliography_entry(p,s)
        else:
            p=doc.add_paragraph(style="P8 small" if s.startswith("关键词") else "Normal");text(p,s)
        i+=1
    out.mkdir(parents=True,exist_ok=True)
    # Directly format title runs as well, including hyperlinks and field placeholders.
    for paragraph in (*doc.paragraphs,*(p for t in doc.tables for row in t.rows for c in row.cells for p in c.paragraphs)):
        if paragraph.style.name in TITLE_STYLES:
            for node in paragraph._p.iter(qn("w:r")):
                simhei(Run(node,paragraph))
    file=out/"开题报告_P8.docx"
    doc.save(file)
    return file

def export(file):
    # Separate hidden Word instance. Only this explicitly opened file is saved and closed.
    ps=r"""
$ErrorActionPreference='Stop'
$w=New-Object -ComObject Word.Application
$w.Visible=$false
$w.DisplayAlerts=0
function Set-TitleFace($font) {
  $font.Name='SimHei'
  $font.NameAscii='SimHei'
  $font.NameFarEast='SimHei'
  $font.NameOther='SimHei'
  $font.NameBi='SimHei'
  $font.Bold=0
  $font.BoldBi=0
  $font.Italic=0
  $font.ItalicBi=0
}
try {
  $d=$w.Documents.Open($env:P8_WORD_INPUT,$false,$false)
  # Use Word's built-in TOC styles across localized Office installations.
  foreach ($id in @(-20,-21)) { Set-TitleFace ($d.Styles.Item([int]$id).Font) }
  $d.Repaginate()
  $d.Fields.Update() | Out-Null
  foreach ($t in $d.TablesOfContents) { $t.Update() }
  $d.Repaginate()
  $d.Fields.Update() | Out-Null
  foreach ($t in $d.TablesOfContents) {
    $t.UpdatePageNumbers()
    Set-TitleFace ($t.Range.Font)
  }
  $d.Save()
  $d.ExportAsFixedFormat($env:P8_WORD_PDF,17,$false,0,0,1,1,0,$true,$true,1,$true,$true,$false)
  $d.Close(0)
} finally { $w.Quit() }
"""
    en=dict(os.environ,P8_WORD_INPUT=str(file.resolve()),P8_WORD_PDF=str(file.with_suffix(".pdf").resolve()))
    subprocess.run(["powershell","-NoProfile","-NonInteractive","-EncodedCommand",base64.b64encode(ps.encode("utf-16-le")).decode()],env=en,check=True)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,default=HERE);p.add_argument("--docx-only",action="store_true")
    args=p.parse_args();f=build(args.out)
    if not args.docx_only:export(f)
