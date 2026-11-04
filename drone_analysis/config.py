"""Validate every input before creating output files."""

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path


def keys(value, expected, location):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f"{location} 欄位必須是：{', '.join(expected)}")


def number(value, name, minimum=0.0, maximum=1_000_000.0, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} 必須是數字")
    value = float(value)
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{name} 必須是 {minimum} 至 {maximum} 間的有限數字")
    if positive and value <= 0:
        raise ValueError(f"{name} 必須大於零")
    return value


@dataclass(frozen=True)
class Range:
    low: float
    high: float
    step: float

    @classmethod
    def parse(cls, raw, name, maximum=1_000_000, positive=False):
        keys(raw, ["min", "max", "step"], name)
        low = number(raw["min"], name + ".min", maximum=maximum, positive=positive)
        high = number(raw["max"], name + ".max", maximum=maximum, positive=positive)
        step = number(raw["step"], name + ".step", positive=True)
        if high < low:
            raise ValueError(f"{name} 的 max 不可小於 min")
        if (high - low) / step > 10_000:
            raise ValueError(f"{name} 超過 10,001 個取樣點，請放大 step")
        return cls(low, high, step)

    def values(self):
        count = math.floor((self.high - self.low) / self.step + 1e-10)
        values = [self.low + i * self.step for i in range(count + 1)]
        if self.high - values[-1] > 1e-9:
            values.append(self.high)
        else:
            values[-1] = self.high
        return values


@dataclass(frozen=True)
class Geometry:
    hinge_width_mm: float
    hinge_length_mm: float
    propeller_diameter_mm: float
    required_clearance_mm: float


@dataclass(frozen=True)
class Case:
    id: str
    label: str
    arm_length_mm: float
    expanded_angle_deg: float
    folded_angle_deg: float


@dataclass(frozen=True)
class Config:
    geometry: Geometry
    cases: tuple[Case, ...]
    length_range: Range
    angle_range: Range
    sweep_expanded_deg: float
    duration_s: float
    completion_limit_s: float
    sample_step_s: float
    delays_s: tuple[float, ...]
    angle_error_deg: float
    position_error_mm: float
    error_range: Range
    raw: dict


def parse_config(raw):
    keys(
        raw,
        [
            "schema_version",
            "geometry",
            "cases",
            "sweep",
            "motion",
            "uncertainty",
            "notes",
        ],
        "設定",
    )
    if type(raw["schema_version"]) is not int or raw["schema_version"] != 1:
        raise ValueError("schema_version 必須是整數 1")
    g = raw["geometry"]
    keys(
        g,
        [
            "hinge_width_mm",
            "hinge_length_mm",
            "propeller_diameter_mm",
            "required_clearance_mm",
        ],
        "geometry",
    )
    geometry = Geometry(
        **{k: number(v, k, positive=k != "required_clearance_mm") for k, v in g.items()}
    )
    if not isinstance(raw["notes"], str):
        raise TypeError("notes 必須是文字")
    if not isinstance(raw["cases"], list) or not 1 <= len(raw["cases"]) <= 12:
        raise ValueError("cases 必須有 1 至 12 個方案")
    cases = []
    for item in raw["cases"]:
        keys(
            item,
            ["id", "label", "arm_length_mm", "expanded_angle_deg", "folded_angle_deg"],
            "cases",
        )
        if not isinstance(item["id"], str) or not re.fullmatch(
            r"[a-z][a-z0-9_]{0,39}", item["id"]
        ):
            raise ValueError("方案 id 請用小寫英文字母開頭，後接英數字或底線，最多40字")
        if (
            not isinstance(item["label"], str)
            or not item["label"].strip()
            or len(item["label"]) > 80
        ):
            raise ValueError("方案 label 必須是 1 至 80 字的名稱")
        length = number(item["arm_length_mm"], "arm_length_mm", positive=True)
        start = number(item["expanded_angle_deg"], "expanded_angle_deg", maximum=90)
        end = number(item["folded_angle_deg"], "folded_angle_deg", maximum=90)
        if end > start:
            raise ValueError("folded_angle_deg 不可大於 expanded_angle_deg")
        cases.append(Case(item["id"], item["label"], length, start, end))
    if len({c.id for c in cases}) != len(cases):
        raise ValueError("方案 id 不可重複")
    sweep = raw["sweep"]
    keys(sweep, ["arm_length_mm", "folded_angle_deg", "expanded_angle_deg"], "sweep")
    lengths = Range.parse(sweep["arm_length_mm"], "sweep.arm_length_mm", positive=True)
    angles = Range.parse(
        sweep["folded_angle_deg"], "sweep.folded_angle_deg", maximum=90
    )
    expanded = number(
        sweep["expanded_angle_deg"], "sweep.expanded_angle_deg", maximum=90
    )
    if angles.high > expanded:
        raise ValueError("掃描終點角度不可大於 sweep.expanded_angle_deg")
    if len(lengths.values()) * len(angles.values()) > 100_000:
        raise ValueError("臂長與角度組合超過100,000組，請縮小範圍或放大步距")
    motion = raw["motion"]
    keys(
        motion,
        ["duration_s", "completion_limit_s", "sample_step_s", "start_delays_s"],
        "motion",
    )
    duration = number(motion["duration_s"], "duration_s", maximum=3600, positive=True)
    limit = number(
        motion["completion_limit_s"], "completion_limit_s", maximum=3600, positive=True
    )
    step = number(
        motion["sample_step_s"], "sample_step_s", maximum=duration, positive=True
    )
    delays = motion["start_delays_s"]
    if not isinstance(delays, list) or len(delays) != 4:
        raise ValueError("start_delays_s 必須有P1至P4的四個非負延遲")
    delays = tuple(number(d, "start_delays_s", maximum=3600) for d in delays)
    if (duration + max(delays)) / step > 20_000:
        raise ValueError("動作取樣超過20,001點，請放大 sample_step_s")
    if (math.ceil((duration + max(delays)) / step) + 2) * len(cases) * 4 > 200_000:
        raise ValueError("全部動作序列合計超過200,000列，請放大 sample_step_s")
    uncertainty = raw["uncertainty"]
    keys(
        uncertainty,
        ["angle_error_deg", "motor_position_error_mm", "angle_error_sweep_deg"],
        "uncertainty",
    )
    error = number(uncertainty["angle_error_deg"], "angle_error_deg", maximum=90)
    position = number(uncertainty["motor_position_error_mm"], "motor_position_error_mm")
    errors = Range.parse(
        uncertainty["angle_error_sweep_deg"], "angle_error_sweep_deg", maximum=90
    )
    return Config(
        geometry,
        tuple(cases),
        lengths,
        angles,
        expanded,
        duration,
        limit,
        step,
        delays,
        error,
        position,
        errors,
        raw,
    )


def load_config(path: Path):
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"JSON 欄位重複：{key}")
            result[key] = value
        return result

    return parse_config(
        json.loads(
            path.read_text(encoding="utf-8-sig"), object_pairs_hook=reject_duplicates
        )
    )
