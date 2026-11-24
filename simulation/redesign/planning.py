"""Public-state calendar and finite conditional tree. No evaluator RNG or latent World."""
from dataclasses import dataclass
import math

import numpy as np
from belief import Action, DOMAINS, LAB, N, outcomes, positive

OPS=LAB["operations"]
COST={k:sum(step[2] for step in v) for k,v in OPS.items()}
MEAN={k:sum(step[1] for step in v) for k,v in OPS.items()}


@dataclass
class Job:
    action: Action
    submitted: float
    index: int=0
    start: float|None=None
    queued: float=0.


def calendar(now,jobs,conf):
    """FCFS forecast with current stages and mean residuals. No sampled future durations."""
    clocks={r:max(now,t) for r,t in conf["blackout"].items()}
    targets=[]
    states=[]
    for order,job in enumerate(jobs):
        a=job.action
        stage=OPS[a.kind][job.index]
        duration=stage[1]*conf["speed"].get(stage[0],1.)
        if job.start is not None:
            end=now+max(.1,duration-(now-job.start))
            clocks[stage[0]]=end
            states.append([end,order,job.index+1])
        else:
            states.append([job.queued,order,job.index])
        targets.append(now)
    # Stage arrival order: the previous stage must complete before the next can join a queue.
    while states:
        states.sort(reverse=True)
        ready,order,index=states.pop()
        a=jobs[order].action
        if index==len(OPS[a.kind]):
            targets[order]=max(now,ready)
            continue
        res,h,_=OPS[a.kind][index]
        start=max(now,ready,clocks.get(res,now))
        end=start+h*conf["speed"].get(res,1.)
        clocks[res]=end
        states.append([end,order,index+1])
    return targets


def release(book,a,label):
    done, eligible, discrepancy, dft_pos, version, wet = book
    eligible=eligible.copy()
    if a.kind=="pellet" and label=="+": eligible[a.i]=True
    dft_pos=dft_pos|({a.i} if a.kind=="dft" and label=="+" else set())
    if a.kind=="fit" and label.startswith("pass"): version=DOMAINS[a.i]
    return done,eligible,discrepancy,dft_pos,version,wet


def reserve(book,a):
    done,eligible,discrepancy,dft_pos,version,wet=book
    updated=wet.copy()
    if a.kind in ("contact","pellet"):updated[a.i]-=1
    return done|{a},eligible,discrepancy,dft_pos,version,updated


def feasible(book,available,policy):
    done,eligible,discrepancy,dft_pos,version,wet=book
    actions=[]
    fit_requested=any(a.kind=="fit" for a in done)
    for i in range(N):
        for kind in ("pellet","structure","contact","md","dft","fit","redo"):
            a=Action(kind,i)
            if a in done or COST[kind]>available:continue
            if kind in ("pellet","contact") and wet[i]<=0:continue
            if kind=="dft" and i not in discrepancy:continue
            if kind=="fit" and (policy!="tree_fit" or fit_requested or i not in dft_pos):continue
            if kind=="redo" and version!=DOMAINS[i]:continue
            actions.append(a)
    return actions


def visible_menu(now,book,budget,jobs,conf,policy):
    menu=[]
    deadlines={}
    for a in feasible(book,budget,policy):
        if a.kind not in deadlines:
            new=Job(a,now,queued=now)
            deadlines[a.kind]=calendar(now,jobs+[new],conf)[-1]
        if deadlines[a.kind]<=conf["freeze_h"]+1e-8:menu.append(a)
    return menu


def best_value(b,book,acts,conf):
    return max(b.utility(book[1],conf["posterior_floor"]),max(b.expected_value(acts,book[1],conf),default=0.))


def pending_outcomes(job,conf):
    if job.action.kind=="fit" and job.index>=4:
        # The acceptance review has already published; only the new trajectory is pending.
        p=positive("fit",conf["fit_repair"])
        return (("pass-",1-p),("pass+",p))
    return outcomes(job.action,conf)


def conditional_wait(now,pending,b,book,budget,conf,policy):
    a=pending.action
    t=calendar(now,[pending],conf)[0]
    value=0.
    for label,like in pending_outcomes(pending,conf):
        post,prob=b.update(a,like)
        branch=release(book,a,label)
        later=visible_menu(t,branch,budget,[],conf,policy)
        value+=prob*best_value(post,branch,later,conf)
    return value


def choose(now,jobs,book,b,budget,conf,policy):
    if policy=="screen_only":return None,"preregistered_no_additional_diagnostics"
    if len(jobs)>=conf["maximum_inflight"]:return None,"inflight_limit"
    items=visible_menu(now,book,budget,jobs,conf,policy)
    if not items:return None,"no_feasible_release"
    preorder=b.probs()
    if policy=="gate":
        # Competing static procedure uses the same evidence and independent confirmation gate.
        rank=sorted(range(N),key=lambda i:-preorder[i])
        staged=[Action(k,i) for k in ("pellet","md","dft") for i in rank[:3]]
        winner=next((a for a in staged if a in items),None)
        return winner,"fixed_top3_pellet_md_dft"
    base=b.utility(book[1],conf["posterior_floor"])
    single=b.expected_value(items,book[1],conf)
    values=single.copy()
    threshold=conf["minimum_action_gain"]
    if jobs:
        pending=jobs[0].action
        # Compare launching now with keeping the pending observation only. Both branches
        # are used even when the planned action would finish before the current job.
        if calendar(now,jobs,conf)[0]<=conf["freeze_h"]:
            values=np.zeros(len(items));base=0.
            for label,like in pending_outcomes(jobs[0],conf):
                post,prob=b.update(pending,like)
                branch=release(book,pending,label)
                base+=prob*post.utility(branch[1],conf["posterior_floor"])
                values+=prob*post.expected_value(items,branch[1],conf)
            if policy.startswith("tree"):
                base=max(base,conditional_wait(now,jobs[0],b,book,budget,conf,policy))
    elif policy.startswith("tree"):
        # Beam over first actions only. Every admissible second action is evaluated.
        priority=sorted(range(len(items)),key=lambda k:(-single[k],COST[items[k].kind],items[k].i))
        keep=priority[:conf["max_outer_branch_actions"]]
        # Ensure evidence for a model update is considered even if first-step EVSI is low.
        for special in ("dft","fit"):
            alt=next((k for k in priority if items[k].kind==special),None)
            if alt is not None and alt not in keep:keep.append(alt)
        continuation=np.zeros(len(items))-np.inf
        for k in keep:
            a=items[k]
            arrival=calendar(now,[Job(a,now,queued=now)],conf)[0]
            held=reserve(book,a)
            conditional=0.
            for label,like in outcomes(a,conf):
                post,prob=b.update(a,like)
                state=release(held,a,label)
                future=visible_menu(arrival,state,budget-COST[a.kind],[],conf,policy)
                conditional+=prob*best_value(post,state,future,conf)
            # If waiting to do nothing informative merely gives credit for a useful second
            # action that could already be launched, prefer that second action first.
            if single[k]-base<=1e-10 and conditional<=single.max()+1e-10:continue
            continuation[k]=conditional
        values=np.maximum(values,continuation)
    k=max(range(len(items)),key=lambda j:(round(values[j],10),round(single[j],10),-COST[items[j].kind],-items[j].i))
    if values[k]-base<threshold:return None,("wait_for_report" if jobs else "small_increment")
    return items[k],f"V={values[k]:.4f}; alternative={base:.4f}; immediate={single[k]:.4f}"
