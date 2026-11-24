"""Outer policy evaluation DES. Hidden World is confined to the simulator, never passed to policies."""
import hashlib
import heapq
import math
import random
from collections import Counter
from dataclasses import dataclass,field
from belief import STATES
from planning import View,observed,disputed,finish,score_actions

def rng(seed,*key):
    token="|".join(map(str,(seed,)+key)).encode()
    return random.Random(int.from_bytes(hashlib.blake2b(token,digest_size=8).digest(),"big"))

class World:
    def __init__(self,seed,belief):
        self.seed=seed;self.b=belief
        self.hidden=[rng(seed,i,"latent").choices(range(12),weights=w)[0] for i,w in enumerate(belief.prior)]
    def duration(self,i,op,k,median,cv,attempt=0):
        # Per-candidate/action/stage random stream is unchanged by alternate schedules.
        resource=self.b.site["stages"][op][k][0]
        law=self.b.site["stage_laws"][resource]
        r=rng(self.seed,i,op,k,attempt,"service")
        if law=="constant":return median
        if law=="triangular":return median*r.triangular(.75,1.25,1.)
        cv=float(law.partition(":")[2])
        return median*math.exp(r.normalvariate(0,math.sqrt(math.log1p(cv*cv))))
    def signal(self,i,op,v):
        if op=="fit":return rng(self.seed,"family","accept").random()<self.b.site["fit_accept"]
        g=self.b.site.get("actual_fit_gain",self.b.site["fit_gain"])*(.7+.6*rng(self.seed,"family","gain").random())
        p=self.b.likelihood(self.hidden[i],op,v,g)
        return rng(self.seed,i,op if op!="redo" else "md","outcome").random()<p

@dataclass
class Sample:
    i:int;arrival:float
    ready:bool=False;closed:bool=False;frozen:bool=False;admitted:bool=False
    ev:tuple=();stock:int=4;performed:set=field(default_factory=set)
    pending:dict=field(default_factory=dict); stopped:bool=False; deferred:bool=False
    alarm:bool=False;label_useful:bool=False; dft_attribution:bool=False; conf_time:float|None=None
@dataclass
class Job:
    id:int;i:int;op:str;v:int;stage:int=0;queued:float=0;started:float=0;active:bool=False;cancelled:bool=False
    first:bool=True;wait:float=0;cost:float=0;attempt:int=0

class Simulator:
    def __init__(self,belief,world,policy,admit=None,trace=False):
        self.b=belief;self.s=belief.site;self.p=belief.project
        self.world=world;self.policy=policy
        self.admit=self.p["admit_floor"] if admit is None else admit
        self.history=[] if trace else None;self.choice=[] if trace else None
        self.now=0.;self.serial=0;self.jid=0;self.calendar=[];self.queue=[];self.active={};self.jobs={}
        self.samples=[Sample(i,i*self.p["period_h"],stock=self.p["powder_aliquots"]) for i in range(7)]
        self.maxslots=self.s["capacity"];self.busy=Counter();self.used=Counter();self.qhours=Counter()
        self.bill=0.;self.encumbered=0.;self.version=0;self.attempted=False;self.first=None;self.metrics=Counter()
        self.fit_i=None; self.lastscore={};self.decision_reason="";self.dirty=set();self.denied=set()
        for day in range(0,int(self.p["horizon_h"])+1,24):
            if day:self.event(day,"shift_open",0)
        for q in self.samples:
            self.event(q.arrival,"entry",q.i);self.event(q.arrival+self.p["freeze_h"],"freeze",q.i)
    def event(self,t,k,v):
        self.serial+=1;heapq.heappush(self.calendar,(t,self.serial,k,v))
    def log(self,k,q,job=None,detail=""):
        if self.history is not None:
            self.history.append(dict(t=round(self.now,4),event=k,i=q.i,x=q.i/10,
              sample_id=f"C{q.i}-"+("B2" if job and job.op=="confirm" else "B1"),
              task=job.id if job else "",action=job.op if job else "",stage=job.stage if job else "",
              resource=self.route(job)[job.stage][0] if job else "",version=(self.version if k=="model_published" else job.v if job else self.version),
              remaining=round(self.p["budget_cny"]-self.encumbered,1),detail=str(detail)))
    def route(self,j):return self.s["stages"][j.op]
    def submit(self,q,op):
        price=self.s["costs"][op]
        if price+self.encumbered>self.p["budget_cny"]+1e-8:
            self.denied.add((q.i,op));return
        if op=="fit":
            if self.attempted:return
            self.attempted=True;self.fit_i=q.i
        if op in ("eis","contact"):
            if q.stock<=0:return
            q.stock-=1
        self.jid+=1
        j=Job(self.jid,q.i,op,self.version if op in ("md","redo","fit") else 0,queued=self.now)
        self.encumbered+=price;self.jobs[j.id]=j;q.pending[op]=j.id
        self.queue.append(j);self.log("submitted",q,j);self.metrics["n_"+op]+=1
        if q.deferred and op!="powder":self.metrics["resumed"]+=1;q.deferred=False;self.log("resumed",q,j)
        if op=="md" and observed(q.ev,"xrd") is None:self.metrics["speculative_md"]+=1
    def cancel(self,q,op,reason):
        if op not in q.pending:return
        j=self.jobs[q.pending[op]]
        if j.active or not j.first:return
        j.cancelled=True;self.queue=[x for x in self.queue if x.id!=j.id]
        self.encumbered-=self.s["costs"][op]
        if op in ("eis","contact"):q.stock+=1
        del q.pending[op];self.metrics["cancelled"]+=1
        self.log("cancelled",q,j,reason)
    def public_slots(self):
        # Project queued pipelines on the public service model. Outer sampled finish events cannot enter.
        cap={k:[self.now]*n for k,n in self.maxslots.items()}
        future=[]
        for j in self.active.values():
            op,jstage=j.op,j.stage
            r,h=self.route(j)[jstage]
            idx=cap[r].index(min(cap[r]))
            end=max(self.now+.05,j.started+h)
            cap[r][idx]=end
            future.append((end,j.id,j,self.route(j)[jstage+1:]))
        for j in self.queue:
            future.append((self.now,j.id,j,self.route(j)[j.stage:]))
        ends={}
        for ready,jid,j,tail in sorted(future,key=lambda v:(v[0],v[1])):
            for r,h in tail:
                idx=min(range(len(cap[r])),key=cap[r].__getitem__)
                ready=max(ready,cap[r][idx])+h;cap[r][idx]=ready
            ends[jid]=ready
        return cap,ends
    def offer(self,q):
        if not q.ready or q.closed or q.frozen or self.now>=q.arrival+self.p["freeze_h"] or "confirm" in q.pending:return
        if len(q.pending)>=2:return
        # Require a paid and genealogically independent confirmation batch for every release decision.
        slots,ends=self.public_slots()
        peers=[p for p in self.samples if p.i!=q.i and p.ready and not p.closed and not p.frozen]
        peer_ops=[]
        for other in peers:
            if "confirm" in other.pending:continue
            e=observed(other.ev,"eis")
            if e is False or "eis" in other.pending:continue
            action="confirm" if e is True else "eis"
            deadline=self.p["horizon_h"] if action=="confirm" else other.arrival+self.p["freeze_h"]
            value=self.b.step(other.i,other.ev,action,self.version,disputed(other.ev))[0]
            peer_ops.append((deadline,action,value))
        peer,peer_action,peer_value=min(peer_ops,default=(self.p["horizon_h"],"eis",0.))
        view=View(q.i,q.ev,frozenset(q.performed),tuple((a,ends.get(j,self.now)) for a,j in q.pending.items()),
          self.now,q.arrival+self.p["freeze_h"],self.p["budget_cny"]-self.encumbered,q.stock,self.version,self.attempted,False,
          len(peers),slots,peer_action,peer,peer_value,tuple(self.active),tuple(j.id for j in self.queue))
        op,records=score_actions(view,self.policy,self.b,self.s,self.p,self.admit,self.history is not None)
        if self.choice is not None and records:
            _,g,b=self.b.stats(q.i,q.ev)
            for act,sc,when,why in records:
                self.choice.append(dict(t=round(self.now,4),i=q.i,x=q.i/10,posterior_good=round(g,5),posterior_bias=round(b,5),
                 published_count=len(q.ev),action=act,selected=int(act==op or act=="wait" and op is None),
                 conditional_value=round(sc,6),expected_release=round(when,3) if when is not None else "",
                 reason=why if act==op else ("比较中未选 / "+why)))
        if op:
            self.lastscore[q.i]=max((a[1] for a in records if a[0]==op),default=0.)
            self.submit(q,op)
        elif q.pending and not q.deferred:
            q.deferred=True;self.metrics["deferred"]+=1;self.log("deferred",q,detail="等待在制或资源")
    def dispatch(self):
        # Only premium policies rank waiting stages with observable decision values. Running stages never preempt.
        dynamic=self.policy in ("Q","H","H-fit","H-shuffle","H-serial","H-wait")
        if dynamic:self.queue.sort(key=lambda j:(j.op!="confirm",-self.lastscore.get(j.i,0),j.queued,j.id))
        else:self.queue.sort(key=lambda j:(j.queued,j.id))
        left=[]
        for j in self.queue:
            r,h=self.route(j)[j.stage]
            if self.used[r]>=self.maxslots[r] or self.now%24>=self.s["shift_hours"].get(r,24):left.append(j);continue
            q=self.samples[j.i];self.used[r]+=1;j.active=True
            j.wait+=self.now-j.queued;self.qhours[r]+=self.now-j.queued
            self.active[j.id]=j;j.started=self.now;j.first=False
            length=self.world.duration(j.i,j.op,j.stage,h,self.s["service_cv"],j.attempt)
            self.busy[r]+=min(length,self.p["horizon_h"]-self.now)
            charge=self.s["costs"][j.op]*h/sum(d for k,d in self.route(j))
            j.cost+=charge;self.bill+=charge
            self.log("stage_start",q,j);self.event(self.now+length,"done",j.id)
        self.queue=left
    def release(self,q,j):
        op=j.op;q.pending.pop(op);q.performed.add(op)
        if op=="powder":q.ready=True;self.log("powder_ready",q,j);return
        val=self.world.signal(q.i,op,j.v)
        self.log("qc_released",q,j, f"y={int(val)}")
        if q.frozen and op!="confirm":self.metrics["late_evidence"]+=1
        if op=="fit":
            self.metrics["fit_accept"]+=int(val)
            if val:
                self.version=1;self.log("model_published",q,j)
                for p in self.samples:
                    self.cancel(p,"md","模型版本更新；未启动旧任务")
                    if p.ready and not p.closed and not p.frozen:self.dirty.add(p.i)
            else:self.log("rollback",q,j)
            return
        if op=="confirm":
            q.admitted=bool(val);q.closed=True;q.conf_time=self.now
            self.metrics["independent_batches"]+=1
            if val and self.first is None:self.first=self.now
            for a in list(q.pending):self.cancel(q,a,"已完成独立确认")
            return
        if op in ("md","redo") and j.v<self.version:self.metrics["stale_md"]+=1
        if op=="dft":q.dft_attribution=bool(val)
        q.ev=self.b.add(q.ev,op,val,j.v)
        if op=="xrd" and not val and ("md" in q.pending or "md" in q.performed):self.metrics["risky_early_work"]+=1
    def run(self):
        while self.calendar:
            t=self.calendar[0][0]
            if t>self.p["horizon_h"]:break
            self.now=t
            while self.calendar and self.calendar[0][0]==t:
                _,_,kind,idx=heapq.heappop(self.calendar)
                if kind=="entry":
                    q=self.samples[idx];self.submit(q,"powder");self.log("entry",q)
                elif kind=="shift_open":
                    self.dirty.update(p.i for p in self.samples if p.ready and not p.closed)
                elif kind=="freeze":
                    q=self.samples[idx];q.frozen=True;self.log("freeze",q)
                    for a in list(q.pending):
                        if a not in ("powder","confirm"):self.cancel(q,a,"窗口冻结")
                elif kind=="done":
                    j=self.jobs[idx];q=self.samples[j.i];r,h=self.route(j)[j.stage]
                    self.used[r]-=1;del self.active[j.id];j.active=False;self.log("stage_done",q,j)
                    failure=(r in ("xrd","eis") and j.attempt==0 and rng(self.world.seed,q.i,j.op,j.stage,"fault").random()<self.s["assay_retry_probability"])
                    if failure:
                        charge=self.s["costs"][j.op]*h/sum(d for k,d in self.route(j))
                        self.metrics["assay_fail"]+=1
                        if charge+self.encumbered<=self.p["budget_cny"]:
                            self.encumbered+=charge;j.attempt=1;j.queued=self.now;self.queue.append(j)
                            self.log("retry_queued",q,j)
                        else:
                            self.log("invalid_unreleased",q,j);q.pending.pop(j.op);q.performed.add(j.op);self.dirty.add(q.i)
                    elif j.stage+1<len(self.route(j)):
                        j.stage+=1;j.attempt=0;j.queued=self.now;self.queue.append(j)
                    else:
                        self.release(q,j);self.dirty.add(q.i)
                    # Free slots or new evidence can wake candidates that previously waited.
                    for p in self.samples:
                        if p.deferred:self.dirty.add(p.i)
            for i in sorted(self.dirty):self.offer(self.samples[i])
            self.dirty.clear()
            self.dispatch()
            # A second proposal can start speculatively while the first is in flight.
            if self.policy not in ("F","G","H-serial","H-wait"):
                for q in self.samples:
                    if len(q.pending)==1 and not q.deferred and q.ready:self.offer(q)
                self.dispatch()
        return self.outcomes()
    def outcomes(self):
        true=[self.b.good[k] for k in self.world.hidden]
        n=sum(true);tp=sum(q.admitted and true[q.i] for q in self.samples)
        fp=sum(q.admitted and not true[q.i] for q in self.samples)
        biased=sum(STATES[k][2] for k in self.world.hidden)
        detected=sum(q.dft_attribution and STATES[self.world.hidden[q.i]][2] for q in self.samples)
        wrong=sum(q.dft_attribution and not STATES[self.world.hidden[q.i]][2] for q in self.samples)
        m=dict(restricted_h=self.first if self.first is not None else self.p["horizon_h"],confirmed_run=int(self.first is not None),
          true_confirmed_run=int(tp>0),cost=self.bill,committed=self.encumbered,good=n,bad=7-n,tp=tp,fp=fp,fn=n-tp,
          bias=biased,bias_detect=detected,bias_wrong=wrong,bias_miss=biased-detected,n=7,unspent=self.p["budget_cny"]-self.encumbered,
          dft_no_bias=sum("dft" in q.performed and not STATES[self.world.hidden[q.i]][2] for q in self.samples),
          useful_dft=detected,invalid_fit=int(self.attempted and (not self.version or self.s.get("actual_fit_gain",self.s["fit_gain"])<=0 or not detected)),
          triple_coexist=sum(STATES[k][1] and STATES[k][2] for k in self.world.hidden),
          confirmed_both=int(bool(tp) and not fp),permitted_fit=int(self.attempted))
        errors_old=errors_cur=ties=0
        for i,k in enumerate(self.world.hidden):
            intrinsic=self.s["intrinsic"][STATES[k][0]]>=self.p["macro_lower_mScm"]
            for ix in range(8):
                u=rng(self.world.seed,i,"audit_holds",ix).random()
                obs0=u<self.b.likelihood(k,"md",0)
                gain=self.s.get("actual_fit_gain",self.s["fit_gain"])* (.7+.6*rng(self.world.seed,"family","gain").random())
                obs1=u<self.b.likelihood(k,"md",self.version,gain)
                errors_old+=obs0!=intrinsic;errors_cur+=obs1!=intrinsic
        m["audit_before"]=errors_old;m["audit_after"]=errors_cur;m["audit_count"]=56
        m["valid_label_pack"]=int(self.fit_i is not None and STATES[self.world.hidden[self.fit_i]][2] and self.version and errors_cur<errors_old)
        m["assay_fail"]=self.metrics["assay_fail"]
        # Pairwise rank quality is a synthetic proxy, comparing posterior family-weighted threshold probabilities
        # to hidden binary truth only over discordant truth pairs, not the published Mo rank.
        wins=0;den=0
        for q in self.samples:
            if not true[q.i]:continue
            g=self.b.stats(q.i,q.ev)[1]
            for x in self.samples:
                if true[x.i]:continue
                h=self.b.stats(x.i,x.ev)[1];den+=1;wins+=1 if g>h else (.5 if g==h else 0)
        m.update(pair_wins=wins,pair_n=den,trace_prior="synthetic")
        for k in ("deferred","resumed","cancelled","speculative_md","risky_early_work","late_evidence","stale_md","fit_accept",
                  "independent_batches"):m[k]=self.metrics[k]
        for op in self.s["stages"]:m["n_"+op]=self.metrics["n_"+op]
        for r,cap in self.maxslots.items():
            m["util_"+r]=self.busy[r]/(cap*self.p["horizon_h"]);m["queue_h_"+r]=self.qhours[r]
        return m
