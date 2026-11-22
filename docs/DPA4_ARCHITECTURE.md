# 一份构型怎样成为能量、力与输运估计

**核查日期为 2026-11-23。** 前向、损失与接口以 DeePMD-kit 标签 v3.2.0 为准。候选检查点来自 OMat24 的 v20260805 发布。本轮核对了文档与代码，所有 LPSC 模型实验都处于设计阶段。[描述符文档](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/doc/model/dpa4.md) · [SeZM 实现](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/deepmd/pt/model/descriptor/sezm.py)

## 从晶胞到守恒势

1. 在给定组成与相约束下建立多个阴离子占位、Li 配位与空位假说。将部分占有的 CIF 实例化为满足整数计量和电中性的超胞。记录原型、占位和随机种子。**示例**：4 个式单元在 x=0.25 时含 Li₂₃P₄S₁₉Cl₅。名义计量只确定原子个数，放置方式仍需实验和 DFT 检验。
2. 每帧读类型编号 t[N]、笛卡尔坐标 R[N,3]（Å）和晶胞 H[3,3]（Å，行是基矢）。元素符号经 type_map 查表。数值 t 是类型索引；原子序数 Z 仅是物理记法。周期镜像构成半径 rcut 内的有向边。模型计算边位移、径向基、平滑包络与边坐标系旋转，反馈给每层。
3. 内层节点保留 SO(3) 等变通道，角阶 ℓ 具有 2ℓ+1 个分量。每条边收集源节点特征并旋到边坐标系，经 SO(2) 卷积后旋回全局并汇聚至目标节点，等变前馈更新节点。层数和角阶以该权重随附 JSON 为准。末层读取 ℓ=0 的标量通道，得到每原子 h[N,d]。随原子顺序同步置换时，原子通道随之置换。
4. dpa4_ener 将 hᵢ 映射成 eᵢ。Σ(real i)eᵢ 是一帧总势能 E，单位 eV。原子能分解由模型定义，通常只有体系总能和原子力等 DFT 标签。坐标梯度生成力 Fᵢ=−∂E/∂Rᵢ。按行基矢约定，在固定分数坐标下 Ξαβ=−Σγ(∂E/∂Hγα)Hγβ。对拉应力取正的参考软件，势能贡献 σ=−Ξ/V，仍须核对上游的号、张量顺序、单位与动能项。旋转晶胞与原子时，E 应不变且 F 应同步旋转。[能量和 virial 定义](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/doc/model/train-energy.md)
5. 用通过验收的势驱动积分器，获取带时间步、温度、胞和模型版本的轨迹。由 Li 解缠位移得到自扩散与集体量，见[分层验收](VALIDATION_PROTOCOL.md)。将重复样品的相、成分、孔隙与测试条件引入独立的样品模型。实验差异触发候选行动；EIS 的电导数据不会作为势的力标签。
6. 可选性质分支有两种可检验实现。原生结构性质任务用 fitting_net.type=property、property_name、task_dim 及 intensive 指定归约，配合 property 损失。研究首选先冻结势，导出 descriptor，按有效原子及元素池化后与实验条件配对训练小型回归。外部样品映射、误差传播与独立验证由课题编写。DeePMD 的 structural_feature 是末隐藏层对有效原子的**求和**；直接跨原子数比较会混入尺寸。[性质头](https://docs.deepmodeling.com/projects/deepmd/en/latest/model/train-fitting-property.html) · [embedding](https://docs.deepmodeling.com/projects/deepmd/en/latest/inference/embedding.html)

## 梯度与监督信号

同一 DFT 口径的回放帧和目标帧 → 批次 → 描述符 θ → 拟合头 φ → 总能 E → 坐标导数 F / 盒形变导数 Ξ。E、F、Ξ 分别对齐参考量。力损失对 θ 的梯度涉及 E 的坐标–参数混合导数。优化器只更新当前模式开放的参数。开发集用于选 checkpoint；隔离的最终集及物理检验决定发布或退回旧势。

取显式配置 intensive_ener_virial=true，MSE、无相对力归一化。B 个帧，第 b 帧有 N_b 个有效原子。定义 L_E=mean_b[(ΔE_b/N_b)²]，L_F=Σ_b,i,α(ΔF_biα)²/(3Σ_b N_b)，L_Ξ=mean_b[Σ_αβ(ΔΞ_bαβ/N_b)²/9]。目标 L=w_E L_E+w_F L_F+w_Ξ L_Ξ。E/F 的单位和分量数不同，权重决定训练时对力和相对能量的取舍，只在开发集调节。传统 intensive_ener_virial=false 时，能量与 virial 的 MSE 项用 1/N 而非 1/N² 缩放。数据缺标签须保留缺失状态。首轮统一将 start_pref_v 和 limit_pref_v 设为 0，待口径与应变探针验证后独立对照。文中监督目标是每构型 DFT，不能推导独立样品的 EIS。[损失实现](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/deepmd/pt/loss/ener.py) · [数据约定](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/doc/data/system.md)

## 模型 I/O 与监督信号契约

|任务 / 版本键|输入与来源|输出、监督与统计|放行条件和消费者|
|---|---|---|---|
|势 / model_id, frame_id|结构 t[N],R[N,3] Å,H[3,3] Å，帧来源和 DFT 参考签名|E[1] eV、F[N,3] eV/Å、可选 Ξ[3,3] eV。DFT 同口径 E/F/Ξ；上述 MSE|原子对齐、元素表、分组留出、独立 ΔE 和力通过 → MD|
|性质 / encoder_id, head_id|h[N,d]、有效掩码、T[K]、条件协变量。依样品–结构配对编号|每帧/样品 y[k]，如条件化 log₁₀(σ/[S cm⁻¹])。独立观测，开发集 MAE，报告校准区间|按独立批次检验；比仅条件/测量先验模型好才使用 → 样品排序|
|MD / model_id, trajectory_id|结构、初速度[N,3]、积分步长、温度、系综和随机种子|轨迹[T,N,3] Å、胞[T,3,3]；D_self 与 D_charge（m²/s）、统计区间。无逐步实验监督|时间步敏感性、跨种子跃迁、有限尺寸和相稳定通过 → 输运比较|
|DFT / reference_id|待标 frame_id、R、H、元素序、泛函、赝势、截断/k 网格、收敛设置|单点总能、力、可选应力/virial。DFT 收敛日志是参考 QC|核对能量基准/力号、网格与截断收敛 → 标注账本或盲测集|
|样品映射 / mapping_id|样品/批次谱系、相/成分、密度、夹具、温度、MD 不确定度；可有多种相容结构|样品级 logσ、区间或排序。独立重复制备 EIS，同条件分层残差|辨识不足时保留解释集合；输出行动或延期|
|DES / policy_id, event_id|任务、资源、可见事件历史、日历时刻[h]、冻结时点、各模型发布日期|开始/完成/释放/取消、费用与失效原因；按同 seed 政策比较。未来日志可校准|审计可见时间和资源守恒 → 节拍统计与独立确认|

## 一步前向验收

用两个不同原子数的手工构型逐帧验证单位和 atom-id。以同一模型复算原结构、同步换序与刚体旋转的结构。对一个 Li 位移 ±δ 做中心差分并减小 δ，比较投影的力；对小胞应变做能差检验。报告浮点精度和误差随 δ 的平台区间。检查点、训练 JSON、元素序、导出后端与设备绑定，结果写入 model_registry。此处是拟执行门槛。
