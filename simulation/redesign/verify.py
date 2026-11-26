"""Recheck the decision math, sample independence, information clock and paired outputs."""
import csv
import gzip
import json
import math
import unittest

import numpy as np
from belief import Action,BATCH1,BIAS,DOMAINS,GOOD,HERE,N,initial,outcomes,positive
from engine import config,prior_world,rng,run
from planning import OPS,Job,calendar,feasible,pending_outcomes,reserve
from run_study import N_BASE,N_TEST,OUT,effect


def rec(name):
    path=OUT/name;opener=gzip.open if path.suffix==".gz" else open
    with opener(path,"rt",encoding="utf-8",newline="") as handle:return list(csv.DictReader(handle))


class Integrity(unittest.TestCase):
    def test_exhaustive_terminal_value(self):
        c=config("baseline");b=initial(c);e=np.array([0,1,0,1,0,0,0],dtype=bool)
        for i in range(N):
            b,_=b.update(Action("old",i),positive("old") if i%2 else 1-positive("old"))
        actions=[Action(k,i) for i in range(N) for k in ("pellet","contact","dft","fit","redo")]
        vals=b.expected_value(actions,e,c)
        for a,got in zip(actions,vals):
            val=0
            for name,l in outcomes(a,c):
                post,q=b.update(a,l);e1=e.copy()
                if a.kind=="pellet" and name=="+":e1[a.i]=True
                val+=q*post.utility(e1,c["posterior_floor"])
            self.assertAlmostEqual(float(got),val,places=11)
            self.assertGreaterEqual(val+1e-12,b.utility(e,c["posterior_floor"]))

    def test_shared_evidence_transfer(self):
        c=config("baseline");b=initial(c)
        b,_=b.update(Action("old",1),positive("old"))
        update,_=b.update(Action("dft",0),positive("dft"))
        self.assertGreater(update.h[1],b.h[1])
        self.assertGreater(abs(update.probs()[1]-b.probs()[1]),1e-5)
        np.testing.assert_allclose(update.p.sum(axis=2),1.)
        # Removing the shared field retains marginal bias risk but removes cross-candidate information.
        mix=b.h @ np.array(c["p_local_bias_by_global"])
        c["p_local_bias_by_global"]=[float(mix)]*2;b=initial(c)
        b,_=b.update(Action("old",1),positive("old"));update,_=b.update(Action("dft",0),positive("dft"))
        self.assertAlmostEqual(update.probs()[1],b.probs()[1])

    def test_b1_and_b2(self):
        c=config("baseline");different=0
        for seed in range(1100,1200):
            states=prior_world(seed,c)
            for i,state in enumerate(states):
                py=c["batch_pass_if_target"] if GOOD[state] else c["batch_pass_if_nontarget"]
                b2=rng(seed,i,"independent_B2_batch").random()<py
                different+=int(b2!=bool(BATCH1[state]))
        self.assertGreater(different,30)
        # Outcomes out of one powder remain correlated even at fixed target, unlike B2.
        py=c["batch_pass_if_target"];s=np.array([.13,.87]);p=np.array([.10,.92]);weights=np.array([1-py,py])
        self.assertGreater(float(weights@(s*p)-(weights@s)*(weights@p)),0)

    def test_resource_forecast(self):
        c=config("baseline")
        jobs=[Job(Action("pellet",0),0.,index=0,start=0.,queued=0.),Job(Action("pellet",1),0.,queued=0.)]
        slow=calendar(1.,jobs,c);fast=calendar(1.,jobs[1:],c)
        self.assertGreater(slow[1],fast[0])
        self.assertAlmostEqual(slow[0],4.6)
        self.assertAlmostEqual(slow[1],8.2)

    def test_gates_and_released_update(self):
        c=config("baseline");book=(frozenset(),np.ones(N,dtype=bool),{0},set(),None,np.full(N,2))
        self.assertNotIn(Action("fit",0),feasible(book,2100,"tree_fit"))
        book=(book[0],book[1],book[2],{0},book[4],book[5])
        self.assertIn(Action("fit",0),feasible(book,2100,"tree_fit"))
        self.assertNotIn(Action("fit",0),feasible(book,2100,"tree"))
        self.assertNotIn(Action("redo",1),feasible(book,2100,"tree_fit"))
        active=Job(Action("fit",0),0,index=4)
        self.assertEqual({s for s,_ in pending_outcomes(active,c)},{"pass-","pass+"})
        self.assertEqual({s for s,_ in pending_outcomes(Job(active.action,0,index=1),c)},{"pass-","pass+","rejected"})

    def test_outer_rows_and_pairing(self):
        rows=rec("replicates.csv.gz");self.assertEqual(len(rows),12288)
        base=[r for r in rows if r["scenario"]=="baseline"]
        nom={p:{int(r["seed"]) for r in base if r["policy"]==p} for p in {r["policy"] for r in base}}
        self.assertEqual(len(next(iter(nom.values()))),N_BASE)
        self.assertTrue(all(v==next(iter(nom.values())) for v in nom.values()))
        for r in rows:
            self.assertLessEqual(float(r["mean_cost"]),2870.)
            self.assertLessEqual(int(r["success_rate"]),min(int(r["batch2_pass"]),int(r["confirm_read"]),int(r["opportunity"])))
            self.assertEqual(int(r["confirm_read"]),int(r["success_rate"])+int(r["wrong_release_rate"]))
            self.assertEqual(int(r["opportunity"]),int(r["success_rate"])+int(r["miss_rate"]))
            if r["policy"]=="tree_serial":self.assertEqual(int(r["parallel_submits"]),0)
        test=rec("risk_replicates.csv.gz");self.assertEqual(len(test),4*N_TEST)
        self.assertFalse({r["seed"] for r in test}&{r["seed"] for r in rows})
        self.assertEqual(len(rec("joint_sensitivity.csv")),24*2*4)

    def test_exact_replays_and_source_metrics(self):
        rows=rec("replicates.csv.gz")
        for index in range(0,len(rows),137):
            r=rows[index];actual,_=run(int(r["seed"]),r["scenario"],r["policy"])
            for key in ("selected","mean_cost","restricted_h","false_bias_flags","success_rate","miss_rate"):
                self.assertAlmostEqual(float(r[key]),actual[key])
        by_policy={r["policy"]:{int(u["seed"]):u for u in rows[:7*N_BASE] if u["policy"]==r["policy"]} for r in rows[:7]}
        fx=rec("paired_effects.csv")
        for m in ("success_rate","mean_cost","wrong_nomination"):
            row=next(r for r in fx if r["scenario"]=="baseline" and r["reference"]=="myopic" and r["policy"]=="tree" and r["metric"]==m)
            dif=[float(v[m])-float(by_policy["myopic"][s][m]) for s,v in by_policy["tree"].items()]
            np.testing.assert_allclose([np.mean(dif),np.mean(dif)-1.96*np.std(dif,ddof=1)/math.sqrt(len(dif))],
                                       [float(row["difference"]),float(row["ci_low"])])

    def test_calendar_and_eligibility_trace(self):
        design=json.loads((OUT/"design.json").read_text());r,ev=run(design["trace_seed"],"baseline","tree_fit",record=True)
        active={};eligible=set();locked=False
        for e in ev:
            tag=e["event"];a=(e["candidate"],e["action"]);res=e["resource"]
            if tag=="start":
                self.assertNotIn(res,active);active[res]=a
            if tag=="complete":self.assertEqual(active.pop(res),a)
            if tag=="initial_release" and a[1]=="screen" and e["detail"]=="+":eligible.add(a[0])
            if tag=="qc_released" and a[1]=="pellet" and e["detail"].startswith("+"):eligible.add(a[0])
            if tag=="qc_released":self.assertFalse(locked)
            if tag=="lock":
                self.assertFalse(locked);locked=True;self.assertIn(a[0],eligible)
            if tag=="submitted" and a[1]=="confirm":self.assertTrue(locked)
        self.assertFalse(active)
        stored=rec("events.csv")
        self.assertEqual([(str(v["time_h"]),v["event"],v["detail"]) for v in ev],
                         [(v["time_h"],v["event"],v["detail"]) for v in stored])

    def test_no_peek_accept_reject(self):
        ok=rec("fit_events.csv");fail=rec("rollback_events.csv")
        a=next(i for i,e in enumerate(ok) if e["event"]=="version_published")
        z=next(i for i,e in enumerate(fail) if e["event"]=="rollback")
        self.assertEqual(ok[:a],fail[:z])
        self.assertTrue(any(e["action"]=="fit" and e["event"]=="qc_released" and e["detail"].startswith("pass") for e in ok))
        self.assertFalse(any(e["action"]=="redo" and e["event"]=="submitted" for e in fail))

    def test_hidden_budget_clock_boundary(self):
        # Screening is unaffected by true acceptance/repair if no version was attempted.
        l,ea=run(874039,"baseline","myopic",record=True,overrides={"truth_accept":0.,"truth_repair":-.25})
        r,eb=run(874039,"baseline","myopic",record=True,overrides={"truth_accept":1.,"truth_repair":.95})
        self.assertEqual(l,r);self.assertEqual(ea,eb)
        none,ev=run(874039,"baseline","tree",record=True,overrides={"budget_diagnostic":0})
        self.assertFalse(any(e["event"]=="submitted" and e["action"]!="confirm" for e in ev))
        no_time,ev=run(874039,"baseline","tree",record=True,overrides={"freeze_h":.01})
        self.assertFalse(any(e["event"]=="submitted" and e["action"]!="confirm" for e in ev))


if __name__=="__main__":
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Integrity)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    (OUT/"checks.json").write_text(json.dumps(dict(passed=result.wasSuccessful(),test_count=result.testsRun,
           main_rows=12288,exact_replays=90,public_input_boundary=True),indent=2),encoding="utf-8",newline="\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
