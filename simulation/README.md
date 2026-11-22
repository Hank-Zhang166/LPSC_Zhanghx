# 复算离散事件实验

本目录交付已执行的研究模拟。它提供假设→事件→决策→独立复验→费用/漏判的可回放链路。数据生成、运行和验证仅需 Python 3.10+ 标准库；绘图另需 Matplotlib 和中文字体。归档运行版本、输入散列、场景覆盖及种子见 `outputs/run_metadata.json`。

在项目根目录执行。完整复算会覆盖本机结果目录，可指定不同输出位置保留归档。

```sh
python simulation/run_study.py --reps 5000 --stress-reps 1000 --seed 731900 --workers 6
python simulation/plot_results.py
python simulation/verify_run.py
```

快速独立复算可执行 `python simulation/run_study.py --scenarios V0 --reps 32 --workers 2 --out replay_small`。回放首批种子的每个逐次值能与归档 CSV 对照；32 次的汇总区间应比 5,000 次宽。Windows 有多个 Python 时可用 `py -3.14` 替换命令中的 python。输出配置为 JSON 兼容 YAML，可用标准库读取。图默认输出 PNG、SVG 两种文件，SVG 保留可编辑文本和矢量元素。

|输出|用途|
|---|---|
|monte_carlo.csv.gz|每个场景×种子×政策的原始数值；CSV 字段名称与下列指标契约对应，共 155,000 条|
|policy_summary.csv|场景与政策汇总均值、条件分位数、95% MC 区间和资源占用率|
|paired_effects.csv|同种子政策的绝对差、相对差、配对 95% 区间；基线分母为零时相对差留空|
|event_trace.csv|预先指定种子区间中首个 B4 发布成功场景的完整五策略流水；仅供作图和事件审计，不用于选择总体效应|
|verification.json|原始数据复算/事件顺序/资源/取消/信息时序核验结果|
|policy_comparison、cost_time、sensitivity|基准策略比较、成本时间位置、相对固定势的场景效应图|
|resource_gantt、event_swimlane、utilization|真实 V0 事件生成的单次资源与样品时间图，以及总体资源利用率|

关键字段：first_h 为至少一个独立复验阳性的时刻，无确认留空；true_first_h 额外要求潜在真值合格，仅用于仿真审计。restricted_h 与 true_restricted_h 分别按 480 h 共同边界处理未确认；confirmed、tp、fp 为独立阳性、真阳性和假阳性个数。positive/negative 是隐藏的潜在真值，调度器不可访问。wrong_drop 是明确被终止的潜在合格候选；unconfirmed_good 还含独立复验失败等未确认情况。timely_phase、timely_eis 为在各候选冻结前取得初筛证据的候选数。

powders、pellets、eis_tests 按真正启动的新粉体、制片和仪器执行计量；同一粉体重复测试不会增加粉体数。dft_frames 对独立探针、训练与留出标签均计费。hours_gpu 只含共享 GPU；hours_dft 为独立 DFT 槽时。span_h 从 0 开始至队列最后事件（含冻结）或共同截止，util_* 按实际服务槽时除以资源容量×span_h。cost_cny 与 cost_index 是全队列资源花费，decision_loss_cny 可另加错淘汰损失。在压力情景中改变后者时应使用对应列比较。

recomputed 是同一候选启动的第 2 个及以后长 MD 数；obsolete_outputs 记录旧版本已开工但返回时版本过期的结果；expired_releases 记录发布时全族已无开放窗口的版本；unused_label_batches 记录到达时该族已经锁定了一批更新的额外包。输出中的 0 意味该事件在指定政策/场景没有发生。更多定义及数值解释见 `docs/DES_SPEC.md` 和 `docs/DES_RESULTS.md`。
