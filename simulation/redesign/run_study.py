"""python run_study.py --workers 8 (NumPy only); all inputs under version control."""
import argparse
import csv
import gzip
import json
import math
import os
import statistics
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from belief import HERE
from engine import SCENARIOS, run

OUT=HERE/"outputs"
PRIMARY=["screen_only","gate","myopic","tree","tree_fit","tree_serial","tree_no_share"]
STRESS=["gate","myopic","tree","tree_fit"]
METRICS=["success_rate","miss_rate","wrong_release_rate","wrong_nomination","no_nomination","mean_cost",
         "restricted_h","dft_count","clean_dft_count","fit_count","accepted_fit","unhelpful_fit","late","false_bias_flags","missed_bias_count","true_bias_count","parallel_submits"]
FLOORS=[.58,.68,.78,.88,.94,.97]
DEV_BASE=908100
TEST_BASE=912500
FPR_LIMIT=.065
N_BASE=1024
N_STRESS=256
N_DEV=192
N_TEST=512


def task(args):
    seed,scenario,p,f=args
    row,_=run(seed,scenario,p,f)
    if f is not None:row["floor"]=f
    return row


def dispatch(pool,plan):
    return list(pool.map(task,plan,chunksize=8))


def dump(name,rows):
    assert rows
    dest=OUT/name
    opener=gzip.open if dest.suffix==".gz" else open
    with opener(dest,"wt",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def avg(v):return statistics.fmean(v)


def effect(rows,reference,fields=METRICS):
    groups=defaultdict(dict)
    for r in rows:groups[r["scenario"],r["policy"]][r["seed"]]=r
    out=[]
    for (s,p),values in groups.items():
        if p==reference or (s,reference) not in groups:continue
        base=groups[s,reference];assert set(base)==set(values)
        for m in fields:
            ds=[v[m]-base[i][m] for i,v in values.items()]
            delta=avg(ds);half=1.96*statistics.stdev(ds)/math.sqrt(len(ds))
            out.append(dict(scenario=s,policy=p,reference=reference,metric=m,
                       difference=delta,ci_low=delta-half,ci_high=delta+half,n=len(ds),discordant=sum(v!=0 for v in ds)))
    return out


def summary(rows):
    groups=defaultdict(list)
    for r in rows:groups[r["scenario"],r["policy"]].append(r)
    return [dict(scenario=s,policy=p,n=len(group),**{m:avg(r[m] for r in group) for m in METRICS},
                 opportunity_rate=avg(r["opportunity"] for r in group)) for (s,p),group in groups.items()]


def study(workers):
    OUT.mkdir(exist_ok=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        plan=[(874031+i,s,p,None) for s in SCENARIOS for i in range(N_BASE if s=="baseline" else N_STRESS)
              for p in (PRIMARY if s=="baseline" else STRESS)]
        rows=dispatch(pool,plan)
        dump("replicates.csv.gz",rows)
        all_summary=summary(rows);dump("policy_summary.csv",all_summary)
        effects=effect(rows,"myopic")+effect(rows,"gate")+effect(rows,"tree")
        dump("paired_effects.csv",effects)
        # Explicitly report examples on both sides of a mean; do not pick a trace as proof.
        by=defaultdict(dict)
        for r in rows:
            if r["scenario"]=="baseline":by[r["seed"]][r["policy"]]=r
        examples=[]
        for label,predicate in [
            ("one_step_confirms_two_step_misses",lambda a,b:a["success_rate"]>b["success_rate"]),
            ("two_step_confirms_one_step_misses",lambda a,b:b["success_rate"]>a["success_rate"]),
            ("proactive_concurrent_evidence",lambda a,b:b["parallel_submits"]>=1 and b["dft_count"]>=1),
            ("training_requested",lambda a,b:b["fit_count"]>=1)]:
            for seed,d in sorted(by.items()):
                a=d["myopic"];b=d["tree_fit"]
                if predicate(a,b):
                    examples.append(dict(case=label,seed=seed,myopic_selected=a["selected"],tree_fit_selected=b["selected"],
                                    myopic_success=a["success_rate"],tree_fit_success=b["success_rate"],tree_fit_cost=b["mean_cost"]));break
        dump("counterexamples.csv",examples)
        # Replay a prespecified type of decision reversal; the first seed meeting it is displayed.
        seed=next((r["seed"] for r in examples if r["case"]=="two_step_confirms_one_step_misses"),874031)
        _,events=run(seed,"baseline","tree_fit",record=True)
        dump("events.csv",events)
        dev=dispatch(pool,[(DEV_BASE+i,"baseline",p,f) for p in STRESS for f in FLOORS for i in range(N_DEV)])
        frozen={};cal=[]
        for p in STRESS:
            scores=[]
            for f in FLOORS:
                block=[r for r in dev if r["policy"]==p and r["floor"]==f]
                wrong=avg(r["wrong_nomination"] for r in block);success=avg(r["success_rate"] for r in block)
                scores.append((wrong>FPR_LIMIT,-success,avg(r["mean_cost"] for r in block),f))
                cal.append(dict(policy=p,floor=f,n=N_DEV,max_wrong_nomination=FPR_LIMIT,actual_wrong=wrong,
                                success_rate=success,mean_cost=scores[-1][2],feasible=int(wrong<=FPR_LIMIT)))
            frozen[p]=min(scores)[-1]
        for r in cal:r["selected"]=int(r["floor"]==frozen[r["policy"]])
        dump("development.csv",cal)
        test=dispatch(pool,[(TEST_BASE+i,"baseline",p,frozen[p]) for i in range(N_TEST) for p in STRESS])
        for r in test:r["scenario"]="held_out_risk"
        dump("risk_evaluation.csv",[{**r,"floor":frozen[r["policy"]]} for r in summary(test)])
        dump("risk_effects.csv",effect(test,"myopic"))
        dump("risk_replicates.csv.gz",test)
    (OUT/"design.json").write_text(json.dumps(dict(baseline_n=N_BASE,stress_n=N_STRESS,dev_n=N_DEV,heldout_n=N_TEST,
                  baseline_seed=874031,dev_seed=DEV_BASE,heldout_seed=TEST_BASE,trace_seed=seed,
                  heldout_floors=frozen,outer_rows=len(rows),test_rows=len(test),development_runs=len(dev),
                  ci_method="paired mean difference ± 1.96*SE across common seven-composition queues; Monte Carlo error only",
                  synthetic_design=True),ensure_ascii=False,indent=2),encoding="utf-8")


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--workers",type=int,default=min(os.cpu_count() or 1,8))
    study(ap.parse_args().workers)
