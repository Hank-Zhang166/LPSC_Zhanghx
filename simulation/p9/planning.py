"""Published-information planning only. Serializable state has no latent truth, sampled event times or RNG."""
from dataclasses import dataclass
from collections import Counter

@dataclass(frozen=True)
class View:
    i:int; ev:tuple; tested:frozenset; pending:tuple; clock:float; cutoff:float
    budget:float; stock:int; version:int; fitted:bool; committed:bool; viable_peers:int
    slots:dict; peer_action:str; peer_deadline:float; peer_value:float; running:tuple; queued:tuple

def finish(slots,t,route,actions):
    # Forward non-preemptive event calendar using public mean stage service times, including review.
    s={k:list(v) for k,v in slots.items()}
    starts=[]
    for op in route:
        for r,h in actions[op]:
            j=min(range(len(s[r])),key=s[r].__getitem__)
            begin=max(t,s[r][j]);t=begin+h
            s[r][j]=t;starts.append((r,begin,t))
    return t,s,starts

def observed(e,op):
    return next((bool(x[1]) for x in e if x[0]==op),None)

def disputed(ev):
    m=observed(ev,"redo")
    if m is None:m=observed(ev,"md")
    e=observed(ev,"eis")
    return e is not None and m is not None and e!=m

def options(v,ev,tested,stock,site,admit,allow_fit,belief,include_pending=True):
    _,g,b=belief.stats(v.i,ev)
    if v.committed:return []
    ops=[]
    if observed(ev,"eis") is True and g>=admit:ops.append("confirm")
    if len(tested.difference({"powder","confirm","fit","redo"}))<belief.project["max_diagnostics"]:
        ops += ["xrd","eis","md"]
        if observed(ev,"xrd") is not None:ops.append("local")
        if observed(ev,"eis") is not None:
            ops+=["repeat","contact"]
            if disputed(ev) and b>=belief.project["dft_alarm_floor"]:ops.append("dft")
    if allow_fit and not v.fitted and observed(ev,"dft") is True:ops.append("fit")
    if allow_fit and v.version and observed(ev,"md") is not None:ops.append("redo")
    return [a for a in ops if a not in tested and (a not in ("eis","contact") or stock>0)
            and (a!="repeat" or "eis" in tested) and (a!="confirm" or "eis" in tested)
            and site["costs"][a]<=v.budget]

def score_actions(v,policy,belief,site,project,admit,trace=False):
    pending=set(a for a,t in v.pending)
    tested=v.tested|pending
    multistep=policy.startswith("H")
    aware=policy in ("Q","H","H-fit","H-serial","H-shuffle","H-wait")
    allow_fit=policy in ("H-fit","H-shuffle")
    allow_parallel=policy not in ("F","G","H-serial","H-wait")
    if len(pending)>=(2 if allow_parallel else 1):return None,[]
    opts=options(v,v.ev,tested,v.stock,site,admit,allow_fit,belief)
    if not opts:return None,[]
    if policy in ("F","G"):
        e=observed(v.ev,"eis")
        if policy=="F":
            order=["xrd","md","eis","local","confirm"]
        elif observed(v.ev,"xrd") is False:
            return None,[]
        else:order=["xrd","eis","md","confirm"]
        ranked=[a for a in order if a in opts]
        return (ranked[0] if ranked else None),[(a,0.,None,"固定路径或专家门禁") for a in ranked]
    routes=site["stages"]
    slots=v.slots if aware else {r:[v.clock]*n for r,n in site["capacity"].items()}
    _,g,b=belief.stats(v.i,v.ev)
    records=[]
    def utility(ev,op,remaining_peers):
        if op=="fit":
            # Gain can be negative. Explicit prospective effect on a future verified family's MD decision.
            _,_,pb=belief.stats(v.i,ev)
            return max(0,site["fit_accept"]*site["fit_gain"]*.43*pb*min(remaining_peers,3)/3)
        return belief.step(v.i,ev,op,v.version,disputed(ev))[0]
    counter=0
    for op in opts:
        end,after,starts=finish(slots,v.clock,[op],routes)
        limit=project["horizon_h"] if op=="confirm" else v.cutoff
        if end>limit:
            records.append((op,-1.,end,"预计发布晚于行动期限"));continue
        value=utility(v.ev,op,v.viable_peers)
        # One-step resources are budget-constrained. B uses expected decision-loss reduction per nominal cost.
        if policy=="B":value=value*100/site["costs"][op]
        if multistep and op not in ("fit","confirm"):
            outcomes=belief.step(v.i,v.ev,op,v.version,disputed(v.ev))[1]
            cont=0.
            for e,prob in outcomes:
                best=0.
                ns=v.stock-int(op in ("contact","eis"))
                for nxt in options(v,e,tested|{op},ns,site,admit,allow_fit,belief):
                    if site["costs"][nxt]+site["costs"][op]>v.budget:continue
                    if nxt not in ("confirm","dft","fit","local","eis","md"):continue
                    nt,_,_=finish(after,end,[nxt],routes)
                    if nt>(project["horizon_h"] if nxt=="confirm" else v.cutoff) or end>v.cutoff:continue
                    best=max(best,utility(e,nxt,v.viable_peers))
                cont+=prob*best
            value+=cont
        # Carry forward already-reserved work; explicit displacement of another pending evidence release
        # within the same modelled decision loss. No currency/hour conversion or duplicate delay tariff.
        if aware and v.peer_value and op!="confirm":
            peer_end=finish(after,v.clock,[v.peer_action],routes)[0]
            peer_before=finish(slots,v.clock,[v.peer_action],routes)[0]
            if peer_before<=v.peer_deadline<peer_end:value-=v.peer_value
        records.append((op,value,end,"二步条件分支" if multistep else "单步决策风险"))
    if pending and multistep:
        # The competing wait path uses the pending outcome, not its realized future observation.
        wait_op,wait_time=min(v.pending,key=lambda x:x[1])
        if wait_op in belief.probs or (wait_op,v.version) in belief.probs:
            wait_val=0.
            for e,p in belief.step(v.i,v.ev,wait_op,v.version,disputed(v.ev))[1]:
                feasible=options(v,e,tested,v.stock,site,admit,allow_fit,belief)
                best=max((utility(e,a,v.viable_peers) for a in feasible if
                     finish(slots,max(v.clock,wait_time),[a],routes)[0]<=(project["horizon_h"] if a=="confirm" else v.cutoff)),default=0.)
                wait_val+=p*best
            records.append(("wait",wait_val,wait_time,"等待在制证据后分支"))
    if not records:return None,[]
    best=max(records,key=lambda t:(t[1],-site["costs"].get(t[0],0),-t[2]))
    if policy=="H-shuffle" and best[0]=="dft" and (v.i+len(v.ev))%2==0:return None,records
    # Physically required EIS can be a gateway even when binary preposterior EVSI has a flat decision boundary.
    if best[1]<=1e-10:
        if not pending and "eis" in opts and next((r[2] for r in records if r[0]=="eis"),1e9)<=v.cutoff:return "eis",records
        return None,records
    return (None if best[0]=="wait" else best[0]),records
