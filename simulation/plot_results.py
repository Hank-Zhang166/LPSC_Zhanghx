"""Build all illustrations exclusively from the recorded CSV output; Matplotlib >=3.6."""
import argparse
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.font_manager as fm
from minimal_des import ROOT,BASE_POLICIES,DEFAULT

OUT=ROOT/"simulation"/"outputs"
FONT=next((x for x in ("Microsoft YaHei","Noto Sans CJK SC","SimHei") if x in {f.name for f in fm.fontManager.ttflist}),"DejaVu Sans")
mpl.rcParams.update({"font.family":FONT,"font.size":10,"axes.spines.top":False,"axes.spines.right":False,
                     "axes.edgecolor":"#9daaad","axes.labelcolor":"#20393e","text.color":"#15383a",
                     "xtick.color":"#34565a","ytick.color":"#34565a","axes.unicode_minus":False,
                     "svg.fonttype":"none","figure.facecolor":"white","axes.facecolor":"white"})
COL=["#8a9697","#698e9b","#3f7094","#128275","#db7d42"]
NAMES=["B0 固定全评","B1 阶段门禁","B2 成本序贯","B3 动态固定势","B4 定向适配"]

def read(p):
    with p.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def output(fig,dst,name):
    for ext in ("svg","png"):
        fig.savefig(dst/(name+"."+ext),dpi=190,facecolor="white",bbox_inches="tight",pad_inches=.12)
    plt.close(fig)

def style(ax):
    ax.grid(axis="x",alpha=.2)
    ax.set_axisbelow(True)

def title(fig,left):
    fig.text(.02,1.035,left,ha="left",va="bottom",size=16,weight="bold")
    fig.text(.02,1.005,"DES V0 情景模拟 / 非实验实证",ha="left",va="top",size=9,color="#527074")

def make(dst):
    summary=read(dst/"policy_summary.csv")
    effects=read(dst/"paired_effects.csv")
    events=read(dst/"event_trace.csv")
    rows=[next(r for r in summary if r["scenario"]=="V0" and r["policy"]==p) for p in BASE_POLICIES]
    fig,axes=plt.subplots(1,2,figsize=(11,3.35),gridspec_kw={"wspace":.4})
    for ax,metric,factor,unit in zip(axes,["restricted_h","recall"],[1,100],["首次独立阳性确认的限制平均时间（h）","合格候选被正确确认（%）"]):
        x=[float(r[metric])*factor for r in rows]
        er=[(float(r[metric+"_hi"])-float(r[metric]))*factor for r in rows]
        ax.barh(range(5),x,color=COL,height=.60)
        ax.errorbar(x,range(5),xerr=er,fmt="none",color="#142e33",capsize=3,lw=1.2)
        ax.set_yticks(range(5),NAMES,fontsize=9)
        ax.invert_yaxis()
        ax.set_xlabel(unit)
        ax.set_xlim(0,max(x)*1.19)
        for k,v in enumerate(x): ax.text(v+max(x)*.032,k,f"{v:.1f}",va="center",size=9)
        style(ax)
    title(fig,"五种政策的确认速度与正确确认率")
    output(fig,dst,"policy_comparison")
    fig,ax=plt.subplots(figsize=(7.6,3.9))
    for k,r in enumerate(rows):
        x=float(r["restricted_h"]);y=float(r["cost_cny"])/10000.
        ax.errorbar(x,y,xerr=float(r["restricted_h_hi"])-x,yerr=float(r["cost_cny_hi"])/10000-y,
                    fmt="o",color=COL[k],ms=9,capsize=3)
        ax.annotate(NAMES[k],(x,y),xytext=((5,10) if k!=3 else (-55,-17)),textcoords="offset points",fontsize=9)
    ax.margins(.15,.2)
    ax.set_xlabel("首次确认限制平均时间（h）")
    ax.set_ylabel("每个 24 候选队列的资源账单（万元）")
    style(ax);title(fig,"时间与资源费用的取舍")
    output(fig,dst,"cost_time")
    fig,ax=plt.subplots(figsize=(8.2,3.5))
    keys=["furnace","xrd","staff","eis","gpu","dft"]
    arr=[[float(r["util_"+s])*100 for s in keys] for r in rows]
    im=ax.imshow(arr,aspect="auto",cmap="GnBu",vmin=0,vmax=100)
    ax.set_yticks(range(5),NAMES)
    ax.set_xticks(range(len(keys)),["合成炉","XRD","人员","EIS","共享 GPU","DFT 槽"])
    for y,row in enumerate(arr):
        for x,v in enumerate(row):
            ax.text(x,y,f"{v:.0f}%",ha="center",va="center",color="white" if v>65 else "#16343a")
    title(fig,"资源忙时占各自可用槽时的比例")
    fig.colorbar(im,ax=ax,pad=.02,label="利用率（%）",shrink=.75)
    output(fig,dst,"utilization")
    scenarios=[("V0","基准"),("late_xrd","初相发布延迟"),("gpu_slack","共享 GPU 宽松"),("fixed_sufficient","固定势已足够"),
               ("slow_acceptance","训练与验收慢"),("fail_all_fits","微调验收全部失败"),("no_gain","验收后物理增益为零"),
               ("favorable_gain","有利微调"),("dft_0.2x","DFT 0.2 倍"),("dft_10x","DFT 10 倍"),
               ("expensive_false_drop","错淘汰代价高"),("exhaustive_confirmation","强制全部确认")]
    fig,axes=plt.subplots(1,2,figsize=(9.5,5.1),sharey=True)
    for ax,(metric,unit) in zip(axes,[("restricted_h","B4 − B3 首次确认时间（h）"),("decision_loss_cny","B4 − B3 队列费用及错淘汰损失（元）")]):
        for k,(scn,label) in enumerate(scenarios):
            r=next(x for x in effects if x["scenario"]==scn and x["policy"]=="B4" and x["reference"]=="B3" and x["metric"]==metric)
            val=float(r["difference"]);lo=float(r["diff_lo"]);hi=float(r["diff_hi"])
            ax.errorbar(val,k,xerr=[[val-lo],[hi-val]],fmt="o",ms=5,color=COL[4] if val>0 else COL[3],capsize=3)
        ax.axvline(0,color="#293d42",lw=1)
        ax.set_xlabel(unit,fontsize=9)
        style(ax)
    axes[0].set_yticks(range(len(scenarios)),[v for _,v in scenarios])
    axes[0].invert_yaxis()
    title(fig,"适配相对固定势的配对效应及 95% 区间")
    output(fig,dst,"sensitivity")
    ev=[r for r in events if r["policy"]=="B4"]
    started={r["task_id"]:r for r in ev if r["event"]=="started"}
    finished={r["task_id"]:r for r in ev if r["event"]=="completed_unreviewed"}
    fig,ax=plt.subplots(figsize=(10.2,4.1))
    slots=[(r,s) for r in keys for s in range(DEFAULT["capacity"][r])]
    ends={k:0. for k in slots}
    color={"prep":"#88b7ad","synth":"#789f90","xrd":"#75aab3","press":"#8ba5bd","eis":"#5592a7",
           "short":"#dabe87","long":"#c78e58","probe":"#bc777c","labels":"#a56e91","train":"#9177a5","validate":"#a489ac","refine":"#508d7b"}
    window=120
    for tid,e in started.items():
        if tid not in finished: continue
        s=float(e["time_h"]);end=float(finished[tid]["time_h"])
        if s>=window: continue
        for rr in e["resources"].split("+"):
            slot=min([k for k in slots if k[0]==rr],key=ends.get)
            ends[slot]=end
            ax.barh(slots.index(slot),min(window,end)-s,left=s,height=.65,color=color.get(e["operation"],"#aaa"),
                    edgecolor="white",linewidth=.25)
    cn=dict(zip(keys,["炉","XRD","人员","EIS","共享 GPU","DFT"]))
    ax.set_yticks(range(len(slots)),[cn[k]+str(i+1) for k,i in slots])
    ax.invert_yaxis();ax.set_xlim(0,window);ax.set_xlabel("队列启动后的时间（h）；切片显示前 120 h")
    from matplotlib.patches import Patch
    ops=["synth","xrd","press","eis","short","long","probe","labels","train"]
    labs=["合成","初相","制片","EIS","短 MD","长 MD","DFT 检查","DFT 标签","微调"]
    ax.legend(handles=[Patch(color=color[k],label=v) for k,v in zip(ops,labs)],loc="upper center",bbox_to_anchor=(.5,-.19),ncol=9,fontsize=7,frameon=False)
    title(fig,f"B4 单次运行的资源甘特图 · 随机种子 {ev[0]['seed']}")
    output(fig,dst,"resource_gantt")
    # One actual independent-confirmed sample provides an unambiguous two-batch trace.
    candidate=next((r["candidate_id"] for r in ev if r["event"]=="independent_decision" and r["detail"]=="True"),ev[0]["candidate_id"])
    mine=[r for r in ev if r["candidate_id"]==candidate and r["operation"] in ("synth","xrd","eis","short","long","press")]
    ykeys=[]
    for e in mine:
        tag=(e["sample_id"],e["operation"])
        if tag not in ykeys: ykeys.append(tag)
    fig,ax=plt.subplots(figsize=(9.5,max(3.2,len(ykeys)*.28)))
    statuses=[("queued","入队","#9ea6ab","|"),("started","开始","#376f83","o"),("completed_unreviewed","完成","#d38048","s"),("qc_released","发布","#16816c","D")]
    for event,label,cc,marker in statuses:
        records=[e for e in mine if e["event"]==event]
        ax.scatter([float(e["time_h"]) for e in records],[ykeys.index((e["sample_id"],e["operation"])) for e in records],
                   label=label,c=cc,marker=marker,s=32 if event!="qc_released" else 15,zorder=3)
    for k,(bat,op) in enumerate(ykeys):
        ts=[float(e["time_h"]) for e in mine if e["sample_id"]==bat and e["operation"]==op]
        ax.hlines(k,min(ts),max(ts),color="#b6c6c6",lw=2,zorder=1)
    frozen=next(e for e in ev if e["candidate_id"]==candidate and e["event"]=="window_frozen")
    ax.axvline(float(frozen["time_h"]),color="#8a6581",ls="--",lw=1,label="冻结")
    zh={"synth":"合成","xrd":"XRD","eis":"EIS","short":"短 MD","long":"长 MD","press":"制片"}
    ax.set_yticks(range(len(ykeys)),[("确认批" if "IND" in b else "筛查批")+" · "+zh[o] for b,o in ykeys])
    ax.invert_yaxis();ax.set_xlabel("队列启动后的时间（h）；同一时点的完成与发布标记重合")
    ax.legend(ncol=5,loc="upper center",bbox_to_anchor=(.5,-.17),frameon=False,fontsize=8)
    title(fig,f"从筛查到新粉体确认 · C{int(candidate):02d} 的事件泳道")
    output(fig,dst,"event_swimlane")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,default=OUT)
    make(p.parse_args().out)
