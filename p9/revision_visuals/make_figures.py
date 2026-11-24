"""Redraw P9 research figures. Run with numpy and matplotlib plus a CJK font.
Source diagrams are exported as editable draw.io (native shapes) as well as SVG and PNG.
Use --model after running simulation/redesign to add policy and replay panels.
"""
import csv
from pathlib import Path
from xml.etree import ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle
import numpy as np

OUT = Path(__file__).resolve().parent
P9 = OUT.parent
ROOT = P9.parent
RANK = P9 / "ranking/outputs"
SIM = ROOT / "simulation/redesign/outputs"
font_names = {f.name for f in font_manager.fontManager.ttflist}
FACE = next(n for n in ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC"] if n in font_names)
INK, GRAY, LIGHT = "#172E3D", "#526774", "#CAD6DB"
TEAL, TPALE, BLUE, BPALE = "#08796D", "#DFF1EB", "#285985", "#E5EFF7"
OCH, OPALE, PURP = "#9D5425", "#F8E8DB", "#715181"
plt.rcParams.update({"font.family":FACE, "font.size":11.5, "axes.unicode_minus":False,
    "font.weight":"normal", "axes.spines.top":False, "axes.spines.right":False,
    "axes.labelcolor":INK, "text.color":INK, "axes.edgecolor":GRAY,
    "xtick.color":GRAY, "ytick.color":GRAY, "svg.fonttype":"none", "svg.hashsalt":"lpsc_p9_revision"})

def read(path):
    with path.open(encoding="utf-8-sig", newline="") as h:
        return list(csv.DictReader(h))

def save(fig, name, trim=False):
    args = dict(bbox_inches="tight",pad_inches=.08) if trim else {}
    for ext in ["svg","png"]:
        fig.savefig(OUT / (name + "." + ext), dpi=260, facecolor="white",
                    metadata={"Date":None} if ext == "svg" else None, **args)
    plt.close(fig)

# All diagram coordinates are on the same 1000-wide canvas in both rendering formats.
class Diagram:
    def __init__(self, name, height=405):
        self.name, self.h = name, height
        self.fig = plt.figure(figsize=(10, height/100), layout=None)
        self.ax = self.fig.add_axes((0,0,1,1))
        self.ax.set(xlim=(0,1000),ylim=(height,0),aspect="equal")
        self.ax.set_axis_off()
        self.model = ET.Element("mxGraphModel", {"pageWidth":"1000","pageHeight":str(height),"adaptiveColors":"auto"})
        self.root = ET.SubElement(self.model,"root")
        ET.SubElement(self.root,"mxCell",id="0"); ET.SubElement(self.root,"mxCell",id="1",parent="0")
        self.index = 1
    def cell(self,style,xywh,value=""):
        self.index+=1
        c=ET.SubElement(self.root,"mxCell",{"id":str(self.index),"parent":"1","vertex":"1","style":style,"value":value})
        x,y,w,h=xywh
        ET.SubElement(c,"mxGeometry",{"x":str(x),"y":str(y),"width":str(w),"height":str(h),"as":"geometry"})
        return c
    def rect(self,x,y,w,h,fc,ec="none",lw=1):
        self.ax.add_patch(Rectangle((x,y),w,h,facecolor=fc,edgecolor=ec,linewidth=lw))
        self.cell(f"rounded=0;html=1;fillColor={fc};strokeColor={ec};strokeWidth={lw};",(x,y,w,h))
    def dot(self,x,y,r,fc,ec="none"):
        self.ax.add_patch(Circle((x,y),r,facecolor=fc,edgecolor=ec,lw=1))
        self.cell(f"ellipse;html=1;fillColor={fc};strokeColor={ec};",(x-r,y-r,2*r,2*r))
    def line(self,x,y,u,v,c=GRAY,arrow=False,dash=False,lw=1.45):
        self.ax.add_patch(FancyArrowPatch((x,y),(u,v),arrowstyle="-|>" if arrow else "-",shrinkA=0,shrinkB=0,
                    color=c,linewidth=lw,linestyle="--" if dash else "-",mutation_scale=14))
        self.index+=1
        a=ET.SubElement(self.root,"mxCell",{"id":str(self.index),"edge":"1","parent":"1","style":f"html=1;endArrow={'block' if arrow else 'none'};endFill=1;strokeColor={c};strokeWidth={lw};dashed={int(dash)};"})
        geo=ET.SubElement(a,"mxGeometry",{"relative":"1","as":"geometry"})
        for xx,yy,k in [(x,y,"sourcePoint"),(u,v,"targetPoint")]:
            ET.SubElement(geo,"mxPoint",{"x":str(xx),"y":str(yy),"as":k})
    def text(self,x,y,value,size=13,c=INK,bold=False,align="left"):
        self.ax.text(x,y,value,fontsize=size,color=c,ha=align,va="center",fontweight="bold" if bold else "normal",linespacing=1.45)
        lines=value.split("\n"); w=max(sum(1 if ord(ch)>255 else .58 for ch in line) for line in lines)*size*1.55+12
        h=len(lines)*size*1.95
        left=x-3 if align=="left" else x-w/2 if align=="center" else x-w+3
        self.cell(f"text;html=1;align={align};verticalAlign=middle;whiteSpace=nowrap;strokeColor=none;fillColor=none;fontColor={c};fontFamily={FACE};fontSize={size*1.39:.1f};fontStyle={int(bold)};",(left,y-h/2,w,h),value.replace("\n","<br>"))
    def save(self):
        save(self.fig,self.name)
        f=ET.Element("mxfile",{"host":"app.diagrams.net"}); pg=ET.SubElement(f,"diagram",{"name":self.name, "id":self.name}); pg.append(self.model)
        ET.ElementTree(f).write(OUT/(self.name+".drawio"), encoding="utf-8",xml_declaration=True)

def architecture():
    d=Diagram("architecture",374)
    labels=[("计算对象","同一组成的无序结构族","占位、空位、独立轨迹",BLUE,BPALE),
            ("实验对象","同一工艺的独立粉体","物相、压实、压片电导",OCH,OPALE),
            ("决策对象","七种组成竞争验证资源","剩余预算、队列、冻结时刻",TEAL,TPALE)]
    for i,(a,b,c,color,pale) in enumerate(labels):
        x=12+i*332
        d.rect(x,11,313,137,pale);d.text(x+15,32,a,14,color,True)
        d.text(x+15,77,b,16,INK,True);d.text(x+15,119,c,12,GRAY)
        d.line(x+156,149,x+156,176,color,True)
    d.text(168,201,"优势、反向、近似并列",14,BLUE,True,"center")
    d.text(500,201,"同条件下的点值或批间区间",14,OCH,True,"center")
    d.text(832,201,"锁定下一项行动或等待",14,TEAL,True,"center")
    d.line(166,222,166,246,BLUE);d.line(500,222,500,246,OCH)
    d.line(166,246,500,246,GRAY);d.line(335,246,335,267,GRAY,True)
    d.text(335,286,"定位足以改变行动的证据分歧",14,INK,True,"center")
    d.line(556,286,832,286,TEAL,True);d.line(832,282,832,224,TEAL,True)
    d.rect(12,328,977,37,"#F2F5F5");d.text(500,347,"冻结前只使用已发布的结果；锁定后用独立新批检验当时的选择。",12,GRAY,False,"center")
    d.save()

def transport():
    d=Diagram("transport",383)
    for x in [334,666]: d.line(x,18,x,315,LIGHT)
    for x,title,sub,cl in [(16,"占位与空位","相同化学计量允许多种局域排列",BLUE),(350,"独立 MD 轨迹","按结构族、模型及初态保存",TEAL),(682,"压片与宏观电导","独立粉体批次定义湿端样本",OCH)]:
        d.text(x,27,title,16,cl,True);d.text(x,58,sub,11.6,GRAY)
    for layer in [0,1]:
        sx=52+layer*38;sy=98+layer*22
        for row in range(3):
            for col in range(4):
                xx=sx+col*59;yy=sy+row*44
                if col<3:d.line(xx,yy,xx+59,yy,LIGHT,lw=.9)
                if row<2:d.line(xx,yy,xx,yy+44,LIGHT,lw=.9)
                if layer==0:d.line(xx,yy,xx+38,yy+22,LIGHT,lw=.8)
                color=BLUE if (col+row+layer*2)%3==0 else OCH
                d.dot(xx,yy,6,color)
    for i,(t,c) in enumerate([("S 位点",OCH),("Cl 位点",BLUE)]):
        d.dot(76+i*105,252,5,c);d.text(88+i*105,252,t,11)
    d.text(166,290,"示意排列，未使用精修坐标",11.4,GRAY,False,"center")
    for j,label in enumerate(["初态 1","初态 2","初态 3"]):
        y=111+j*46;d.text(356,y,label,11,GRAY)
        a=np.array([0,3,-2,-5,2,6,1,3,0])*2
        for k in range(8):
            d.line(423+k*26,y+a[(k+2*j)%9],449+k*26,y+a[(k+1+2*j)%9],TEAL,lw=1.2)
    d.text(509,252,"保留族内轨迹间差异",13,TEAL,True,"center")
    d.text(509,290,"集体电荷位移 → 输运条件分布",11.4,GRAY,False,"center")
    d.rect(722,100,225,14,INK);d.rect(722,202,225,14,INK);d.rect(722,114,225,88,OPALE)
    for xs in [(744,114,763,158),(763,158,739,202),(763,158,813,167),(795,114,813,167),(813,167,803,202),(850,114,836,144),(836,144,813,167),(836,144,882,166),(882,166,875,202),(908,114,882,166),(882,166,947,181)]:
        d.line(*xs,OCH,lw=1.0)
    d.dot(803,148,5,"white",OCH);d.dot(864,177,4,"white",OCH);d.dot(925,162,5,"white",OCH)
    d.text(834,252,"阻挡电极／晶粒／孔隙",13,OCH,True,"center")
    d.text(834,290,"厚度、面积与拟合阻抗 → 总电导",11.4,GRAY,False,"center")
    d.rect(12,331,977,40,"#F2F5F5");d.text(500,351,"配方级比较共享名义组成与工艺条件；多晶体的连通性和晶界需要另外建模。",12,GRAY,False,"center")
    d.save()

def diagnosis():
    d=Diagram("diagnosis",430)
    d.text(18,22,"竞争解释",14,GRAY,True);d.text(359,22,"最小的区分性观测",14,GRAY,True);d.text(710,22,"允许改变的对象",14,GRAY,True)
    groups=[("物相或占位不相容","物相复核／留出占位观测","支持集与结构权重",BLUE,BPALE),
            ("短程迁移采样不足","独立启动、有效跨笼跳跃","轨迹长度与采样预算",TEAL,TPALE),
            ("成形或测量异常","同粉体分片／装夹复测","宏观映射与测量判断",OCH,OPALE),
            ("局域势造成可行动偏差","同构型独立 DFT 力及相对能","补标、适配和独立验收",PURP,"#EFEAF4")]
    for i,(cause,measure,change,c,pale) in enumerate(groups):
        y=47+75*i;d.rect(14,y,966,60,"#F6F8F8" if i%2==0 else "white")
        d.rect(14,y,7,60,c);d.text(32,y+30,cause,13,INK,True);d.line(279,y+30,329,y+30,c,True)
        d.text(350,y+30,measure,13);d.line(640,y+30,692,y+30,c,True);d.text(712,y+30,change,13,c,True)
    d.rect(14,355,966,60,"#EFF3F3");d.text(30,377,"多因可同时存在。",12.5,INK,True)
    d.text(30,399,"只有独立原子参考支持、验收可做且发布赶得上冻结时，才提交定向训练。",12.2,GRAY)
    d.save()

def network():
    d=Diagram("network",390)
    cols=[(22,"证据申请"),(228,"资源预约／排队"),(465,"执行"),(680,"审核发布"),(874,"决策")]
    for x,s in cols:d.text(x,26,s,14,INK,True)
    for i,(y,lead,t1,t2,con,c,pale) in enumerate([
        (76,"结构与粉体","仪器、样品","结构或 EIS","结构／宏观",OCH,OPALE),
        (159,"原子计算","GPU 或 DFT","MD 或独立参考","原子／轨迹",BLUE,BPALE),
        (242,"模型更新","GPU、标签、审核","训练与盲测","版本及重算",TEAL,TPALE)]):
        d.rect(15,y-20,963,57,pale);d.text(27,y+8,lead,13,c,True)
        d.line(160,y+8,211,y+8,c,True);d.text(228,y+8,t1,12)
        d.line(387,y+8,445,y+8,c,True);d.text(457,y+8,t2,12)
        d.line(598,y+8,655,y+8,c,True);d.text(677,y+8,con,12)
        d.line(817,y+8,859,y+8,c,True);d.text(874,y+8,"重规划",12,c,True)
    d.line(666,52,666,285,GRAY,False,True,lw=1.3)
    d.text(15,321,"同一资源服务不同组成，提前占用会延迟另一项任务。",13,INK,True)
    d.text(15,352,"日历记录提交、开始、完成、质控发布与冻结。只有发布事件更新可见证据。",12.4,GRAY)
    d.save()

def two_simulations():
    d=Diagram("two_simulations",383)
    d.rect(9,14,482,303,BPALE);d.rect(509,14,482,303,TPALE)
    d.text(27,43,"决策时前瞻",17,BLUE,True);d.text(529,43,"政策评价",17,TEAL,True)
    d.text(28,79,"输入  当前已发布证据和资源日历",12,INK);d.text(529,79,"输入  共享的潜在队列与外层随机机制",12,INK)
    d.dot(58,180,7,BLUE);d.line(65,180,144,132,BLUE,True);d.line(65,180,144,228,BLUE,True)
    for y,sub in [(131,"观测阳性"),(229,"观测阴性")]:
        d.text(151,y,sub,12,BLUE);d.line(248,y,285,y-19,BLUE,True);d.line(248,y,285,y+19,BLUE,True)
    for y,t in [(111,"备选后续行动"),(150,"等待或锁定"),(210,"补一项证据"),(249,"改选／停止")]:d.text(295,y,t,12)
    for i,t in enumerate(["静态门禁","单步政策","条件两步"]):
        y=115+i*55;d.text(533,y+13,t,12,TEAL,True);d.line(635,y+13,717,y+13,TEAL,True)
        d.text(729,y+13,"执行事件 → 冻结 → 新批",12)
    d.text(28,289,"对条件结果积分，实际只执行首项行动。",12,BLUE,True)
    d.text(529,289,"在同一外层队列上计算配对差。",12,TEAL,True)
    d.text(500,353,"外层真值仅用于生成观测和事后评分。策略读取审核后发布的观测。",12.8,INK,True,"center")
    d.save()

def validation():
    d=Diagram("validation",347)
    d.text(12,24,"标准工艺筛选",16,BLUE,True);d.text(397,24,"锁定比较",16,TEAL,True);d.text(685,24,"独立确认",16,OCH,True)
    for j,label in enumerate(["区组 1","区组 2"]):
        y=90+j*68;d.text(12,y,label,12,GRAY)
        for i in range(7):
            x=94+i*36;d.dot(x,y,12,BPALE,BLUE)
            d.text(x,y,f".{i}" if i else "0",8.4,BLUE,False,"center")
    d.line(335,123,384,123,TEAL,True);d.rect(395,68,209,113,TPALE)
    d.text(500,102,"锁定 A、B 及方向",13,TEAL,True,"center")
    d.text(500,146,"登记阈值与版本",12,INK,False,"center")
    d.line(613,123,668,123,TEAL,True)
    for i,t in enumerate(["A，新批 1","B，新批 1","A，新批 2","B，新批 2"]):
        x=678+i%2*150;y=70+i//2*63
        d.rect(x,y,140,43,OPALE);d.text(x+70,y+21,t,12,OCH,False,"center")
    d.text(15,227,"每个圆点代表一个独立粉体批次；同粉体分样和 EIS 技术重复另记父键。",12.4,GRAY)
    d.rect(12,267,976,61,"#F0F4F3");d.text(26,286,"单名额情景仿真只研究一次预约决策。",12.8,INK,True)
    d.text(26,310,"两组成复验是湿实验计划，需在现场确认资源和最小可行动差后实施。",12,GRAY)
    d.save()
