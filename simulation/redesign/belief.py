"""Factorized joint model. All likelihoods refer to synthetic, binary readouts."""
from functools import lru_cache
import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT = json.loads((HERE / "project.json").read_text(encoding="utf-8-sig"))
LAB = json.loads((HERE / "lab.json").read_text(encoding="utf-8-sig"))
N = len(PROJECT["compositions"])
FAM, CONTACT, BIAS, BATCH1 = np.array([(f,c,b,l) for f in range(3) for c in range(2)
                                      for b in range(2) for l in range(2)]).T
# F and CONTACT are persistent formulation/SOP regimes. BATCH1 is the realized
# screening powder conditional on its formulation; multiple aliquots share it.
DOMAINS = PROJECT["local_domains"]
assert len(DOMAINS)==N
# Proxy latent macro threshold 5, values in scenario mS/cm. Do not fit Mo Table S1.
GOOD = np.array([3.9,5.4,7.1])[FAM] - 1.6*CONTACT >= 5.
PRIOR_PATH = HERE.parents[1] / "p9" / "ranking" / "outputs" / "des_structure_prior.csv"
with PRIOR_PATH.open(encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle))
assert len(rows) == 21 and all(row["synthetic_only"].lower() == "true" for row in rows)
PRIORS = np.zeros((N,3))
for row in rows:
    PRIORS[round(float(row["x"])*10), ["low","mid","high"].index(row["structure_state"])] = float(row["prior_probability"])
assert np.allclose(PRIORS.sum(axis=1), 1)

@dataclass(frozen=True)
class Action:
    kind: str
    i: int


def initial(conf):
    h = np.array([1.-conf["p_global_risk"], conf["p_global_risk"]])
    p = np.empty((2,N,len(FAM)))
    pb = np.where(GOOD,conf["batch_pass_if_target"],conf["batch_pass_if_nontarget"])
    batch_weight = np.where(BATCH1,pb,1.-pb)
    for g, rate in enumerate(conf["p_local_bias_by_global"]):
        p[g] = (PRIORS[:,FAM] * np.where(CONTACT,conf["p_contact"],1-conf["p_contact"])
                * np.where(BIAS,rate,1-rate)*batch_weight)
    return Belief(h,p)


@lru_cache(maxsize=80)
def positive(kind,repair=.75):
    if kind in ("screen","pellet"):
        # Two different pellet tests from the same powder; common contact and intrinsic state.
        return np.where(BATCH1, .87 if kind=="screen" else .92, .13 if kind=="screen" else .10)
    if kind=="structure": return np.array([.10,.52,.90])[FAM]
    if kind=="contact": return np.where(CONTACT,.87,.13)
    if kind=="dft": return np.where(BIAS,.91,.09)
    if kind in ("old","md","redo","fit"):
        clean = np.array([.10,.55,.92])[FAM]
        biased = np.array([.72,.79,.29])[FAM]
        if kind in ("redo","fit"):
            biased = np.clip(biased+repair*(clean-biased),.01,.99)
        return np.where(BIAS,biased,clean)
    raise ValueError(kind)


def outcomes(a,conf):
    p = positive(a.kind,conf["fit_repair"])
    if a.kind=="fit":
        accept = conf["acceptance"]
        return (("rejected",np.zeros_like(p)+1-accept),("pass-",accept*(1-p)),("pass+",accept*p))
    return (("-",1-p),("+",p))


@dataclass
class Belief:
    h: np.ndarray     # P(G | all releases)
    p: np.ndarray     # P(theta_i | G, all releases), conditionally independent across i

    def probs(self):
        return self.h @ (self.p @ GOOD)

    def update(self,a,likelihood):
        mass_g = self.p[:,a.i] @ likelihood
        total = self.h @ mass_g
        conditional = self.p.copy()
        conditional[:,a.i] *= likelihood
        conditional[:,a.i] /= mass_g[:,None]
        return Belief(self.h*mass_g/total,conditional),float(total)

    def utility(self, eligible, floor):
        # Reward 1 for a sound nomination, loss floor/(1-floor) for an unsound one; abstain=0.
        score = np.where(eligible,(self.probs()-floor)/(1-floor),0.)
        return max(0.,float(score.max()))

    def expected_value(self,actions,eligible,conf):
        """Exact one-step terminal value for each action; vectorized over the action menu."""
        if not actions: return np.empty(0)
        k = len(actions)
        ids = np.array([a.i for a in actions])
        like = np.array([positive(a.kind,conf["fit_repair"]) for a in actions])
        local = self.p[:,ids]
        yes = (local*like).sum(axis=2)
        yes_good = (local*(like*GOOD)).sum(axis=2)
        pgood_g = self.p @ GOOD
        base = self.h @ pgood_g
        pyes = self.h @ yes
        joint = (yes*self.h[:,None]).T @ pgood_g
        joint[np.arange(k),ids] = self.h @ yes_good
        epos = np.broadcast_to(eligible,(k,N)).copy()
        for j,a in enumerate(actions):
            if a.kind=="pellet": epos[j,a.i]=True
        floor = conf["posterior_floor"]
        pos = np.maximum(0,np.where(epos,joint-floor*pyes[:,None],0).max(axis=1))
        neg = np.maximum(0,np.where(eligible,base-joint-floor*(1-pyes[:,None]),0).max(axis=1))
        result=(pos+neg)/(1-floor)
        for j,a in enumerate(actions):
            if a.kind=="fit":
                result[j] = (conf["acceptance"]*result[j]
                             +(1-conf["acceptance"])*self.utility(eligible,floor))
        return result
