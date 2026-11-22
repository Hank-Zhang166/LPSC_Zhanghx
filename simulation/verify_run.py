"""Verify the archived seed tape, event invariants, accounting and no-lookahead prefix."""
import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from minimal_des import ROOT, DES, World, BASE_POLICIES, RES
from run_study import OUT,config

def check():
    meta=json.loads((OUT/"run_metadata.json").read_text(encoding="utf-8"))
    tests={}
    for file,expected in meta["files_sha256"].items():
        normalized=Path(*file.replace("\\","/").split("/"))
        assert hashlib.sha256((ROOT/normalized).read_bytes()).hexdigest()==expected, file
    tests["input_code_and_config_hashes"]=len(meta["files_sha256"])
    counts=Counter();replayed=0
    with gzip.open(OUT/"monte_carlo.csv.gz","rt",encoding="utf-8",newline="") as f:
        for row in csv.DictReader(f):
            scn,p=row["scenario"],row["policy"]
            counts[scn,p]+=1
            if int(row["rep"])>=2: continue
            c=config(scn)
            result=DES(c,World(c,int(row["seed"])),p).run()
            for k,v in result.items():
                assert (row[k]=="" if v is None else abs(float(row[k])-v)<1e-7),(scn,p,k)
            assert result["tp"]+result["fp"]==result["confirmed"]
            assert 0<=result["wrong_drop"]<=result["unconfirmed_good"]<=result["positive"]
            assert all(0<=result["util_"+r]<=1 for r in c["capacity"])
            replayed+=1
    for (scn,p),n in counts.items():
        assert n==meta["paired_replicates_v0" if scn=="V0" else "paired_replicates_per_stress"]
    tests.update(raw_rows=sum(counts.values()),replayed_seed_policy_profiles=replayed,scenario_count=len({s for s,p in counts}))
    with (OUT/"event_trace.csv").open(encoding="utf-8-sig",newline="") as f:
        logs=list(csv.DictReader(f))
    for p in BASE_POLICIES:
        started={};done={};issued={};cancelled=set();slots=Counter();released_ids=set()
        time=-1
        for e in (e for e in logs if e["policy"]==p):
            t=float(e["time_h"]);tid=e["task_id"];op=e["operation"]
            assert t>=time
            time=t
            if e["event"]=="queued":
                issued[tid]=t
            elif e["event"]=="started":
                assert tid in issued and issued[tid]<=t and tid not in cancelled
                started[tid]=t
                for r in RES[op]:
                    slots[r]+=1
                    assert slots[r]<=config("V0")["capacity"][r]
            elif e["event"]=="completed_unreviewed":
                assert tid in started and started[tid]<=t
                done[tid]=t
                for r in RES[op]:
                    slots[r]-=1
                    assert slots[r]>=0
            elif e["event"]=="qc_released":
                assert tid in done and done[tid]<=t
                released_ids.add(tid)
            elif e["event"]=="observation_applied":
                assert tid in released_ids
            elif e["event"]=="cancelled":
                assert tid in issued and tid not in started
                cancelled.add(tid)
        assert not any(slots.values())
    tests["event_rows_checked"]=len(logs)
    cfg=config("V0"); seed=meta["event_trace_seed"]
    w1=World(cfg,seed);w2=World(cfg,seed)
    for _,_,u,_ in w2.candidates:
        u[7]=1-u[7]  # Alter only still-hidden primary EIS outcomes.
    for p in BASE_POLICIES:
        a=DES(cfg,w1,p,True);b=DES(cfg,w2,p,True)
        a.run();b.run()
        t=min(r["time_h"] for r in a.trace if r["operation"]=="eis" and r["event"]=="qc_released")
        assert [r for r in a.trace if r["time_h"]<t]==[r for r in b.trace if r["time_h"]<t]
    tests["future_eis_changed_identical_observable_prefix"]=5
    cfg=config("exhaustive_confirmation")
    w=World(cfg,seed)
    assert all(DES(cfg,w,p).run()==DES(cfg,w,"B0").run() for p in BASE_POLICIES)
    tests["forced_protocol_policy_identity"]=True
    assert (24*10-(24-6)*10,6/24)==(60,0.25)
    tests["arithmetic_example_only"]={"gpu_h":60,"fraction":.25}
    (OUT/"verification.json").write_text(json.dumps(tests,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(tests,ensure_ascii=False))

if __name__=="__main__":
    check()
