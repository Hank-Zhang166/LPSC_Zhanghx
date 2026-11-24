# P9 证据审计（2026-11-24）

科学输入分为四层。Mo 的同文压片数值用于回顾性方向对照；外部结构精修用于生成与约束各自的结构候选；DFT 给同几何原子势做监督；宜宾公开材料只确定主体、能力类别和建设阶段。每种用途均可追到原文或确实打开的文件。

| 文件 | 如何使用 |
|---|---|
| [Mo 七组成](mo_s1.csv) / [组别与来源](MO_BENCHMARK.md) / [额外诊断对照](diagnostic_groups.csv) | 25 ℃ 七个宏观电导的点值、排名及来源。自制原料的压实子实验和商业/自制活化能另表 |
| [扰动临界因子](ordering_margins.csv) / [确定性排序压力表](ordering_stress.csv) | 用同一乘除因子分别扰动七个电导点，逐对求区间开始相交的位置。重算命令为 `python p9/evidence/ordering_robustness.py` |
| [来源指纹](source_manifest.csv) / [公共原子与材料数据](data_access.csv) | 区分已取得的完整文件、已查局部、只有作者声明、待申请和待新增。表内 SHA 的对象标明，不把响应文件散列当成整个数据集散列 |
| [可观测结构先验](external_occupancy.csv) / [结构方法与论文](STRUCTURE_LITERATURE.md) | 可追溯的母体 4a/4d 占位与实验条件。候选构型族的后验权重需另外估计 |
| [Bath 样本结果](bath_prefix_audit.json) / [复算](audit_bath_prefix.py) | 从 44 GB 公开归档的 60 MiB 前缀读取完整 VASP XML 成员，核对一个结构的 E/F/stress |
| [DPA4 与 DFT 契约](DPA4_AND_LABELS.md) | 官方代码版本、模型指针及许可，选择性定向补标、验收和回退 |
| [宜宾现场证据](YIBIN.md) / [校准登记](site_calibration.csv) | 现场事实、合理迁移和待校准参数分别登记。情景初值不等于在地实测 |
| [可纳入正式报告的章节](report_insert.md) | 文献基准、结构数据三步核查与宜宾实施边界 |

用 Python 标准库复核附件：`python audit_mo_inputs.py PAPER.pdf SUPPLEMENT.docx`。本轮还用父目录 [公开档案读取器](../../refs/audit_public_files.py) 重跑了 Oxford / AIS 两份包 / DaRUS-4510 / OBELiX 的计数，核对源档 SHA 和统计结果。未把出版商 PDF、DOCX、CIF、第三方权重或原始计算包重新存入本仓库；本目录保留派生数字和证据指针。
