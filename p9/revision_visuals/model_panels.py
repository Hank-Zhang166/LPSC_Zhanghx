"""Chart observed outer-DES records. No generated/illustrative values enter these panels."""
import re
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from make_figures import SIM, TEAL, BLUE, OCH, PURP, GRAY, INK, LIGHT, read, save

LABEL={"screen_only":"只用初筛","gate":"静态门禁","myopic":"资源感知单步","tree":"条件两步","tree_fit":"两步可适配"}
ACTION={"pellet":"复测压片","contact":"接触诊断","structure":"结构诊断","md":"独立 MD","dft":"独立 DFT","fit":"适配与重算","redo":"重算 MD","confirm":"独立新批"}
def policy():
    rr=[r for r in read(SIM/"policy_summary.csv") if r["scenario"]=="baseline" and r["policy"] in LABEL]
    compare=[r for r in read(SIM/"paired_effects.csv") if r["scenario"]=="baseline" and r["reference"]=="myopic"]
    rows={r["policy"]:r for r in rr}
    fig,(a,b)=plt.subplots(1,2,figsize=(9.9,3.75),layout="constrained",width_ratios=[1.1,1.1])
    policies=list(LABEL);others=[x for x in policies if x!="myopic"]
    for i,k in enumerate(policies):
        r=rows[k];c=TEAL if k.startswith("tree") else BLUE if k=="myopic" else GRAY
        a.scatter(100*float(r["success_rate"]),i,c=c,s=58,zorder=3)
        a.text(100*float(r["success_rate"])+.18,i,f"{float(r['success_rate']):.1%}",va="center",fontsize=9.6,color=c)
    vals=[100*float(rows[k]["success_rate"]) for k in policies]
    a.set(yticks=range(len(policies)),yticklabels=[LABEL[k] for k in policies],ylim=(len(policies)-.45,-.5),xlabel="配方、新批达标且测量阳性（%）",xlim=(min(vals)-1,max(vals)+2.2));a.grid(axis="x",alpha=.25)
    a.set_title("A　独立确认成功率",loc="left",fontsize=14,weight="bold")
    for i,k in enumerate(others):
        r=next(r for r in compare if r["policy"]==k and r["metric"]=="mean_cost");v,lo,hi=[float(r[j]) for j in ["difference","ci_low","ci_high"]]
        b.errorbar(v,i,xerr=[[v-lo],[hi-v]],fmt="o",color=TEAL if k.startswith("tree") else GRAY,capsize=4,ms=5.5)
    b.axvline(0,color=OCH,linestyle="--",lw=1);b.grid(axis="x",alpha=.22)
    b.set(yticks=range(len(others)),yticklabels=[LABEL[k] for k in others],ylim=(len(others)-.45,-.5),xlabel="相对单步的费用差（情景元）")
    b.set_title("B　同队列配对费用差及 95% 区间",loc="left",fontsize=14,weight="bold")
    save(fig,"policy_results")
def timeline():
    ev=read(SIM/"events.csv")
    tasks=[(r["candidate"],r["action"]) for r in ev if r["event"]=="submitted"]
    lock=next(r for r in ev if r["event"]=="lock")
    markers={};starts={}
    fig,ax=plt.subplots(figsize=(9.7, max(3.5,len(tasks)*.34+1.5)),layout="constrained")
    for y,(c,a) in enumerate(tasks):
        items=[r for r in ev if (r["candidate"],r["action"])==(c,a)];get=lambda z:float(z["time_h"])
        st=next(get(r) for r in items if r["event"]=="submitted")
        end=max(get(r) for r in items)
        ax.barh(y,end-st,left=st,height=.52,color="#E3E8EB",linewidth=0)
        for r in items:
            if r["event"]=="start":starts[r["resource"]]=get(r)
            if r["event"]=="complete" and r["resource"] in starts:
                t0=starts.pop(r["resource"])
                color=OCH if r["resource"]=="review" else TEAL if a=="confirm" else BLUE
                ax.barh(y,get(r)-t0,left=t0,height=.52,color=color,linewidth=0)
            if r["event"] in ("independent_release","qc_released","late_release"):
                m="x" if r["event"]=="late_release" else "D"
                ax.plot(get(r),y,marker=m,ms=5.3,color=INK,linestyle="none")
                if r["event"]=="independent_release":
                    ax.text(get(r)+.55,y,f"{get(r):.1f} h  {r['detail']}",va="center",fontsize=10.5,color=TEAL)
    tlock=get(lock)
    ax.axvline(tlock,color=PURP,linestyle="--",lw=1.2)
    ax.text(tlock+.4,-.56,f"冻结 {tlock:g} h",va="bottom",color=PURP,fontsize=10.5)
    ax.set(yticks=range(len(tasks)),yticklabels=[f"x={c}　{ACTION[a]}" for c,a in tasks],ylim=(len(tasks)-.45,-.93),xlabel="从统一初筛发布起的情景时钟（h）")
    ax.set_xlim(-.4,max(float(r["time_h"]) for r in ev)+7);ax.grid(axis="x",alpha=.22)
    ax.legend(handles=[Patch(color=BLUE,label="诊断执行"),Patch(color=TEAL,label="新批制备／测量"),Patch(color=OCH,label="质控"),Line2D([0],[0],marker="D",color=INK,lw=0,label="发布"),Line2D([0],[0],marker="x",color=INK,lw=0,label="冻结后发布")],ncol=5,loc="upper center",bbox_to_anchor=(.52,-.21),frameon=False,fontsize=9.3)
    save(fig,"swimlane")
def generate():
    policy()
    timeline()
if __name__=="__main__":
    generate()
