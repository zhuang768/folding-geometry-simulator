"""English chart text, kept separate from numerical calculations."""

from .geometry import envelope


def english_chart_labels(config, run_tag):
    g = config.geometry
    labels = {
        "左右位置 x（mm）": "Lateral position x (mm)",
        "前後位置 y（mm）": "Longitudinal position y (mm)",
        "四臂共同角度（度）": "Common arm angle (°)",
        "外廓尺寸（mm）": "Planform dimension (mm)",
        "寬度隨角度變化": "Planform width",
        "長度隨角度變化": "Planform length",
        "角度對機身寬度及長度的影響": "Effect of arm angle on planform width and length",
        "曲線包含未達槳盤間距的角度，不能整段當成可用範圍。": "Curves include angles below the clearance threshold; not every plotted angle is feasible.",
        "名目角度，全路徑解析最小值": "Nominal angles: analytical full-range minimum",
        "收折終點角度（度）": "Folded angle (°)",
        "機臂長度（mm）": "Arm length (mm)",
        "最小槳盤間距／保守下界（mm）": "Minimum clearance / conservative lower bound (mm)",
        "黑線為暫定門檻；黑點限相同展開角且位於掃描範圍的方案；灰色表示超出誤差模型。": "Black line: provisional threshold. Dots: cases with the same deployed angle, within the sweep. "
        "Gray: outside the uncertainty model.",
        "暫定門檻": "Provisional threshold",
        "模擬時間（秒）": "Simulated time (s)",
        "槳盤間距（mm）": "Rotor disk clearance (mm)",
        "假設不同步收折：六組槳盤間距的取樣時間序列": "Assumed folding with staggered starts: six rotor pair clearances",
        "圖為指定動作的離散取樣；全角度範圍判定另使用解析界線。": "Sampled trajectories for the specified delays; full-range clearance is verified separately by analytical bounds.",
        "角度（度）": "Angle (°)",
        "角速度（度／秒）": "Angular velocity (°/s)",
        "角加速度（度／秒²）": "Angular acceleration (°/s²)",
        "包含設定的四臂啟動延遲；角度曲線是規劃值，不是伺服實際量測。": "Includes the four configured start delays. Planned trajectories, not measured servo responses.",
        "暫定間距門檻": "Provisional clearance threshold",
        "每支機臂各自的角度誤差上限 ±（度）": "Per-arm angle error bound, ±e (°)",
        "全角度範圍槳隙下界（mm）": "Full-range clearance lower bound (mm)",
        "角度誤差如何影響最小槳盤間距": "Sensitivity of minimum clearance to arm angle uncertainty",
        "理想槳盤外廓寬度（mm）": "Ideal rotor-disk planform width (mm)",
        "理想槳盤外廓長度（mm）": "Ideal rotor-disk planform length (mm)",
        "符合名目槳盤間距的寬度與長度取捨": "Width–length tradeoff subject to the nominal clearance threshold",
        "僅篩選名目間距；不代表完整開口穿越或飛行已驗證。": "Filtered by nominal clearance only; complete gap traversal and flight are not validated.",
        "僅檢查理想平面槳盤間距；未驗證結構、氣流及飛行穩定性。": "Ideal coplanar rotor disks only; structure, airflow, and flight stability are not validated.",
        (
            f"理論計算｜槳徑 {g.propeller_diameter_mm:g} mm｜轉軸間距 {g.hinge_width_mm:g} × {g.hinge_length_mm:g} mm"
            f"｜暫定間距 {g.required_clearance_mm:g} mm｜設定 {run_tag}"
        ): (
            f"Theoretical model | Propeller diameter {g.propeller_diameter_mm:g} mm | "
            f"Hinge spacing {g.hinge_width_mm:g} × {g.hinge_length_mm:g} mm | "
            f"Provisional clearance {g.required_clearance_mm:g} mm | Config {run_tag}"
        ),
        f"各臂角度誤差 ±{config.angle_error_deg:g}°，位置誤差 {config.position_error_mm:g} mm": f"Per-arm uncertainty: angle ±{config.angle_error_deg:g}°, position {config.position_error_mm:g} mm",
        f"臂長與收折角度掃描：展開角度固定 {config.sweep_expanded_deg:g}°": f"Arm length and folding angle sweep: deployed angle fixed at {config.sweep_expanded_deg:g}°",
        f"位置誤差上限固定 {config.position_error_mm:g} mm；曲線斷開處表示超出0至90度模型。": f"Position error bound fixed at {config.position_error_mm:g} mm. "
        "Missing segments are outside the 0°–90° model.",
    }
    filenames = {
        "02_角度與外廓": "02_angle_vs_planform",
        "03_設計可行區域": "03_design_feasibility",
        "04_不同步六組槳隙": "04_staggered_rotor_pair_clearances",
        "06_角度誤差敏感度": "06_angle_uncertainty_sensitivity",
        "07_寬度與長度取捨": "07_width_length_tradeoff",
    }
    for case in config.cases:
        label = f"{case.arm_length_mm:g} mm arms"
        labels[case.label] = label
        labels[f"{case.label}：展開與收折的等比例俯視圖"] = (
            f"{label}: deployed and folded configurations (same scale)"
        )
        labels[f"{case.label}：假設五次平滑曲線的收折動作"] = (
            f"{label}: assumed quintic folding trajectories"
        )
        filenames[f"01_{case.id}_構型"] = f"01_{case.id}_configuration"
        filenames[f"05_{case.id}_收折動作"] = f"05_{case.id}_folding_motion"
        for angle in (case.expanded_angle_deg, case.folded_angle_deg):
            shape = envelope(g, case.arm_length_mm, [angle] * 4)
            labels[
                f"角度 {angle:g}°\n外廓 {shape['width_mm']:.1f} × {shape['length_mm']:.1f} mm"
            ] = f"Angle {angle:g}°\nPlanform {shape['width_mm']:.1f} × {shape['length_mm']:.1f} mm"
    return labels, filenames
