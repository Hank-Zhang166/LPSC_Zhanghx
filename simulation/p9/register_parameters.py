"""Export a readable resource/parameter ledger from the exact computational inputs without imputing observations."""
import csv
import json
from pathlib import Path
from study import D
s=json.loads((D/"site.json").read_text(encoding="utf8"));p=json.loads((D/"project.json").read_text(encoding="utf8"))
rows=[]
def put(key,meaning,stage,value,unit,interval,law,grade,source,correlation,why,impact,verify):
    rows.append(dict(parameter=key,meaning=meaning,stage_or_resource=stage,value=value,unit=unit,scenario_range=interval,
      mechanism=law,evidence_grade=grade,as_of="2026-11-24",source=source,dependencies_or_correlation=correlation,
      rationale=why,decision_effect=impact,onsite_verification=verify))
put("site.existence","宜宾已报道电解液与固态电解质实验室建设及 Uni-Lab 配料、混料、烧结、表征联动","宜宾研发平台","已公开报道","定性",
 "不外推出硫化物授权、具体设备和槽数","公开资料审计","A","p9/evidence/YIBIN.md | https://www.bsia.org.cn/site/content/34720.html",
 "平台建设与项目对接相关","区分存在性与具体可用性","决定向谁核实而非直接赋予数值","核实 LPSC 可操作性、SOP 和通行范围")
labels={"staff":"称量、分装与外送准备","furnace":"合成/独立新批的烧结槽","xrd":"初相与复验相检","press":"压片与压实对照",
 "eis":"筛查、复测及复验阻抗测试","review":"人工质控审核队列","ship":"往返运输物流槽","ext":"委外局域结构表征","gpu":"共享 MD、训练与验收算力","dft":"独立标签与适配补标"}
for k,v in s["capacity"].items():
    put("capacity."+k,labels[k],k,v,"并发槽",f"0（不可约）或 1–{max(2,2*v)}；情景可改",
     "非抢占容量约束","D","site.json / capacity","同资源所有候选及相关动作争用","压力建模占位","决定队列与信息过期","核实设备清单、维护、排班与外部预约量")
for op,stages in s["stages"].items():
    for k,(r,h) in enumerate(stages):
        law=s["stage_laws"][r]
        put(f"stages.{op}.{k}",labels[r],f"{op} / {r}",h,"名义 h",f"{h*.5:g}–{h*2:g} 基本情景范围",
            law+"；三角取 0.75/1/1.25 倍；对数正态以给定工时为中位","D","site.json / stages & stage_laws",
            "同候选同阶段随机流跨政策配对；真实跨仪器相关性待估","分步建立工时与释放边界",
            "决定原始完成和可见发布时间","按步骤记录触发、排队、开始、完成、审核，再按任务族拟合")
for k,v in s["costs"].items():
    put("costs."+k,"一次任务的全流程情景价格",k,v,"元/任务",f"{v*.5:g}–{v*2:g} 情景",
     "预算以整项占用，实际支出按执行阶段的名义工时比例摊付","D","site.json / costs","与该操作阶段工时比例相关",
     "建立可逆预订与发生额","限制昂贵检验/确认能否排入","分解设备、人员、试剂、外送与计算费用")
for k,v in s["shift_hours"].items():
    put("shift."+k,"每日允许启动作业的工作窗口",k,v,"h/天","12–24","到班次开放重新决策，运行中不抢占","D","site.json / shift_hours",
    "审核和制样周期影响积压","模拟非全天人工能力","决定待发布任务的审核延后","确认实际班表、交接与加班情况")
put("service_cv","未指定分布时的备用 CV","工序",s["service_cv"],"CV","0–0.6","各已建资源的 stage_laws 优先","D","site.json",
 "按资源异质化，备用值未决定当前所有工时","区分默认与覆盖值","久候与真实耗时相关性待识别","核实每个阶段的经验分布")
specs={
 "confirm_sens":("独立复验通行灵敏度","确认粉体","0.70–0.99"),"confirm_fpr":("独立复验假阳性率","确认粉体","0.01–0.20"),
 "prior_bias":("关键原子环境潜在局域势偏差概率","原子参考","0.01–0.42"),"prior_contact":("潜在跨尺度接触损失概率","样品","0.10–0.50"),
 "fit_accept":("独立模型验收通过情景概率","模型验收","0–1"),"fit_gain":("通过后可纠正的 MD 判断性能差距比例","模型和 MD","真实错配压力 −0.60 至规划 0.65"),
 "quality_scale":("非确认观测的辨识度缩放","多种观测","0–1.12；观测概率裁剪"),
 "assay_retry_probability":("每个 XRD/EIS 阶段首次质控失效概率","XRD/EIS","0–0.15")}
for k,(meaning,resource,interval) in specs.items():
    put(k,meaning,resource,s[k],"概率或比例",interval,"详见 belief.py 和 engine.py 的条件抽样","E","site.json；本研究构造",
        "共享样品状态、域内版本；观测条件独立近似","展示条件决策与误判代价","影响 EVSI、归因和计划排程","使用独立原子参考与盲评新批校准")
put("intrinsic","三类结构族的合成晶内代表水平","输运演示",json.dumps(s["intrinsic"]),"mS/cm","合成取值，无实测置信区间",
 "由结构族决定","E","site.json；与 Mo 实测七点隔离","与每组成的三态权重同用","提供可评价真值","生成宏观是否达到阈值的情景标签","替换为独立 MD 输运分布")
put("contact_loss","接触损失的合成幅度","宏观映射",s["contact_loss"],"mS/cm","0–3","按隐藏样品状态扣减","E","site.json",
    "与结构状态和偏差状态共同进入评价","提供可并存竞争假说","影响独立确认和结构解释","拟合独立新批与同粉体压实对照")
put("structural_evidence","结构先验低/中/高","排名桥接","21 个输入单元","概率","每组三项和为 1","来自上游合成采样情景的前置均值","E",
    "../../p9/ranking/outputs/des_structure_prior.csv","共享计算参数未在此完整传播","界定结果是否在已有样品证据之前","控制各配方概率分布","审计结构表征与上游采样质量")
for k in ("xs","macro_lower_mScm","period_h","freeze_h","horizon_h","budget_cny","powder_aliquots","max_diagnostics","admit_floor","dft_alarm_floor",
          "seed_outer","calibration_seed"):
    unit={"xs":"取代量 x","macro_lower_mScm":"mS/cm","period_h":"h","freeze_h":"h","horizon_h":"h","budget_cny":"元"}.get(k,"数值或比例")
    rg={"macro_lower_mScm":"阈值待预注册","period_h":"1.5–4","freeze_h":"43–90","budget_cny":"8200–10700",
    "admit_floor":"0.10–0.99","seed_outer":"连续固定种子","calibration_seed":"与评价分离"}.get(k,"固定方案，可更换项目")
    put("project."+k,{"xs":"七个项目组成，不用于生成已知真实实验排序","macro_lower_mScm":"合成宏观性能下界","period_h":"候选入池间隔",
        "freeze_h":"每候选可改行动截止","horizon_h":"全队列观察上限","budget_cny":"共同经费上限","powder_aliquots":"每批可消耗的分样单元",
        "max_diagnostics":"初筛诊断种类上限","admit_floor":"独立确认前的后验门槛","dft_alarm_floor":"DFT 诊断前的偏差后验门槛",
        "seed_outer":"外层评价种子起点","calibration_seed":"开发种子起点"}[k],"项目配置",json.dumps(p[k]),unit,rg,"明确输入或预注册条件",
        "E","project.json；七组成范围由用户任务及 Mo 等限定","所有政策共享；部分单独消融","按开发与评价隔离","改变允许行动或比较单位","由项目方锁定门槛、预算、粉体余量和时限")
for op,values in {"xrd":"0.20/0.63/0.83","local":"0.08/0.52/0.92","eis":"0.86/0.17","repeat":"0.83/0.16","contact":"0.86/0.17",
 "dft":"0.89/0.09","md":"0.88 普通；0.45 有偏"}.items():
    put("likelihood."+op,"二元结果的结构/类别条件似然",op,values,"条件概率","可按 quality_scale 连续压至 0.5",
        "按真实隐藏状态生成，政策仅见发布后的 y","E","belief.py / likelihood","与共同 f/c/b 关联，非真实仪器标定",
        "使假说可识别程度可变","决定 EVSI、复验与 DFT 选择","采集同类独立参考或合作方盲测校准")
with (D/"parameter_register.csv").open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(len(rows))
