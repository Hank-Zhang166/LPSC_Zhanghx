"""Read audited observations or explicitly synthetic output tables to produce research panels."""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle
from make_figures import OUT, P9, RANK, INK, GRAY, LIGHT, BLUE, BPALE, TEAL, TPALE, OCH, OPALE, PURP, read, save

def plot_basis(ax):
    ax.grid(axis="y",alpha=.24,color=GRAY,lw=.6)
    ax.set_axisbelow(True)
def panel(ax,txt):
    ax.set_title(txt,loc="left",fontsize=14,fontweight="bold",pad=8,color=INK)
def mo_curve():
    m=read(P9/"evidence/mo_s1.csv"); groups=[r for r in read(P9/"evidence/diagnostic_groups.csv") if r["group_id"]=="S_press"]
    fig,axs=plt.subplots(1,2,figsize=(9.65,3.76),layout="constrained",width_ratios=[1.3,1])
    a,b=axs;x=[float(r["x"]) for r in m];y=[float(r["sigma_mS_cm"]) for r in m]
    a.plot(x,y,lw=2.2,color=TEAL,marker="o",ms=5.5)
    for xx,yy in zip(x,y):a.annotate(f"{yy:.1f}",(xx,yy),ha="center",xytext=(0,7),textcoords="offset points",fontsize=10.5)
    a.set(xlabel="名义取代量 x",ylabel="总电导（mS/cm）",ylim=(3,9.4),xticks=x)
    panel(a,"A　七组成同系列，25 ℃")
    for cl,xx in zip([BLUE,TEAL,OCH],["0.3","0.4","0.5"]):
        g=sorted((r for r in groups if r["x"]==xx),key=lambda r:r["condition"]);v=[float(t["value"]) for t in g]
        b.plot([0,1],v,color=cl,lw=2.2,marker="o",ms=5)
        b.text(-.055,v[0],f"{v[0]:.1f}",ha="right",va="center",fontsize=10.5,color=cl)
        b.text(1.065,v[1],f"{v[1]:.1f}  (x={xx})",va="center",fontsize=10.5,color=cl)
    b.set(xlim=(-.22,1.67),ylim=(3,9.4),xticks=[0,1],xticklabels=["冷压","热压"],ylabel="总电导（mS/cm）");panel(b,"B　自制原料分组，25 ℃")
    for q in axs:plot_basis(q)
    save(fig,"mo_curve")

def hull(points):
    pts=sorted(set(map(tuple,points)))
    cross=lambda o,a,b:(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    def side(seq):
        s=[]
        for p in seq:
            while len(s)>=2 and cross(s[-2],s[-1],p)<=0: s.pop()
            s.append(p)
        return s
    return np.array(side(pts)[:-1]+side(pts[::-1])[:-1])

def weights():
    fs=[r for r in read(RANK/"family_weights.csv") if r["x"]=="0.4"]
    diag=next(r for r in read(RANK/"structure_diagnostics.csv") if r["x"]=="0.4" and float(r["lambda_value"])==1)
    fig,(a,b)=plt.subplots(1,2,figsize=(9.65,3.85),layout="constrained",width_ratios=[1,1.12])
    pts=np.array([[float(r["forward_site_proxy"]),float(r["forward_pair_proxy"])] for r in fs])
    poly=hull(pts);a.fill(poly[:,0],poly[:,1],color=BPALE,label="族混合的可达区域")
    a.scatter(*pts.T,c=BLUE,s=30,label="候选族前向观测");a.scatter(float(diag["training_site_observed"]),float(diag["training_pair_observed"]),marker="*",s=160,color=OCH,label="合成观测",zorder=4)
    a.set(xlabel="平均位点占位指标",ylabel="近邻关联指标")
    a.legend(loc="upper left",frameon=False,fontsize=9);panel(a,"A　观测是否落在支持集内")
    idx=np.arange(len(fs));prior=np.array([float(r["thermal_prior_mean"]) for r in fs]);post=np.array([float(r["bme_weight_mean"]) for r in fs])
    lo=np.array([float(r["bme_world_q05"]) for r in fs]);hi=np.array([float(r["bme_world_q95"]) for r in fs])
    b.plot(idx,prior,"o",mec=BLUE,mfc="white",ms=6,label="热先验（均值）")
    b.errorbar(idx+.12,post,yerr=[post-lo,hi-post],fmt="o",ms=4,color=TEAL,capsize=2,label="更新值及情景范围")
    b.set(xticks=idx,xticklabels=[str(i) for i in range(1,len(fs)+1)],xlabel="同一组成的九个抽象结构族",ylabel="族权重")
    b.legend(frameon=False,fontsize=9,loc="upper right");plot_basis(b);panel(b,"B　同一证据容许多组权重")
    save(fig,"weights")
def rankings():
    names=[f"{i/10:.1f}" for i in range(7)]
    comps=[r for r in read(RANK/"pairwise.csv") if r["method"]=="bme" and r["primary_delta"]=="true"]
    rec=next(r for r in comps if r["x_a"]=="0.4" and r["x_b"]=="0.5")
    fig,(a,b)=plt.subplots(1,2,figsize=(9.3,3.58),layout="constrained",width_ratios=[.85,1.35])
    observed = {r["x"]:float(r["sigma_mS_cm"]) for r in read(P9/"evidence/mo_s1.csv")}
    pair_readings = [observed["0.4"], observed["0.5"]]
    a.bar([0,1],pair_readings,color=[TEAL,BLUE],width=.59)
    for i,v in enumerate(pair_readings):a.text(i,v+.15,str(v),ha="center",fontsize=13)
    a.set(xticks=[0,1],xticklabels=["x=0.4","x=0.5"],ylim=(0,10),ylabel="压片总电导（mS/cm）")
    panel(a,"A　历史实测点值");plot_basis(a)
    for i,(prefix,lab,c) in enumerate([("p_plus","0.4 优势",TEAL),("p_minus","0.5 优势",BLUE),("p_tie","近似并列",OCH)]):
        v=float(rec[prefix]);lo=float(rec[prefix+"_world_q05"]);hi=float(rec[prefix+"_world_q95"])
        b.errorbar(v,i,xerr=[[v-lo],[hi-v]],fmt="o",color=c,capsize=4,ms=7)
        b.text(.98,i,f"{v:.1%}",va="center",ha="right",color=c,fontsize=12)
    b.set(yticks=[0,1,2],yticklabels=["0.4 优势","0.5 优势","近似并列"],ylim=(2.5,-.5),xlim=(0,1),xlabel="合成比较概率（点）及情景范围（线）")
    b.grid(axis="x",alpha=.22);panel(b,"B　随机结构族的晶内输运")
    save(fig,"case_pair")

    ecdf=[r for r in read(RANK/"weighted_ecdf.csv") if r["method"]=="bme"]
    fig,(a,b)=plt.subplots(1,2,figsize=(9.5,3.6),layout="constrained",sharey=True)
    for ax,subset,labs in [(a,["0.0","0.1","0.2","0.3"],[GRAY,PURP,OCH,BLUE]),(b,["0.4","0.5","0.6"],[TEAL,BLUE,OCH])]:
        for x,k in zip(subset,labs):
            data=[r for r in ecdf if r["x"]==x]
            ax.step([float(r["log_relative_transport"]) for r in data],[float(r["ecdf"]) for r in data],where="post",lw=2,label=f"x={x}",color=k)
        ax.set(xlabel="自然对数相对输运（合成）",ylim=(-.02,1.04),xlim=(-.62,1.12))
        ax.legend(loc="lower right",frameon=False,fontsize=9);plot_basis(ax)
    a.set_ylabel("累积概率");panel(a,"A　母体至 x=0.3");panel(b,"B　x=0.4 至 0.6")
    save(fig,"weighted_ecdf")

    d=np.full((7,7),np.nan);ref=np.full((7,7),np.nan)
    for r in comps:
        i=names.index(r["x_a"]);j=names.index(r["x_b"])
        if i!=j:d[i,j]=float(r["p_plus"])
    directions=[r for r in read(RANK/"public_direction.csv") if r["method"]=="bme" and float(r["historical_margin_mS_cm"])==0]
    for r in directions:
        i,j=names.index(r["x_a"]),names.index(r["x_b"]);ref[i,j]=float(r["p_supporting_historic_point"])
    cmap=LinearSegmentedColormap.from_list("adv",["#EBF4F1","#B4DBCC","#5EA899","#246D66","#144E4F"])
    for val,stem in [(d,"prob_advantage"),(ref,"prob_conflict")]:
        fig=plt.figure(figsize=(8.25,4.2));ax=fig.add_axes((.09,.16,.49,.81)); color_ax=fig.add_axes((.62,.58,.31,.047))
        op=ax.imshow(val,cmap=cmap,vmin=0,vmax=1)
        for i,j in zip(*np.where(np.isfinite(val))):
            ax.text(j,i,f"{val[i,j]:.2f}",ha="center",va="center",fontsize=10.7,color="white" if val[i,j]>.61 else INK)
        for v in range(7): ax.text(v,v,"—",ha="center",va="center",color=LIGHT)
        ax.set(xticks=range(7),yticks=range(7),xticklabels=names,yticklabels=names,xlabel="比较组成 B",ylabel="参照组成 A")
        ax.add_patch(Rectangle((4.50,3.50),1,1,fill=False,edgecolor=OCH,linewidth=2.4))
        fig.colorbar(op,cax=color_ax,orientation="horizontal",ticks=[0,.5,1])
        fig.text(.62,.79,"A 相对 B 的优势概率" if stem=="prob_advantage" else "支持历史点值方向的概率",fontsize=13,color=INK,weight="bold")
        fig.text(.62,.35,"描边格取 A=0.4、B=0.5。",fontsize=11.5)
        fig.text(.62,.15, "该格为 0.13。反向优势和\n近似并列须另行计算。" if stem=="prob_advantage" else "每个配方对只列一次。\n21 对均未达到方向判定门槛。",fontsize=10.9,color=GRAY,linespacing=1.6)
        save(fig,stem)
