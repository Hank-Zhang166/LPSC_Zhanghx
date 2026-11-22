# 势选择、定向标注与参数更新协议

**拟执行。** 已核对发布文件、v3.2.0 接口与训练代码。未在本研究进行 LPSC 训练、预测或性能评测。下列阈值和预算均为开发阶段起点。学校、实验室与算力平台尚待协调运行。

## 从冻结基线开始

|候选|能力与来源|本研究检验|
|---|---|---|
|DPA4-Plus-OMat24-v20260805|8,849,376 参数，6 Å 截断，面向高精度；CC BY-NC 4.0|在同一批构型评估独立 E/F、迁移 ΔE 与测试机每千步时间，筛选较大势是否值得|
|DPA4-Neo-OMat24-v20260805|1,125,372 参数，同训练材料域、单位及许可。轻量候选|测量同盒、同温度、同积分精度的速度、内存、跃迁排序。按误差–成本前沿决策|
|DPA-SSE|论文所用 DPA-2 硫化物领域势；适用元素、权重使用条款与具体可下载组件须分别记录|使用其原生工具链做独立预测；共同 frame_id 对齐预测表。既有权重不能直接做 DPA4 初始化，公开训练重叠帧不得评价外推|

两款 OMat24 权重的公开指针 SHA256 写入研究 YAML。随附 JSON 和模型卡锁在同一提交。保留整个 model 块，类型表完整覆盖 H–Og。完整表内 Li/P/S/Cl 的零起始索引为 2/14/15/16；文件里的局部类型按符号映射。权重卡所列 3.2.0、PyTorch 2.11、CUDA 12.8 是发布方训练环境；目标机资源按需求测量，FP32、内存、吞吐与总费均入账。[权重与配置发布](https://huggingface.co/deepmodelingcommunity/DPA4-OMat24/commit/173bfd5a26f90a756ee891777270ef117078d9be) · [模型卡](https://huggingface.co/deepmodelingcommunity/DPA4-OMat24) · [DPA-SSE 正式论文](https://doi.org/10.1038/s41524-025-01764-6) · [官方安装](https://docs.deepmodeling.com/projects/deepmd/en/latest/getting-started/install.html) · [软件发布说明](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/README.md)

## 为相同预算组装数据

1. 模型输入从可信晶胞起步；对 x=0、0.25、0.5 枚举 S/Cl 占位、Li 空位补偿与多个随机排布。结构族包括母体/松弛近邻、小应变、热扰动、迁移前后及过渡附近、物相可疑的负例。每个样品允许多个相容假说。大重叠、错误计量、电荷不守恒构型进入剔除日志。结构改动保存父版本。
2. 合并前核对数据许可、泛函、赝势与数值设置。首轮单势只用一种参考口径。OMat24 权重预训练和目标 DFT 可有元素能量零点差；按训练集计量矩阵检查秩，对可辨识常数做偏置对照；相同计量的迁移 ΔE 与力不受常数偏置影响。不同泛函带来的力差需参考重算或分头建模。
3. 清查相邻帧、超胞对称及重复结构。按共同母体、轨迹、相邻时间窗和构型族建立连通组；组内全进同一 split。参考缺 ID 时用组成、能量/原子、周期环境指纹与局部相似阈值聚类，另用更严阈值重复。先隔离目标组成/跳跃环境做外推，再按组近似 70/15/15 划训练/开发/盲测。写明每组独立数。母体–轨迹连成一组时整组隔离；数据稀少改为逐族留出并公开不确定性。
4. 对 H1 每轮比较随机、委员会力分歧＋结构多样性、湿端 XRD/组成容许集合内的分歧＋多样性。每臂使用同一候选池、初始模型、相同独立 DFT 标签数（累计16/32/64）和同一数据划分。先打散高相似帧，再在不同 Li 局域/占位/迁移族分层配额；独立探针保留到验收。记录没被选择的族及 DFT 拒算。混合回放建议目标/源=0.6/0.4，规定源指经核验的**同 DFT 口径**源域样本；无相容源时运行目标单域并单列遗忘检验。
5. 独立参考证实某个可改变后续行动的关键环境偏差时，登记拟补帧、预计耗时、候选决策截止和信息收益。纯样品接触异常、无法收敛的 MSD、待确认物相等先交回相应层。若基线已满足预先约定容差且入选候选稳定，停止追加标签。

## 训练入口与模型选择

将 JSON 递交前核对实际 dp 版本、训练 schema、元素词表、损失、读研数据路径及许可。原版预训练 JSON 带有特定 OMat24 数据路径、统计文件及训练周期，迁移到本地数据时重建 training 和 learning_rate；清除不可访问的只读预训练统计文件以及与 numb_steps 冲突的 num_epochs。保留对应模型结构。拟对照 MSE 时同时替换整个 loss 块，避免继承该发布 JSON 的 MAE 与 f_use_norm=true。检查点训练入口采用 .pt，部署包 .pt2 在实际目标机生成。建议在独立环境逐项验证。[原生微调](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/doc/train/finetuning.md) · [OMat24 用法](https://huggingface.co/deepmodelingcommunity/DPA4-OMat24)

|试验|更新位置|比较、输出与放行依据|
|---|---|---|
|M0 固定|无梯度；可另设只用训练集拟合元素偏置的子臂|所有同帧预测表、机时、OOD/迁移误差；旧势足够好就保留|
|M1 从头|随机初始化描述符与势头|控制模型容量、步数及重复种子，量化预训练价值|
|M2 全量 FT|所选预训练描述符与能量头|与同种子、同标签的冻结/LoRA 比较独立 E/F、ΔE、源域和 MD|
|M3 LoRA|SO(3)/SO(2) 主线性基权重加低秩 A/B；实现同时开放能量头、径向投影、部分门控/偏置等|导出 requires_grad 清单；记录可训练形式与合并后文件的预测一致性|
|M4 冻结描述符、训练性质头|势固定；从有效原子表示训练外部性质回归头；原生 property 头作为后续对照|具有相/密度/温度和独立响应的严格配对组；按样品批次留出|
|M5 可选多任务|共享描述符和各自的能量头；批次只走本任务损失|设为不同 DFT 参考两个势头，逐头检查误差与负迁移。可选性质继续用 M4；两类标签不可混作单种真值|
|M6 条件蒸馏|教师冻结，学生描述符和能量头|先有长 MD 推理瓶颈，再验收物理精度和付出回本|

DPA-ADAPT 的 v3.2.0 DPATrainer 读取 shared_dict 下的 dpa3_descriptor，并给 repflow 写字段，默认下游头为 property。这个封装入口不适用于上述标准 OMat24 检查点。以 DeePMD 原生入口执行。v3.2.0 的 LoRA 单任务实现还冻结 adam_type_embedding 与 adam_freqs，且会开放特定小模块，启动后记录参数统计。[包装器源码](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/dpa_adapt/trainer.py#L245-L265) · [LoRA 更新策略](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/deepmd/pt/model/descriptor/sezm_nn/lora.py#L365-L420) · [多任务接口](https://docs.deepmodeling.com/projects/deepmd/en/latest/train/multi-task-training.html)

全量/LoRA 初始配置为 batch 2 帧、学习率由 1e−4 至 1e−6、上限 10,000 步、每 500 步存盘并跑完整开发集；连续四次关键族力 RMSE 和开发 ΔE 未改善 1% 即外部早停。初轮关闭 EMA，若启用则在开发阶段同一沟通预算内与原始 checkpoint 比较并记录 decay。固定的一个组成为最终 OOD 时不参加阈值或超参选择。完整模式卡与注册表分别记录输入、执行入口、产物及否决条件。[实验卡索引](../experiments/README.md) · [评测](VALIDATION_PROTOCOL.md)

本研究参考钙钛矿分类仓库按配置、实验编号、元数据和独立测试组织复现。其下游结构级分类与 CE 不适用于力梯度训练。DPGEN2 已实现迭代训练、探索、选择、标注；本项目记录湿端约束和任务冻结时间带来的**额外**证据价值。[参考仓库实现](https://github.com/zhangsf3413/synthesizability_classification/blob/main/docs/IMPLEMENTATION.md) · [DPGEN2 算法](https://docs.deepmodeling.com/projects/dpgen2/en/latest/developer.html)
