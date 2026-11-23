# P8 关键主张审计

核查日期为 2026-11-23。每条主张同时登记证据性质、原件和结论范围。新增通用势训练、DFT、长 MD、压片或实验排程均未在本轮实做。报告实际运行的是公开文件统计和研究用 DES。交付物中带“拟”“情景”“独立复算”的标记应随引用保留。

|主张及位置|证据等级与复核入口|允许作出的解释与当前边界|
|---|---|---|
|首轮组成 x=0、0.25、0.50；汇 3|化学式计量＋拟选子域；正文 §1.2、[材料域](../docs/MATERIAL_DOMAIN.md)|每个 Cl 替 S 对应计量上少一个 Li；实际成相、占位与补偿分布须由独立制备和表征判断|
|DPA-SSE 与领域适配已有先例；汇 4|正式论文、作者归属与方法；[证据矩阵](../refs/EVIDENCE_SOURCES.md)|区分直接署名、使用模型、独立同行；公开资料无法判断合作方内部已实现的流程|
|SeZM 与可训练参数；汇 8–10|[v3.2.0 模型](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/doc/model/dpa4.md)，[LoRA 源码](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/deepmd/pt/model/descriptor/sezm_nn/lora.py)，[模型卡](https://huggingface.co/deepmodelingcommunity/DPA4-OMat24)|原子势预测 E 及导数；单任务 LoRA 同时开放规定的小模块。权重许可和文件指针已核，无实测 LPSC 精度或速度|
|28,100 个 Oxford 构型；汇 6|逐帧解析及散列；[组成计数](../refs/oxford_counts.json)、[力分位数](../refs/oxford_force_profile.json)|22,500/2,800/2,800 对应 Li₆PS₅Cl、Li₅PS₄Cl₂、Li₇PS₆。参考力模描述标签本身，未计算势误差；中间配方仍需补证|
|SSE-VASP 领域覆盖；汇 6|原包按 train/validation 等字段解析；[检查结果](../refs/sse_vasp_counts.json)|训练 54,771、验证 4,900；严格四元素域只含母体。独立测试需查预训练重叠。SSE-ABACUS 发布方约 127,000；本次下载包实数 131,670 帧，严格母体 862 帧，不能并入 SSE-VASP 同口径训练总数|
|OBELiX 及晶界数据；汇 6|[实验表解析](../refs/obelix_counts.json)、[DaRUS 4510](../refs/darus4510_counts.json)、[清单](../configs/dataset_manifest.csv)|599 是实验条目数，321 为 CIF 状态 done。严格四元素 3 条全是母体，其中两行为 done，一条标为 close match。DaRUS-4510 重复结构块应隔离；5959 仅核查记录与部分文件，未逐帧计数|
|条件化的输运解释；汇 2/12|原论文场景与[三层验收协议](../docs/VALIDATION_PROTOCOL.md)|脑图/Blender 图仅作尺度示意；文献 QENS/NE 推断与 EIS 压片测量的量纲相同、观测对象不同，条件不可平移|
|独立样品计划；汇 14|[粉体](../pilot/powders.csv)和[压片](../pilot/pellets.csv)预登记，status=planned|首轮 6 个独立粉体、12 片；另预留 4 个独立确认粉体与对应 4 片。片端重复不能提高独立合成批次数|
|V0 的耗时、误判和单价；汇 16/17|[情景参数](../configs/assumptions.yaml)、[模拟规格](../docs/DES_SPEC.md)|24 个候选、基准冻结 96 h 等属于显式建模输入。公开结构/电导文件不能校准该实验室的仪器排队或训练成功概率|
|首次独立阳性与召回；汇 18–21|[原始重复](../simulation/outputs/monte_carlo.csv.gz)、[汇总](../simulation/outputs/policy_summary.csv)、[配对差](../simulation/outputs/paired_effects.csv)|实际运行 V0，每个主政策和 4 个消融各 5,000 次，22 个压力设置各 1,000 配对重复。独立复验阳性可误判，根据潜在真值另计召回。480 h 截尾平均与仅成功队列分位数的分母不同|
|B4 在 V0 的代价；汇 20|相同 rep 的 B4−B3。独立读取压缩原始表，重新求平均成本差与限制平均确认时间差；再核对原始汇总三项区间|时间 +0.247 h [0.196, 0.297]；整队列费用 +830.11 情景元 [816.62, 843.60]；召回 +0.0657 个百分点 [0.0320, 0.0995]。区间为 Monte Carlo 95%，不含参数估计/真实实验不确定性|
|物理学习、辨识行动、系统节拍三个增量；汇 5/22|H1/H2 为预注册计划；H3 为条件情景比较；[实验卡](../experiments/README.md)、[DES 结果](../docs/DES_RESULTS.md)|B4 采用代理更新结果，基准显示相对 B3 的时间和费用增加。尚未在同召回、等支出或真实研发现场证明净收益|

**版本与复算。** 模型选择和停止阈值须在实际开发前登记。DES 修改参数、策略或随机预算后，以新运行数据替换定量表、图与讲稿，保留上个版本的输入和 hash。独立审查人可以从上表逐条回到原始文件或明确的未来试验。

本表按最终 22 页汇报核对。公开参考力分布见汇 7，每确认候选费用和槽时见汇 19。

文字稿 §2.1 和表 2.2 区分已公开的样品输运与本项目的原子参考标签。Wang 等直接覆盖 x=0、0.25、0.50、0.70；Adeli 等在 298 K 分别报告冷压与烧结样品。历史观测按条件比较，不能进入势训练的 E/F 真值，也不能替代冻结后的独立新批。具体读数、缺失项及原文位置见[输运证据表](../refs/literature_transport_benchmarks.csv)。决策假设与 DES 政策比较继续沿用原有参数与结果。
