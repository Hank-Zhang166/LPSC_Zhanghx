## 第5章　把实验与计算放到同一事件时钟
### 5.1 模拟对象、可见性和反事实
物理 MD 输入结构、初态、势版本和温度，输出轨迹及计算耗时。DES 的对象是候选、粉体、压片、构型族、任务、证据和模型版本。DES 记录资源占用和等待，产生“何时能看到什么”的反事实。此次没有从 DPA4 在线预测力，也没有模拟真实电化学过程。潜在物性、误判、标签效果和训练成功以显式情景分布表示；公开原子力和实验记录不能识别本课题真实设备排队时长。
对每个任务记录提交、入队、开始、完成、审核发布和冻结。策略只有在发布时间到达后才可用该证据。对尚未启动的可取消任务释放预约；对已执行作业则保留资源流水。相同候选号不能取代粉体、压片、证据与模型版本的子标识。实际部署中，某一候选可以复用旧势结果，也可能只有部分结构族需重算。保存旧版及其可用时间能避免用未来信息美化过去的决策。
![图 5.1　单条模拟记录中的报告采集、质控发布和独立确认。DES V0 情景模拟，非实验实证。](simulation/outputs/event_swimlane.png)
### 5.2 基准参数与五种政策
基准队列 24 候选。合成炉、XRD、EIS、共享 MD/训练 GPU、DFT 槽位分别为 2/1/1/2/1。合成、初相检测、初相报告审核、制片、EIS、EIS 审核的中位时长依次为 12、2、3、4、3、2 h，变异系数依次为 0.30、0.20、0.40、0.25、0.25、0.40。对中位数 m、变异系数 c，若 T 服从对数正态，则 log T 的均值为 ln m，标准差为 √ln(1+c²)。短/长 MD 取 2/10 GPU·h，DFT 取 1 槽时/帧；首批训练与验收 6+2 h，冻结基准 96 h。初相潜在不相容/含混/相容为 30%/20%/50%，误判 5%。这些值均是情景假设；以人民币计价的部分同样是示例单价。
B0 固定全评价。B1 可在早期相门禁终止明显不相容的候选。B2 用可见证据更新后验成功机会，按单位名义成本决定下一项任务，给这一对照正确的情景先验；具体实现是成本感知多阶段贝叶斯决策，未拟合连续配方空间的高斯过程。B3 增加等待时间、冻结余量和结构复核，仍用固定势。B4 继承 B3，在独立偏差诊断通过后才分配标签、训练、验收及重算；适配成功及可纠正差距为待现场校准的随机机制。这样既能比较完整流程，也可通过关闭单项机制做消融。
每个队列使用相同候选、相同容量和成对随机数。策略的行动不同，看到的证据可以不同。基准每种政策 5,000 个重复，22 个压力设置每个 1,000 个重复。首次独立阳性确认指独立新批经过质控后给出阳性；它可能误放行，另报基于潜在真值的召回及假阳性。若 480 h 内没有阳性，则限制平均时间将该重复记作 480 h。费用为全队列累计，每确认费用用全体重复的总费用除以确认总数。两种统计的分母不同，费用差不能直接解释为“提前一个小时值多少元”。
### 5.3 实际计算结果
@BASE_TABLE
表 5.1　DES V0 情景模拟／非实验实证。RMST 为首次独立阳性确认的限制平均时间；中位/P90 只取成功队列。费用使用情景单价。
B2 的时间和费用最低，但真合格候选召回也最低。在项目特别忌讳漏掉有潜力的组成时，这一取舍会影响选策。B1 保留更多合格候选，B3 用较多信息改善快速策略的召回。若要声称方法符合“同准确率节省时间”，需先登记召回底线，在开发情景校准阈值、用新情景作等召回或等预算比较。当前研究实施了共同资源容量与共同确认标准比较，没有将不同政策的实际支出或召回率人为固定成相等。
![图 5.2　五项政策的首次独立确认时间与真合格候选召回。DES V0 情景模拟，非实验实证。](simulation/outputs/policy_comparison.png)
@DELTA_TABLE
表 5.2　B4 减去对照的配对差。h、费用和召回分别使用小时、情景元与百分点；括号内为蒙特卡洛 95% 区间。
在可分离定向适配增量的 B4 对 B3 比较中，B4 平均慢约 0.25 h，整队列多用约 830 元，召回增加约 0.066 个百分点。相对 B2，约 4.17 个百分点的额外召回对应约 13.70 h 的额外等待。相对 B1，B4 较快，但召回更低。这些结果来自指定参数和代理机制。重复次数多只缩小蒙特卡洛误差，不能修复真实设备时间或模型收益分布的偏差。
### 5.4 失败边界与贡献归因
图 5.3 比较同一情景和种子下 B4 与 B3 的差。扫描包括设备和审核等待、固定势充分、错淘汰代价、全确认、DFT 时长、冻结窗口、微调零增益及有利增益。费用区分真实占用的情景计价与错淘汰惩罚，完整流水另计取消、过期和重算。
![图 5.3　B4 相对 B3 的情景敏感性。每个压力设置 1,000 次配对模拟。](simulation/outputs/sensitivity.png)
@ABLATION_TABLE
表 5.3　V0 成对差；正值表示启用该机制后相应指标增大，95% 区间见技术附录。
系统层代理可以量化阶段门禁、排队优先、结构复核、标签包选择和更新时机在设定条件下的边际值。标签包选择的消融并非真正的原子级主动学习对比；后者仍需在隔离的参考帧池上执行 H1。基准中 B4 未带来净时效改善，因而更适合把资源投向“测准什么时候值得更新”，而非宣称更新一定带来加速。
## 第6章　实施顺序、分工与停止条件
### 6.1 第一项可执行工作
建模负责人先从公开数据复算组成计数和力标签分位数，冻结时间/结构族分组、统一能量与力的参考。对未知轨迹 ID 建立几何簇并做隔离敏感性，登记重叠预训练来源；资格不足的测试数据只作诊断。随后在同一批独立构型上比较固定 Plus、Neo 与 DPA-SSE 的局域误差、预测速度、显存和对候选排序的影响。没有数据支持前，任何一档模型都不预先占据部署位置。
实验负责人确认空气敏感材料的场地 SOP、样品余量、几何测量和可分辨阻抗分量。先用现有记录或不干预决策的影子流程，采集一份包括排队、完成、质控发布和冻结的事件账本。然后执行六粉体、十二片的配对先导。合格先导先锁定 A/B、主条件和最小有意义差，再开始独立新批复验。记录缺失、失效与重测，并保留冻结前的决策快照。
工业工程负责人用真实仪器占用和审核间隔替换情景分布，检查资源闲忙、失败重试、发布顺序和确认等待是否与真实记录相符；按项目方确认的召回底线和费用上限，用未参与校准的批次重评 B0–B4。文献电导的外部对照不提供仪器排队、审核时长或模型改进概率。若无真实时序，系统层只报告情景敏感性；若先导粉体无法稳定成相，暂缓定向训练，先改结构与工艺假说；若固定势验收充分，则以其作为当期生产性计算的候选。
### 6.2 拟提交项目与可复核结论
原始审计、引用清单、势实验卡、样品谱系、模型注册、DES 配置和运行结果按版本集中保存。研究人员先查看 README 和技术附录，再按角色打开对应实验卡。新增数据须明确使用许可和参考口径，实验结果须保留原始文件散列与发布时间；修改任何策略均应重新运行对应种子和验证，不覆盖已有结论。
截至本版，已完成的物理层工作是数据文件审计、标签统计和实现核查；已完成的工业工程工作是运行 DES、比较政策并检查其失效条件。物理势能否因定向补标获得更低的局域误差，真实设备能否复现模拟中的等待分布，均是后续独立检验。课题最早可以提交的科研结果，是清楚指出哪类新证据改变了下一项任务、花了多少资源、在什么时候仍来得及改变决定，并让反例获得同样的记录空间。
## 参考文献与可复核资料
[1] OU Y, SCHOLZ L, KESHAV S, et al. Microstructural insights into fast ion transport in solid electrolytes via multiscale modeling [J]. Nature Communications, 2026, 17(1): 8726. https://doi.org/10.1038/s41467-026-76216-w
[2] KORJUS O, MITRA S, BERROD Q, et al. Investigating the densification of Li6PS5Cl solid electrolyte through multi-scale characterization techniques [J]. Energy Storage Materials, 2025, 82: 104589. https://doi.org/10.1016/j.ensm.2025.104589
[3] ZHANG L, HAN J, WANG H, et al. Deep Potential Molecular Dynamics: A Scalable Model with the Accuracy of Quantum Mechanics [J]. Physical Review Letters, 2018, 120(14): 143001. https://doi.org/10.1103/PhysRevLett.120.143001
[4] DEISEROTH HJ, KONG ST, ECKERT H, et al. Li6PS5X: A Class of Crystalline Li‐Rich Solids With an Unusually High Li+ Mobility [J]. Angewandte Chemie International Edition, 2008, 47(4): 755–758. https://doi.org/10.1002/anie.200703900
[5] RAO R P, SHARMA N, PETERSON VK, et al. Formation and conductivity studies of lithium argyrodite solid electrolytes using in-situ neutron diffraction [J]. Solid State Ionics, 2013, 230: 72–76. https://doi.org/10.1016/j.ssi.2012.09.014
[6] LANGE M A, FAKA V, KRAFT M A, et al. Insights into Li5.5PS4.5Cl1.5 Formation Based on Precursor Mixing: In Situ Monitoring via Neutron Powder Diffraction [J]. Inorganic Chemistry, 2026, 65(35): 20522–20533. https://doi.org/10.1021/acs.inorgchem.6c03060
[7] ADELI P, BAZAK J D, PARK K H, et al. Boosting Solid‐State Diffusivity and Conductivity in Lithium Superionic Argyrodites by Halide Substitution [J]. Angewandte Chemie International Edition, 2019, 58(26): 8681–8686. https://doi.org/10.1002/anie.201814222
[8] YU C, LI Y, WILLANS M, et al. Superionic conductivity in lithium argyrodite solid-state electrolyte by controlled Cl-doping [J]. Nano Energy, 2020, 69: 104396. https://doi.org/10.1016/j.nanoen.2019.104396
[9] FENG X, CHIEN PH, WANG Y, et al. Enhanced ion conduction by enforcing structural disorder in Li-deficient argyrodites Li6−xPS5−xCl1+x [J]. Energy Storage Materials, 2020, 30: 67–73. https://doi.org/10.1016/j.ensm.2020.04.042
[10] WANG Y, BAZAK J D, ZHOU L, et al. Liquid-like solid-state diffusion of lithium ions in super-halide-rich argyrodite [J]. Cell Reports Physical Science, 2024, 5(12): 102314. https://doi.org/10.1016/j.xcrp.2024.102314
[11] ZHOU L, ZHANG Q, NAZAR L F. Li-Rich and Halide-Deficient Argyrodite Fast Ion Conductors [J]. Chemistry of Materials, 2022, 34(21): 9634–9643. https://doi.org/10.1021/acs.chemmater.2c02343
[12] HELM B, SARAVANAN R S, LANGE M A, et al. Exploring the Possibility of Extrinsic Anion Vacancies in Li6PS5Cl [J]. ACS Applied Energy Materials, 2026, 9(18): 12499–12509. https://doi.org/10.1021/acsaem.6c02127
[13] GAUTAM A, AL-KUTUBI H, FAMPRIKIS T, et al. Exploring the Relationship Between Halide Substitution, Structural Disorder, and Lithium Distribution in Lithium Argyrodites (Li6−xPS5−xBr1+x) [J]. Chemistry of Materials, 2023, 35(19): 8081–8091. https://doi.org/10.1021/acs.chemmater.3c01525
[14] MINAFRA N, KRAFT M A, BERNGES T, et al. Local Charge Inhomogeneity and Lithium Distribution in the Superionic Argyrodites Li6PS5X (X = Cl, Br, I) [J]. Inorganic Chemistry, 2020, 59(15): 11009–11019. https://doi.org/10.1021/acs.inorgchem.0c01504
[15] HANGHOFER I, BRINEK M, EISBACHER S L, et al. Substitutional disorder: structure and ion dynamics of the argyrodites Li6PS5Cl, Li6PS5Br and Li6PS5I [J]. Physical Chemistry Chemical Physics, 2019, 21(16): 8489–8507. https://doi.org/10.1039/C9CP00664H
[16] YU C, GANAPATHY S, DE KLERK N J J, et al. Unravelling Li-Ion Transport from Picoseconds to Seconds: Bulk versus Interfaces in an Argyrodite Li6PS5Cl–Li2S All-Solid-State Li-Ion Battery [J]. Journal of the American Chemical Society, 2016, 138(35): 11192–11201. https://doi.org/10.1021/jacs.6b05066
[17] MORGAN B J. Mechanistic Origin of Superionic Lithium Diffusion in Anion-Disordered Li6PS5X Argyrodites [J]. Chemistry of Materials, 2021, 33(6): 2004–2018. https://doi.org/10.1021/acs.chemmater.0c03738
[18] JEON T, CHA G H, JUNG S C. Understanding the anion disorder governing lithium distribution and diffusion in an argyrodite Li6PS5Cl solid electrolyte [J]. Journal of Materials Chemistry A, 2024, 12(2): 993–1002. https://doi.org/10.1039/D3TA06069A
[19] GUAN Q, WANG K, YEO J, et al. Path entropy-driven design of solid-state electrolytes [J]. Nature Communications, 2026, 17(1): 4736. https://doi.org/10.1038/s41467-026-71316-z
[20] PAYNE B T, JUELSHOLT M, PÉREZ-OSORIO M A, et al. How multi-length scale disorder shapes ion transport in lithium argyrodites [J]. Energy & Environmental Science, 2025, 18(19): 8876–8888. https://doi.org/10.1039/D5EE01612F
[21] WANG Y, LIM R, LARSON K, et al. Chemical and Electrochemical Characterization of Hot‐Pressed Li6PS5Cl Solid State Electrolyte: Operating Pressure‐Invariant High Ionic Conductivity [J]. ChemSusChem, 2024, 17(21): e202400718. https://doi.org/10.1002/cssc.202400718
[22] BÖGER T, STROTMANN K, FAKA V, et al. Impact of structural coherence and disorder on the ionic transport and lattice dynamics in Li+-conducting argyrodites [J]. Journal of Materials Chemistry A, 2025, 13(45): 39211–39228. https://doi.org/10.1039/D5TA07185B
[23] OU Y, IKEDA Y, SCHOLZ L, et al. Atomistic modeling of bulk and grain boundary diffusion in solid electrolyte Li6PS5Cl using machine-learning interatomic potentials [J]. Physical Review Materials, 2024, 8(11): 115407. https://doi.org/10.1103/PhysRevMaterials.8.115407
[24] WANG R, GUO M, GAO Y, et al. A pre-trained deep potential model for sulfide solid electrolytes with broad coverage and high accuracy [J]. npj Computational Materials, 2025, 11(1): 266. https://doi.org/10.1038/s41524-025-01764-6
[25] 卢智浩, 吴宏宇, 高于翔, 等. 基于固态电解质大原子模型的Li6PS5Cl中缺陷调控离子导率 [J]. 硅酸盐学报, 2025, 53(7): 1920–1928. https://doi.org/10.14062/j.issn.0454-5648.20250089
[26] WANG H, ZHANG L, HAN J, et al. DeePMD-kit: A deep learning package for many-body potential energy representation and molecular dynamics [J]. Computer Physics Communications, 2018, 228: 178-184. https://doi.org/10.1016/j.cpc.2018.03.016
[27] BATZNER S, MUSAELIAN A, SUN L, et al. E(3)-equivariant graph neural networks for data-efficient and accurate interatomic potentials [J]. Nature Communications, 2022, 13(1): 2453. https://doi.org/10.1038/s41467-022-29939-5
[28] ZHANG D, LIU X, ZHANG X, et al. DPA-2: a large atomic model as a multi-task learner [J]. npj Computational Materials, 2024, 10(1): 293. https://doi.org/10.1038/s41524-024-01493-2
[29] LI T, LI W, PENG A, et al. DPA4: Pushing the Accuracy-Cost Frontier of Interatomic Potentials with EMFA SO(2) Convolution [EB/OL]. arXiv:2606.02419v4, 2026 [2026-11-23]. https://arxiv.org/abs/2606.02419v4
[30] PERDEW J P, RUZSINSZKY A, CSONKA G I, et al. Restoring the Density-Gradient Expansion for Exchange in Solids and Surfaces [J]. Physical Review Letters, 2008, 100(13): 136406. https://doi.org/10.1103/PhysRevLett.100.136406
[31] HUANG X, DENG B, ZHONG P, et al. Cross-functional transferability in foundation machine learning interatomic potentials [J]. npj Computational Materials, 2025, 11(1): 313. https://doi.org/10.1038/s41524-025-01796-y
[32] DENG B, CHOI Y, ZHONG P, et al. Systematic softening in universal machine learning interatomic potentials [J]. npj Computational Materials, 2025, 11(1): 9. https://doi.org/10.1038/s41524-024-01500-6
[33] HENKELMAN G, UBERUAGA B P, JÓNSSON H. A climbing image nudged elastic band method for finding saddle points and minimum energy paths [J]. The Journal of Chemical Physics, 2000, 113(22): 9901-9904. https://doi.org/10.1063/1.1329672
[34] RADOVA M, STARK W G, ALLEN C S, et al. Fine-tuning foundation models of materials interatomic potentials with frozen transfer learning [J]. npj Computational Materials, 2025, 11(1): 237. https://doi.org/10.1038/s41524-025-01727-x
[35] ZHANG Y, WANG H, CHEN W, et al. DP-GEN: A concurrent learning platform for the generation of reliable deep learning based potential energy models [J]. Computer Physics Communications, 2020, 253: 107206. https://doi.org/10.1016/j.cpc.2020.107206
[36] PODRYABINKIN E V, SHAPEEV A V. Active learning of linearly parametrized interatomic potentials [J]. Computational Materials Science, 2017, 140: 171-180. https://doi.org/10.1016/j.commatsci.2017.08.031
[37] IMBALZANO G, ANELLI A, GIOFRÉ D, et al. Automatic selection of atomic fingerprints and reference configurations for machine-learning potentials [J]. The Journal of Chemical Physics, 2018, 148(24): 241730. https://doi.org/10.1063/1.5024611
[38] ZAVERKIN V, HOLZMÜLLER D, CHRISTIANSEN H, et al. Uncertainty-biased molecular dynamics for learning uniformly accurate interatomic potentials [J]. npj Computational Materials, 2024, 10(1): 83. https://doi.org/10.1038/s41524-024-01254-1
[39] MONTES DE OCA ZAPIAIN D, WOOD M A, LUBBERS N, et al. Training data selection for accuracy and transferability of interatomic potentials [J]. npj Computational Materials, 2022, 8(1): 189. https://doi.org/10.1038/s41524-022-00872-x
[40] FU X, WU Z, WANG W, et al. Forces are not Enough: Benchmark and Critical Evaluation for Machine Learning Force Fields with Molecular Simulations [J]. Transactions on Machine Learning Research, 2023. https://openreview.net/forum?id=A8pqQipwkt
[41] HE X, ZHU Y, EPSTEIN A, et al. Statistical variances of diffusional properties from ab initio molecular dynamics simulations [J]. npj Computational Materials, 2018, 4(1): 18. https://doi.org/10.1038/s41524-018-0074-y
[42] MCCLUSKEY A R, COLES S W, MORGAN B J. Accurate Estimation of Diffusion Coefficients and their Uncertainties from Computer Simulation [J]. Journal of Chemical Theory and Computation, 2025, 21(1): 79-87. https://doi.org/10.1021/acs.jctc.4c01249
[43] HE X, ZHU Y, MO Y. Origin of fast ion diffusion in super-ionic conductors [J]. Nature Communications, 2017, 8(1): 15893. https://doi.org/10.1038/ncomms15893
[44] MORGAN B J. Lattice-geometry effects in garnet solid electrolytes: a lattice-gas Monte Carlo simulation study [J]. Royal Society Open Science, 2017, 4(11): 170824. https://doi.org/10.1098/rsos.170824
[45] MAEVSKIY A, CARVALHO A, SATAEV E, et al. Predicting ionic conductivity in solids from the machine-learned potential energy landscape [J]. Physical Review Research, 2025, 7(2): 023167. https://doi.org/10.1103/PhysRevResearch.7.023167
[46] CHO M Y, PYO K, LEE B D, et al. Discovering Multi‐Compositional Li‐Argyrodite Solid‐State Electrolytes via Experimental Active Learning [J]. Small, 2025, 21(21): 2410008. https://doi.org/10.1002/smll.202410008
[47] ATTIA P M, GROVER A, JIN N, et al. Closed-loop optimization of fast-charging protocols for batteries with machine learning [J]. Nature, 2020, 578(7795): 397-402. https://doi.org/10.1038/s41586-020-1994-5
[48] DAVE A, MITCHELL J, BURKE S, et al. Autonomous optimization of non-aqueous Li-ion battery electrolytes via robotic experimentation and machine learning coupling [J]. Nature Communications, 2022, 13(1): 5454. https://doi.org/10.1038/s41467-022-32938-1
[49] LAZIC S E, CLARKE-WILLIAMS C J, MUNAFÒ M R. What exactly is ‘N’ in cell culture and animal experiments? [J]. PLOS Biology, 2018, 16(4): e2005282. https://doi.org/10.1371/journal.pbio.2005282
[50] MACLEOD B P, PARLANE F G L, MORRISSEY T D, et al. Self-driving laboratory for accelerated discovery of thin-film materials [J]. Science Advances, 2020, 6(20): eaaz8867. https://doi.org/10.1126/sciadv.aaz8867
[51] BURGER B, MAFFETTONE P M, GUSEV V V, et al. A mobile robotic chemist [J]. Nature, 2020, 583(7815): 237-241. https://doi.org/10.1038/s41586-020-2442-2
[52] LIANG H, WANG C, YU H, et al. Real-time experiment-theory closed-loop interaction for autonomous materials science [J]. Science Advances, 2025, 11(27): eadu7426. https://doi.org/10.1126/sciadv.adu7426
[53] GUEVARRA D, STATT M J, POPOVICH K, et al. Active learning path-dependent properties using a cloud-based materials acceleration platform [J]. Digital Discovery, 2025, 4(12): 3674-3682. https://doi.org/10.1039/D5DD00325C
[54] DEEPMODELING COMMUNITY. DPGEN2 developers’ guide [EB/OL]. [2026-11-23]. https://docs.deepmodeling.com/projects/dpgen2/en/latest/developer.html
[55] ANGUSEZHANG et al. MatMaster: finetune_dpa_agent，版本 d27abb9 [CP/OL]. [2026-11-23]. https://github.com/AnguseZhang/MatMaster/tree/d27abb9e24c5686702278d39d2a90f0f7c1a2c17
[56] POLOCZEK M, WANG J, FRAZIER P. Multi-Information Source Optimization [C] // Advances in Neural Information Processing Systems, 2017, 30: 4288–4298. https://proceedings.neurips.cc/paper_files/paper/2017/hash/df1f1d20ee86704251795841e6a9405a-Abstract.html
[57] HERBOL H C, POLOCZEK M, CLANCY P. Cost-effective materials discovery: Bayesian optimization across multiple information sources [J]. Materials Horizons, 2020, 7(8): 2113-2123. https://doi.org/10.1039/D0MH00062K
[58] KUSAKAWA S, TAKENO S, INATSU Y, et al. Bayesian Optimization for Cascade-Type Multistage Processes [J]. Neural Computation, 2022, 34(12): 2408-2431. https://doi.org/10.1162/neco_a_01550
[59] TORRESI L, FRIEDERICH P. Multi-stage Bayesian optimisation for dynamic decision-making in self-driving labs [J]. Digital Discovery, 2026, 5(4): 1900-1912. https://doi.org/10.1039/D5DD00572H
[60] ASTUDILLO R, JIANG D, BALANDAT M, et al. Multi-Step Budgeted Bayesian Optimization with Unknown Evaluation Costs [C] // Advances in Neural Information Processing Systems, 2021, 34: 20197–20209. https://proceedings.neurips.cc/paper_files/paper/2021/hash/a8ecbabae151abacba7dbde04f761c37-Abstract.html
[61] KANDASAMY K, KRISHNAMURTHY A, SCHNEIDER J, et al. Parallelised Bayesian Optimisation via Thompson Sampling [C] // Proceedings of the Twenty-First International Conference on Artificial Intelligence and Statistics, 2018, PMLR 84: 133–142. https://proceedings.mlr.press/v84/kandasamy18a.html
[62] FOLCH J P, LEE R M, SHAFEI B, et al. Combining multi-fidelity modelling and asynchronous batch Bayesian Optimization [J]. Computers & Chemical Engineering, 2023, 172: 108194. https://doi.org/10.1016/j.compchemeng.2023.108194
[63] ZHOU J, LUO M, CHEN L, et al. A multi-robot–multi-task scheduling system for autonomous chemistry laboratories [J]. Digital Discovery, 2025, 4(3): 636-652. https://doi.org/10.1039/D4DD00313F
[64] ZHOU J, GE L, LI X, et al. Multi-task scheduling of self-driving laboratories under scientific constraints [J]. Chemical Science, 2026, 17(38): 18326-18338. https://doi.org/10.1039/D6SC03892A
[65] SARGENT R G. Verification and validation of simulation models [J]. Journal of Simulation, 2013, 7(1): 12-24. https://doi.org/10.1057/jos.2012.20
[66] GLASSERMAN P, YAO D D. Some Guidelines and Guarantees for Common Random Numbers [J]. Management Science, 1992, 38(6): 884-908. https://doi.org/10.1287/mnsc.38.6.884
[67] NELSON B L, MATEJCIK F J. Using Common Random Numbers for Indifference-Zone Selection and Multiple Comparisons in Simulation [J]. Management Science, 1995, 41(12): 1935-1945. https://doi.org/10.1287/mnsc.41.12.1935
[68] ROYSTON P, PARMAR M K. Restricted mean survival time: an alternative to the hazard ratio for the design and analysis of randomized trials with a time-to-event outcome [J]. BMC Medical Research Methodology, 2013, 13(1): 152. https://doi.org/10.1186/1471-2288-13-152
[69] THERRIEN F, ABOU HAIBEH J, SHARMA D, et al. OBELiX: a curated dataset of crystal structures and experimentally measured ionic conductivities for lithium solid-state electrolytes [J]. Digital Discovery, 2026, 5: 910–918. https://doi.org/10.1039/D5DD00441A
[70] POLETAYEV A. Training data and models for molecular dynamics of Li6PS5Cl [DS/OL]. Zenodo, 2026 [2026-11-23]. https://doi.org/10.5281/zenodo.23226230
[71] AIS SQUARE. Solid_State_Electrolyte: SSE-VASP，数据记录 217 [DS/OL]. 2024 [2026-11-23]. https://www.aissquare.com/datasets/detail?pageType=datasets&name=Solid_State_Electrolyte&id=217
[72] DEEPMODELING / AIS SQUARE. SSE-abacus，数据记录 260 [DS/OL]. 2024 [2026-11-23]. https://www.aissquare.com/datasets/detail?pageType=datasets&name=SSE-abacus&id=260
[73] DEEPMODELING COMMUNITY. 2024 Q2 OpenLAM Report: More Stable Code, Richer Domain Models [EB/OL]. 2024 [2026-11-23]. https://blogs.deepmodeling.com/OpenLAM-2024Q2/
[74] NRC–MILA. OBELiX experimental ionic conductivity dataset，all.csv，版本 4eaac88 [DS/OL]. [2026-11-23]. https://github.com/NRC-Mila/OBELiX/tree/4eaac889809dd489e3bae468c45d5c0e02b9147a
[75] OU Y, IKEDA Y, SCHOLZ L, et al. Data for: Atomistic modeling of bulk and grain boundary diffusion in solid electrolyte Li6PS5Cl using machine-learning interatomic potentials [DS/OL]. Version 2.0. DaRUS, 2024 [2026-11-23]. https://doi.org/10.18419/DARUS-4510
[76] OU Y, SCHOLZ L, KESHAV S, et al. Data for: Microstructural Insights into Fast Ion Transport in Solid Electrolytes via Multiscale Modeling [DS/OL]. Version 2.0. DaRUS, 2026 [2026-11-23]. https://doi.org/10.18419/DARUS-5959
[77] DEEPMODELING COMMUNITY. DeePMD-kit 源码与 DPA4 描述符说明，v3.2.0 [CP/OL]. [2026-11-23]. https://github.com/deepmodeling/deepmd-kit/tree/v3.2.0
[78] DEEPMODELING COMMUNITY. DPA4-OMat24 model card and model files, v20260805, revision 173bfd5 [DS/OL]. Hugging Face, 2026 [2026-11-23]. https://huggingface.co/deepmodelingcommunity/DPA4-OMat24/tree/173bfd5a26f90a756ee891777270ef117078d9be
## 附录　复核索引
原始文件计数与力分位数见 refs/ 下的脚本与 JSON。拟开展模式及阈值见 configs/model_experiments.yaml 和 experiments/cards/。样品预登记见 pilot/。复现 DES 使用 simulation/README.md 中的同一种子、配置与运行命令。基准结果、逐重复压缩表、配对区间、事件轨迹与甘特图在 simulation/outputs/。技术附录整合了上述字段定义、假设的来源类别和失败处理规则。
审计一项报告时，先按种子和政策筛选 event_trace.csv，再按 task_id 依次寻找 queued、started、completed_unreviewed 和 qc_released。XRD 或 EIS 的仪器工时取完成减开始，审核延迟取发布减完成。取消只允许发生在开始之前。复验样品标识为 IND，必须能追溯到新粉体的合成和相检。
复算政策效应时，从 monte_carlo.csv.gz 保留同一场景中每个政策共有的种子。没有在 480 h 内确认的队列将时间截为 480 h；逐种子相减后估计均值和蒙特卡洛误差。每确认费用则先汇总全队列费用和确认数，再取两者比值。比较口径、统计代码和原始行见 simulation/run_study.py。
冻结物理计算前，分别检查构型是否独立于训练数据、DFT 方法与元素顺序能否对齐、输入的样品指标属于晶内还是压片总响应。独立诊断、训练和最终验收的帧应登记不同用途。同一物理标签的哈希若跨训练与留出出现，须先解决泄漏再解释结果。
