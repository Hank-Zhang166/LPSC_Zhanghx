# P8 交付核查
核查日期 2026-11-23。下列记录对应本版交付，模型正确性验收与真实湿端试验仍按后续计划单独开展。

|核查项|本版结果|复核位置|
|---|---|---|
|P7 来源|书面原件 29 个实体页含一页空白，幻灯稿 20 页，逐页给出保留、改写或删除及 P8 对应位置|P7_TO_P8_CHANGELOG.md|
|科学问题与已有成果|限制到氯富集候选；已有领域势、缺陷微调、输运、平台和排程按署名及证据类型分列，H1–H3 可独立失败|../refs/EVIDENCE_SOURCES.md、../docs/RESEARCH_QUESTION.md|
|势模型|核对映射、SeZM、能量头、力导数、损失归一和 LoRA 开放的实际模块；固定、适配、性质与蒸馏均有实验卡|../docs/DPA4_ARCHITECTURE.md、../experiments/cards/|
|公开数据|文件级复核 Oxford、SSE-VASP、SSE-ABACUS、OBELiX 与 DaRUS-4510；DaRUS-5959 核至元数据和演示目录|../docs/DATA_AUDIT.md|
|发布与撤回|独立参考、版本验收、重算和冻结均有门槛；蒸馏需额外证明速度和摊销收益|../docs/DISTILLATION_DECISION.md、../schemas/model_registry.md|
|定量 DES|基准 5,000 配对重复，22 个压力设置各 1,000 配对重复；全量重复表 155,000 行；238 项逐字段回放验证及 4,269 个样例事件|../simulation/outputs/verification.json、../docs/DES_RESULTS.md|
|湿端独立性|10 个粉体编号、16 个压片编号，均为 planned，已核对父键及 A/B 新批区分|../pilot/、../docs/WET_EXPERIMENT.md|
|文献综述与引文|第 2.1 节实引 67 篇学术文献（63 篇期刊、3 篇会议、1 篇预印本），另列 11 项数据与软件资料。文内编号与文末 78 条一一对应。表 2.2 及逐项外部记录标注条件、单位和证据边界|../refs/literature_review.csv、../refs/literature_transport_benchmarks.csv|
|PDF 与可编辑源|书面 PDF 32 页、汇报 PDF 22 页。PowerPoint 与汇报每页标题一致，Word 汇报词有相同的 22 个逐页讲述段。书面 PDF 内的文献跳转和 78 个外链经核查。同步校准了汇报第 3、4、6、14 页和对应讲稿|../tests/verify_deliverables.py|
|决定依据与未决问题|系统费用为情景单价。更换实际仪器、SOP、势权重和数据参考后须重新校准。未执行新 DFT、势训练、MD 或湿实验|P8_CLAIM_AUDIT.md|

