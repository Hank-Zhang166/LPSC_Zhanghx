# 任务流水契约

用途是重建每个决策能看到的样品、结构族、版本、设备占用与数据发布时间。该格式在 DES 已使用，将来接入实验室 LIMS/排程系统时需要同合作方校准。标识作用域为一次 seed × policy 运行。

|字段|表示与约束|
|---|---|
|seed / policy|共同随机场景编号、政策代号；配对比较按 seed 联结|
|candidate_id / sample_id|零起候选编号；Cxx-SCREEN、Cxx-IND 分别指筛查和新合成确认粉体。MD 与 DFT 挂靠候选参考粉体，未声称构型与真实样品逐原子配对|
|structure_family_id / potential_version|F0–F2 的离散域及其族内版本；族内版本 0 为初始，1 为新验收。上游必须保留真实模型及标签包哈希|
|task_id / operation|一次具体排队尝试和操作；重试得到新任务号；非任务事件可空|
|time_h / event|自运行开始的小时；同一文件的记录顺序决定同刻先后；跨政策不能按 time_h 混合回放|
|evidence_id / qc_released_at|只有 qc_released 行赋值。消费前必须出现其任务的发布记录|
|resources / detail|采用“+”连接同一任务原子占用的资源；排队小时、后验、冻结承诺或验收决定按事件填入|

生命周期为 submitted → queued → started → completed_unreviewed → qc_released → observation_applied / independent_decision；queued → cancelled 与 completed_unreviewed → qc_failed_retry → 新 queued 为支路。batch_locked、model_published / model_rollback、window_frozen、eliminated 用于重建版本与行动边界。检修特殊任务没有研究结果。已经开始的非中断任务在执行完前一直占槽。审核延时从 completed_unreviewed 到 qc_released，期间结果对决策不可见。

适配真实系统时应补充 UTC 时间、时区、批号、仪器号、操作人匿名标识、重复/失败原因、参考 DFT 方法、原始文件哈希、模型与结构哈希、单价版本。未经授权不记录可识别人员信息。验收时检查每项入队/启动/完成/发布时间单调、资源不超标、独立批次没有复用筛查粉体、谱系能回溯到实际模型注册项。
