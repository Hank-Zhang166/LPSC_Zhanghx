# LPSC_Zhanghx
## 氯富集硫银锗矿的输运分歧与序贯验证
当 Li₆₋ₓPS₅₋ₓCl₁₊ₓ 在晶内模拟中排在前面，压片电导却没有体现优势，下一笔预算应当投向改结构、补采样、核查样品，还是用独立 DFT 检验原子势？本项目将不同尺度的证据和实际可用时点同时纳入开题研究。

**本版能复核两件事。** 第一，公开原子文件与实验数据中究竟包含哪些组成、参考力和重复结构。第二，在给定假设下，五种研发策略获得首次独立阳性确认的时间、召回与费用如何变化。新 DFT、DPA4 适配、输运 MD 和独立湿端确认均为后续实验。

[书面开题报告](paper/开题报告_P8.pdf) · [汇报 PDF](paper/汇报版开题报告_P8.pdf) · [可编辑 PowerPoint](paper/汇报版开题报告_P8.pptx) · [逐页 Word 汇报词](paper/P8_逐页汇报词.docx) · [可编辑书面报告](paper/开题报告_P8.docx) · [技术附录](P8_技术附录.md) · [P7 逐页修改对照](paper/P7_TO_P8_CHANGELOG.md)

~~~text
名义组成 + 已发布的相/成分证据 → 枚举结构族 → 同口径独立 DFT
                                            ↓
元素/坐标/晶胞 → DPA4 → E、F → MD 轨迹 → 晶内输运及其区间
                                            ↓
新粉体 → 同粉体分样 → 压片 EIS + 条件 → 锁定 A/B → 新批独立确认
                                            ↓
任务和证据时间戳 → DES 队列与费用 → 继续/取消/补证/保留或更新势
~~~

### 实际结果
- Oxford 的 PBEsol 文件含 28,100 帧、三个组成。中间组成 x=0.25 和 0.50 尚需独立验证。公开 Li 力模的逐组成分位数已复算。
- 五种政策使用 5,000 组成对基准重复，另跑 22 个压力设置。相对动态排程且固定势的 B3，允许定向适配的 B4 在基准参数下使首个独立阳性确认的限制均时增加 0.247 h，每个 24 候选队列增加约 830 元情景费用，真合格召回增加 0.066 个百分点。成对区间、分母和实际失败情景均见 [DES 结果](docs/DES_RESULTS.md)。
- 系统仿真中的费用单价、误判率、势更新效果与时长为明确可替换的参数。现场决策先登记可接受的漏选和成本，再比较同口径策略。

### 从哪里动手
|负责内容|先打开|第一项可验收产物|
|---|---|---|
|数据与材料|[审计及复算](docs/DATA_AUDIT.md)、[数据清单](configs/dataset_manifest.csv)|冻结来源、单位、重复簇、轨迹族与留出清单|
|原子计算|[势的数据流](docs/DPA4_ARCHITECTURE.md)、[七张实验卡](experiments/README.md)|同构型上固定权重与独立 DFT 的误差、时长、适用域|
|实验|[配对方案](docs/WET_EXPERIMENT.md)、[粉体清单](pilot/powders.csv)、[压片清单](pilot/pellets.csv)|合作方确认 SOP 与盲码，记录真实完成、审核和冻结时刻|
|工业工程|[系统规格](docs/DES_SPEC.md)、[运行说明](simulation/README.md)、[核验记录](simulation/outputs/verification.json)|独立重放同一随机种子，换入实测时长后重新比较|
|研究归因|[比较协议](docs/COMPARISONS.md)、[主张审计](paper/P8_CLAIM_AUDIT.md)|登记 H1/H2/H3 各自允许得出的结论|
|图与文稿|[制图说明](figures/README.md)、[复现入口](docs/REPRODUCIBILITY.md)|编辑 draw.io / Blender / Office 源，重新导出图表与报告|

### 在新目录复核
Python 3.10+ 的标准库足以运行最小 DES。先读归档验证或指定新的输出目录，完整运行命令和单元口径在 [simulation/README.md](simulation/README.md)。原始逐重复 CSV 使用 gzip 压缩，可直接用 Python 或 pandas 读取。大型公开原包与外部权重按各自许可证单独取得。

~~~sh
python simulation/verify_run.py
python simulation/run_study.py --help
~~~

~~~text
configs/      数据清单、模型拟议配置、DES 情景和决策参数
docs/         科学问题、已有研究、验收和模拟结果
experiments/  固定势、微调、性质任务、多任务与蒸馏实验卡
figures/      draw.io、SVG、Blender 源、脚本与渲染
paper/        两份 P8 PDF、Office 可编辑源、汇报词和逐页对照
pilot/        含父子关系的预登记样品编号
refs/         引用清单、公开文件实算脚本、哈希与审计结果
schemas/      原子、样品、事件与模型版本字段
simulation/   研究用 DES、结果、单次事件流水、图与验证
tests/        研究和交付的验收条件
~~~

项目版本 P8.0，资料核查日期 2026-11-23。第三方权重、数据与图形来源见 [使用说明](THIRD_PARTY_NOTICES.md)。

