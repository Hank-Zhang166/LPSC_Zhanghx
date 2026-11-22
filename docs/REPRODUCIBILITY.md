# 从公开材料复核 P8
本页是研究与交付的运行入口。所列命令在项目根目录执行，保留已有输出时将新一轮指向其他目录。每次记录输入哈希、运行环境、随机种子与结果差异。

## 公开材料审计
按 configs/dataset_manifest.csv 逐项取得相应版本；原始数据与权重不随本项目分发。使用 refs/ 中的审计脚本（帮助入口 --help），将输出与同名 json 中的文件或成员 SHA-256、计数、唯一块及分位数比较。下游把模型预测与参考标签在同一 frame_id 上比较。以原子出现数为分母的标签分布不构成独立测试集。
## DES
按 ../simulation/README.md 的标准库命令复核。基准种子起点 731900。逐重复 CSV、成对均值差、相对差、区间、资源谱系与完整样例事件日志在 simulation/outputs。默认复算参数必须与元数据一致。系统参数校准后为情景分配新 ID，不覆盖归档 V0。
## 图与报告
用 Python 3 安装 python-pptx、python-docx、Pillow 与 matplotlib，按脚本的字体参数提供合适的中文字体。已导出的图表随库提供，编辑文字无需重新安装 Blender。若重画其他图形，执行以下命令。
~~~sh
python figures/make_diagrams.py
python figures/plot_forces.py
python simulation/plot_results.py
blender --background --python figures/blender/pellet.py
blender --background --python figures/oxford/render_frame.py
python paper/build_briefing.py
~~~
在 Windows 有 PowerPoint 时运行 paper/export_briefing.ps1 导出同版 PDF；Word 稿与讲稿可直接编辑。书面报告由 paper/manuscript.md、paper/manuscript_des.md 及数值 CSV 生成，具体入口见 paper/build_manuscript.py。更改汇报页序或脚本后须同步重新生成讲稿，再逐页检查。版面中的源图有 SVG、绘图程序或原生 draw.io，与 presentation 的可编辑表格互补。
## 新实验与审批
实验卡是拟议协议。数据许可、算力、DFT 口径、湿实验 SOP 和密封/转运条件在具体场地确认。不会用规划的样品编号或仿真事件向注册表写入虚构的实测。验收由独立记录及版本对齐完成。

