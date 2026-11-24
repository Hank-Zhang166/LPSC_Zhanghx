"""Out-of-sample comparison under matched development rates, and Latin-hypercube joint sensitivities."""
import argparse
import csv
import hashlib
import json
import math
import multiprocessing as mp
import random
from statistics import fmean,stdev
from study import OUT,POLICIES,run,calc,grouped,write,model,STRESS,Simulator,World

def mix_u(seed,policy,label):
    # Separate randomization of a policy threshold; no candidate data are read.
    return random.Random(seed+int(hashlib.sha256((policy+label).encode()).hexdigest()[:12],16)).random()

def choose(points,m,target):
    pairs=[]
    for a in points:
        for b in points:
            x,y=a[m],b[m]
            if x<=target<=y and y>x:
                w=(target-x)/(y-x)
                pairs.append(((1-w)*a["cost"]+w*b["cost"],a,b,w))
    if pairs:
        _,a,b,w=min(pairs,key=lambda v:(v[0],v[1]["t"],v[2]["t"]))
        return a["t"],b["t"],w,True
    a=min(points,key=lambda v:(abs(v[m]-target),v["cost"]))
    return a["t"],a["t"],0.,abs(a[m]-target)<1e-12

def mix_worker(task):
    seed,plans=task;b=model("baseline");w=World(seed,b);out=[]
    for m,po,t0,t1,q in plans:
        t=t1 if mix_u(seed,po,m)<q else t0
        r=Simulator(b,w,po,t).run();out.append((m,po,r))
    return out

def lhs(i_and_config):
    i,settings,n,base_seed=i_and_config
    label="lhs-"+str(i);STRESS[label]=settings;b=model(label)
    out=[];cache={}
    for k in range(n):
        seed=base_seed+k;w=World(seed,b)
        for po in ("Q","H","H-fit"):
            cache[po]=Simulator(b,w,po).run()
        out.append(tuple(cache[p][m]-cache[q][m] for p,q,m in (
           ("H","Q","restricted_h"),("H","Q","cost"),("H-fit","H","cost"),("H-fit","H","tp"))))
    return dict(design=i,**settings,paired_reps=n,
       h_minus_q_h=fmean(r[0] for r in out),h_minus_q_cost=fmean(r[1] for r in out),
       fit_minus_h_cost=fmean(r[2] for r in out),fit_minus_h_true_confirmations=fmean(r[3] for r in out))

def main():
    a=argparse.ArgumentParser();a.add_argument("--workers",type=int,default=8);o=a.parse_args()
    base=model("baseline").project["seed_outer"]
    dev=model("baseline").project["calibration_seed"];grid=(.10,.40,.65,.85,.95,.99)
    plans=[];matched=[];n=384;nd=96;lhs_n=24;lhs_reps=40
    with mp.Pool(o.workers) as pool:
        rows=run(pool,"baseline",dev,nd,POLICIES,{p:[(str(t),t) for t in grid] for p in POLICIES})
        groups=grouped(rows)
        for po in POLICIES:
            pts=[dict(t=t,**{m:calc(groups[po,str(t)],m)[0] for m in ("cost","fpr","recall")}) for t in grid]
            for m,target in (("recall",.60),("fpr",.008)):
                lo,hi,weight,ok=choose(pts,m,target)
                plans.append((m,po,lo,hi,weight))
                matched.append(dict(policy=po,metric=m,target=target,dev_feasible=int(ok),threshold_a=lo,threshold_b=hi,
                      probability_b=weight,dev_n=nd,eval_n=n))
        groups={}
        for batch in pool.imap(mix_worker,[(base+i,plans) for i in range(n)],chunksize=4):
            for m,po,r in batch:groups.setdefault((m,po),[]).append(r)
        for row in matched:
            m=row["metric"];po=row["policy"];rs=groups[m,po]
            for metric in ("recall","fpr","restricted_h","cost"):
                x,inf=calc(rs,metric);err=1.96*stdev(inf)/n**.5
                row[metric]=x;row[metric+"_lo"]=max(0,x-err);row[metric+"_hi"]=min(1,x+err) if metric in ("recall","fpr") else x+err
            row["holdout_gap"]=row[m]-row["target"]
        write("matched_operating_points.csv",matched)
        pairs=[]
        for m in ("recall","fpr"):
            for po,ref in (("H","Q"),("H-fit","H"),("Q","B")):
                for metric in ("restricted_h","cost","recall","fpr"):
                    x,u=calc(groups[m,po],metric);y,v=calc(groups[m,ref],metric)
                    diff=x-y;e=1.96*stdev(a-b for a,b in zip(u,v))/n**.5
                    pairs.append(dict(matched_on=m,policy=po,reference=ref,metric=metric,delta=diff,lo95=diff-e,hi95=diff+e))
        write("matched_pair_effects.csv",pairs)
        rnd=random.Random(72031)
        dims={"dft_factor":(.5,3.),"external_factor":(.6,4.),"freeze_h":(43.,90.),"quality_scale":(.55,1.1),
              "prior_bias":(.05,.4),"actual_fit_gain":(-.4,.95)}
        cols={}
        for key,(low,high) in dims.items():
            vals=[low+(high-low)*(i+rnd.random())/lhs_n for i in range(lhs_n)]
            rnd.shuffle(vals);cols[key]=vals
        tasks=[(i,{k:v[i] for k,v in cols.items()},lhs_reps,base+5000) for i in range(lhs_n)]
        glob=list(pool.imap(lhs,tasks));write("joint_sensitivity.csv",glob)
    print("matched",n,"holdout seeds; LHS",lhs_n,"joint profiles x",lhs_reps,"seeds")
if __name__=="__main__":main()
