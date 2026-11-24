"""Draw editable workflows and plot only the recorded evidence and synthetic outputs."""
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import ListedColormap
import numpy as np

HERE = Path(__file__).resolve().parent
P9 = HERE.parent
ROOT = P9.parent
sys.path.insert(0, str(ROOT / "figures"))
import make_diagrams as renderer
from make_diagrams import box, edge

TEAL, BLUE, OCHRE, INK = "#11796C", "#315B8B", "#AE632C", "#243940"
face = next(name for name in ("SimHei", "Noto Sans CJK SC")
            if name in {font.name for font in font_manager.fontManager.ttflist})
plt.rcParams.update({
    "font.family": face, "font.size": 11, "axes.unicode_minus": False,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.labelcolor": INK, "text.color": INK, "svg.fonttype": "none",
})


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def save(fig, stem):
    for extension in ("svg", "png"):
        fig.savefig(HERE / f"{stem}.{extension}", dpi=190,
                    facecolor="white", bbox_inches="tight", pad_inches=.12)
    plt.close(fig)


def two_lanes(stem, title, first, second, links):
    nodes = []
    for lane_id, lane in enumerate((first, second)):
        for i, (label, subtext, color) in enumerate(lane):
            nodes.append(box(16 + 303 * i, 54 + 201 * lane_id, 258, 99,
                             label, subtext, color))
    renderer.generate(stem, title, nodes, links, title_size=26, detail_size=23, two_line=True)


def workflows():
    renderer.OUT = HERE
    renderer.H = 378
    renderer.BOLD = str(Path(renderer.FONT).with_name("simhei.ttf")) if sys.platform == "win32" else renderer.BOLD
    row = [edge(i, i+1) for i in (0, 1, 2, 4, 5, 6)]
    two_lanes("pipeline", "构型加权输运与压片证据",
              [("七种名义组成", "Li / P / S / Cl 整数计量", "gray"),
               ("相容构型族", "S / Cl 占位与 Li 空位", "blue"),
               ("统一 DPA4 与轨迹", "每族独立采样集体输运", "blue"),
               ("配方晶内分布", "构型加权 · 优胜 · 并列", "teal")],
              [("标准工艺独立粉体", "批次为实验单位", "gray"),
               ("结构与样品条件", "相、成分、密度、接触", "gold"),
               ("标准条件 EIS", "压片总电导与测量区间", "gold"),
               ("宏观决策对照", "共享配方 · 外部一致性", "teal")],
              row + [edge(5, 1, "tb", True), edge(3, 7, "bt", True)])
    two_lanes("weights", "先验与结构证据重加权",
              [("结构假说", "整数计量、相与局域约束", "gray"),
               ("热历史与相对能", "整胞 ΔF、有效冻结温度", "blue"),
               ("归一化先验", "简并度、提议概率、支持集", "blue"),
               ("重加权族分布", "BME 点解与权重区间", "teal")],
              [("结构表征", "XRD、NMR、中子、总散射", "gold"),
               ("前向观测及误差", "按仪器、相和相关性建模", "blue"),
               ("多解与权重诊断", "留出误差、ESS、敏感性", "teal"),
               ("输出或补证", "支持不足时扩充假说", "gray")],
              row + [edge(1, 5, "bt"), edge(6, 2, "tb", True), edge(3, 7, "bt")])
    two_lanes("transfer", "从排序分歧到版本发布",
              [("概率排序分歧", "定位贡献最大的结构族", "gray"),
               ("竞争原因", "物相、权重、采样、样品、势", "gold"),
               ("分层诊断", "XRD、短 MD、复测、DFT", "blue"),
               ("信息进入决策", "证据发布及未冻结窗口", "teal")],
              [("独立 DFT 超差", "同构型局域力和相对能", "gold"),
               ("计算行动价值", "稀有迁移帧与同预算补标", "blue"),
               ("验收并放行", "源域、盲测、MD、部署", "teal"),
               ("选择性重算", "按受影响依赖 · 可回滚", "teal")],
              row + [edge(0, 4, "bt", True), edge(7, 3, "tb", True)])
    two_lanes("network", "实验与算力共享的行动网络",
              [("制备与分样", "炉台、人力、样品消耗", "gold"),
               ("物相与成分", "XRD 槽 · 审核发布", "gold"),
               ("主条件 EIS", "压片、EIS 槽、装夹", "gold"),
               ("独立新批确认", "重复制备与最终判据", "teal")],
              [("结构支持与外送", "构型权重或局域表征", "blue"),
               ("短 MD 或扩样", "共享 GPU、预留与返工", "blue"),
               ("独立 DFT 检查", "DFT 槽、参考质量", "blue"),
               ("适配与重算", "GPU、质控和冻结窗口", "teal")],
              row + [edge(5, 1, "tb", True), edge(2, 6, "bt", True)])
    two_lanes("two_simulations", "规划与评价的两层事件过程",
              [("当前信息状态", "仅已发布信念及可见队列", "gray"),
               ("条件未来分支", "待发布及备选动作", "blue"),
               ("时间与发布预测", "队列、审核、动作可用性", "blue"),
               ("执行可行首步", "提交、并行、等待或停止", "teal")],
              [("共同潜在情景", "稳定键随机数、外层真值", "gold"),
               ("完整事件重放", "五类观测各自发布", "blue"),
               ("候选与费用终点", "确认、风险、资源", "teal"),
               ("配对政策比较", "同种子差值与重复区间", "teal")],
              row + [edge(7, 3, "tb", True)])


def mo_curve():
    records = rows(P9 / "evidence/mo_s1.csv")
    xs = [float(r["x"]) for r in records]
    ys = [float(r["sigma_mS_cm"]) for r in records]
    fig, ax = plt.subplots(figsize=(8.7, 4.0), layout="constrained")
    ax.plot(xs, ys, color=TEAL, linewidth=2, marker="o", markersize=7, zorder=3)
    peak = max(zip(ys, xs))
    ax.scatter([peak[1]], [peak[0]], s=190, color="#C7E7DF", zorder=2, edgecolor="none")
    for x, y in zip(xs, ys):
        ax.annotate(f"{y:.1f}", (x, y), xytext=(0, 10),
                    textcoords="offset points", ha="center", fontsize=12)
    ax.set(xlabel="名义氯取代量 x", ylabel="25 ℃ 压片总电导（mS/cm）",
           xticks=xs, ylim=(3.15, 9.0), xlim=(-.03, .63))
    ax.grid(axis="y", alpha=.22, zorder=0)
    ax.text(.01, .97, "Mo 等 · 补充 Table S1", transform=ax.transAxes, va="top")
    save(fig, "mo_curve")


def rank_figures():
    output = P9 / "ranking/outputs"
    comparisons = [r for r in rows(output / "pairwise.csv")
                   if r["method"] == "bme" and r["primary_delta"] == "true"]
    compositions = sorted({r["x_a"] for r in comparisons}, key=float)
    indices = {x: i for i, x in enumerate(compositions)}
    p = np.full((7, 7), np.nan)
    for r in comparisons:
        a, b = indices[r["x_a"]], indices[r["x_b"]]
        if a != b:
            p[a, b] = float(r["p_plus"])
    direction = [r for r in rows(output / "public_direction.csv")
                 if r["method"] == "bme" and float(r["historical_margin_mS_cm"]) == 0]
    statuses = {"undetermined": (0, "未决"), "agree": (1, "同向"), "conflict": (2, "反向")}
    conflict = np.full((7, 7), np.nan)
    notes = {}
    for r in direction:
        key = (indices[r["x_a"]], indices[r["x_b"]])
        status, label = statuses[r["comparison"]]
        conflict[key] = status
        notes[key] = f"{label}\n{float(r['p_supporting_historic_point']):.2f}"
    fig, axes = plt.subplots(1, 2, figsize=(10.3, 4.7), layout="constrained")
    maps = [axes[0].imshow(p, cmap="PuBuGn", vmin=0, vmax=1),
            axes[1].imshow(conflict, cmap=ListedColormap(["#EAF0F2", "#BFDED0", "#F2CFAC"]),
                           vmin=-.5, vmax=2.5)]
    for ax, title in zip(axes, ("(a) 合成晶内优势概率", "(b) 合成预测与历史点值方向")):
        ax.set(xticks=range(7), yticks=range(7), xticklabels=compositions,
               yticklabels=compositions, xlabel="组成 B 的 x", ylabel="组成 A 的 x")
        ax.set_title(title, loc="left", fontsize=15, pad=12)
    for a in range(7):
        for b in range(7):
            if np.isfinite(p[a, b]):
                axes[0].text(b, a, f"{p[a,b]:.2f}", ha="center", va="center",
                             color="white" if p[a,b] > .62 else INK, fontsize=10)
    for (a, b), label in notes.items():
        axes[1].text(b, a, label, ha="center", va="center", fontsize=10)
    fig.colorbar(maps[0], ax=axes[0], orientation="horizontal", fraction=.055, pad=.13,
                 label="P(A 的相对输运高于 B 超过 10%)")
    axes[1].text(.5, -.25, "21 个共享历史点对 · 概率来自合成输入",
                 transform=axes[1].transAxes, ha="center")
    save(fig, "probability_matrix")
    for matrix, stem in ((p, "prob_advantage"), (conflict, "prob_conflict")):
        fig, ax = plt.subplots(figsize=(5.3, 4.8), layout="constrained")
        ax.set(xticks=range(7), yticks=range(7), xticklabels=compositions,
               yticklabels=compositions, xlabel="组成 B 的 x", ylabel="组成 A 的 x")
        if stem == "prob_advantage":
            heat = ax.imshow(matrix, cmap="PuBuGn", vmin=0, vmax=1)
            for a, b in zip(*np.where(np.isfinite(matrix))):
                ax.text(b, a, f"{matrix[a,b]:.2f}", ha="center", va="center",
                        color="white" if matrix[a,b] > .62 else INK, fontsize=12)
            fig.colorbar(heat, ax=ax, fraction=.05, pad=.035, label="合成优势概率")
        else:
            ax.imshow(matrix, cmap=ListedColormap(["#EAF0F2", "#BFDED0", "#F2CFAC"]),
                       vmin=-.5, vmax=2.5)
            for (a, b), label in notes.items():
                ax.text(b, a, label, ha="center", va="center", fontsize=10.5)
        save(fig, stem)

    records = [r for r in rows(output / "weighted_ecdf.csv") if r["method"] == "bme"]
    fig, ax = plt.subplots(figsize=(8.7, 4.0), layout="constrained")
    colors = ("#425863", "#806695", "#A46230", "#416D9B", "#11796C", "#A23F50", "#526C2D")
    for x, color in zip(compositions, colors):
        part = [r for r in records if r["x"] == x]
        ax.step([float(r["log_relative_transport"]) for r in part],
                [float(r["ecdf"]) for r in part], where="post", label=x, color=color, lw=1.65)
    ax.legend(title="名义 x", ncols=7, frameon=False, loc="upper center")
    ax.set(xlabel="自然对数相对输运（合成）", ylabel="构型加权累积概率", ylim=(0, 1.16))
    ax.grid(axis="y", alpha=.2)
    save(fig, "weighted_ecdf")


def policy_figures():
    output = ROOT / "simulation/p9/outputs"
    policies = ["F", "G", "B", "Q", "H", "H-fit"]
    summaries = {(r["policy"], r["metric"]): r for r in rows(output / "policy_summary.csv")
                 if r["scenario"] == "baseline" and r["setting"] == "default"}
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 4.2), sharey=True, layout="constrained")
    for ax, (metric, title, unit, scale) in zip(axes, (
        ("restricted_h", "(a) 限制均时", "小时", 1),
        ("cost", "(b) 全队列费用", "千情景元", .001),
        ("recall", "(c) 真合格召回", "%", 100),
    )):
        for j, policy in enumerate(policies):
            row = summaries[policy, metric]
            m, lo, hi = [scale * float(row[k]) for k in ("mean", "lo95", "hi95")]
            c = TEAL if policy == "Q" else OCHRE if policy == "H-fit" else BLUE
            ax.errorbar(m, j, xerr=[[m-lo], [hi-m]], fmt="D" if j >= 4 else "o",
                        markersize=6, capsize=3, color=c)
        ax.set_title(title, loc="left", fontsize=14)
        ax.set(yticks=range(6), yticklabels=policies, xlabel=unit, ylim=(5.55, -.55))
        ax.grid(axis="x", alpha=.22)
    fig.suptitle("P9 基准情景 · 512 个配对七组成队列 · 点为均值，线为 95% 区间", fontsize=13)
    save(fig, "policy_results")

    paired = {(r["scenario"], r["action"], r["reference"], r["metric"]): r
              for r in rows(output / "paired_effects.csv") if r["setting"] == "default"}
    fig, axes = plt.subplots(1, 2, figsize=(10.9, 4.65), layout="constrained")
    sets = [
        ("(a) H-fit 相对 H", "全队列费用差（情景元）", "cost",
         [(name, "H-fit", "H", label) for name, label in [
             ("baseline", "基准"), ("fixed_adequate", "固定势充分"),
             ("zero_gain", "适配零收益"), ("negative_gain", "适配负收益"),
             ("slow_dft_fit", "DFT / 训练缓慢"), ("early_freeze", "冻结提前")]]),
        ("(b) 基准事件机制", "首次确认限制均时差（h）", "restricted_h",
         [("baseline", "H", "Q", "二步 H - 单步 Q"),
          ("baseline", "H", "H-nostate", "H - 隐去队列"),
          ("baseline", "H", "H-serial", "H - 关闭并行")])
    ]
    for ax, (title, label, metric, selection) in zip(axes, sets):
        ticks = []
        for i, (scenario, action, reference, name) in enumerate(selection):
            r = paired[scenario, action, reference, metric]
            d, lo, hi = (float(r[k]) for k in ("delta", "lo95", "hi95"))
            ax.errorbar(d, i, xerr=[[d-lo], [hi-d]], fmt="D",
                        capsize=3, markersize=6, color=OCHRE if d > 0 else TEAL)
            ticks.append(name)
        ax.set_title(title, loc="left", fontsize=14)
        ax.set(yticks=range(len(ticks)), yticklabels=ticks, xlabel=label,
               ylim=(len(ticks) - .5, -.5))
        ax.axvline(0, color="#A6B2B7", linestyle="--", linewidth=1)
        ax.grid(axis="x", alpha=.2)
    fig.suptitle("情景评价 · 政策差值与 95% 配对重复区间", fontsize=13)
    save(fig, "paired_results")


def event_swimlane():
    records = [r for r in rows(ROOT / "simulation/p9/outputs/event_trace.csv")
               if r["seed"] == "481184" and r["policy"] == "H-fit"]
    spec = [("0.2", "dft", "x=0.2 · 独立 DFT"),
            ("0.2", "fit", "x=0.2 · 定向适配"),
            ("0.1", "confirm", "x=0.1 · 独立新批"),
            ("0.6", "redo", "x=0.6 · 版本重算")]
    fig, ax = plt.subplots(figsize=(11.1, 3.55), layout="constrained")
    for y, (x, action, _) in enumerate(spec):
        items = [r for r in records if r["x"] == x and r["action"] == action]
        start = next(float(i["t"]) for i in items if i["event"] == "submitted")
        end = next(float(i["t"]) for i in items if i["event"] == "qc_released")
        ax.barh(y, end-start, left=start, height=.43, color="#DDE5E7")
        for r in items:
            if r["event"] != "stage_start":
                continue
            done = next(i for i in items if i["task"] == r["task"] and i["stage"] == r["stage"]
                        and i["event"] == "stage_done")
            st = float(r["t"])
            ax.barh(y, float(done["t"])-st, left=st, height=.43,
                    color=OCHRE if r["resource"] == "review" else BLUE)
        ax.scatter([end], [y], color=TEAL, marker="D", s=42, zorder=4)
        ax.annotate(f"{end:.2f}", (end, y), xytext=(7, 0), textcoords="offset points", va="center")
    ax.axvline(79, color="#A0444A", ls="--", lw=1)
    ax.text(79.2, -.49, "x=0.2 冻结", va="bottom", color="#A0444A", fontsize=9)
    ax.set(xlim=(28, 86), xlabel="队列时钟（h）", yticks=range(4),
           yticklabels=[s[2] for s in spec], ylim=(3.6, -.78))
    ax.grid(axis="x", alpha=.2)
    ax.set_title("情景种子 481184 · H-fit · 等待、执行、审核与发布", loc="left", fontsize=13)
    save(fig, "swimlane")


if __name__ == "__main__":
    workflows()
    mo_curve()
    rank_figures()
    if (ROOT / "simulation/p9/outputs/policy_summary.csv").is_file():
        policy_figures()
        event_swimlane()
