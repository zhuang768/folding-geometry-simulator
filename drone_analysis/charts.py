"""Publication images. Import only for runs that actually request charts."""

import re
import textwrap
from pathlib import Path


def create_charts(
    config, result, output: Path, run_tag, language="zh-TW", chart_directory=None
):
    if language not in ("zh-TW", "en"):
        raise ValueError("圖表語言僅支援 zh-TW 或 en")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib import font_manager
    from matplotlib.patches import Circle, Rectangle
    from matplotlib.text import Text

    from .geometry import ARMS, envelope
    from .localization import english_chart_labels

    project = Path(__file__).resolve().parents[2]
    candidates = [
        project / "報告/NotoSansCJKtc-Bold.otf",
        project / "報告/硬體報告製作紀錄/fonts/NotoSansCJKtc-Bold.otf",
        project / "報告/fonts/NotoSansCJKtc-Bold.otf",
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    ]
    font_family = "DejaVu Sans"
    if language == "zh-TW":
        font = next((p for p in candidates if p.is_file()), None)
        if font is None:
            raise ValueError(
                "找不到繁體中文字型，請保留專案的報告/NotoSansCJKtc-Bold.otf"
            )
        font_manager.fontManager.addfont(str(font))
        font_family = font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams.update(
        {
            "font.family": font_family,
            "font.size": 10,
            "axes.unicode_minus": False,
            "svg.fonttype": "path",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.prop_cycle": matplotlib.cycler(
                color=["#176B87", "#B45F29", "#56834C", "#775AA6"]
            ),
        }
    )
    directory = (
        Path(chart_directory) if chart_directory is not None else output / "圖表"
    )
    directory.mkdir()
    labels, english_filenames = (
        english_chart_labels(config, run_tag) if language == "en" else ({}, {})
    )
    paths = []
    g = config.geometry
    footer = (
        f"理論計算｜槳徑 {g.propeller_diameter_mm:g} mm｜轉軸間距 {g.hinge_width_mm:g} × {g.hinge_length_mm:g} mm"
        f"｜暫定間距 {g.required_clearance_mm:g} mm｜設定 {run_tag}"
    )

    def save(
        fig,
        filename,
        title,
        note="僅檢查理想平面槳盤間距；未驗證結構、氣流及飛行穩定性。",
    ):
        try:
            title_artist = fig.suptitle(title, fontsize=16, y=0.985)
            fig.text(
                0.5,
                0.075 if language == "en" else 0.047,
                footer,
                ha="center",
                fontsize=8,
            )
            note_artist = fig.text(
                0.5, 0.018, note, ha="center", fontsize=8, color="#555555"
            )
            if language == "en":
                for artist in fig.findobj(match=Text):
                    original = artist.get_text()
                    translated = labels.get(original, original)
                    if re.search(r"[\u3400-\u9fff]", translated):
                        raise ValueError(f"圖表尚有未翻譯文字：{original}")
                    artist.set_text(translated)
                note_artist.set_text(
                    textwrap.fill(
                        note_artist.get_text(), width=int(fig.get_figwidth() * 14)
                    )
                )
                title_artist.set_text(
                    textwrap.fill(labels[title], width=int(fig.get_figwidth() * 8))
                )
                filename = english_filenames[filename]
                title = labels[title]
            fig.tight_layout(rect=(0.02, 0.16, 0.98, 0.91))
            for extension in ("png", "svg"):
                fig.savefig(
                    directory / f"{filename}.{extension}", dpi=300, facecolor="white"
                )
            paths.append((filename, title))
        finally:
            plt.close(fig)

    for case in config.cases:
        fig, axes = plt.subplots(1, 2, figsize=(11, 6))
        shapes = [
            envelope(g, case.arm_length_mm, [angle] * 4)
            for angle in (case.expanded_angle_deg, case.folded_angle_deg)
        ]
        extent = max(max(s["width_mm"], s["length_mm"]) for s in shapes) / 2 + 30
        for ax, angle, shape in zip(
            axes, (case.expanded_angle_deg, case.folded_angle_deg), shapes
        ):
            ax.add_patch(
                Rectangle(
                    (-g.hinge_width_mm / 2, -g.hinge_length_mm / 2),
                    g.hinge_width_mm,
                    g.hinge_length_mm,
                    facecolor="#E8ECEF",
                    edgecolor="#475569",
                )
            )
            for (name, sx, sy), point in zip(ARMS, shape["points"]):
                hinge = (sx * g.hinge_width_mm / 2, sy * g.hinge_length_mm / 2)
                ax.plot(
                    [hinge[0], point[0]],
                    [hinge[1], point[1]],
                    color="#263A47",
                    linewidth=3,
                )
                ax.add_patch(
                    Circle(
                        point,
                        g.propeller_diameter_mm / 2,
                        facecolor="#176B8715",
                        edgecolor="#176B87",
                    )
                )
                ax.plot(*hinge, "o", color="#B45F29", markersize=4)
                ax.annotate(
                    name,
                    hinge,
                    xytext=(sx * 12, -sy * 12),
                    textcoords="offset points",
                    ha="right" if sx < 0 else "left",
                    va="top" if sy > 0 else "bottom",
                    fontsize=9,
                    backgroundcolor="white",
                )
                ax.plot(*point, "o", color="#176B87", markersize=3)
            ax.set(
                xlim=(-extent, extent),
                ylim=(-extent, extent),
                aspect="equal",
                xlabel="左右位置 x（mm）",
                ylabel="前後位置 y（mm）",
                title=f"角度 {angle:g}°\n外廓 {shape['width_mm']:.1f} × {shape['length_mm']:.1f} mm",
            )
        save(fig, f"01_{case.id}_構型", f"{case.label}：展開與收折的等比例俯視圖")

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.8))
    for case in config.cases:
        rows = [r for r in result["tables"]["angle_scan"] if r["case_id"] == case.id]
        angles = [r["folded_angle_deg"] for r in rows]
        for ax, key in zip(axes, ("folded_width_mm", "folded_length_mm")):
            (line,) = ax.plot(angles, [r[key] for r in rows], label=case.label)
            chosen = next(
                r for r in rows if r["folded_angle_deg"] == case.folded_angle_deg
            )
            ax.plot(case.folded_angle_deg, chosen[key], "o", color=line.get_color())
            ax.set(xlabel="四臂共同角度（度）", ylabel="外廓尺寸（mm）")
            ax.grid(alpha=0.2)
            ax.legend()
    axes[0].set_title("寬度隨角度變化")
    axes[1].set_title("長度隨角度變化")
    save(
        fig,
        "02_角度與外廓",
        "角度對機身寬度及長度的影響",
        "曲線包含未達槳盤間距的角度，不能整段當成可用範圍。",
    )

    lengths, angles = config.length_range.values(), config.angle_range.values()
    rows = result["tables"]["design_sweep"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    for ax, key, title in zip(
        axes,
        ("path_min_gap_mm", "robust_min_gap_mm"),
        (
            "名目角度，全路徑解析最小值",
            f"各臂角度誤差 ±{config.angle_error_deg:g}°，位置誤差 {config.position_error_mm:g} mm",
        ),
    ):
        values = np.array(
            [r[key] if r[key] is not None else np.nan for r in rows]
        ).reshape(len(lengths), len(angles))
        masked = np.ma.masked_invalid(values)
        mesh = ax.pcolormesh(
            angles,
            lengths,
            masked,
            shading="nearest",
            # A raster color field avoids seams between SVG cells; labels and
            # the clearance contour retain their vector representation.
            rasterized=True,
            cmap="RdYlBu",
            vmin=min(-20, g.required_clearance_mm - 30),
            vmax=g.required_clearance_mm + 40,
        )
        finite = values[np.isfinite(values)]
        if (
            len(lengths) > 1
            and len(angles) > 1
            and finite.size
            and finite.min() < g.required_clearance_mm < finite.max()
        ):
            ax.contour(
                angles,
                lengths,
                masked,
                levels=[g.required_clearance_mm],
                colors="black",
                linewidths=1,
            )
        for case in config.cases:
            if (
                case.expanded_angle_deg == config.sweep_expanded_deg
                and angles[0] <= case.folded_angle_deg <= angles[-1]
                and lengths[0] <= case.arm_length_mm <= lengths[-1]
            ):
                ax.plot(
                    case.folded_angle_deg,
                    case.arm_length_mm,
                    "o",
                    color="black",
                    markersize=4,
                )
        ax.set_facecolor("#D6D6D6")
        ax.set(xlabel="收折終點角度（度）", ylabel="機臂長度（mm）", title=title)
        fig.colorbar(mesh, ax=ax, label="最小槳盤間距／保守下界（mm）")
    save(
        fig,
        "03_設計可行區域",
        f"臂長與收折角度掃描：展開角度固定 {config.sweep_expanded_deg:g}°",
        "黑線為暫定門檻；黑點限相同展開角且位於掃描範圍的方案；灰色表示超出誤差模型。",
    )

    fig, axes = plt.subplots(
        len(config.cases), 1, figsize=(11, 3.2 * len(config.cases) + 1.8), squeeze=False
    )
    for case, ax in zip(config.cases, axes[:, 0]):
        rows = [
            r
            for r in result["tables"]["motion"]
            if r["case_id"] == case.id
            and r["direction"] == "fold"
            and r["scenario"] == "staggered"
        ]
        for key in rows[0]:
            if key.endswith("_gap_mm") and key != "min_gap_mm":
                ax.plot(
                    [r["time_s"] for r in rows],
                    [r[key] for r in rows],
                    label=key.replace("_gap_mm", "").upper(),
                )
        ax.axhline(
            g.required_clearance_mm, color="#A33030", linestyle="--", label="暫定門檻"
        )
        ax.set(title=case.label, xlabel="模擬時間（秒）", ylabel="槳盤間距（mm）")
        ax.legend(ncol=4, fontsize=8)
        ax.grid(alpha=0.2)
    save(
        fig,
        "04_不同步六組槳隙",
        "假設不同步收折：六組槳盤間距的取樣時間序列",
        "圖為指定動作的離散取樣；全角度範圍判定另使用解析界線。",
    )

    for case in config.cases:
        fig, axes = plt.subplots(1, 3, figsize=(13, 5.5))
        rows = [
            r
            for r in result["tables"]["motion"]
            if r["case_id"] == case.id
            and r["direction"] == "fold"
            and r["scenario"] == "staggered"
        ]
        for ax, suffix, ylabel in zip(
            axes,
            ("angle_deg", "speed_deg_s", "acceleration_deg_s2"),
            ("角度（度）", "角速度（度／秒）", "角加速度（度／秒²）"),
        ):
            for i in range(1, 5):
                ax.plot(
                    [r["time_s"] for r in rows],
                    [r[f"p{i}_{suffix}"] for r in rows],
                    label=f"P{i}",
                )
            ax.set(xlabel="模擬時間（秒）", ylabel=ylabel)
            ax.legend()
            ax.grid(alpha=0.2)
        save(
            fig,
            f"05_{case.id}_收折動作",
            f"{case.label}：假設五次平滑曲線的收折動作",
            "包含設定的四臂啟動延遲；角度曲線是規劃值，不是伺服實際量測。",
        )

    fig, ax = plt.subplots(figsize=(10, 5.8))
    for case in config.cases:
        rows = [
            r for r in result["tables"]["angle_sensitivity"] if r["case_id"] == case.id
        ]
        ax.plot(
            [r["angle_error_deg"] for r in rows],
            [
                r["clearance_lower_bound_mm"] if r["supported"] else float("nan")
                for r in rows
            ],
            label=case.label,
        )
    ax.axhline(
        g.required_clearance_mm, color="#A33030", linestyle="--", label="暫定間距門檻"
    )
    ax.set(
        xlabel="每支機臂各自的角度誤差上限 ±（度）", ylabel="全角度範圍槳隙下界（mm）"
    )
    ax.legend()
    ax.grid(alpha=0.2)
    save(
        fig,
        "06_角度誤差敏感度",
        "角度誤差如何影響最小槳盤間距",
        f"位置誤差上限固定 {config.position_error_mm:g} mm；曲線斷開處表示超出0至90度模型。",
    )

    fig, ax = plt.subplots(figsize=(10, 5.8))
    for case in config.cases:
        rows = [
            r
            for r in result["tables"]["angle_scan"]
            if r["case_id"] == case.id and r["nominal_pass"]
        ]
        if rows:
            ax.plot(
                [r["folded_width_mm"] for r in rows],
                [r["folded_length_mm"] for r in rows],
                label=case.label,
            )
    ax.set(xlabel="理想槳盤外廓寬度（mm）", ylabel="理想槳盤外廓長度（mm）")
    if ax.lines:
        ax.legend()
    ax.grid(alpha=0.2)
    save(
        fig,
        "07_寬度與長度取捨",
        "符合名目槳盤間距的寬度與長度取捨",
        "僅篩選名目間距；不代表完整開口穿越或飛行已驗證。",
    )
    return paths
