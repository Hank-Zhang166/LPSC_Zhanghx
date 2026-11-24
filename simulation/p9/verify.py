"""Regression tests for clock semantics, hidden-state isolation and the archived matched experiment."""
import csv
import gzip
import hashlib
import json
import math
from collections import Counter
from dataclasses import fields,replace
from pathlib import Path
from engine import Simulator,World
from belief import Beliefs,load_priors
from planning import View,finish,score_actions
from study import D,OUT,PRIOR,FULL,STRESS,model

def main():
    m=json.loads((OUT/"metadata.json").read_text(encoding="utf8"))
    for name,digest in m["sha256"].items():assert hashlib.sha256((D/name).read_bytes()).hexdigest()==digest,name
    checks={"sha256_inputs":len(m["sha256"])}
    assert not any(f.name in ("world","truth","hidden","outer_seed","sampled_duration") for f in fields(View))
    b=model("baseline");q0=0
    for i in range(7):
        for op in ("md","eis","dft","contact","local","xrd","repeat"):
            evsi,paths,risk=b.step(i,(),op,0,True)
            assert -.0000001<=evsi<=risk+1e-8
            assert abs(sum(w for e,w in paths)-1)<1e-10
            w,g,bias=b.stats(i,());gnew=sum(b.stats(i,e)[1]*p for e,p in paths)
            assert abs(g-gnew)<1e-10
            q0+=1
    checks["evsi_evpi_bounds_and_total_probability"]=q0
    # Exact uninformative-action degeneration. Confirmation is intentionally not this action class.
    z=model("unhelpful_diagnostics")
    for i in range(7):
        for op in ("md","dft","eis","local","xrd","contact"):assert abs(z.step(i,(),op,0,True)[0])<1e-10
    checks["uninformative_action_zero_evsi"]=42
    class FlipEIS(World):
        def signal(self,i,op,v):
            y=super().signal(i,op,v)
            return not y if op=="eis" else y
    for pol in ("F","G","B","Q","H","H-fit"):
        a=Simulator(b,World(m["trace_seed"],b),pol,trace=True);c=Simulator(b,FlipEIS(m["trace_seed"],b),pol,trace=True)
        a.run();c.run()
        first=min(r["t"] for r in a.history if r["event"]=="qc_released" and r["action"]=="eis")
        assert [r for r in a.history if r["t"]<first]==[r for r in c.history if r["t"]<first]
        assert [r for r in a.choice if r["t"]<first]==[r for r in c.choice if r["t"]<first]
    checks["future_signal_reversal_leaves_event_and_decision_prefix"]=6
    with (OUT/"event_trace.csv").open(encoding="utf-8-sig",newline="") as f:events=list(csv.DictReader(f))
    for p in FULL:
        cur=Counter();submitted={};started=set();last=-1;published=set();positive_eis=set();positive_dft=set()
        closed=set();powder=set();frozen=set();released_versions={0}
        for e in (e for e in events if e["policy"]==p):
            t=float(e["t"]);assert t>=last;last=t
            ev=e["event"];op=e["action"];tid=e["task"];i=e["i"];r=e["resource"]
            if ev=="freeze":frozen.add(i)
            if ev=="powder_ready":powder.add(i)
            if ev=="submitted":
                assert float(e["remaining"])>=-.01
                if op!="powder":assert i in powder and i not in frozen
                if op=="confirm":assert i in positive_eis and "B2" in e["sample_id"]
                if op=="fit":assert i in positive_dft
                if op=="redo":assert int(e["version"]) in released_versions
                submitted[tid]=e
            if ev=="cancelled":assert tid in submitted and tid not in started
            if ev=="stage_start":
                assert tid in submitted
                started.add(tid);cur[r]+=1;assert cur[r]<=b.site["capacity"][r]
            if ev=="stage_done":cur[r]-=1;assert cur[r]>=0
            if ev=="qc_released":
                assert tid in started
                if op=="eis" and e["detail"]=="y=1":positive_eis.add(i)
                if op=="dft" and e["detail"]=="y=1":positive_dft.add(i)
                published.add(tid)
            if ev=="model_published":assert tid in published and int(e["version"])==1;released_versions.add(1)
    checks["event_rows_with_dependencies_and_slots"]=len(events)
    basecount=Counter();replayed=0
    with gzip.open(OUT/"replicates.csv.gz","rt",encoding="utf8",newline="") as f:
        for row in csv.DictReader(f):
            sc,policy,setting,seed=row["scenario"],row["policy"],row["setting"],int(row["seed"])
            basecount[(sc,policy,setting)]+=1
            assert float(row["cost"])<=float(row["committed"])+1e-5
            if seed in (m["base_seed"],m["base_seed"]+1):
                bm=model(sc);result=Simulator(bm,World(seed,bm),policy,float(row["threshold"])).run()
                for k,v in result.items():
                    if isinstance(v,str):assert v==row[k]
                    else:assert abs(v-float(row[k]))<1e-6,(sc,policy,k)
                replayed+=1
    assert all(n==(m["replicates"] if sc=="baseline" else m["stress_replicates"]) for (sc,p,label),n in basecount.items())
    checks["evaluation_rows"]=sum(basecount.values());checks["exact_replay_records"]=replayed
    # A forced off-window wait then a recovered stock slot must not interrupt an active irreversible stage.
    w=World(7,b);s=Simulator(b,w,"H");q=s.samples[0];q.ready=True
    s.submit(q,"eis");assert q.stock==b.project["powder_aliquots"]-1
    s.cancel(q,"eis","test");assert q.stock==b.project["powder_aliquots"] and abs(s.encumbered)<1e-7
    s.submit(q,"eis");s.dispatch();s.cancel(q,"eis","test");assert "eis" in q.pending
    checks["cancellation_stock_budget_nonpreemption"]=True
    # Order-invariant keyed timestamps and the two-step calendar's exact one-resource fork.
    w1=World(112,b);w2=World(112,b)
    assert [w1.signal(i,"md",0) for i in (0,1,3)]==list(reversed([w2.signal(i,"md",0) for i in (3,1,0)]))
    slots={"a":[10.],"r":[0.]};route={"x":[["a",3],["r",2]],"y":[["a",1],["r",1]]}
    assert finish(slots,0,["x","y"],route)[0]==17 and slots["a"]==[10.]
    checks["stable_keys_and_forward_calendar"]=True
    for name in ("matched_operating_points.csv","joint_sensitivity.csv"):
        if (OUT/name).exists():
            with (OUT/name).open(encoding="utf-8-sig",newline="") as f:checks[name+"_rows"]=len(list(csv.DictReader(f)))
    (OUT/"checks.json").write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps(checks))
if __name__=="__main__":main()
