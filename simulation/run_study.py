"""Run all common-random-number policy comparisons; only Python standard library."""
import argparse
import copy
import csv
import gzip
import hashlib
import json
import multiprocessing as mp
import platform
import statistics as st
from datetime import datetime, timezone
from pathlib import Path
from minimal_des import ROOT, DEFAULT, DES, World, BASE_POLICIES

OUT=ROOT/"simulation"/"outputs"
ABLATIONS=["B3-no-structure","B3-no-queue","B4-random-label","B4-immediate"]
SCENARIOS={
    "V0":{},"pilot6":{"n_candidates":6},
    "late_xrd":{"durations.xreview":[18,0.4]},
    "expensive_false_drop":{"opportunity_loss":50000,"phase_error":0.15},
    "gpu_slack":{"capacity.gpu":8},"fixed_sufficient":{"phys.biased_share":0},
    "slow_acceptance":{"durations.train":[24,0],"durations.validate":[16,0]},
    "exhaustive_confirmation":{"all_confirm":True},
    "dft_0.2x":{"durations.dft_frame":[0.2,0]},"dft_5x":{"durations.dft_frame":[5,0]},
    "dft_10x":{"durations.dft_frame":[10,0]},
    "no_gain":{"fit.gain_lo":0,"fit.gain_hi":0},
    "fail_all_fits":{"fit.accept":0},"favorable_gain":{"fit.accept":1,"fit.gain_lo":0.8,"fit.gain_hi":1},
    "freeze_48":{"freeze":48},"freeze_144":{"freeze":144},
    "phase_low":{"phase_prior":[.15,.20,.65]},"phase_high":{"phase_prior":[.45,.20,.35]},
    "outage":{"outage_hours":24,"retry_probability":.05},
    "half_wet_time":{"wet_factor":0.5},"double_wet_time":{"wet_factor":2},
    "half_wet_price":{"wet_price_factor":0.5},"double_wet_price":{"wet_price_factor":2}
}
COUNTS=["cancelled","recomputed","obsolete_outputs","unused_label_batches","expired_releases","retries","fit_attempts","releases","rollbacks","powders","pellets","eis_tests","dft_frames","hours_gpu","hours_dft","cost_cny","decision_loss_cny","cost_index","confirmed"]
RATIOS={"ppv":("tp","confirmed"),"recall":("tp","positive"),"wrong_drop_rate":("wrong_drop","positive"),
        "fpr":("fp","negative"),"timely_phase_rate":("timely_phase","n"),"timely_eis_rate":("timely_eis","n"),
        "powders_per_confirmation":("powders","confirmed"),"eis_per_confirmation":("eis_tests","confirmed"),
        "frames_per_confirmation":("dft_frames","confirmed"),"gpu_h_per_confirmation":("hours_gpu","confirmed"),
        "cny_per_confirmation":("cost_cny","confirmed"),"index_per_confirmation":("cost_index","confirmed"),
        "cny_per_true_confirmation":("cost_cny","tp")}

def config(scenario):
    cfg=copy.deepcopy(DEFAULT)
    for k,v in SCENARIOS[scenario].items():
        if k=="wet_factor":
            for op in ("prep","synth","xrd","xreview","press","eis","ereview","refine"):
                cfg["durations"][op][0]*=v
        elif k=="wet_price_factor":
            for r in ("staff","furnace","xrd","eis","powder"):
                cfg["cost_cny"][r]*=v
        elif "." in k:
            path,key=k.split(".")
            cfg[path][key]=v
        else:
            cfg[k]=v
    return cfg

def worker(job):
    scenario,base,start,end,ext=job
    cfg=config(scenario)
    policies=BASE_POLICIES+(ABLATIONS if ext else [])
    records=[]
    for rep in range(start,end):
        seed=base+rep
        world=World(cfg,seed)
        for policy in policies:
            r=DES(cfg,world,policy).run()
            records.append(dict(scenario=scenario,policy=policy,rep=rep,seed=seed,**r))
    return records

def pct(v,p):
    s=sorted(v)
    if not s: return None
    z=(len(s)-1)*p
    i=int(z)
    return s[i]+(s[min(i+1,len(s)-1)]-s[i])*(z-i)

def write_csv(path,rows):
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        for row in rows:
            w.writerow({k:(round(v,8) if isinstance(v,float) else v) for k,v in row.items()})

def mean_se(v):
    return st.fmean(v),st.stdev(v)/len(v)**.5 if len(v)>1 else 0.

def estimator(rows,metric):
    # Influence values for paired ordinary means and pooled ratio-of-means.
    if metric in RATIOS:
        a,b=RATIOS[metric]
        m=st.fmean(r[b] for r in rows)
        if m==0: return 0.,[0. for r in rows]
        point=st.fmean(r[a] for r in rows)/m
        return point,[(r[a]-point*r[b])/m for r in rows]
    if metric=="completion_prob":
        vals=[float(r["first_h"] is not None) for r in rows]
    else:
        vals=[r[metric] for r in rows]
    point=st.fmean(vals)
    return point,[v-point for v in vals]

def summarize(scn,group,summary,pairs):
    for policy,rows in group.items():
        accepted=[r["first_h"] for r in rows if r["first_h"] is not None]
        actual=[r["restricted_h"] for r in rows]
        rec=dict(scenario=scn,policy=policy,reps=len(rows),first_cond_mean_h=st.fmean(accepted) if accepted else "",
                 first_cond_median_h=pct(accepted,0.5),first_cond_p90_h=pct(accepted,0.9),
                 first_rmst_median_h=pct(actual,.5),first_rmst_p90_h=pct(actual,.9))
        for met in ["restricted_h","true_restricted_h","completion_prob"]+COUNTS+list(RATIOS)+["util_"+r for r in DEFAULT["capacity"]]:
            x,inf=estimator(rows,met)
            se=mean_se(inf)[1]
            rec[met]=x
            rec[met+"_lo"]=x-1.959964*se
            rec[met+"_hi"]=x+1.959964*se
            if met=="completion_prob":
                z=1.959964
                n=len(rows)
                center=(x+z*z/(2*n))/(1+z*z/n)
                radius=z*(x*(1-x)/n+z*z/(4*n*n))**.5/(1+z*z/n)
                rec[met+"_lo"]=max(0.,center-radius)
                rec[met+"_hi"]=min(1.,center+radius)
            elif met in ("ppv","recall","wrong_drop_rate","fpr","timely_phase_rate","timely_eis_rate") or met.startswith("util_"):
                rec[met+"_lo"]=max(0.,rec[met+"_lo"])
                rec[met+"_hi"]=min(1.,rec[met+"_hi"])
        summary.append(rec)
    comparisons=[("B4",x) for x in ("B0","B1","B2","B3")]+[("B1","B0"),("B3","B2")]
    if scn=="V0":
        comparisons += [("B3","B3-no-structure"),("B3","B3-no-queue"),("B4","B4-random-label"),("B4","B4-immediate")]
    for a,b in comparisons:
        for metric in ["restricted_h","true_restricted_h","completion_prob","cost_cny","decision_loss_cny","cny_per_confirmation",
                       "hours_gpu","dft_frames","cancelled","recomputed","wrong_drop_rate","fpr","recall","ppv","timely_phase_rate","timely_eis_rate"]:
            x,ux=estimator(group[a],metric)
            y,uy=estimator(group[b],metric)
            diff=x-y
            se=mean_se([p-q for p,q in zip(ux,uy)])[1]
            rel=(x/y-1)*100 if y else None
            sr=mean_se([100*(p-x/y*q)/y for p,q in zip(ux,uy)])[1] if y else None
            pairs.append(dict(scenario=scn,policy=a,reference=b,metric=metric,difference=diff,
                        diff_lo=diff-1.959964*se,diff_hi=diff+1.959964*se,relative_pct=rel,
                        pct_lo=rel-1.959964*sr if y else None,pct_hi=rel+1.959964*sr if y else None))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--reps",type=int,default=5000)
    parser.add_argument("--stress-reps",type=int,default=1000)
    parser.add_argument("--seed",type=int,default=731900)
    parser.add_argument("--workers",type=int,default=6)
    parser.add_argument("--out",type=Path,default=OUT)
    parser.add_argument("--scenarios",nargs="+",choices=list(SCENARIOS),default=list(SCENARIOS))
    args=parser.parse_args()
    if min(args.reps,args.stress_reps)<2: raise ValueError("至少需要两个种子")
    dst=args.out
    dst.mkdir(parents=True,exist_ok=True)
    summary=[];pairs=[]
    with mp.Pool(args.workers) as pool,gzip.open(dst/"monte_carlo.csv.gz","wt",encoding="utf-8",newline="",compresslevel=3) as raw:
        writer=None
        for scn in args.scenarios:
            count=args.reps if scn=="V0" else args.stress_reps
            jobs=[(scn,args.seed,start,min(count,start+32),scn=="V0") for start in range(0,count,32)]
            group={}
            for batch in pool.imap(worker,jobs):
                if writer is None:
                    writer=csv.DictWriter(raw,fieldnames=list(batch[0]))
                    writer.writeheader()
                for r in batch:
                    writer.writerow({k:(round(v,8) if isinstance(v,float) else v) for k,v in r.items()})
                    group.setdefault(r["policy"],[]).append(r)
            summarize(scn,group,summary,pairs)
            write_csv(dst/"policy_summary.csv",summary)
            write_csv(dst/"paired_effects.csv",pairs)
            print("finished",scn,count,flush=True)
    # A fixed, fully auditable counterfactual tape for every policy.
    trace=[]
    cfg=config("V0")
    demo_seed=args.seed
    for offset in range(100):
        tape=World(cfg,args.seed+offset)
        if DES(cfg,tape,"B4").run()["releases"]>0:
            demo_seed=args.seed+offset
            break
    for policy in BASE_POLICIES:
        sim=DES(cfg,World(cfg,demo_seed),policy,trace=True)
        sim.run()
        trace.extend(dict(seed=demo_seed,policy=policy,**r) for r in sim.trace)
    write_csv(dst/"event_trace.csv",trace)
    meta={"python":platform.python_version(),"run_utc":datetime.now(timezone.utc).isoformat(),
          "seed_base":args.seed,"paired_replicates_v0":args.reps,"paired_replicates_per_stress":args.stress_reps,
          "scenario_overrides":{k:SCENARIOS[k] for k in args.scenarios},"event_trace_seed":demo_seed,
          "event_trace_selection":"first of 100 fixed seeds with an accepted B4 version; demonstration only",
          "files_sha256":{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in
          [Path(__file__),ROOT/"simulation/minimal_des.py",ROOT/"configs/assumptions.yaml",ROOT/"configs/decision_policies.yaml"]}}
    (dst/"run_metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")

if __name__=="__main__":
    main()
