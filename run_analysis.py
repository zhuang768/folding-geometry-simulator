#!/usr/bin/env python3
"""One entry point for reproducible folding-geometry analyses."""

import argparse
import hashlib
import json
import platform
import sys
import tempfile
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from zoneinfo import ZoneInfo

from drone_analysis import __version__
from drone_analysis.analysis import MODEL_SCOPE, calculate, write_json, write_tables
from drone_analysis.config import load_config
from drone_analysis.report import write_report

ROOT = Path(__file__).resolve().parent


def run(config_path, output_base, no_plots=False):
    config = load_config(config_path)
    canonical = json.dumps(
        config.raw, sort_keys=True, ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    config_hash = hashlib.sha256(canonical).hexdigest()
    # Calculate before creating any output, so invalid input leaves no partial run.
    result = calculate(config)
    output_base.mkdir(parents=True, exist_ok=True)
    now = datetime.now(ZoneInfo("Asia/Taipei"))
    output = Path(
        tempfile.mkdtemp(prefix=now.strftime("%Y%m%d_%H%M%S_"), dir=output_base)
    )
    manifest = {
        "status": "running",
        "tool_version": __version__,
        "created_at_taipei": now.isoformat(),
        "python_version": platform.python_version(),
        "config_sha256": config_hash,
        "config_hash_method": "sort_keys=True、ensure_ascii=False的JSON，以UTF-8計算SHA-256",
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(
                [ROOT / "run_analysis.py", *(ROOT / "drone_analysis").glob("*.py")]
            )
        },
        "data_kind": "理論計算與假設情境，非實測",
        "model_scope": MODEL_SCOPE,
        "continuous_clearance_method": "矩形四角、等長機臂、共同0至90度角度區間之連續解析極值",
        "row_counts": {name: len(rows) for name, rows in result["tables"].items()},
    }
    write_json(output / "執行資訊.json", manifest)
    try:
        write_json(output / "輸入參數.json", config.raw)
        write_tables(result, output / "數據")
        charts = []
        if not no_plots:
            try:
                from drone_analysis.charts import create_charts

                charts = create_charts(config, result, output, config_hash[:8])
                manifest["plotting_versions"] = {
                    name: version(name) for name in ("matplotlib", "numpy")
                }
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    f"缺少繪圖套件 {exc.name}，請依README安裝，或使用 --no-plots"
                ) from exc
        write_report(config, result, output, manifest, charts)
        write_json(
            output / "摘要.json",
            {
                "data_kind": manifest["data_kind"],
                "model_scope": MODEL_SCOPE,
                "summaries": result["summaries"],
            },
        )
        manifest.update(status="complete", chart_count=len(charts))
        write_json(output / "執行資訊.json", manifest)
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        manifest.update(status="failed", error=str(exc))
        try:
            write_json(output / "執行資訊.json", manifest)
        except OSError as manifest_error:
            print(f"另無法更新失敗狀態檔：{manifest_error}", file=sys.stderr)
        raise RuntimeError(
            f"本次分析未完成。已保留部分輸出於 {output}。原因：{exc}"
        ) from exc
    return output, result


def main():
    parser = argparse.ArgumentParser(
        description="收折無人機理想平面幾何、連續槳隙、動作及誤差分析"
    )
    parser.add_argument(
        "--config", type=Path, default=ROOT / "設定.json", help="JSON設定檔"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "執行批次" / "幾何分析",
        help="輸出根目錄，每次建立新的子目錄",
    )
    parser.add_argument(
        "--no-plots", action="store_true", help="只產生數據與報告，不需繪圖套件"
    )
    args = parser.parse_args()
    try:
        output, result = run(
            args.config.resolve(), args.output.resolve(), args.no_plots
        )
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(f"分析失敗：{exc}", file=sys.stderr)
        return 1
    print(f"分析完成：{output}")
    print(f"報告：{output / '分析報告.md'}")
    for summary in result["summaries"]:
        robust = (
            f"{summary['robust_min_gap_mm']:.6f} mm"
            if summary["robust_supported"]
            else "超出模型範圍"
        )
        print(
            f"{summary['label']}：名目最小槳隙 {summary['path_min_gap_mm']:.6f} mm；誤差情境 {robust}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
