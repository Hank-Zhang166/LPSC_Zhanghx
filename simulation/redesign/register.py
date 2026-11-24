"""Export a versioned engineering parameter registry directly from the runnable model."""
import csv
from itertools import groupby
from belief import HERE,LAB,PROJECT,positive

rows=[]
def add(name,meaning,scope,value,range_,generator,dependency,calibration,source,grade="E"):
    rows.append(dict(parameter=name,meaning=meaning,resource_or_stage=scope,nominal=value,studied_range=range_,
               generator=generator,dependence=dependency,grade=grade,source=source,date="2026-11-24",field_check=calibration))
for stage,steps in LAB["operations"].items():
    for j,(resource,h,cost) in enumerate(steps,1):
        add(f"{stage}.{j}.hours","占槽服务时长（h）",resource,h,"审核服务倍率0.75–3；规格另见压力配置" if resource=="review" else "固定均值，工期按下列噪声抽取",
            "GPU界内均匀；其余相应变异系数的对数正态",
            "每阶段独占槽；同资源占用互斥，排队内生","分开收集开始、结束和结果审核发布时刻","lab.json / operations","D")
        add(f"{stage}.{j}.cost","开工后发生的额外费用（情景元）",resource,cost,"本轮固定单价","阶段启动记账",
            "提交时先预留整包，未开始可取消","核报价、开票方式、共享算力内部分摊","lab.json / operations","D")
for res,cv in LAB["cv"].items():
    add("cv."+res,"服务时间标准差／均值",res,cv,"固定设计值","同任务/阶段/候选共用稳定键",
        "不同任务的等待由相同槽的占用相关联","按设备和工作班次估计服务变异","lab.json / cv")
labels={
"freeze_h":("唯一不可逆提名时点（h）","13；联合扫描14–44","读取实际冻结时刻"),
"horizon_h":("队列观察上限（h）","72","确认独立审核的观察时限"),
"budget_diagnostic":("冻结前最多承诺的费用（情景元）","850–2600","项目方冻结预算及新批留额"),
"posterior_floor":("长期达标提名后验门槛","开发网格0.58–0.97","预登记风险/损失与基准可接受值"),
"minimum_action_gain":("可触发新的诊断订单的最低决策效用增益","固定设计值","评估微小改善是否值得占用"),
"maximum_inflight":("诊断同时在制上界","1或2","实际提交限制与预约机制"),
"max_outer_branch_actions":("两步政策按单步价值进入搜索的首动作数","3，另加最佳DFT和适配","计时并评价增大搜索宽度后的稳健性"),
"p_global_risk":("全队共享高偏差普遍率状态概率","真值联合扫描0.06–0.50","独立参考识别跨候选共性"),
"p_local_bias_by_global":("在G低/高时的局域偏差先验","[0.09,0.64]；固定势充分压力另见engine.py","辨识有效局域域和两层变异"),
"p_contact":("配方－工艺长期接触不利倾向概率","固定设计值","密度、粒径和同粉压片对照"),
"batch_pass_if_target":("长期目标达标时新制粉体实际达标概率","联合0.72–0.98","独立制粉分层重复"),
"batch_pass_if_nontarget":("长期目标未达标时新制粉体实际达标概率","联合0.02–0.28","独立制粉分层重复"),
"confirm_sensitivity":("新批确实达标时报告判阳概率","固定设计值","盲法审核及仪器重复"),
"confirm_specificity":("新批确实未达标时报告判阴概率","固定设计值","盲法审核及仪器重复"),
"acceptance":("定向适配独立留出通过情景概率","基准0.68；压力值0.42；路径检查0/1","按版本的真实留出准则和记录"),
"fit_repair":("允许适配时假设消除的观察偏差比例","外层联合−0.40–0.95","真实独立DFT与轨迹复算；验证失准风险"),
"local_domains":("假定可迁移的局域环境域","A/B交错七组成","独立局域描述符归类，替换合成域"),
}
for key,(meaning,range_,calibration) in labels.items():
    add(key,meaning,"项目或潜在状态",PROJECT[key],range_,"配置／条件伯努利或决策常量",
        "同一参数可能被整个队列共享；具体条件见README及belief.py",calibration,"project.json / "+key)
for kind in ("screen","pellet","structure","contact","old","md","dft","redo"):
    values=sorted(set(round(float(x),4) for x in positive(kind)))
    add("obs."+kind,"在不同潜在态下读阳概率",kind," / ".join(map(str,values)),
        "初筛与分样正确性朝0.5收缩（质量因子联合0.50–1）" if kind in ("screen","pellet") else "状态条件详见计算函数",
        "伯努利；具体哪个状态产生哪个概率见函数","B1内共享制备实现，MD共享局域误差",
        "用独立参考或盲测先导数据估计似然","belief.py / positive")
add("site","宜宾项目工位容量、SOP、审核记录的证据状态","宜宾","待核实","现场条件外推未知",
    "该行不生成工时或能力","上面D/E值未转成宜宾实测","核验各工位、班次及可接受留额","../../p9/evidence/YIBIN.md 和 site_calibration.csv","A（仅公开建设信息）")
with (HERE/"parameters.csv").open("w",newline="",encoding="utf-8") as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
