# DPA4 检查点、原子参考和发布条件

本项目于 2026-11-24 核对 DeePMD-kit v3.2.0 的代码、文档和模型发布记录。七组成的物理试验仍在规划阶段。正式任务用下表识别拟检验的模型，跨机器复算时应固定检查点、元素映射、后端与精度。[DeePMD-kit v3.2.0](https://github.com/deepmodeling/deepmd-kit/releases/tag/v3.2.0) · [版本化模型卡](https://huggingface.co/deepmodelingcommunity/DPA4-OMat24/tree/173bfd5a26f90a756ee891777270ef117078d9be)

| 对象 | 冻结身份与来源 | P9 的用途 |
| --- | --- | --- |
| DeePMD-kit | v3.2.0，提交 8cfd46e37448feca361ff3427a6c2b514ce5a2bb。[软件许可](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/LICENSE) | 核对 PyTorch 推断、训练、特征处理及导出接口 |
| DPA4-Plus-OMat24-v20260805 | .pt 的 LFS SHA-256 为 6820a320dc241a4002e6c257ad21983950df178b1f80271a6e6af199adb18567 | 比较关键 Li 邻域力、迁移能差和相同硬件的轨迹成本 |
| DPA4-Neo-OMat24-v20260805 | .pt 的 LFS SHA-256 为 fd7f34ae28f921201e4a0328ddf56179892752084f8363e7796038201471c989 | 与 Plus 在相同结构和目标采样精度下作对照 |
| DPA-SSE | [AIS 模型卡 #266](https://backend.aissquare.com/dpa/detail/models?type=models&id=266&name=SSE-VASP-dpa2)登记 SSE-VASP-dpa2.pt，120,922,466 字节 | DPA-2 领域势在相同几何上独立评估。分组标明可能与其训练数据重叠的结构。 |

OMat24 模型库的固定提交为 173bfd5a26f90a756ee891777270ef117078d9be，模型卡给出的权重许可为 CC BY-NC 4.0。DeePMD-kit 软件与 DPA-SSE 模型卡分别标示 LGPL-3.0，AIS #217 的数据卡标示 CC BY 4.0。产业合作需按实际权重和拟用范围核对授权。登记的 Plus/Neo 哈希来自上游大文件指针；本项目核对了指针和元数据，权重文件未随仓库分发。[文件范围和来源指纹](source_manifest.csv) · [数据版本与许可](data_access.csv)

## 单构型到输运分布

1. 为一个结构族生成满足计量和电荷约束的整数超胞。以 x＝0.4、20 个 P 为例，计量为 Li₁₁₂P₂₀S₉₂Cl₂₈；相同计量可有多种 S/Cl 和 Li 空位排布。记录父结构、族标识、采样规则、周期边界以及原子索引。
2. 每帧输入为元素映射和类型索引、笛卡尔坐标 R（N × 3，Å）及晶胞 H（3 × 3，Å）。能量分支读出标量总势能 E（eV），原子力 F 为 E 对坐标的负梯度（eV/Å）。virial Ξ 为每帧 3 × 3 的能量量纲张量。应力与 virial 对齐前须核实符号、体积、分量排序、单位和是否含动能项。用同一几何的原子置换、刚体转动、小位移和小应变作数值检查。[结构输入](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/doc/data/system.md) · [能量与 virial 定义](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/doc/model/train-energy.md)
3. 用经原子参考检查的势运行独立初态轨迹；以拟合窗、跃迁统计和跨种子误差检验输运收敛。按研究中定义的结构族后验和共享误差，生成配方间优势、反向和近似并列三种概率。压片总电导在另一实验层级记录；训练势的监督仍来自同一构型的原子参考。[概率排序与算例](../ranking/README.md) · [新批及留出协议](../protocol/VALIDATION.md)

## 训练和独立验收

第一个问题是新证据会改变哪项行动。成相或局域占位证据用于修订结构支持和权重，有效跳跃不足用于追加独立轨迹，压片与接触问题由同粉分样或新批处理。独立同构型 DFT 证实关键局域偏差后，再根据冻结时间、队列和验收成本决定是否启动定向补标。诊断参考、训练标签、最终盲测三个池按父结构、近重复族与轨迹隔离。[七组成 G0–G3 对照与盲测](../protocol/VALIDATION.md)

实际训练前对同一帧核实元素顺序、参考泛函、赝势、收敛和缺失标签标志。总能、力和可用 virial 分别计算损失，明确有效原子数、归一化方式和对应训练权重；应力口径未对齐时保留缺失标志并关闭该项监督。只有相同参考口径的绝对能才能直接合并。固定中间组成与局域结构的留出片段，分别检查总能差、力的尾部、迁移能差和源域保持，再按相同计算协议比较独立 MD。[能量任务损失实现](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/deepmd/pt/loss/ener.py)

PyTorch 原生微调入口为 `dp --pt train input.json --finetune CHECKPOINT.pt`。取得拟用权重后先做一帧预检；如使用低秩适配，记录该版本实际开放的参数及合并后导出的一致性。验收记录绑定模型 ID、父版本、证据发布时间和重算的局域范围。若新势未通过，或重算无法赶上仍可改变的决定，继续保留已验收版本。[v3.2.0 微调文档](https://docs.deepmodeling.com/projects/deepmd/en/v3.2.0/train/finetuning.html) · [LoRA 实现](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/deepmd/pt/model/descriptor/sezm_nn/lora.py)
