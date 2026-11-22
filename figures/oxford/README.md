# Li₆PS₅Cl 的一个公开计算构型

图中 52 个球对应 24 Li（浅蓝 #6CADD7）、4 P（紫 #9659AF）、20 S（琥珀 #DEA43D）、4 Cl（青绿 #169780）。线画周期晶胞边，晶胞边长约 10.469 Å。球半径仅区分物种。图中没有键线，也没有使用单帧推断扩散、无序程度或实验物相。

**来源与许可**　Andrey Poletayev，University of Oxford，*Training data and models for molecular dynamics of Li6PS5Cl*，Zenodo，2026-10-08。原数据及随附的单帧摘录、据此生成的图以 CC BY 4.0 标注。改动为提取首帧、转写 JSON、居中平移坐标和正交球模型渲染。[原版本](https://doi.org/10.5281/zenodo.23226230)；[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。

- `first_frame.json` 取自 `datasets.zip / 230923_PBEsol_28100.extxyz` 的第 1 帧（index 0），含原始晶胞向量、导出坐标及原始力。整个 extxyz 成员 SHA-256 为 `551cbfc02708e6dfb13d8fd7a4ac3f9c16462e99bf5faa5eec7d8e90ccf94245`。
- `render_frame.py` 使用这 52 个原始坐标建场景。整体减去原胞中心，优化正交投影观察方向以减少遮挡；原子间距与晶胞矢量保留。Blender 5.3.0 生成 1280×1280 RGBA PNG 和可编辑 .blend。
- 复算命令为 `blender --background --factory-startup --python render_frame.py`。输出位于脚本同目录。`lpsc_52.png` 可用于幻灯片，`lpsc_52.blend` 可逐原子核查编号。
