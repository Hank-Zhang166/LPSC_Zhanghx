"""Rebuild figures from actual primary/auxiliary output CSV. Matplotlib required."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from study import OUT,POLICIES
plt.rcParams.update({"font.family":next((f for f in ("Microsoft YaHei","Noto Sans CJK SC","SimHei") if f in {x.name for x in font_manager.fontManager.ttflist}),"DejaVu Sans"),
 "font.size":10,"axes.spines.top":False,"axes.spines.right":False,"axes.unicode_minus":False,"svg.fonttype":"none",
 "axes.edgecolor":"#8d9c9c","text.color":"#17383e","axes.labelcolor":"#17383e","xtick.color":"#395357","ytick.color":"#395357"})
def read(name):
    with (OUT/name).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def title(fig,t,sub):
    fig.text(.02,1.05,t,ha="left",va="bottom",fontsize=16,weight="bold")
    fig.text(.02,1.015,sub,ha="left",va="top",fontsize=9,color="#4c686e")
def save(fig,name):
    for f in ("png","svg"):fig.savefig(OUT/(name+"."+f),dpi=200,bbox_inches="tight",pad_inches=.14,facecolor="white")
    plt.close(fig)
def main():
    rr=read("policy_summary.csv");ee=read("paired_effects.csv")
    base={(r["policy"],r["metric"]):r for r in rr if r["scenario"]=="baseline" and r["setting"]=="default"}
    fig,axes=plt.subplots(1,3,figsize=(11,3.4),sharey=True)
    colors=["#9aaba9","#758e9c","#418997","#087c72","#375e8c","#ce7848"]
    labels=["F 固定","G 门禁","B 成本单步","Q 资源单步","H 二步固定势","H-fit 二步可适配"]
    for ax,key,unit,scale in zip(axes,("restricted_h","recall","bias_miss_rate"),("首次确认限制均时 / h","真合格召回率 / %","势偏差漏诊率 / %"),(1,100,100)):
        for i,po in enumerate(POLICIES):
            r=base[(po,key)];x=float(r["mean"])*scale;lo=float(r["lo95"])*scale;hi=float(r["hi95"])*scale
            ax.barh(i,x,.52,color=colors[i]);ax.errorbar(x,i,xerr=[[x-lo],[hi-x]],fmt="none",color="#264248",capsize=3)
        ax.set_xlabel(unit);ax.grid(axis="x",alpha=.18);ax.set_axisbelow(True)
    axes[0].set_yticks(range(6),labels);axes[0].invert_yaxis()
    title(fig,"资源感知单步政策最早确认，二步政策减少了势偏差漏诊","七组成联合队列  ·  512 个配对评价种子  ·  误差线为边际 95% 蒙特卡洛区间  ·  情景模拟")
    save(fig,"p9_policy")
    events=[r for r in read("event_trace.csv") if r["policy"]=="H-fit"]
    seed=events[0]["seed"]
    dec=[r for r in read("decision_trace.csv") if r["policy"]=="H-fit" and r["action"]=="fit" and r["i"]=="2"]
    if not dec:return
    fig,ax=plt.subplots(figsize=(10.8,3.85))
    rows=[("1","confirm","x=0.1  独立新批确认"),("2","dft","x=0.2  独立 DFT"),("2","fit","x=0.2  标签、训练与验收"),("6","dft","x=0.6  独立 DFT"),("6","redo","x=0.6  新势重算")]
    for i,(cid,op,name) in enumerate(rows):
        e=[r for r in events if r["i"]==cid and r["action"]==op]
        if not e:continue
        ts=[float(r["t"]) for r in e];ax.hlines(i,min(ts),max(ts),color="#b4c7c5",lw=5)
        for kind,mark,c in (("submitted","|","#5a6c73"),("qc_released","D","#13776c")):
            v=[float(r["t"]) for r in e if r["event"]==kind];ax.scatter(v,[i]*len(v),marker=mark,c=c,s=48,zorder=3)
    ax.axvline(79,color="#944e56",lw=1.2,ls="--")
    ax.text(79.25,4.15,"x=0.2 冻结",fontsize=9,color="#944e56",va="bottom")
    ax.annotate("初次预测 79.37 h，超窗暂缓",(53.06,2),xytext=(38,2.60),fontsize=9,arrowprops={"arrowstyle":"->","lw":.8,"color":"#ab713f"})
    ax.annotate("队列释放后提交",(54.80,2),xytext=(57.0,2.55),fontsize=9,arrowprops={"arrowstyle":"->","lw":.8,"color":"#ab713f"})
    ax.set_yticks(range(len(rows)),[r[-1] for r in rows]);ax.invert_yaxis();ax.set_xlim(28,85)
    ax.set_xlabel("队列起点后的时间 / h");ax.grid(axis="x",alpha=.2);ax.set_axisbelow(True)
    ax.legend(handles=[Line2D([0],[0],marker="|",color="#5a6c73",linestyle="",label="提交"),Line2D([0],[0],marker="D",color="#13776c",linestyle="",label="审核发布")],
              loc="upper right",ncol=2,frameon=False)
    title(fig,"实验确认与势更新在同一队列中异步推进",f"H-fit  ·  从种子 {seed} 的事件和决策流水重绘  ·  单例用于说明版本发布条件")
    save(fig,"p9_event_trace")
    fig,axes=plt.subplots(1,2,figsize=(9.4,4.4),sharey=True)
    cases=[("baseline","基准"),("zero_gain","零适配收益"),("negative_gain","真实收益为负"),("fixed_adequate","固定势充分"),
      ("slow_dft_fit","DFT 与训练慢"),("congestion","资源拥堵"),("early_freeze","冻结提前"),("unidentified_structure","结构不可辨识"),
      ("coexisting_causes","双重原因共存"),("tight_budget","预算紧张")]
    for ax,key,sc,unit in zip(axes,("cost","audit_accuracy_gain"),(1,100),("H-fit − H 整队列费用 / 元","合成留出探针准确度差 / 百分点")):
        for i,(case,label) in enumerate(cases):
            r=next(r for r in ee if r["scenario"]==case and r["setting"]=="default" and r["action"]=="H-fit" and r["reference"]=="H" and r["metric"]==key)
            val=float(r["delta"])*sc;lo=float(r["lo95"])*sc;hi=float(r["hi95"])*sc
            ax.errorbar(val,i,xerr=[[val-lo],[hi-val]],fmt="o",ms=5,capsize=3,color="#13776c" if val<=0 else "#b07347")
        ax.axvline(0,color="#40575b",lw=1);ax.set_xlabel(unit);ax.grid(axis="x",alpha=.18)
    axes[0].set_yticks(range(len(cases)),[s[1] for s in cases]);axes[0].invert_yaxis()
    title(fig,"定向适配的代价取决于可用时间与真实增益","H-fit 对 H 的配对 95% 蒙特卡洛区间  ·  基准 512 次，压力情景各 128 次  ·  合成观测模型")
    save(fig,"p9_stress")
if __name__=="__main__":main()
