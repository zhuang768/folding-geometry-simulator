"""A readable report that keeps assumptions beside numerical conclusions."""

from .analysis import MODEL_SCOPE


def write_report(config, result, output, manifest, charts):
    g = config.geometry
    lines = [
        "# 收折無人機離線分析報告",
        "",
        f"執行時間：{manifest['created_at_taipei']}。",
        "",
        "本報告為理論計算與假設情境，未使用實機量測資料。",
        "",
        "## 模型範圍",
        "",
        MODEL_SCOPE,
        "",
        "角度以機身前後軸為0度，向外展開為正；不是伺服PWM角度。",
        "",
        (
            f"槳徑 {g.propeller_diameter_mm:g} mm。轉軸間距 {g.hinge_width_mm:g} × {g.hinge_length_mm:g} mm。"
            f"暫定槳盤間距門檻 {g.required_clearance_mm:g} mm，這個門檻不是已驗證的安全標準。"
        ),
        "",
        f"設定檔 SHA-256：`{manifest['config_sha256']}`。完整設定見 [輸入參數.json](輸入參數.json)。",
        "",
        "## 既有方案比較",
        "",
        "| 方案 | 展開寬×長 mm | 收折寬×長 mm | 寬度縮減 | 全區間最小槳隙 mm | 名目門檻 |",
        "|---|---|---|---|---|---|",
    ]
    for s in result["summaries"]:
        lines.append(
            f"| {s['label']} | {s['expanded_width_mm']:.2f} × {s['expanded_length_mm']:.2f} | "
            f"{s['folded_width_mm']:.2f} × {s['folded_length_mm']:.2f} | "
            f"{s['width_reduction_percent']:.2f}% | {s['path_min_gap_mm']:.6f} | "
            f"{'達到' if s['nominal_pass'] else '未達'} |"
        )
    lines.extend(
        [
            "",
            "這裡的『達到』僅指所列槳盤間距門檻。計算涵蓋四臂在共同角度區間內各自取值，允許不同步；不代表機體能安全飛行或通過真實開口。",
            "",
            "## 誤差情境",
            "",
            f"假設每臂實際角度各可偏移 ±{config.angle_error_deg:g}°，每個馬達中心的額外平面位置誤差上限為 {config.position_error_mm:g} mm。",
            "",
        ]
    )
    for s in result["summaries"]:
        if s["robust_supported"]:
            lines.append(
                f"- {s['label']}：槳隙保守下界 {s['robust_min_gap_mm']:.6f} mm，"
                f"{'達到' if s['robust_pass'] else '未達'}暫定門檻。"
            )
        else:
            lines.append(
                f"- {s['label']}：誤差區間超出0至90度，本模型不支援；沒有截斷誤差範圍或判定通過。"
            )
    lines.extend(
        [
            "",
            "若有位置誤差，兩馬達最小中心距的保守下界為 max(0, d − 2r)，再扣除槳徑。未假設誤差機率分布，因此不輸出成功率或故障機率。",
            "",
            "## 假設動作與時間",
            "",
            (
                f"單臂動作時間 {config.duration_s:g} 秒，整體完成門檻 {config.completion_limit_s:g} 秒。"
                f"P1至P4延遲為 {', '.join(f'{d:g}' for d in config.delays_s)} 秒。"
            ),
            "",
            "動作採五次平滑曲線 s(u)=10u³−15u⁴+6u⁵，起終點速度與加速度為零。時間序列為指定軌跡的取樣，並非伺服負載下的實際響應。",
            "",
        ]
    )
    for s in result["summaries"]:
        lines.append(
            f"- {s['label']}：同步完成 {s['simultaneous_completion_s']:g} 秒，"
            f"{'符合' if s['simultaneous_time_pass'] else '超過'}時間門檻；"
            f"不同步完成 {s['staggered_completion_s']:g} 秒，"
            f"{'符合' if s['staggered_time_pass'] else '超過'}時間門檻。"
            f"單臂解析峰值速度 {s['analytic_peak_speed_deg_s']:.3f} 度／秒，"
            f"峰值加速度 {s['analytic_peak_acceleration_deg_s2']:.3f} 度／秒²。"
        )
    lines.extend(
        [
            "",
            "## 掃描與連續驗證的區別",
            "",
            "臂長與終點角度採指定離散取樣，包含上下端點。掃描沒有涵蓋未取樣的設計尺寸。每一個取樣設計的全路徑槳隙，則使用連續角度解析法計算。",
            "",
            "水平槳對的最小距離在共同下限角；垂直槳對在共同上限角；對角槳對逐變數為凹函數，最小值可在四個角度端點組合取得。每對的見證角度存於 pair_bounds.csv。",
            "",
            "不同步動作時間圖只描述所設定的延遲。全區間解析驗證另涵蓋允許區間內任意不同步組合，結果比單一路徑取樣更一般。",
            "",
            "## 圖表",
            "",
        ]
    )
    if charts:
        for stem, title in charts:
            lines.extend(
                [
                    f"### {title}",
                    "",
                    f"![{title}](圖表/{stem}.png)",
                    "",
                    f"[向量圖 SVG](圖表/{stem}.svg)",
                    "",
                ]
            )
    else:
        lines.extend(["這次以 --no-plots 執行，未產生圖片。", ""])
    lines.extend(
        [
            "## 數據表",
            "",
            "CSV使用UTF-8含BOM，方便試算表開啟。欄名尾綴標示單位。True／False是該模型門檻結果；不支援的誤差結果留空，須搭配 supported 欄位解讀，不能當成零。",
            "",
        ]
    )
    for name, rows in result["tables"].items():
        lines.append(f"- [{name}.csv](數據/{name}.csv)：{len(rows)} 列。")
    lines.extend(
        [
            "",
            "## 尚未加入本版",
            "",
            "本版未計算結構強度、伺服負載扭力、推重比、耗電、續航、氣流、飛行動態、完整3D開口穿越與AI辨識效能。這些項目需要質量分布、材料與截面、動力曲線、摩擦及控制模型等額外輸入，不能由目前幾何值直接推定。",
            "",
            "程式只在本機計算與產生檔案，不連接或控制飛控、伺服、相機或網路服務。",
            "",
        ]
    )
    (output / "分析報告.md").write_text("\n".join(lines), encoding="utf-8")
