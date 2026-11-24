"""Discrete-event outer evaluation. A stable mechanism key gives paired counterfactuals."""
import hashlib
import heapq
import math
import random
from copy import deepcopy

import numpy as np

from belief import Action, BATCH1, BIAS, CONTACT, DOMAINS, GOOD, LAB, N, PROJECT, initial, positive
from planning import COST, OPS, Job, choose, release, reserve

SCENARIOS={
    "baseline":{},
    "busy_review":{"blackout":{"review":9.5},"speed":{"review":2.7}},
    "early_freeze":{"freeze_h":13.},
    "weak_repair":{"truth_repair":-.30,"truth_accept":.42},
    "poor_screen":{"screen_quality":.56},
    "adequate_potential":{"truth_local":[.025,.045],"truth_global":.10},
}


def config(scenario,floor=None):
    cfg=deepcopy(PROJECT)
    cfg.update({"blackout":{},"speed":{},"truth_accept":cfg["acceptance"],
                "truth_repair":cfg["fit_repair"],"truth_local":cfg["p_local_bias_by_global"],
                "truth_global":cfg["p_global_risk"],"screen_quality":1.})
    cfg.update(SCENARIOS[scenario])
    if floor is not None:cfg["posterior_floor"]=floor
    return cfg


def rng(seed,*keys):
    raw="|".join(map(str,(seed,*keys))).encode()
    return random.Random(int.from_bytes(hashlib.blake2b(raw,digest_size=8).digest(),"big"))


def prior_world(seed,cfg):
    outer=dict(cfg,p_global_risk=cfg["truth_global"],p_local_bias_by_global=cfg["truth_local"])
    b=initial(outer)
    g=int(rng(seed,"shared_field").random()<outer["p_global_risk"])
    return [rng(seed,i,"candidate").choices(range(len(GOOD)),weights=b.p[g,i])[0] for i in range(N)]


def duration(seed,a,j,cfg):
    r,h,_=OPS[a.kind][j]
    cv=LAB["cv"][r];stream=rng(seed,a.i,a.kind,j,"duration")
    if r=="gpu": factor=stream.uniform(1-math.sqrt(3)*cv,1+math.sqrt(3)*cv)
    else:
        s=math.sqrt(math.log1p(cv**2));factor=stream.lognormvariate(-s*s/2,s)
    return h*factor*cfg["speed"].get(r,1.)


def observe(seed,a,state,cfg):
    like=positive(a.kind,cfg["truth_repair"])
    if a.kind in ("screen","pellet"):
        like=.5+cfg["screen_quality"]*(like-.5)
    return rng(seed,a.i,a.kind,"reading").random()<like[state]


def run(seed,scenario,policy,floor=None,record=False,world_override=None,overrides=None):
    cfg=config(scenario,floor)
    if overrides:cfg.update(overrides)
    states=prior_world(seed,cfg) if world_override is None else world_override
    # Explicit read boundary: outside service draws, actual labels, batch realizations and
    # misspecified outer likelihoods are never fields of the decision-time configuration.
    public_keys=("p_global_risk","p_local_bias_by_global","p_contact","freeze_h","speed",
                 "blackout","maximum_inflight","posterior_floor","minimum_action_gain",
                 "max_outer_branch_actions","fit_repair","acceptance","batch_pass_if_target","batch_pass_if_nontarget")
    planner_cfg={k:cfg[k] for k in public_keys}
    if policy=="tree_no_share":
        mix=(1-cfg["p_global_risk"])*cfg["p_local_bias_by_global"][0]+cfg["p_global_risk"]*cfg["p_local_bias_by_global"][1]
        planner_cfg["p_local_bias_by_global"]=[mix,mix]
    if policy=="tree_serial":cfg["maximum_inflight"]=planner_cfg["maximum_inflight"]=1
    b=initial(planner_cfg);eligible=np.zeros(N,dtype=bool);diff=set()
    calendar=[];count=0;clock=0.;jobs={};busy={};events=[]
    total_cost=0.;budget=cfg["budget_diagnostic"];frozen=False;selected=-1;confirmed=False
    selected_prob=0.;first_confirmation=cfg["horizon_h"];late=0;forks=0;dft=0;fit=0;accepted=0
    wrong_fit=0;dft_clean=0;batch2_pass=False;bias_flags=set()
    def event(when,kind,payload=None):
        nonlocal count
        count+=1
        # A release occurring at exactly freeze must be processed before freeze.
        priority={"stage_done":0,"freeze":1,"external_release":0}.get(kind,3)
        heapq.heappush(calendar,(when,priority,count,kind,payload))
    def log(name,a=None,res="",detail=""):
        if record:
            events.append(dict(time_h=round(clock,4),event=name,candidate=("" if a is None else f"{a.i/10:.1f}"),
                               action=("" if a is None else a.kind),resource=res,detail=detail))

    for i,state in enumerate(states):
        seen={}
        for kind in ("screen","old"):
            a=Action(kind,i);y=observe(seed,a,state,cfg);seen[kind]=y
            likelihood=positive(kind)
            b,_=b.update(a,likelihood if y else 1-likelihood)
            log("initial_release",a,detail="+" if y else "-")
        eligible[i]=seen["screen"]
        if seen["screen"]!=seen["old"]:diff.add(i)
    book=(frozenset(),eligible,diff,frozenset(),None,np.full(N,2))
    for res,t in cfg["blackout"].items():busy[res]=None;event(t,"external_release",res)
    event(cfg["freeze_h"],"freeze")
    def submit(a,why):
        nonlocal budget,book,dft,fit,forks,dft_clean,wrong_fit
        if a.kind!="confirm":
            budget-=COST[a.kind];book=reserve(book,a)
            assert budget>=0 and np.min(book[-1])>=0
        dft+=int(a.kind=="dft")
        dft_clean+=int(a.kind=="dft" and not BIAS[states[a.i]])
        fit+=int(a.kind=="fit")
        if a.kind!="confirm" and any(j.start is not None for j in jobs.values()):forks+=1
        jobs[a]=Job(a,clock,queued=clock);log("submitted",a,detail=why)
    def start_ready():
        nonlocal total_cost
        for job in sorted(jobs.values(),key=lambda j:(j.queued,j.submitted,j.action.i,j.action.kind)):
            if job.start is not None:continue
            a=job.action;res,_,fee=OPS[a.kind][job.index]
            if res in busy:continue
            busy[res]=a;job.start=clock;total_cost+=fee
            event(clock+duration(seed,a,job.index,cfg),"stage_done",a)
            log("start",a,res,f"stage={job.index+1}; batch={'B2' if a.kind=='confirm' else 'B1/compute'}")
    def decide():
        if frozen:return
        while len(jobs)<cfg["maximum_inflight"]:
            a,why=choose(clock,list(jobs.values()),book,b,budget,planner_cfg,policy)
            if a is None:
                log("wait",detail=why);break
            submit(a,why);start_ready()

    decide()
    while calendar:
        time,_,_,kind,payload=heapq.heappop(calendar)
        if time>cfg["horizon_h"]:break
        clock=time
        if kind=="external_release":
            del busy[payload];log(kind,res=payload)
        elif kind=="freeze":
            frozen=True
            p=b.probs()
            idx=[i for i in range(N) if book[1][i] and p[i]>=cfg["posterior_floor"]]
            selected=max(idx,key=lambda i:(p[i],-i),default=-1)
            if selected>=0:selected_prob=float(p[selected])
            log("lock",None if selected<0 else Action("confirm",selected),
                detail=f"floor={cfg['posterior_floor']:.2f}; posterior={selected_prob:.4f}; eligible={sum(book[1])}")
            # Only a job whose first stage has never begun is reversible.
            for a,j in list(jobs.items()):
                if j.index==0 and j.start is None:
                    del jobs[a];budget+=COST[a.kind]
                    if a.kind in ("contact","pellet"):
                        book[-1][a.i]+=1
                    log("cancelled",a,detail="unstarted at lock; unspent reservation released")
            if selected>=0:submit(Action("confirm",selected),"reserved independent powder B2")
        else:
            a=payload;j=jobs[a];res=OPS[a.kind][j.index][0]
            assert busy.pop(res)==a
            log("complete",a,res,f"stage={j.index+1}")
            rejected=(a.kind=="fit" and j.index==3 and rng(seed,a.i,"fit","accept").random()>=cfg["truth_accept"])
            if a.kind=="fit" and j.index==3:
                log("rollback" if rejected else "version_published",a,res,"holdout rejected" if rejected else f"scenario domain {DOMAINS[a.i]}; re-MD follows")
                if not rejected:
                    accepted+=1
                    book=(book[0],book[1],book[2],book[3],DOMAINS[a.i],book[5])
                wrong_fit+=int(rejected or not BIAS[states[a.i]] or cfg["truth_repair"]<=0)
            if j.index+1<len(OPS[a.kind]) and not rejected:
                j.index+=1;j.start=None;j.queued=clock
            else:
                del jobs[a]
                if a.kind=="confirm":
                    # Independent powder draw, followed by a separate EIS readout.
                    yield_prob=cfg["batch_pass_if_target"] if GOOD[states[a.i]] else cfg["batch_pass_if_nontarget"]
                    batch2_pass=rng(seed,a.i,"independent_B2_batch").random()<yield_prob
                    prob=cfg["confirm_sensitivity"] if batch2_pass else 1-cfg["confirm_specificity"]
                    confirmed=rng(seed,a.i,"independent_B2_EIS").random()<prob
                    if confirmed:first_confirmation=clock
                    log("independent_release",a,res,"+" if confirmed else "-")
                else:
                    if rejected:label="rejected"
                    else:
                        label="+" if observe(seed,a,states[a.i],cfg) else "-"
                        if a.kind=="fit":label="pass"+label
                    if frozen:
                        late+=1;log("late_release",a,res,label)
                    else:
                        from belief import outcomes
                        likelihood=dict(outcomes(a,cfg))[label]
                        if a.kind=="dft" and label=="+":bias_flags.add(a.i)
                        old_top=int(b.probs().argmax())
                        b,_=b.update(a,likelihood);book=release(book,a,label)
                        log("qc_released",a,res,f"{label}; p_candidate={b.probs()[a.i]:.3f}; P_shared={b.h[1]:.3f}; leader={old_top/10:.1f}->{b.probs().argmax()/10:.1f}")
        start_ready()
        # Simultaneous completions are visible together; freeze takes precedence over new starts.
        if not calendar or calendar[0][0]>clock+1e-12:decide()

    anygood=any(GOOD[j] for j in states)
    truly_good=selected>=0 and bool(GOOD[states[selected]])
    success=confirmed and truly_good and batch2_pass
    true_bias={i for i,state in enumerate(states) if BIAS[state]}
    return dict(scenario=scenario,policy=policy,seed=seed,success_rate=int(success),
                opportunity=int(anygood),miss_rate=int(anygood and not success),
                wrong_release_rate=int(confirmed and not (truly_good and batch2_pass)),wrong_nomination=int(selected>=0 and not truly_good),
                no_nomination=int(selected<0),mean_cost=total_cost,restricted_h=first_confirmation,
                dft_count=dft,clean_dft_count=dft_clean,fit_count=fit,accepted_fit=accepted,unhelpful_fit=wrong_fit,late=late,
                false_bias_flags=len(bias_flags-true_bias),missed_bias_count=len(true_bias-bias_flags),
                true_bias_count=len(true_bias),batch2_pass=int(batch2_pass),confirm_read=int(confirmed),
                parallel_submits=forks,selected=selected,selected_p=selected_prob),events
