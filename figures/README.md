# 科研图与数据来源
|图组|数据身份|可编辑源和再生成方式|
|---|---|---|
|多晶压片及电极爆炸视图|本项目概念模型。几何、晶粒形貌、颜色、间距均为示意|blender/pellet.blend，Blender 5.3；pellet.py 重建，pellet.png 为透明背景渲染|
|Oxford 的 52 原子周期胞|Poletayev 公开的计算构型第一帧；有原始坐标与外部许可|oxford/ 含单帧、坐标模型、渲染和归属说明；颜色区分元素，图不推断化学键|
|势模型、梯度、物理尺度、证据发布|据锁定实现与研究设计重绘|architecture、gradient、levels、release 各有 .drawio、.svg、.png；draw.io 可编辑关系，make_diagrams.py 共用坐标与标签生成各格式|
|参考力分位数|Oxford 原始 DFT 标签复算。两点表示中位和 P90|plot_forces.py 读取 refs/oxford_force_profile.json，输出 force_profile.svg 与 PNG|
|政策比较、甘特图、事件泳道、资源利用、费用与时效、压力测试|DES V0 及变体的实际程序输出，全部属于情景模拟|simulation/plot_results.py 和 simulation/outputs/ 中对应 SVG、PNG、CSV|
不可把封面晶粒、随机日程或样品计划读成真实测量。编辑科研图时同时维护图注、统计分母、数据版本和引用。

