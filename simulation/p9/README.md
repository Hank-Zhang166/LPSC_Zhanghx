# 七组成概率证据与事件驱动决策

本目录是 P9 新版，模型和输出与上一级 simulation/ 的 P8 V0 分开。可运行的部分包括贝叶斯观测更新、任务发布/冻结、有限资源队列、条件二步前向规划、共用随机场景的外层政策评价、独立阈值校准、压力分析和复算。所有观测与成本机制均为可替换的情景假设。

在项目根目录运行。依赖 Python 3.10+ 标准库，绘图另用 Matplotlib 及中文字体。

~~~sh
python simulation/p9/study.py --reps 512 --stress 128 --dev 64 --workers 8
python simulation/p9/constraints_sensitivity.py --workers 8
python simulation/p9/register_parameters.py
python simulation/p9/verify.py
python simulation/p9/plot.py
~~~

核心代码在 belief.py（读取上游权重；十二态假说与观测似然）、planning.py（无隐藏状态的单步/二步决策和前向资源日历）、engine.py（外层任务、不可中断资源、费用和审核；潜在真值只用于生成观测和评价）。site.json 与 project.json 可分别替换设施/队列假设和单次项目范围。parameter_register.csv 登记 88 项，包括公开事实、工序/资源边界、情景数值、分布、证据等级及待核事项。未取得真实先验、独立参考或现场日志时，应保留 synthetic 标识。研究协议、公式、资源假设、指标分母和实现限制见 TECHNICAL_NOTE.md；可引入报告的结果见 report_insert.md。

|输出|如何使用|
|---|---|
|outputs/replicates.csv.gz|每种情景、阈值条件、政策、种子一行；主试验共 18,432 条评价记录。按 scenario、setting、seed 配对。|
|outputs/policy_summary.csv / paired_effects.csv|均值、边界与 95% 区间；基准设置选择 baseline、default。比率分母为零时点估计留空。|
|outputs/development_calibration.csv|64 个开发种子、五点门槛网格、共同风险或最低召回约束的可行性。|
|outputs/matched_operating_points.csv / matched_pair_effects.csv|96 个开发种子选两阈值混合，384 个独立评价种子重测实际近似等召回或等风险的运行点；不可达保留标记。|
|outputs/joint_sensitivity.csv|24 组拉丁超立方六维扰动，每组 40 个共同随机队列，数值与单因素压力扫描分开。|
|outputs/event_trace.csv / decision_trace.csv|共同示例队列的任务、成本预约、样品批号、审核发布和候选行动、理由、预期发布时间与后验。所选种子只用于解释发布行为。|
|outputs/checks.json / metadata.json|程序、配置与上游先验 SHA-256；无窥视前缀、物理前序、容量、冻结、退款、信息价值边界和重放验证。|
|outputs/p9_policy、p9_event_trace、p9_stress|均含 PNG 与 SVG，从实际轨迹及统计表生成，可直接在报告使用。|

留出评价得到的 Q、H、H-fit 首次独立阳性确认限制均时分别为 48.15、58.55、58.55 h。适配相对固定势增加 126 情景元，二步前瞻相对单步将潜在势偏差漏诊降低 7.37 个百分点。决策目标不同会改变优选政策。此结果无法替代真实 DFT/MD、配对先导或现场班次校准。
