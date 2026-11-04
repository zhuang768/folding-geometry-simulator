"""Batch calculations and explicit, machine-readable model boundaries."""

import csv
import json
from pathlib import Path

from .config import Range
from .geometry import envelope, independent_clearance, robust_clearance, smooth_motion

MODEL_SCOPE = (
    "四臂等長、轉軸為矩形四角、角度由機身前後軸向外量起，範圍0至90度。"
    "僅檢查理想同高度圓形槳盤的平面間距；未檢查機臂、機身、伺服、線材及3D避讓，"
    "亦未涵蓋氣流、彈性變形、伺服實際追蹤與飛行穩定性。"
    "圖中的中央矩形只供外廓與位置參考，沒有執行槳盤對矩形的干涉驗證。"
)


def feasible(gap, required):
    # Classification uses full precision, not rounded CSV/chart labels.
    return gap >= required


def row_for(g, length, angle, expanded, angle_error, position_error):
    shape = envelope(g, length, [angle] * 4)
    path = independent_clearance(g, length, angle, expanded)
    robust = robust_clearance(g, length, angle, expanded, angle_error, position_error)
    return {
        "arm_length_mm": length,
        "folded_angle_deg": angle,
        "expanded_angle_deg": expanded,
        "folded_width_mm": shape["width_mm"],
        "folded_length_mm": shape["length_mm"],
        "instant_min_gap_mm": shape["min_gap_mm"],
        "path_min_gap_mm": path["min_gap_mm"],
        "path_worst_pair": path["worst_pair"],
        "nominal_pass": feasible(path["min_gap_mm"], g.required_clearance_mm),
        "robust_supported": robust is not None,
        "robust_min_gap_mm": robust["min_gap_mm"] if robust else None,
        "robust_pass": feasible(robust["min_gap_mm"], g.required_clearance_mm)
        if robust
        else None,
    }


def calculate(config):
    g = config.geometry
    tables = {
        name: []
        for name in (
            "case_summary",
            "angle_scan",
            "design_sweep",
            "pair_bounds",
            "motion",
            "angle_sensitivity",
        )
    }
    summaries = []
    for case in config.cases:
        nominal = independent_clearance(
            g, case.arm_length_mm, case.folded_angle_deg, case.expanded_angle_deg
        )
        robust = robust_clearance(
            g,
            case.arm_length_mm,
            case.folded_angle_deg,
            case.expanded_angle_deg,
            config.angle_error_deg,
            config.position_error_mm,
        )
        summary = row_for(
            g,
            case.arm_length_mm,
            case.folded_angle_deg,
            case.expanded_angle_deg,
            config.angle_error_deg,
            config.position_error_mm,
        )
        expanded = envelope(g, case.arm_length_mm, [case.expanded_angle_deg] * 4)
        summary.update(
            case_id=case.id,
            label=case.label,
            expanded_width_mm=expanded["width_mm"],
            expanded_length_mm=expanded["length_mm"],
            width_reduction_percent=100
            * (1 - summary["folded_width_mm"] / expanded["width_mm"]),
            simultaneous_completion_s=config.duration_s,
            staggered_completion_s=config.duration_s + max(config.delays_s),
            simultaneous_time_pass=config.duration_s <= config.completion_limit_s,
            staggered_time_pass=config.duration_s + max(config.delays_s)
            <= config.completion_limit_s,
            analytic_peak_speed_deg_s=1.875
            * (case.expanded_angle_deg - case.folded_angle_deg)
            / config.duration_s,
            analytic_peak_acceleration_deg_s2=(10 / 3**0.5)
            * (case.expanded_angle_deg - case.folded_angle_deg)
            / config.duration_s**2,
        )
        summaries.append(summary)
        tables["case_summary"].append(summary.copy())
        for kind, bound in (
            ("nominal_exact", nominal),
            ("uncertainty_lower_bound", robust),
        ):
            if bound:
                for pair in bound["pairs"]:
                    tables["pair_bounds"].append(
                        {
                            "case_id": case.id,
                            "kind": kind,
                            **pair,
                            "required_clearance_mm": g.required_clearance_mm,
                            "pass": feasible(
                                pair["clearance_lower_bound_mm"],
                                g.required_clearance_mm,
                            ),
                        }
                    )
        angles = sorted(
            set(
                config.angle_range.values()
                + [case.folded_angle_deg, case.expanded_angle_deg]
            )
        )
        for angle in angles:
            if angle <= case.expanded_angle_deg:
                tables["angle_scan"].append(
                    {
                        "case_id": case.id,
                        **row_for(
                            g,
                            case.arm_length_mm,
                            angle,
                            case.expanded_angle_deg,
                            config.angle_error_deg,
                            config.position_error_mm,
                        ),
                    }
                )
        for error in config.error_range.values():
            bound = robust_clearance(
                g,
                case.arm_length_mm,
                case.folded_angle_deg,
                case.expanded_angle_deg,
                error,
                config.position_error_mm,
            )
            tables["angle_sensitivity"].append(
                {
                    "case_id": case.id,
                    "angle_error_deg": error,
                    "position_error_mm": config.position_error_mm,
                    "supported": bound is not None,
                    "clearance_lower_bound_mm": bound["min_gap_mm"] if bound else None,
                    "pass": feasible(bound["min_gap_mm"], g.required_clearance_mm)
                    if bound
                    else None,
                }
            )
        for direction in ("fold", "unfold"):
            start, end = case.expanded_angle_deg, case.folded_angle_deg
            if direction == "unfold":
                start, end = end, start
            for scenario, delays in (
                ("simultaneous", (0.0,) * 4),
                ("staggered", config.delays_s),
            ):
                completion = config.duration_s + max(delays)
                times = sorted(
                    set(
                        Range(0, completion, config.sample_step_s).values()
                        + list(delays)
                        + [d + config.duration_s for d in delays]
                    )
                )
                for time in times:
                    states = [
                        smooth_motion(time, start, end, config.duration_s, delay)
                        for delay in delays
                    ]
                    shape = envelope(g, case.arm_length_mm, [s[0] for s in states])
                    row = {
                        "case_id": case.id,
                        "direction": direction,
                        "scenario": scenario,
                        "time_s": time,
                        "width_mm": shape["width_mm"],
                        "length_mm": shape["length_mm"],
                        "min_gap_mm": shape["min_gap_mm"],
                        "worst_pair": shape["worst_pair"],
                        "completion_s": completion,
                        "time_pass": completion <= config.completion_limit_s,
                    }
                    for i, (angle, speed, acceleration) in enumerate(states, 1):
                        row.update(
                            {
                                f"p{i}_angle_deg": angle,
                                f"p{i}_speed_deg_s": speed,
                                f"p{i}_acceleration_deg_s2": acceleration,
                            }
                        )
                    for pair, gap in shape["pair_gaps"]:
                        row[pair.lower().replace("-", "_") + "_gap_mm"] = gap
                    tables["motion"].append(row)
    for length in config.length_range.values():
        for angle in config.angle_range.values():
            tables["design_sweep"].append(
                row_for(
                    g,
                    length,
                    angle,
                    config.sweep_expanded_deg,
                    config.angle_error_deg,
                    config.position_error_mm,
                )
            )
    return {"summaries": summaries, "tables": tables}


def write_tables(result, directory: Path):
    directory.mkdir()
    for name, rows in result["tables"].items():
        with (directory / f"{name}.csv").open(
            "w", encoding="utf-8-sig", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
