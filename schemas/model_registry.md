# 势、性质头与证据版本 v1

每次输入结构改变、势参数更新、样品回归更新分别登记 hypothesis_id、model_id、mapping_id。发布模型须能复原哪些证据在当时已经到达。下表规定未来记录，尚无已训练 LPSC 模型。

|记录|必填信息与单位|
|---|---|
|身份|model_id、parent_id、模式、descriptor/拟合头、软件 tag/commit、Torch/设备、元素词表顺序、checkpoint 和部署文件 SHA256、权重许可、选定发布者|
|证据|训练/开发/盲测 frame_id 清单及各自 hash、参考 DFT 签名、标签种类、样品/QC 关联、采样与剪裁规则、来源版本|
|训练|随机种子、真实 batch 与步数、训练配置 hash、可训练参数名单与参数量、优化器、偏置校准、EMA 用法、最佳开发 checkpoint、计时及机时|
|状态|submitted_at、trained_at、validated_at、published_at（带时区）；状态 proposed / trained / validated / published / rejected / superseded；记录失败项与审批者|
|适用域|组成、相、温度、环境、误差门槛、外推警记、适用的 MD 任务和截止；按组留出表与冻结的评估文件|
|部署|目标主机/硬件、推理精度、导出模式、导出前后 E/F 一致性、回滚 parent_id、第一批使用任务|

发布事件由 model_id 与 validated_at 唯一确定。发布前提交的 MD 锁定其旧 model_id。版本晋级只重算与新增误差相关的在途或已完成候选，逐个记录 redo_of、原因、优先级、重算工期和费用。已冻结实验表保持历史决策版本。失败或超时沿用最近已验收版本；失败报告同样入库。用户可从任何一条输运结果反查到势文件、结构、DFT 标签与启动时的可见证据。
