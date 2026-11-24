"""Joint sensitivity over declared engineering ranges. The reserve/scope is unchanged."""
from concurrent.futures import ProcessPoolExecutor
import csv
import math

import numpy as np
from engine import run
from run_study import OUT,dump,effect,summary

N_DESIGNS=24
N_PAIRS=96
RANGES={"freeze_h":(14,44),"review_scale":(.75,3.),"budget":(850,2600),"screen_quality":(.50,1.),
        "actual_global":(.06,.50),"actual_repair":(-.4,.95),"batch_separation":(.72,.98)}
# The last factor changes new-batch reproducibility for BOTH planner and world; previous
# unknown external screening degradation and true repair strength are hidden from policy.
def design():
    gen=np.random.default_rng(973480)
    profiles=[{} for _ in range(N_DESIGNS)]
    for name,(lo,hi) in RANGES.items():
        quant=(gen.permutation(N_DESIGNS)+gen.random(N_DESIGNS))/N_DESIGNS
        for row,q in zip(profiles,quant):row[name]=float(lo+(hi-lo)*q)
    return profiles

def block(arg):
    i,profile=arg
    cfg=dict(freeze_h=profile["freeze_h"],speed={"review":profile["review_scale"]},
             budget_diagnostic=round(profile["budget"]),screen_quality=profile["screen_quality"],
             truth_global=profile["actual_global"],truth_repair=profile["actual_repair"],
             batch_pass_if_target=profile["batch_separation"],batch_pass_if_nontarget=1-profile["batch_separation"])
    rows=[]
    for j in range(N_PAIRS):
        for p in ("myopic","tree","tree_fit"):
            r,_=run(933400+j,"baseline",p,overrides=cfg)
            r["scenario"]=f"profile_{i:02d}"
            rows.append(r)
    fx=effect(rows,"myopic",["success_rate","mean_cost","wrong_nomination","fit_count"])
    return [dict(profile=i,**profile,**r) for r in fx]

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument("--workers",type=int,default=8)
    with ProcessPoolExecutor(max_workers=ap.parse_args().workers) as pool:
        rows=[r for group in pool.map(block,enumerate(design())) for r in group]
    dump("joint_sensitivity.csv",rows)
