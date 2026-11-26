# 参与 P9 研究

欢迎从一条可复核的改进开始。数据勘误可以在 [Issues](https://github.com/Hank-Zhang166/LPSC_Zhanghx/issues) 说明出处、表号、单位和受影响的记录。提交代码或文稿时，从 `main` 建分支，在 Pull Request 中说明改变了哪个研究判断、如何复核，以及报告或图中哪些结论受到影响。

## 找到要改的源文件

| 想改什么 | 从这里开始 | 改完怎样检查 |
| --- | --- | --- |
| 公开测量或数据覆盖 | [证据目录](p9/evidence/README.md)。登记 DOI、版本、测量温度、样品或计算批次，以及允许的用途。 | 复核同一来源内的组别与单位。历史电导点值有变动时，重跑 `python p9/evidence/ordering_robustness.py`，核对排序边界，并检查下游算例。 |
| 构型权重或配方排序 | [排序模型](p9/ranking/model.py)和[合成算例](p9/ranking/run_demo.py)。 | 运行排序单测，再用 `python p9/ranking/run_demo.py --output preview/ranking` 生成独立候选输出。正式刷新先验后，重新评价使用它的政策。 |
| 实验行动、资源或调度政策 | [实验协议](p9/protocol/VALIDATION.md)、[项目参数](simulation/redesign/project.json)、[工位配置](simulation/redesign/lab.json)和[规划器](simulation/redesign/planning.py)。 | 从相同候选和随机种子比较政策，分别报告投入、确认和误判。按照[仿真说明](simulation/redesign/README.md)刷新主试验、敏感性、参数表和验证记录。 |
| 正文、公式或汇报 | [正文源](p9/revision_text/report.md)、[公式源](p9/revision_text/equations.json)、[逐页讲稿源](p9/paper/speaker_script.json)。 | 先导出预览。正式稿更新时，同步核对 PDF、可编辑文档、讲稿及幻灯片备注。 |
| 图、图注或表格 | [图清单](p9/revision_visuals/manifest.json)、[科研制图入口](p9/revision_visuals/build.py)。 | 数值图按来源 CSV 重绘，核对轴、单位和样本量。架构图同时保留可编辑源。 |

## 复现环境

在仓库根目录执行。日常数值检查可用独立虚拟环境。

~~~bash
python -m venv .venv
~~~

Windows PowerShell 用 `.\.venv\Scripts\Activate.ps1` 激活，macOS 或 Linux 用 `source .venv/bin/activate`。随后运行 [README 的复核命令](README.md#在本地复核)。GitHub Actions 在面向 `main` 的 Pull Request 和 `main` 推送上执行轻量检查，包括公开点值的排序边界、概率模型单测、仿真回放和已发布文档的一致性。

完整政策试验会写入 `simulation/redesign/outputs`。在独立分支或另一份检出运行，保留旧提交以比较差异。仿真金额、时长与隐状态参数均属于情景设定；实测数据、合成输入和待验假设请在字段及图注中注明来源。配对区间度量有限次重复的误差，跨参数情景的变化另行报告。

## 重绘与排版

仅核对已发布成稿时，直接运行 `python p9/paper/verify_p9.py`。需要修改图文时，先安装[图文构建依赖](p9/paper/requirements.txt)。

~~~bash
python -m pip install -r p9/paper/requirements.txt
python p9/revision_visuals/build.py --model
python p9/paper/build_report.py --out preview/written
python p9/paper/build_briefing.py --export-pdf --out preview/briefing
~~~

绘图使用微软雅黑、黑体或 Noto Sans CJK SC。Word 数学转换使用 Office 的 MML2OMML.XSL，正式 PDF 使用 Windows 桌面版 Word 和 PowerPoint。可用 `--template` 指定学校模板。Blender 封面有随仓渲染图，改三维场景时可运行 `blender -b -P p9/revision_visuals/cover_render.py`。

正文中的历史点值扰动表来自[历史排序分析](p9/evidence/ordering_insert.md)，第 7 章结果来自[政策试验结果](simulation/redesign/results.md)。新增引文时，把条目写入[书目源](p9/revision_text/references.md)，在对应论点处引用其键。合成后的[在线全文](p9/paper/开题报告_P9_文稿.md)供阅读。若先在 Word 或 PowerPoint 中修改过内容，重新构建前应将需要保留的改动同步回相应写作源。

预览确认后，在构建命令中省略 `--out` 更新[正式交付稿](p9/交付稿)，再运行 `python p9/paper/verify_p9.py`。提交改动时一并列出所用命令、输入或种子，以及尚待实验确认的问题。第三方原始数据的归属和下载位置见[来源说明](THIRD_PARTY_NOTICES.md)。
