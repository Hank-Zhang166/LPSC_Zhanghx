# 公开证据与现场待核项

七个配方的回顾性比较使用 Mo 等在 25 ℃ 报告的同一系列压片读数。要复核第 2 章，先查看来源与样品组别，再按需要核查原子参考、结构表征或场地能力。登记表保留查阅日期、具体数据版本以及文件哈希所指的对象。

| 研究问题 | 从这里开始 |
| --- | --- |
| 七个点值怎样得到，哪些样品可以相互比较？ | [原始位置与组别](MO_BENCHMARK.md)、[七组成点值](mo_s1.csv)、[同研究的诊断性对照](diagnostic_groups.csv) |
| 电导变化多大才会交换排序？ | [21 对临界因子](ordering_margins.csv)、[不同扰动下的可能首位](ordering_stress.csv)。因子是人为设定的压力条件，实际批间变异留待新批次估计。 |
| 哪些公开数据能给原子势提供标签？ | [取得范围、计算口径与许可](data_access.csv)、[来源及哈希](source_manifest.csv)、[按原归档复算](#复算公开数据)。原作者验证集的独立性要对照模型预训练来源另行核查。 |
| 实验能约束哪些结构？ | [外部占位与样品条件](external_occupancy.csv)、[局域权重的文献证据](STRUCTURE_LITERATURE.md)。外部母体的冷压和烧结结果分别登记。 |
| 怎样检验 DPA4 的输入输出和更新？ | [冻结的权重、许可、原子参考与验收](DPA4_AND_LABELS.md)、[七组成实施协议](../protocol/VALIDATION.md) |
| 宜宾工位、产能和耗时有何依据？ | [公开调研与核实问题](YIBIN.md)、[现场校准登记](site_calibration.csv)。仿真实际读取的设计值另见[工位配置](../../simulation/redesign/lab.json)与[模型参数登记](../../simulation/redesign/parameters.csv)。 |
| 如何沿文献继续调研？ | [文献笔记](literature_notes.csv)按题名与 DOI 或原文链接记录 66 项已引研究的发现和适用范围；完整书目在[现行报告](../交付稿/开题报告_P9.pdf)末尾。 |

## 复算公开数据

以下命令从仓库根目录执行，仅需 Python 标准库。取得原始文件后将示例路径换成实际位置。Mo 核对器先检查论文与补充文件的版本，再直接提取表 S1。第二条命令从已登记的七个点重算仓库内两张扰动表。

~~~shell
python p9/evidence/audit_mo_inputs.py /path/to/paper.pdf /path/to/supplement.docx
python p9/evidence/ordering_robustness.py
~~~

[现行数据集复核工具](dataset_audits/audit_public_files.py)直接读取下载的原始文件，输出输入文件的 SHA-256 和按源计数。将结果与下表的 JSON 对照即可核对相同版本和分组。原始下载地址与许可列在[数据登记](data_access.csv)。

~~~shell
python p9/evidence/dataset_audits/audit_public_files.py oxford /path/to/datasets.zip
python p9/evidence/dataset_audits/audit_public_files.py deepmd /path/to/20240412-SSE.zip
python p9/evidence/dataset_audits/audit_public_files.py deepmd /path/to/SSE-abacus.tar.gz
python p9/evidence/dataset_audits/audit_public_files.py darus4510 /path/to/data.zip
python p9/evidence/dataset_audits/audit_public_files.py obelix /path/to/all.csv
~~~

| 冻结的核查结果 | 抽查时应看到的数量与单位 |
| --- | --- |
| [Oxford PBEsol](dataset_audits/oxford_counts.json) | 28,100 帧中有 22,500 帧母体，x＝−1 与 x＝1 各 2,800 帧；六种富氯中间组成均缺少直接数据 |
| [AIS SSE-VASP](dataset_audits/sse_vasp_counts.json) | 发布方训练和验证分组分别含 54,771 和 4,900 帧；严格四元组成中，母体分别为 1,172 和 200 帧 |
| [AIS SSE-ABACUS](dataset_audits/sse_abacus_counts.json) | 366 个 DeepMD 数据分组，合计 131,670 个 E/F/virial 首轴对齐的记录；严格四元域中有母体 862 帧及另一界面组成 1,168 帧 |
| [DaRUS 4510](dataset_audits/darus4510_counts.json) | 五套训练数据共出现 14,332 个 CFG 块，其中按块文本去重后为 6,694 个；近重复结构还需进一步检查 |
| [OBELiX](dataset_audits/obelix_counts.json) | 599 条实验记录中 321 条标记有 CIF；严格四元元素筛选得到 3 条母体记录 |
| [Bath VASP XML](bath_prefix_audit.json) | 从归档前 60 MiB 中取得一个完整 XML 压缩成员，包含一组 416 × 3 的力和 3 × 3 的应力。文件和应力单位见[读取脚本](audit_bath_prefix.py)，此项仅代表该成员。 |

补充证据时，给出 DOI 或固定版本链接、页码或归档成员、观测条件及可复算的记录单位。对下载包、单个成员、网页响应分别记录哈希范围。外部数据的再利用条件随条目保存，派生结论应注明可比较的样品、结构或轨迹范围。
