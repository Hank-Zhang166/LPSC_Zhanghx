# 模型权重、使用条件和可训练标签

## 冻结可复核接口

2026-11-24 读取 DeePMD-kit 官方 release API、版本化文档、许可证和 Hugging Face 模型 API（含 LFS 指针）。当日 latest 标记 v3.2.0，发布于 2026-08-19，标签提交为 `8cfd46e37448feca361ff3427a6c2b514ce5a2bb`。软件采用 GNU Lesser General Public License v3.0；模型、数据采用各自的许可。所核 OMat24 仓库固定版本为 `173bfd5a26f90a756ee891777270ef117078d9be`，模型卡列 CC BY-NC 4.0。对产业合作需先核对拟用场景及权重使用权。代码开源并不将第三方权重改成可商用许可。[DeePMD-kit 发布](https://github.com/deepmodeling/deepmd-kit/releases/tag/v3.2.0)；[软件条款](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/LICENSE)；[模型仓库](https://huggingface.co/deepmodelingcommunity/DPA4-OMat24/tree/173bfd5a26f90a756ee891777270ef117078d9be)。

| 同一组成和构型的候选 | 实际文件 / SHA-256 | 对照目的 |
|---|---|---|
| DPA4-Plus-OMat24-v20260805 | *.pt；6820a320dc241a4002e6c257ad21983950df178b1f80271a6e6af199adb18567 | 精度候选，先用冻结模型核对关键 Li 邻域、迁移能差和耗时 |
| DPA4-Neo-OMat24-v20260805 | *.pt；fd7f34ae28f921201e4a0328ddf56179892752084f8363e7796038201471c989 | 较轻量候选，比较等轨迹质量下的成本 |
| DPA-SSE（DPA-2） | AIS 数据 #217（数据 CC BY 4.0）；[模型卡 #266](https://backend.aissquare.com/dpa/detail/models?type=models&id=266&name=SSE-VASP-dpa2) 标注 LGPL-3.0，列 SSE-VASP-dpa2.pt（120,922,466 字节），冻结领域势单独运行 | 与硫化物领域势作被试相同几何的强对照，避免预训练重叠；不把 DPA-2 权重传给 DPA4 初始化 |

大文件 SHA 是模型仓库公布的 LFS SHA。本次未下载权重、启动微调或部署到宜宾。DeePMD 原生训练的模型输入、损失和后处理详见 [架构](../../docs/DPA4_ARCHITECTURE.md) 与 [训练模式](../../docs/MODEL_TRAINING.md)。与七组成相容的数据拆分和版本管理在本轮任务中单独冻结。

## 决策与可执行条件

1. 压片排序不一致先拆成样品映射、结构支持/权重、MD 采样或势误差的可并存解释，记录哪一类行动可改变冻结前的选择。接触/密度证据、新相或跳跃不足可分别触发复测、修改输入或延长 MD。
2. 同一几何上独立诊断 DFT 能够检验局域误差。诊断、训练及最终验收分别建池，按轨迹/环境族/化学组成封存，不能将诊断后的构型重新别名送入终验。补标优先度是“可能改变关键决策的后验质量 × 局域误差/覆盖 × 诊断的区分能力 ÷ 边际成本”的待检验规则。保留冷门但对反转敏感的迁移族。
3. 如误差且值得更新，先用明确的 PyTorch 原生 `dp --pt train input.json --finetune <checkpoint.pt>` 路线，在受支持的数值环境做类型表、checkpoint 和单步预检；仅把独立 DFT 的 E、F 及已校准 virial 输入能量任务损失。DPA-ADAPT 的 DPA3 专用包装器不能因同一项目维护而视为兼容所有权重。LoRA 先核对该检查点描述符、脚本的可训练参数掩码和独立组留出，见 [v3.2.0 微调](https://docs.deepmodeling.com/projects/deepmd/en/v3.2.0/train/finetuning.html)、[LoRA 代码](https://github.com/deepmodeling/deepmd-kit/blob/v3.2.0/deepmd/pt/model/descriptor/sezm_nn/lora.py)。
4. 除总体 E/F，还要查看 Li、缺陷和迁移近邻的分层误差、相对能量、源域保持、热稳定及独立 MD 排序。在固定结构池/权重/协议下评估旧势与新势，另行评估联合更新。验收未过或来不及发布时，保留旧势、记录失败和重算范围；吞吐不足且学生满足独立 DFT、MD 及无偏排序后才讨论蒸馏。
