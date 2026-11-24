"""Posterior interface for the seven composition-level candidates. No outer random tape here."""
import csv
import itertools
import math
from functools import lru_cache
from pathlib import Path

STATES=tuple(itertools.product(range(3),(0,1),(0,1)))  # family, sample/contact penalty, local potential error
ACTIONS=("xrd","md","eis","local","contact","repeat","dft","confirm","redo")
FAMILIES=("low","mid","high")

def load_priors(source):
    with Path(source).open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==21 and all(r["synthetic_only"].strip().lower()=="true" for r in rows)
    priors=[]
    for i in range(7):
        sub={r["structure_state"]:float(r["prior_probability"]) for r in rows if abs(float(r["x"])-i/10)<1e-7}
        vec=tuple(sub[k] for k in FAMILIES)
        assert all(v>=0 for v in vec) and abs(sum(vec)-1)<1e-6
        priors.append(vec)
    return priors

class Beliefs:
    def __init__(self,site,project,priors):
        self.site=site;self.priors=priors;self.project=project
        self.good=tuple(site["intrinsic"][f]-c*site["contact_loss"]>=project["macro_lower_mScm"] for f,c,b in STATES)
        pb=site["prior_bias"];pc=site["prior_contact"]
        joint=site.get("bias_contact_joint",pc*pb)
        assert max(0,pc+pb-1)<=joint<=min(pc,pb)
        cp={(1,1):joint,(0,1):pb-joint,(1,0):pc-joint,(0,0):1-pb-pc+joint}
        self.prior=[tuple(vec[f]*cp[c,b] for f,c,b in STATES) for vec in priors]
        self.probs={(op,v):tuple(self.likelihood(k,op,v) for k in range(12)) for op in ACTIONS for v in (0,1)}
    def likelihood(self,k,op,v=0,gain=None):
        f,c,b=STATES[k];g=self.good[k]
        if op in ("md","redo"):
            # Mismatch is a false high signal for low intrinsic transport, a false low signal for high.
            positive=self.site["intrinsic"][f]>=self.project["macro_lower_mScm"]
            baseline=.45 if b else .88
            if v and b:
                baseline+= (self.site["fit_gain"] if gain is None else gain)*(.88-.45)
            pr=baseline if positive else 1-baseline
        elif op=="xrd":pr=(.20,.63,.83)[f]
        elif op=="local":pr=(.08,.52,.92)[f]
        elif op=="eis":pr=.86 if g else .17
        elif op=="repeat":pr=.83 if g else .16
        elif op=="contact":pr=.86 if c else .17
        elif op=="dft":pr=.89 if b else .09
        elif op=="confirm":pr=self.site["confirm_sens"] if g else self.site["confirm_fpr"]
        else:raise KeyError(op)
        if op!="confirm":pr=.5+(pr-.5)*self.site["quality_scale"]
        if op in ("local","xrd"):pr=.5+(pr-.5)*self.site.get("struct_quality",1.)
        return min(.995,max(.005,pr))
    @lru_cache(maxsize=80000)
    def stats(self,i,evidence):
        w=list(self.prior[i])
        for op,y,v in evidence:
            like=self.probs[op,v]
            for k in range(12):w[k]*=like[k] if y else 1-like[k]
        z=sum(w);w=[a/z for a in w]
        g=sum(a for a,good in zip(w,self.good) if good);b=sum(a for a,s in zip(w,STATES) if s[2])
        return tuple(w),g,b
    def add(self,ev,op,y,v):
        # Updated MD replaces prior version on the same job rather than double-counting it.
        if op=="redo":ev=tuple(e for e in ev if e[0] not in ("md","redo"))
        return tuple(sorted(ev+((op,int(y),v if op in ("md","redo") else 0),)))
    @lru_cache(maxsize=120000)
    def step(self,i,ev,op,v,diagnose):
        weights,g,b=self.stats(i,ev)
        q=sum(a*l for a,l in zip(weights,self.probs[op,v]))
        outcomes=tuple((self.add(ev,op,y,v),q if y else 1-q) for y in (0,1))
        r=min(g,1-g)+(min(b,1-b) if diagnose else 0)
        remaining=0.
        for e,p in outcomes:
            _,gy,by=self.stats(i,e)
            remaining+=p*(min(gy,1-gy)+(min(by,1-by) if diagnose else 0))
        # An independent wet result changes the feasible terminal decision from withhold to verified advance.
        if op=="confirm":
            val=g*self.site["confirm_sens"]-(1-g)*self.site["confirm_fpr"]
        else:val=max(0,r-remaining)
        return val,outcomes,r
