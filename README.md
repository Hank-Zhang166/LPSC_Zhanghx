# 氯富集硫银锗矿的概率排序与资源受限研发决策

[文字版 PDF](p9/交付稿/开题报告_P9.pdf) · [可编辑 Word](p9/交付稿/开题报告_P9.docx) · [汇报 PDF](p9/交付稿/汇报版开题报告_P9.pdf) · [PowerPoint](p9/交付稿/汇报版开题报告_P9.pptx) · [逐页汇报词](p9/交付稿/P9_逐页汇报词.docx)

项目研究七个名义组成在相同主要工艺下的研发决策。Mo 等的公开压片数据中，x＝0.4 的室温总电导高于 0.5。若计算倾向相反，应该先查构型权重、轨迹、样品还是局域势误差？新版本用这一对组成解释概率排序，再让全体七种组成在给定资源日历内竞争一个独立确认名额。

| 想复核什么 | 到哪里看 |
| --- | --- |
| 哪些是实测，哪些仍缺数据 | [证据登记](p9/evidence/README.md)、[历史点值的扰动边界](p9/evidence/ordering_stress.csv)、[宜宾现场待核实项](p9/evidence/site_calibration.csv) |
| 七组成如何从构型得到分布 | [排序算法与合成算例](p9/ranking/README.md)、[每个配方对的三种概率](p9/ranking/outputs/pairwise.csv) |
| 单个确认名额如何分配 | [本次重构的仿真](simulation/redesign/README.md)、[主表](simulation/redesign/outputs/policy_summary.csv)、[配对差](simulation/redesign/outputs/paired_effects.csv)、[事件回放](simulation/redesign/outputs/events.csv) |
| 哪些研究还需要现场与计算支持 | [预注册与独立验收](p9/protocol/VALIDATION.md)、[DPA4及标签检查](p9/evidence/DPA4_AND_LABELS.md)、[技术附录](P9_技术附录.md) |
| 本次逐项改了什么 | [修订和验证记录](p9/复核与变更.md) |

## 下一次迭代

只读或手工修改正式稿，打开 [交付稿](p9/交付稿)。正文的可复现写作入口是 [report.md](p9/revision_text/report.md)，九个编号式的数学源在 [equations.json](p9/revision_text/equations.json)。第 2 章的公开点值敏感性与第 7 章的仿真结果分别引入 [历史扰动分析](p9/evidence/ordering_insert.md) 和 [政策结果](simulation/redesign/results.md)。[图题和来源](p9/revision_visuals/manifest.json)由正文和科研图共用。[逐页稿源](p9/paper/speaker_script.json)同时写入 PowerPoint 备注与讲稿 Word。

直接在 Word 或 PowerPoint 做过修改时，先将修改保存到版本历史，并把需要长期保留的内容同步回对应源文件。重新构建会替换交付稿中的同名文件。可先用 `python p9/paper/build_report.py --out 预览` 生成候选正文，核对后再更新正式稿。教师姓名和职称可用 `--adviser "姓名 职称"` 写入封面。

按需从仓库根目录运行相应阶段。数值部分使用 Python 与 NumPy；科研图使用 Matplotlib、Pillow 和各图构建脚本所列依赖。正式稿使用 python-docx、python-pptx、Pillow、lxml、latex2mathml（本次 3.79.0）、pypdf，及装有黑体、宋体和 Cambria Math 的 Windows Word/PowerPoint。公式通过 Office 自带的 MML2OMML.XSL 生成。首次从空产物构建可用 `--template` 指定学校原版模板。

~~~powershell
python p9/evidence/ordering_robustness.py
python p9/ranking/run_demo.py
python -m unittest discover -s p9/ranking -p "test_*.py"
python simulation/redesign/run_study.py --workers 8
python simulation/redesign/sensitivity.py --workers 8
python simulation/redesign/fit_fixture.py
python simulation/redesign/register.py
python simulation/redesign/verify.py
python p9/revision_visuals/build.py --model
python p9/paper/build_report.py
python p9/paper/build_briefing.py --export-pdf
python p9/paper/verify_p9.py
~~~

若检验的是政策效果，应按上述次序核对配置、运行结果、正文数字与图；仅修改文字时可直接复用已归档且有来源的结果表。冻结的首轮研究包括两个七组成筛查区组和两个入围配方的独立确认。本次情景仿真专门检验其中资源收紧到单个名额时的决策。

[上一版 P9](https://github.com/Hank-Zhang166/LPSC_Zhanghx/tree/00a3827001f9f4075add2a0761a18051560a1e97)和[P8](https://github.com/Hank-Zhang166/LPSC_Zhanghx/tree/10ed7881d2509c814581bdd6659f6d2ac129c099)可按快照追溯；旧七候选仿真在 `simulation/p9`，24 候选历史试验在 `simulation/outputs`。
