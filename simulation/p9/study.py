"""P9 controlled policy comparison. Run from any folder. Dependencies: Python standard library."""
import argparse
import copy
import csv
import gzip
import hashlib
import json
import math
import multiprocessing as mp
import os
import statistics
from functools import lru_cache
from pathlib import Path
from belief import Beliefs,load_priors
from engine import Simulator,World

D=Path(__file__).resolve().parent
PRIOR=D.parents[1]/"p9/ranking/outputs/des_structure_prior.csv"
OUT=D/"outputs"
POLICIES=("F","G","B","Q","H","H-fit")
FULL=POLICIES+("H-nostate","H-serial","H-shuffle")
STRESS={
 "baseline":{},"fixed_adequate":{"prior_bias":.01},"zero_gain":{"actual_fit_gain":0},
 "negative_gain":{"actual_fit_gain":-.6},"slow_dft_fit":{"dft_factor":3,"train_factor":2.5},
 "congestion":{"capacity.furnace":1,"shift_hours.review":13,"period_h":1.5},
 "external_delayed":{"external_factor":5},"unidentified_structure":{"struct_quality":0},
 "coexisting_causes":{"bias_contact_joint":.20},"noisy_signals":{"quality_scale":.45},
 "early_freeze":{"freeze_h":47},"unhelpful_diagnostics":{"quality_scale":0.},
 "premature_md":{"stage_md_factor":4,"prior_bias":.42},"optimistic":{"period_h":4,"capacity.review":2,"shift_hours.review":24,"quality_scale":1.12},
 "conservative":{"capacity.furnace":1,"shift_hours.review":12,"external_factor":4,"dft_factor":2,"quality_scale":.65},
 "tight_budget":{"budget_cny":8200}}
RATIOS={"recall":("tp","good"),"fpr":("fp","bad"),"fnr":("fn","good"),"bias_miss_rate":("bias_miss","bias"),
 "valid_label_fraction":("valid_label_pack","n_fit"),"diagnostic_precision":("useful_dft","n_dft"),
 "posterior_binary_auc":("pair_wins","pair_n"),"audit_accuracy_gain":("audit_diff","audit_count"),
 "true_confirm_per_1000_cny":("tp_in_thousands","cost")}
METRICS=("restricted_h","confirmed_run","true_confirmed_run","cost","tp","fp","fn","bias_wrong","bias_miss","dft_no_bias","invalid_fit",
         "valid_label_pack","assay_fail","deferred","resumed","cancelled","risky_early_work","late_evidence","stale_md",
         "n_fit","fit_accept","n_dft","n_local","n_eis","n_md","n_confirm","n_contact","n_repeat","n_redo","n_xrd","util_review","util_furnace",
         "queue_h_review","queue_h_eis",*RATIOS)
@lru_cache(maxsize=40)
def model(scenario):
    s=json.loads((D/"site.json").read_text(encoding="utf8"));p=json.loads((D/"project.json").read_text(encoding="utf8"))
    for key,val in STRESS[scenario].items():
        if key=="dft_factor":
            for op in ("dft","fit"):
                for row in s["stages"][op]:
                    if row[0]=="dft":row[1]*=val
        elif key=="train_factor":
            for row in s["stages"]["fit"]:
                if row[0]=="gpu":row[1]*=val
        elif key=="external_factor":
            for row in s["stages"]["local"]:
                if row[0] in ("ship","ext"):row[1]*=val
        elif key=="stage_md_factor":
            for row in s["stages"]["md"]:
                if row[0]=="gpu":row[1]*=val
        elif "." in key:
            a,c=key.split(".");s[a][c]=val
        elif key in p:p[key]=val
        else:s[key]=val
    return Beliefs(s,p,load_priors(PRIOR))
def worker(task):
    sc,start,n,policies,settings=task
    b=model(sc);records=[]
    for seed in range(start,start+n):
        w=World(seed,b)
        for po in policies:
            for label,thr in settings[po]:
                sim=Simulator(b,w,po,thr)
                r=sim.run();r["audit_diff"]=r["audit_before"]-r["audit_after"];r["tp_in_thousands"]=r["tp"]*1000
                records.append(dict(scenario=sc,seed=seed,policy=po,setting=label,threshold=thr,**r))
    return records
def calc(rows,metric):
    if metric in RATIOS:
        a,b=RATIOS[metric];den=sum(r[b] for r in rows)
        if not den:return None,None
        x=sum(r[a] for r in rows)/den
        return x,[(r[a]-x*r[b])*len(rows)/den for r in rows]
    vals=[r[metric] for r in rows]
    x=statistics.fmean(vals);return x,[y-x for y in vals]
def delta(aa,bb,m):
    a,u=calc(aa,m);b,v=calc(bb,m)
    if a is None or b is None:return [None]*5
    dif=a-b;s=statistics.stdev(i-j for i,j in zip(u,v))/math.sqrt(len(u))
    return [a,b,dif,dif-1.96*s,dif+1.96*s]
def write(name,rows):
    if not rows:return
    with (OUT/name).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def run(pool,sc,start,n,policies,settings):
    tasks=[(sc,start+k,min(8,n-k),policies,settings) for k in range(0,n,8)]
    return [r for batch in pool.imap(worker,tasks) for r in batch]
def grouped(rows):
    g={}
    for row in rows:g.setdefault((row["policy"],row["setting"]),[]).append(row)
    return g
def stats(rows):
    out=[]
    for (po,label),rr in grouped(rows).items():
        for m in METRICS:
            value,inf=calc(rr,m);lo=hi=None
            if value is not None:
                err=1.96*statistics.stdev(inf)/math.sqrt(len(rr))
                lo=value-err;hi=value+err
                if m!="audit_accuracy_gain":lo=max(0.,lo)
                if m in ("confirmed_run","true_confirmed_run"):
                    n=len(rr);z=1.959964;mid=(value+z*z/(2*n))/(1+z*z/n)
                    ext=z*(value*(1-value)/n+z*z/(4*n*n))**.5/(1+z*z/n);lo=max(0,mid-ext);hi=min(1,mid+ext)
                elif m in ("fpr","fnr","recall","bias_miss_rate","valid_label_fraction","diagnostic_precision","posterior_binary_auc"):
                    lo=max(0,lo);hi=min(1,hi)
            out.append(dict(scenario=rr[0]["scenario"],policy=po,setting=label,reps=len(rr),metric=m,mean=value,lo95=lo,hi95=hi))
    return out
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--reps",type=int,default=512);ap.add_argument("--stress",type=int,default=128);ap.add_argument("--dev",type=int,default=64)
    ap.add_argument("--workers",type=int,default=8)
    args=ap.parse_args();OUT.mkdir(exist_ok=True)
    seed=model("baseline").project["seed_outer"];dseed=model("baseline").project["calibration_seed"]
    assert not set(range(dseed,dseed+args.dev)).intersection(range(seed,seed+max(args.reps,args.stress)))
    grid=(.10,.40,.65,.85,.95)
    calibration=[];summary=[];pairs=[];thmaps={}
    targets={"recall_floor":.65,"fpr_ceiling":.025}
    with mp.Pool(args.workers) as pool:
        dev=run(pool,"baseline",dseed,args.dev,POLICIES,{p:[(str(t),t) for t in grid] for p in POLICIES})
        g=grouped(dev)
        for po in POLICIES:
            views=[]
            for t in grid:
                rs=g[po,str(t)]
                rc=calc(rs,"recall")[0];fpr=calc(rs,"fpr")[0];cost=calc(rs,"cost")[0];tm=calc(rs,"restricted_h")[0]
                views.append((t,rc,fpr,cost,tm))
            matched={}
            for label,target in targets.items():
                feasible=[row for row in views if (row[1]>=target if label=="recall_floor" else row[2]<=target)]
                # Common constraint, not equality; choose lowest calendar time among feasible settings, cost tiebreaks.
                choice=min(feasible,key=lambda row:(row[4],row[3],row[0])) if feasible else min(views,key=lambda row:abs(row[1 if label=="recall_floor" else 2]-target))
                matched[label]=choice[0]
                calibration.append(dict(policy=po,constraint=label,target=target,threshold=choice[0],dev_feasible=int(bool(feasible)),
                                         dev_recall=choice[1],dev_fpr=choice[2],dev_cost=choice[3],dev_rmst=choice[4],reps=args.dev))
            thmaps[po]=matched
        write("development_calibration.csv",calibration)
        print("dev calibrated",flush=True)
        with gzip.open(OUT/"replicates.csv.gz","wt",encoding="utf-8",newline="",compresslevel=2) as f:
            wr=None
            for sc in STRESS:
                policies=FULL if sc=="baseline" else ("B","Q","H","H-fit")
                settings={p:[("default",model(sc).project["admit_floor"])] for p in policies}
                if sc=="baseline":
                    for p in POLICIES:settings[p]+=list(thmaps[p].items())
                rows=run(pool,sc,seed,args.reps if sc=="baseline" else args.stress,policies,settings)
                if wr is None:
                    wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader()
                for r in rows:
                    wr.writerow({k:round(v,8) if isinstance(v,float) else v for k,v in r.items()})
                summary+=stats(rows);g=grouped(rows)
                for label in ("default","recall_floor","fpr_ceiling"):
                    for a,b in (("G","F"),("B","G"),("Q","B"),("H","Q"),("H-fit","H"),("H","H-nostate"),("H","H-serial"),("H-fit","H-shuffle"),("H-fit","G"),("H-fit","B")):
                        if (a,label) not in g or (b,label) not in g:continue
                        for m in METRICS:
                            x,y,d,lo,hi=delta(g[a,label],g[b,label],m)
                            pairs.append(dict(scenario=sc,setting=label,action=a,reference=b,metric=m,mean_a=x,mean_b=y,delta=d,lo95=lo,hi95=hi))
                write("policy_summary.csv",summary);write("paired_effects.csv",pairs)
                print(sc,len(rows),flush=True)
    # Traces shown once per policy, selected only to illustrate versioning, not to estimate any effect.
    base=model("baseline");chosen=seed
    for k in range(seed,seed+250):
        if Simulator(base,World(k,base),"H-fit").run()["fit_accept"]>0:chosen=k;break
    events=[];dec=[]
    for p in FULL:
        sim=Simulator(base,World(chosen,base),p,trace=True);sim.run()
        events.extend(dict(seed=chosen,policy=p,**r) for r in sim.history)
        dec.extend(dict(seed=chosen,policy=p,**r) for r in sim.choice)
    write("event_trace.csv",events);write("decision_trace.csv",dec)
    files=[D/x for x in ("belief.py","planning.py","engine.py","study.py","site.json","project.json")]+[PRIOR]
    meta=dict(base_seed=seed,development_seed=dseed,replicates=args.reps,stress_replicates=args.stress,dev_replicates=args.dev,
              stress=STRESS,trace_seed=chosen,inner="exact enumeration of binary observation branches; no inner RNG",
              sha256={os.path.relpath(f,D).replace(os.sep,"/"):hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
    (OUT/"metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf8")
if __name__=="__main__":main()
