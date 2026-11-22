"""P8 evidence-release DES. Python >=3.10; standard library only."""
from __future__ import annotations
import csv
import heapq
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "configs/assumptions.yaml").read_text(encoding="utf-8"))
DEFAULT = {k:v["value"] for k,v in SPEC["parameters"].items()}
RULES = json.loads((ROOT / "configs/decision_policies.yaml").read_text(encoding="utf-8"))
TH = RULES["thresholds"]
RES = {"prep":("staff",),"synth":("furnace",),"xrd":("xrd","staff"),
       "press":("staff",),"eis":("eis",),"short":("gpu",),"long":("gpu",),
       "refine":("xrd","staff"),"probe":("dft",),"labels":("dft",),"train":("gpu",),
       "validate":("gpu",),"outage":("xrd",)}
STAGE = ["prep","synth","xrd","xreview","press","eis","ereview","short","long","refine"]
BASE_POLICIES = ["B0","B1","B2","B3","B4"]


def gaussian_duration(rng, median, cv):
    if cv == 0:
        return median
    return median * math.exp(rng.gauss(0, math.sqrt(math.log1p(cv*cv))))


class World:
    """Draw every branch before any policy runs; neither truth nor tape reaches priority rules."""
    def __init__(self, cfg, seed):
        rng = random.Random(seed)
        self.candidates = []
        pp = cfg["phase_prior"]
        for i in range(cfg["n_candidates"]):
            p = rng.random()
            phase = 0 if p < pp[0] else (1 if p < pp[0]+pp[1] else 2)
            truth = rng.random() < cfg["success_by_phase"][phase]
            draws = [rng.random() for _ in range(19)]
            dates = {}
            for confirm in (0,1):
                for op in STAGE:
                    dates[confirm,op] = gaussian_duration(rng,*cfg["durations"][op])
            self.candidates.append((phase,truth,draws,dates))
        self.fits = [(rng.random(),rng.random()) for _ in range(3)]


def odds(q):
    return q / max(1-q,1e-12)


@dataclass
class Candidate:
    id: int
    arrival: float
    family: int
    odds: float
    visible: dict = field(default_factory=dict)
    stopped: bool = False
    frozen: bool = False
    freeze_allowed: bool = True
    decision_locked: bool = False
    confirmed: bool = False
    requested: set = field(default_factory=set)
    long_version: int = -1
    long_lr: float = 1
    long_runs: int = 0
    @property
    def p(self):
        return self.odds / (1 + self.odds)


class DES:
    def __init__(self,cfg,world,policy,trace=False):
        self.c = cfg
        self.world = world
        self.policy = policy
        self.base = policy[:2]
        self.dynamic = self.base in ("B2","B3","B4")
        self.queue_aware = self.base in ("B3","B4") and policy != "B3-no-queue"
        self.structure = self.base in ("B3","B4") and policy != "B3-no-structure"
        self.adapt = self.base == "B4"
        self.all_confirm = cfg.get("all_confirm",False)
        if self.all_confirm:
            self.dynamic = self.queue_aware = self.structure = self.adapt = False
        self.trace = [] if trace else None
        self.now = 0.
        self.serial = 0
        self.events = []
        self.waiting = []
        self.free = dict(cfg["capacity"])
        self.busy = Counter()
        self.count = Counter()
        self.version = [0]*3
        self.gain = [0.]*3
        self.tickets = defaultdict(list)
        self.attempted = set()
        self.probes_booked = 0
        self.first = None
        self.true_first = None
        self.accept_times = []
        self.candidates = []
        self.p0 = sum(f*q for f,q in zip(cfg["phase_prior"],cfg["success_by_phase"]))
        for i in range(cfg["n_candidates"]):
            q = Candidate(i, i*cfg["arrival_gap"], i%3, odds(self.p0))
            self.candidates.append(q)
            self.event(q.arrival,"arrive",i)
            self.event(q.arrival+cfg["freeze"],"freeze",i)
        if cfg["outage_hours"]:
            self.event(24,"outage",0)

    def event(self,t,kind,data):
        self.serial += 1
        heapq.heappush(self.events,(t,self.serial,kind,data))

    def log(self,kind,cid,op="",batch=0,version="",tid="",details=""):
        if self.trace is not None:
            self.trace.append({"time_h":round(self.now,6),"event":kind,"candidate_id":cid,
              "sample_id":f"C{cid:02d}-{'IND' if batch else 'SCREEN'}" if cid>=0 else "",
              "structure_family_id":f"F{cid%3}" if cid>=0 else "","task_id":tid,
              "operation":op,"potential_version":version,"evidence_id":f"E{tid}" if kind=="qc_released" else "",
              "qc_released_at":round(self.now,6) if kind=="qc_released" else "",
              "resources":"+".join(RES.get(op,())),"detail":details})

    def submit(self,cid,op,b=0,version=0,extra=0,retry=0):
        self.serial+=1
        job=(self.serial,cid,op,b,version,extra,retry,self.now)
        self.waiting.append(job)
        self.log("queued",cid,op,b,version,self.serial)

    def request(self,q,op,b=0,version=0):
        k=(op,b,version)
        if k not in q.requested:
            q.requested.add(k)
            self.submit(q.id,op,b,version)

    def duration(self,job):
        _,i,op,b,v,n,_,_=job
        if op in STAGE:
            return self.world.candidates[i][3][b,op]
        d=self.c["durations"]
        f=self.c["fit"]
        if op in ("probe","labels"):
            return n*d["dft_frame"][0]
        if op=="train":
            return d["train"][0]+(n-1)*f["additional_h_per_ticket"]
        if op=="validate":
            return d["validate"][0]
        return self.c["outage_hours"]

    def priority(self,j):
        tid,i,op,b,v,n,retry,submitted=j
        if op=="outage":
            return 1000.
        if not self.dynamic:
            return -tid*1e-7
        q=self.candidates[i]
        # All policies use the same nominal operation costs. No scheduler can read a queued job's sampled duration.
        unit_cost={"synth":12,"press":4,"long":10,"short":2,"probe":2,"labels":6,"train":6,"validate":2}
        score=(0.12+q.p+0.45*b)/unit_cost.get(op,2)
        if self.queue_aware:
            remaining=q.arrival+self.c["freeze"]-self.now
            wait=self.now-submitted
            score+=0.015*wait+0.45/(1+max(0.,remaining)/12)
            if op in ("train","validate"):
                score+=0.13
        return score-tid*1e-9

    def dispatch(self):
        if not self.waiting:
            return
        # Each job atomically obtains all its slots. No partial reservations/deadlock.
        self.waiting.sort(key=self.priority,reverse=True)
        keep=[]
        for j in self.waiting:
            tid,i,op,b,v,n,retry,tq=j
            r=RES[op]
            if any(self.free[k]<=0 for k in r):
                keep.append(j)
                continue
            length=self.duration(j)
            for k in r:
                self.free[k]-=1
                if op!="outage":
                    self.busy[k]+=min(length,max(0.,self.c["horizon"]-self.now))
            if op=="synth":
                self.count["powders"]+=1
            if op=="press":
                self.count["pellets"]+=1
            if op=="eis":
                self.count["eis_tests"]+=1
            if op in ("probe","labels"):
                self.count["dft_frames"]+=n
            if op=="long":
                self.candidates[i].long_runs+=1
                self.count["recomputed"]+=int(self.candidates[i].long_runs>1)
            self.log("started",i,op,b,v,tid,f"queue_h={self.now-tq:.4f}")
            self.event(self.now+length,"done",j)
        self.waiting=keep

    def cancel(self,q,only_old=False):
        keep=[]
        for j in self.waiting:
            tid,i,op,b,v,n,retry,tq=j
            obsolete=op=="long" and v<self.version[q.family]
            optional=op in ("press","eis","long","refine","probe")
            if i==q.id and b==0 and (obsolete if only_old else optional):
                self.count["cancelled"]+=1
                self.log("cancelled",i,op,b,v,tid)
            else:
                keep.append(j)
        self.waiting=keep

    def stop(self,q):
        q.stopped=True
        if self.dynamic:
            self.cancel(q)
        self.log("eliminated",q.id)

    def observe(self,q,key,positive,sens,fpr,replace=False):
        lr=sens/fpr if positive else (1-sens)/(1-fpr)
        if replace:
            q.odds/=q.long_lr
            q.long_lr=lr
        q.odds*=lr
        q.visible[key]=positive

    def phase_evidence(self,q,obs):
        weights=[1-self.c["phase_error"] if i==obs else self.c["phase_error"]/2 for i in range(3)]
        num=sum(p*s*w for p,s,w in zip(self.c["phase_prior"],self.c["success_by_phase"],weights))
        den=sum(p*(1-s)*w for p,s,w in zip(self.c["phase_prior"],self.c["success_by_phase"],weights))
        q.odds*=num/den/odds(self.p0)
        q.visible["phase"]=obs

    def decision(self,q):
        if q.stopped or q.decision_locked:
            return
        v=q.visible
        if "phase" not in v:
            return
        gate=self.base!="B0" and not self.all_confirm
        if gate and v["phase"]==0 and (not self.dynamic or q.p<0.55):
            self.stop(q)
            return
        if self.dynamic and v["phase"]==1 and "short" in v and self.structure and "refine" not in v and not q.frozen:
            self.request(q,"refine")
            return
        if self.dynamic and "short" in v and q.p<TH["drop_p"] and "eis" not in v and not q.frozen:
            self.stop(q)
            return
        if self.dynamic and "short" in v and not q.frozen:
            version=self.version[q.family]
            self.request(q,"long",version=version)
            # Prioritize a useful wet job when a predicted GPU backlog would miss the decision window.
            nominal_backlog=sum(j[2]=="long" for j in self.waiting)*10/self.c["capacity"]["gpu"]
            if q.p>=TH["eis_p"] and (q.p>=0.48 or "long" in v or (self.queue_aware and self.now+nominal_backlog+10>q.arrival+self.c["freeze"]-12)):
                self.request(q,"press")
            if self.adapt and v.get("alarm") and q.family not in self.attempted and "probed" not in v and self.probes_booked<max(3,len(self.candidates)//3):
                # Negative probes remain in the analysis: they do not trigger adaptation.
                eligible=q.p>=TH["label_p"] and q.p<=0.87
                if self.policy=="B4-random-label":
                    eligible=self.world.candidates[q.id][2][16]<0.60
                if eligible:
                    v["probed"]=True
                    self.probes_booked+=1
                    self.submit(q.id,"probe",extra=self.c["fit"]["probe_frames"])
        if not self.dynamic or (q.frozen and q.freeze_allowed):
            self.request(q,"press")
        if "eis" in v and ("long" in v or self.all_confirm):
            q.decision_locked=True
            # Independent work is allowed after freeze only under the previously committed contingency.
            admit=self.all_confirm or (v["eis"] and q.freeze_allowed and (not self.dynamic or q.p>=TH["confirm_p"]))
            if admit:
                self.request(q,"prep",1)
            else:
                self.stop(q)

    def completed(self,j):
        tid,i,op,b,v,n,retry,tq=j
        for k in RES[op]:
            self.free[k]+=1
        self.log("completed_unreviewed",i,op,b,v,tid)
        if op=="outage":
            return
        phase,truth,u,dates=self.world.candidates[i]
        if op in ("xrd","eis") and not retry and u[9+2*b+(op=="eis")]<self.c["retry_probability"]:
            self.count["retries"]+=1
            self.log("qc_failed_retry",i,op,b,v,tid)
            self.submit(i,op,b,v,n,1)
            return
        wait=dates[b,"xreview" if op in ("xrd","refine") else "ereview"] if op in ("xrd","refine","eis") else 0
        self.event(self.now+wait,"release",j)

    def train_batch(self,f):
        if f in self.attempted or not self.tickets[f]:
            return
        self.attempted.add(f)
        ids=self.tickets[f]
        self.submit(ids[0],"train",extra=len(ids))
        self.log("batch_locked",ids[0],"train",details=f"family={f};members={ids}")

    def release(self,j):
        tid,i,op,b,v,n,retry,tq=j
        q=self.candidates[i]
        pp=self.c["phys"]
        fit=self.c["fit"]
        phase,truth,u,dates=self.world.candidates[i]
        self.log("qc_released",i,op,b,v,tid)
        if op=="prep":
            self.request(q,"synth",b)
        elif op=="synth":
            self.request(q,"xrd",b)
        elif op=="xrd":
            off=13 if b else 0
            observed=phase if u[off]>=self.c["phase_error"] else (phase+1+int(u[off+1]>.5))%3
            if b:
                # Independent repeat must include its own phase measurement.
                if observed!=0 or self.all_confirm:
                    q.visible["confirm_phase_ok"]=observed!=0
                    self.request(q,"press",1)
            else:
                self.phase_evidence(q,observed)
                self.log("observation_applied",i,op,b,v,tid,f"phase_class={observed};posterior={q.p:.5f}")
                if self.now<=q.arrival+self.c["freeze"]:
                    self.count["timely_phase"]+=1
        elif op=="press":
            if b or not q.stopped:
                self.request(q,"eis",b)
        elif op=="eis":
            if b:
                decision=bool(q.visible.get("confirm_phase_ok")) and u[8]<(pp["confirm_sens"] if truth else pp["confirm_fpr"])
                q.confirmed=decision
                if decision:
                    self.accept_times.append(self.now)
                    if self.first is None:
                        self.first=self.now
                    if truth and self.true_first is None:
                        self.true_first=self.now
                self.log("independent_decision",i,op,b,v,tid,str(decision))
            else:
                self.observe(q,"eis",u[7]<(pp["primary_sens"] if truth else pp["primary_fpr"]),pp["primary_sens"],pp["primary_fpr"])
                if self.now<=q.arrival+self.c["freeze"]:
                    self.count["timely_eis"]+=1
        elif op=="short":
            pos=truth if u[3]<pp["short_accuracy"] else not truth
            self.observe(q,"short",pos,pp["short_accuracy"],1-pp["short_accuracy"])
            biased=u[4]<pp["biased_share"]
            q.visible["alarm"]=u[5]<(pp["alarm_sens"] if biased else pp["alarm_fpr"])
            if not self.dynamic:
                self.request(q,"long")
        elif op=="long":
            if self.adapt and v<self.version[q.family]:
                self.count["obsolete_outputs"]+=1
                if not q.stopped and not q.frozen and not q.decision_locked:
                    self.request(q,"long",version=self.version[q.family])
                # Retain previously locked version for a candidate whose decision is frozen.
                if not q.frozen:
                    return
            biased=u[4]<pp["biased_share"]
            acc=pp["biased_long_accuracy"] if biased else pp["long_accuracy"]
            if biased and v:
                acc+=self.gain[q.family]*(pp["long_accuracy"]-acc)
            pos=truth if u[6]<acc else not truth
            estimated=pp["long_accuracy"]*(1-pp["biased_share"])+pp["biased_long_accuracy"]*pp["biased_share"]
            self.observe(q,"long",pos,estimated,1-estimated,replace=True)
            q.long_version=v
        elif op=="refine":
            # Additional occupancy/structure result is a noisy proxy for compatibility, never a force label.
            positive=truth if u[17]<pp["refine_accuracy"] else not truth
            self.observe(q,"refine",positive,pp["refine_accuracy"],1-pp["refine_accuracy"])
        elif op=="probe":
            biased=u[4]<pp["biased_share"]
            if u[15]<(pp["probe_sens"] if biased else pp["probe_fpr"]) and not q.stopped and not q.frozen and q.family not in self.attempted:
                self.submit(i,"labels",extra=fit["train_frames"]+fit["holdout_frames"])
        elif op=="labels":
            f=q.family
            if f not in self.attempted:
                self.tickets[f].append(i)
                if self.policy=="B4-immediate" or len(self.tickets[f])>=fit["batch"]:
                    self.train_batch(f)
                else:
                    self.event(self.now+fit["wait"],"flush",f)
            else:
                self.count["unused_label_batches"]+=1
        elif op=="train":
            self.count["fit_attempts"]+=1
            self.submit(i,"validate")
        elif op=="validate":
            family=q.family
            a,g=self.world.fits[family]
            if a>=fit["accept"]:
                self.count["rollbacks"]+=1
                self.log("model_rollback",i,op,version=0,tid=tid)
                return
            self.count["releases"]+=1
            self.version[family]=1
            self.gain[family]=fit["gain_lo"]+(fit["gain_hi"]-fit["gain_lo"])*g
            useful=0
            self.log("model_published",i,op,version=1,tid=tid,details=f"family={family}")
            for other in self.candidates:
                if other.family!=family or other.stopped or other.frozen or other.decision_locked:
                    continue
                if ("long",0,0) in other.requested:
                    self.cancel(other,only_old=True)
                    if other.long_version==0 and "long" in other.visible:
                        other.visible.pop("long")
                        other.odds/=other.long_lr
                        other.long_lr=1
                        other.long_version=-1
                    self.request(other,"long",version=1)
                if other.arrival+self.c["freeze"]>self.now:
                    useful+=1
            self.count["expired_releases"]+=int(useful==0)
        if not b and op in ("xrd","eis","short","long","refine"):
            if op in q.visible:
                self.log("observation_applied",i,op,b,v,tid,f"positive={q.visible[op]};posterior={q.p:.5f}")
            self.decision(q)

    def run(self):
        while self.events:
            t=self.events[0][0]
            if t>self.c["horizon"]:
                break
            self.now=t
            while self.events and self.events[0][0]==t:
                _,_,event,d=heapq.heappop(self.events)
                if event=="arrive":
                    q=self.candidates[d]
                    phase,truth,u,_=self.world.candidates[d]
                    acc=self.c["phys"]["prior_accuracy"]
                    self.observe(q,"prior",truth if u[2]<acc else not truth,acc,1-acc)
                    self.log("submitted",d)
                    self.request(q,"prep")
                    self.request(q,"short")
                elif event=="done":
                    self.completed(d)
                elif event=="release":
                    self.release(d)
                elif event=="flush":
                    self.train_batch(d)
                elif event=="outage":
                    self.submit(0,"outage")
                else:
                    q=self.candidates[d]
                    q.frozen=True
                    if self.dynamic:
                        q.freeze_allowed=not q.stopped and q.p>=TH["freeze_p"]
                        if q.freeze_allowed and not q.decision_locked:
                            self.request(q,"long",version=self.version[q.family])
                        elif not q.decision_locked:
                            self.stop(q)
                    self.log("window_frozen",d,details=f"allow={q.freeze_allowed}")
                    self.decision(q)
            self.dispatch()
        assert all(x>=0 for x in self.free.values())
        n=len(self.candidates)
        accepted=sum(q.confirmed for q in self.candidates)
        truths=sum(w[1] for w in self.world.candidates)
        tp=sum(q.confirmed and self.world.candidates[q.id][1] for q in self.candidates)
        fn_stop=sum(q.stopped and self.world.candidates[q.id][1] for q in self.candidates)
        span=self.c["horizon"] if self.events else max(self.now,1)
        result={"n":n,"first_h":self.first,"true_first_h":self.true_first,
                "restricted_h":self.first if self.first is not None else self.c["horizon"],
                "true_restricted_h":self.true_first if self.true_first is not None else self.c["horizon"],
                "confirmed":accepted,"tp":tp,"positive":truths,"negative":n-truths,"fp":accepted-tp,
                "wrong_drop":fn_stop,"unconfirmed_good":truths-tp,"span_h":span}
        for key in ("powders","pellets","eis_tests","dft_frames","timely_phase","timely_eis","cancelled","recomputed",
                    "obsolete_outputs","unused_label_batches","expired_releases","retries","fit_attempts","releases","rollbacks"):
            result[key]=self.count[key]
        for k in self.free:
            result["hours_"+k]=self.busy[k]
            result["util_"+k]=self.busy[k]/(span*self.c["capacity"][k])
        for name in ("cost_index","cost_cny"):
            price=self.c[name]
            result[name]=sum(price[k]*self.busy[k] for k in self.free)+price["powder"]*self.count["powders"]
        result["decision_loss_cny"]=result["cost_cny"]+result["wrong_drop"]*self.c["opportunity_loss"]
        return result
