"""Generate the editable presentation and the synchronized Chinese Word speaking notes."""
from pathlib import Path
import csv, json, math
from pptx import Presentation
from pptx.util import Inches as I, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN,MSO_ANCHOR,MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.xmlchemy import OxmlElement
from PIL import Image
from docx import Document
from docx.shared import Cm, Pt as WordPt, RGBColor as WColor
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement as WE
from deck_content import SLIDES,slide
import deck_results

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
OUT=ROOT/'simulation/outputs'
slide('公开参考力提供了可直接复算的量级','原始标签实算',
      '按每次 Li 原子出现等权统计。三种组成的中位力模约为 0.49–0.56，P90 约为 1.05–1.14。','force',[],
      '图 1a　Oxford PBEsol 原文件。本次实算；无势预测参与，文件头未显式标记力单位。')
SLIDES.insert(6,SLIDES.pop())
slide('把整组费用折算到每个确认候选','实算结果  Ⅱ',
      '每确认费用用所有队列的合计费用除以阳性确认总数，保留了零确认队列的消耗。','efficiency',[],
      '图 7a　DES V0 情景模拟／非实验实证。累计费用与首次确认时间分别计算。')
i=next(i for i,x in enumerate(SLIDES) if x['kind']=='results')
SLIDES.insert(i+1,SLIDES.pop())
speeches=json.loads((HERE/'speaker_script.json').read_text(encoding='utf-8'))
if len(speeches)!=len(SLIDES):
    raise ValueError('Speaker script and presentation must have the same number of pages.')
for n,(item,entry) in enumerate(zip(SLIDES,speeches),1):
    if entry['page']!=n or entry['title']!=item['title'] or not entry['speech'].strip():
        raise ValueError(f'Speaker script does not match slide {n}.')
    item['talk']=entry['speech']
base={r['policy']:r for r in csv.DictReader((OUT/'policy_summary.csv').open(encoding='utf-8-sig')) if r['scenario']=='V0' and r['policy'] in ('B0','B1','B2','B3','B4')}
effects={(r['scenario'],r['policy'],r['reference'],r['metric']):r for r in csv.DictReader((OUT/'paired_effects.csv').open(encoding='utf-8-sig'))}
def f(r,k):return float(r[k])
ppt=Presentation()
ppt.slide_width,ppt.slide_height=I(13.333),I(7.5)
INK='18343E'; TEAL='0B7065'; GRAY='526872'; NAVY='24495D'; WHITE='FFFFFF'; PALE='E8F4F1'; ACC='AD6530'; PAPER='FAFBF9'
def rgb(s):return RGBColor.from_string(s)
def apply_font(r,size,color,bold=False):
    r.font.name='Microsoft YaHei';r.font.size=Pt(size);r.font.bold=bold;r.font.color.rgb=rgb(color)
    pr=r._r.get_or_add_rPr()
    for kind,face in [('a:ea','Microsoft YaHei'),('a:cs','Arial')]:
        x=OxmlElement(kind);x.set('typeface',face);pr.append(x)
def text(s,txt,x,y,w,h,size=16,color=INK,bold=False,align='left',val='middle'):
    sh=s.shapes.add_textbox(I(x),I(y),I(w),I(h));tf=sh.text_frame
    tf.margin_left=tf.margin_right=I(.01);tf.margin_top=tf.margin_bottom=I(.005)
    tf.word_wrap=True;tf.vertical_anchor=MSO_ANCHOR.MIDDLE if val=='middle' else MSO_ANCHOR.TOP
    tf.auto_size=MSO_AUTO_SIZE.NONE
    for j,t in enumerate(str(txt).split('\n')):
        p=tf.paragraphs[0] if j==0 else tf.add_paragraph()
        p.alignment={'left':PP_ALIGN.LEFT,'center':PP_ALIGN.CENTER,'right':PP_ALIGN.RIGHT}[align]
        p.space_after=Pt(0);p.space_before=Pt(0)
        r=p.add_run();r.text=t;apply_font(r,size,color,bold)
    return sh
def rect(s,x,y,w,h,fill):
    o=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,I(x),I(y),I(w),I(h))
    o.fill.solid();o.fill.fore_color.rgb=rgb(fill);o.line.fill.background();return o
def picture(s,p,x,y,w,h):
    p=Path(p)
    iw,ih=Image.open(p).size
    a=min(w/iw,h/ih);nw,nh=iw*a,ih*a
    return s.shapes.add_picture(str(p),I(x+(w-nw)/2),I(y+(h-nh)/2),I(nw),I(nh))
def native_table(s,rows,x=.67,y=2.07,w=12.0,h=4.47,fr=None):
    nr,nc=len(rows),len(rows[0])
    fr=fr or ([.22,.38,.40] if nc==3 else [1/nc]*nc)
    tb=s.shapes.add_table(nr,nc,I(x),I(y),I(w),I(h)).table
    for j,v in enumerate(fr):tb.columns[j].width=I(w*v)
    for i,row in enumerate(rows):
        rh=.53 if i==0 else (h-.53)/(nr-1);tb.rows[i].height=I(rh)
        for j,v in enumerate(row):
            c=tb.cell(i,j);c.text='';c.fill.solid();c.fill.fore_color.rgb=rgb(NAVY if i==0 else ('EDF4F3' if i%2 else 'F7F9F8'))
            c.margin_left=c.margin_right=I(.13);c.margin_top=c.margin_bottom=I(.025);c.vertical_anchor=MSO_ANCHOR.MIDDLE
            p=c.text_frame.paragraphs[0];p.space_after=Pt(0);r=p.add_run();r.text=str(v)
            size=14 if i==0 else (15 if nc<=3 else 14)
            if nr>6:size-=1
            apply_font(r,size,WHITE if i==0 else (TEAL if j==0 else INK),i==0 or (j==0 and nc<=4))
def head(s,d,n):
    rect(s,0,0,13.333,7.5,PAPER)
    rect(s,.65,.43,.25,.055,TEAL)
    text(s,d['section'],1,.24,8,.43,12,TEAL,True)
    text(s,'LPSC  /  P8',10.25,.25,2.43,.4,12,GRAY,False,'right')
    text(s,d['title'],.65,.79,12.03,.70,31,INK,True)
    text(s,d['lead'],.67,1.53,12.03,.5,15,GRAY)
    rect(s,.67,6.84,12,.013,'CBD9D6')
    text(s,d['source'],.67,6.99,11.30,.31,10,GRAY)
    text(s,f'{n:02d}',12.05,6.95,.60,.34,13,TEAL,True,'right')
def metric(s,x,y,w,value,label,desc,fg=TEAL):
    rect(s,x,y,w,1.80,'E7F3F0' if fg==TEAL else 'F6EDDF')
    text(s,label,x+.19,y+.15,w-.38,.32,14,INK,True)
    text(s,value,x+.19,y+.51,w-.38,.66,29,fg,True)
    text(s,desc,x+.19,y+1.25,w-.38,.35,13,GRAY)
def cover(s,d):
    rect(s,0,0,13.333,7.5,'F1F5F1');rect(s,.67,.73,.42,.07,TEAL)
    text(s,d['section'],1.22,.54,5,.44,15,TEAL,True)
    text(s,'氯富集硫银锗矿的\n输运分歧与序贯验证',.65,1.66,7.1,1.85,34,INK,True)
    text(s,d['lead'],.70,3.82,6.25,.90,20,NAVY)
    text(s,d['source'],.70,6.1,7,.50,15,GRAY)
    picture(s,ROOT/'figures/blender/pellet.png',7.10,.48,5.82,5.88)
    text(s,'阻挡电极与多晶压片的分解示意  ·  Blender 5.3',7.00,6.43,5.86,.32,11,GRAY,False,'center')
def render(d,n):
    s=ppt.slides.add_slide(ppt.slide_layouts[6]);k=d['kind']
    if k=='cover':cover(s,d)
    else:
        head(s,d,n)
        if k=='table' and d['section']=='材料与对照':
            native_table(s,d['body'],.66,2.35,7.03,3.62,[.16,.48,.36])
            picture(s,ROOT/'figures/oxford/lpsc_52.png',7.75,2.05,4.88,3.97)
            text(s,'Oxford 第一帧  ·  52 原子周期胞',7.84,5.96,4.66,.32,14,INK,True,'center')
            text(s,'Li 浅蓝　P 紫　S 琥珀黄　Cl 青绿',7.77,6.33,4.85,.26,11,GRAY,False,'center')
        elif k=='table':native_table(s,d['body'])
        elif k=='diagram':picture(s,ROOT/('figures/'+d['body']+'.png'),.65,2.16,12.03,4.32)
        elif k=='audit':
            native_table(s,[['数据源','本次文件核查','可用范围'],['Oxford · PBEsol','28,100 帧，三种组成；母体 22,500 帧','可作同参考计算对照，缺 x = 0.25、0.50'],['SSE–VASP / ABACUS','VASP 训练子集严格四元素母体 1,172 帧；ABACUS 母体 862 帧','须查预训练重叠和化学计量，再构造独立检验集'],['OBELiX · 实验','599 条，321 条登记 CIF；严格四元素仅三条母体','限定数据库所收记录；原始论文另有中间点'],['DaRUS–4510','14,332 次完整 CFG 块出现，6,694 种文本块','先按重复与父结构分组，再隔离留出']])
        elif k=='force':
            picture(s,ROOT/'figures/force_profile.png',.9,2.15,11.5,4.15)
            text(s,'计数单位为 Li 原子出现次数。母体 540,000　｜　氯富端元 56,000　｜　Li₇PS₆ 78,400',1.1,6.22,11.15,.4,13,GRAY,False,'center')
        elif k=='pilot':
            metric(s,.7,2.29,3.81,'3 × 2 = 6','独立制备的粉体','三个组成，各做两个独立批次')
            metric(s,4.76,2.29,3.81,'6 × 2 = 12','先导压片','每个粉体各取 L / H 两种条件')
            metric(s,8.81,2.29,3.81,'4 批 / 4 片','新批次确认','锁定 A/B 后各做两批',ACC)
            native_table(s,[['已知文献与先导样品','独立确认'],['按温度和制备条件比较文献量级。同粉体 L/H 对照检查压实敏感性。','先锁定方向、主工艺与最小可行动差，再制新批复验。区组矛盾时报告未分辨。']],.7,4.60,11.92,1.7,[.5,.5])
        elif k=='event':picture(s,OUT/'event_swimlane.png',.85,2.05,11.6,4.64)
        elif k=='results':
            rows=[['政策','限制均时 / h','中位 / P90 / h','召回率','整队列情景费 / 元']]
            for key,r in base.items():rows.append([key,f"{f(r,'restricted_h'):.2f}",f"{f(r,'first_cond_median_h'):.1f} / {f(r,'first_cond_p90_h'):.1f}",f"{100*f(r,'recall'):.2f}%",f"{f(r,'cost_cny'):,.0f}"])
            native_table(s,rows,.7,2.15,11.93,4.38,[.12,.21,.25,.16,.26])
        elif k=='efficiency':
            picture(s,OUT/'cost_time.png',.7,2.05,6.2,4.62)
            rows=[['政策','元/确认','GPU·h/确认','DFT帧/确认']]+[[k,f"{f(r,'cny_per_confirmation'):,.0f}",f"{f(r,'gpu_h_per_confirmation'):.1f}",f"{f(r,'frames_per_confirmation'):.1f}"] for k,r in base.items()]
            native_table(s,rows,6.94,2.30,5.70,3.93,[.15,.27,.29,.29])
        elif k=='delta':
            metric(s,.71,2.38,3.81,'+0.247 h','首个独立阳性确认','95% 区间  +0.196 至 +0.297',ACC)
            metric(s,4.76,2.38,3.81,'+830 元','24 候选整队列费用','95% 区间  +817 至 +844',ACC)
            metric(s,8.81,2.38,3.81,'+0.066','真合格召回增量 / 百分点','95% 区间  +0.032 至 +0.100')
            text(s,'在这组假设下，适配改善了少量召回，代价是额外的工时和支出。',.9,4.67,11.57,.65,23,INK,True)
            text(s,'现场若有明确的最低召回要求，应先锁定该要求，再比较等召回或等预算的政策。',.9,5.46,11.57,.59,16,GRAY)
        elif k=='stress':
            rows=[['同一情景中的 B4 − B3','首次确认时间差 / h（95% 区间）','整队列费用差 / 元']]
            for code,label in [('V0','基准'),('slow_acceptance','训练验收变慢'),('dft_10x','每帧 DFT 工时 ×10'),('fixed_sufficient','固定势已足够'),('exhaustive_confirmation','所有候选均确认')]:
                r=effects[code,'B4','B3','restricted_h']; c=effects[code,'B4','B3','cost_cny'];rows.append([label,f"{f(r,'difference'):+.3f}  [{f(r,'diff_lo'):+.3f}, {f(r,'diff_hi'):+.3f}]",f"{f(c,'difference'):+,.0f}"])
            native_table(s,rows,.7,2.14,11.94,4.40,[.33,.41,.26])
    s.notes_slide.notes_text_frame.text=d['talk']
for n,d in enumerate(SLIDES,1):render(d,n)
ppt.core_properties.title='氯富集硫银锗矿的输运分歧与序贯验证'
ppt.save(HERE/'汇报版开题报告_P8.pptx')

def wf(run,size,bold=False,col='23383E',face='宋体'):
    run.font.name=face;run.bold=bold;run.font.size=WordPt(size);run.font.color.rgb=WColor.from_string(col)
    fonts=run._element.get_or_add_rPr().rFonts
    for key in ('ascii','hAnsi','eastAsia','cs'):
        fonts.set(qn('w:'+key),face)
    return run
def spoken_paragraph(doc,content):
    p=doc.add_paragraph()
    p.paragraph_format.space_after=WordPt(9)
    p.paragraph_format.line_spacing=1.45
    p.paragraph_format.keep_together=True
    wf(p.add_run(content),14)
    return p
def field(p,key):
    a=WE('w:fldSimple');a.set(qn('w:instr'),key);p._p.append(a)
doc=Document();sec=doc.sections[0]
title_pr=doc.styles['Title']._element.get_or_add_pPr()
for el in list(title_pr):
    if el.tag==qn('w:pBdr'):title_pr.remove(el)
sec.page_width=Cm(21);sec.page_height=Cm(29.7);sec.left_margin=sec.right_margin=Cm(2.25)
sec.top_margin=Cm(1.85);sec.bottom_margin=Cm(1.8)
sec.header_distance=Cm(.72);sec.footer_distance=Cm(.72)
wf(sec.header.paragraphs[0].add_run('综合论文训练    /    P8 开题汇报词'),9,False,GRAY)
foot=sec.footer.paragraphs[0];foot.alignment=WD_ALIGN_PARAGRAPH.RIGHT;wf(foot.add_run('张皓轩     ·     '),9,False,GRAY);field(foot,'PAGE')
t=doc.add_paragraph(style='Title')
wf(t.add_run('开题汇报词'),22,face='黑体')
subtitle=doc.add_paragraph()
subtitle.paragraph_format.space_after=WordPt(10)
wf(subtitle.add_run('氯富集硫银锗矿的输运分歧与序贯验证'),14,False,TEAL,'黑体')
for i,d in enumerate(SLIDES):
    p=doc.add_paragraph();p.paragraph_format.keep_with_next=True;p.paragraph_format.space_before=WordPt(6)
    wf(p.add_run(f'{i+1:02d}　'),11,False,TEAL,'黑体')
    wf(p.add_run(d['title']),12,False,TEAL,'黑体')
    spoken_paragraph(doc,d['talk'])
doc.core_properties.title='P8 开题汇报词'
doc.save(HERE/'P8_逐页汇报词_现场朗读版.docx')
outline='# P8 汇报页序\n\n'+'\n'.join(f"{i:02d}. {d['title']} —— {d['lead']}" for i,d in enumerate(SLIDES,1))
(HERE/'P8_OUTLINE.md').write_text(outline+'\n',encoding='utf-8')

