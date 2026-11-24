# LPSC_Zhanghx

## P9 氯富集硫银锗矿的构型概率排序与研发决策

[文字版 PDF](p9/paper/开题报告_P9.pdf) · [可编辑 Word](p9/paper/开题报告_P9.docx) · [汇报 PDF](p9/paper/汇报版开题报告_P9.pdf) · [PowerPoint](p9/paper/汇报版开题报告_P9.pptx) · [AISI 逐页汇报词](p9/paper/P9_逐页汇报词.docx) · [技术附录](P9_技术附录.md) · [变更与复核](p9/复核与变更.md)

P9 在统一主工艺下比较 x=0.0–0.6 七种名义组成。先由相容构型族和实验结构约束获得加权晶内输运分布，再用独立新粉体压片评估宏观排序。研发调度器在质控发布后决定下一项行动。势的微调需要独立参考发现可改变行动的局域偏差，并且验收与重算须及时完成。

|证据|本版提供的结果|复核入口|
|---|---|---|
|公开测量|Mo 等补充表 S1 的 25 ℃ 七点，x=0.4 的点值 8.2 mS/cm 最高。单组七点没有独立批间误差|[证据目录](p9/evidence/README.md)|
|算法运行|合成结构观测的重加权、共享不确定度的优势/反向/并列概率和 ECDF|[概率排序](p9/ranking/README.md)|
|政策仿真|512 个配对基准队列及扩展压力、近似约束匹配和联合敏感性。基准中 Q 的首确认限制均时 48.15 h，H 为 58.55 h，但 H 漏诊局域势偏差较少|[新 DES](simulation/p9/README.md)|
|拟开展试验|结构及原子盲测、MD、样品区组、独立新批、模型运行验收|[实施协议](p9/protocol/VALIDATION.md)|

实际能力及预约仍按[宜宾调研](p9/evidence/YIBIN.md)和[现场校准登记](p9/evidence/site_calibration.csv)确认。系统配置中，长期设施能力与具体项目配方、预算、期限分别保存。

## 复现入口

从仓库根目录运行。概率示例依赖 NumPy，科研图另需 Matplotlib 和 Pillow。Word 及 PowerPoint 导出需要本机相应桌面应用和字体。

~~~powershell
python p9/ranking/run_demo.py
python -m unittest discover -s p9/ranking -p "test_*.py"
python simulation/p9/study.py --reps 512 --stress 128 --dev 64 --workers 8
python simulation/p9/constraints_sensitivity.py --workers 8
python simulation/p9/verify.py
python simulation/p9/register_parameters.py
python p9/protocol/create_protocol.py
python p9/figures/make_figures.py
python p9/paper/build_report.py
python p9/paper/build_briefing.py --export-pdf
python p9/paper/verify_p9.py
~~~

Word 正文构建源为 [章节 Markdown](p9/paper/manuscript.md)、[结果](p9/paper/results.md)、[增补参考文献](p9/paper/reference_additions.md)和已登记的章节插入文件。构建后保存[按引文首次出现编号的完整文稿](p9/paper/开题报告_P9_文稿.md)。P9 科研示意图提供 SVG、PNG 和可编辑 draw.io，数值图由公开摘录或实际运行 CSV 生成。

## P8 历史交付

P8 的文稿、原子研究说明和 24 候选 DES V0 结果仍可沿下列入口复核。P9 协议以 p9 目录和 simulation/p9 为准。

[P8 文字版](paper/开题报告_P8.pdf) · [P8 汇报版](paper/汇报版开题报告_P8.pdf) · [P8 技术附录](P8_技术附录.md) · [P8 DES V0](simulation/README.md) · [P8 文献综述表](refs/literature_review.csv)
