"""Exact planar rotor-disk geometry for four equal outward-facing arms.

The continuous independent-angle solver applies only to corner hinges
(±A, ±B), identical arm lengths, and a common angle interval in [0°, 90°].
It does not certify rotor/body, arm/arm, 3D interference, or flight safety.
"""

import math
from itertools import combinations, product

from .config import Geometry

ARMS = (("P1", -1, 1), ("P2", 1, 1), ("P3", -1, -1), ("P4", 1, -1))
PAIRS = tuple(combinations(range(4), 2))


def center(g: Geometry, length, index, angle_deg):
    _, sx, sy = ARMS[index]
    angle = math.radians(angle_deg)
    return (
        sx * (g.hinge_width_mm / 2 + length * math.sin(angle)),
        sy * (g.hinge_length_mm / 2 + length * math.cos(angle)),
    )


def envelope(g, length, angles):
    if len(angles) != 4 or any(
        not math.isfinite(a) or not 0 <= a <= 90 for a in angles
    ):
        raise ValueError("必須提供四個0至90度的有限角度")
    points = [center(g, length, i, angle) for i, angle in enumerate(angles)]
    pair_gaps = [
        (
            f"P{i + 1}-P{j + 1}",
            math.dist(points[i], points[j]) - g.propeller_diameter_mm,
        )
        for i, j in PAIRS
    ]
    radius = g.propeller_diameter_mm / 2
    # Include the central rectangle as well as the rotating rotor disks.
    left = min(-g.hinge_width_mm / 2, *(p[0] - radius for p in points))
    right = max(g.hinge_width_mm / 2, *(p[0] + radius for p in points))
    back = min(-g.hinge_length_mm / 2, *(p[1] - radius for p in points))
    front = max(g.hinge_length_mm / 2, *(p[1] + radius for p in points))
    worst = min(pair_gaps, key=lambda p: p[1])
    return {
        "width_mm": right - left,
        "length_mm": front - back,
        "min_gap_mm": worst[1],
        "worst_pair": worst[0],
        "pair_gaps": pair_gaps,
        "points": points,
    }


def independent_clearance(g, length, low_deg, high_deg, position_error_mm=0):
    """Minimum over ALL independent angles, not a time/grid sampling.

    Opposite horizontal arms: x separation is monotone in each angle, so
    the lower bound is attained at (low, low), with zero y difference.
    Opposite vertical arms: analogous at (high, high).
    Diagonals: fixing either angle leaves C + 2L(Qx sin θ + Qy cos θ),
    Qx,Qy > 0. Its interior stationary point is a maximum; endpoints suffice.
    Radial center uncertainty r gives the conservative lower bound d - 2r.
    """
    if not (
        math.isfinite(low_deg)
        and math.isfinite(high_deg)
        and 0 <= low_deg <= high_deg <= 90
    ):
        raise ValueError("連續解析模型僅支援0至90度內的共同角度區間")
    pairs = []
    for i, j in PAIRS:
        _, sx1, sy1 = ARMS[i]
        _, sx2, sy2 = ARMS[j]
        if sy1 == sy2:
            candidates = [(low_deg, low_deg)]
        elif sx1 == sx2:
            candidates = [(high_deg, high_deg)]
        else:
            candidates = list(product((low_deg, high_deg), repeat=2))
        distance, a, b = min(
            (math.dist(center(g, length, i, a), center(g, length, j, b)), a, b)
            for a, b in candidates
        )
        pairs.append(
            {
                "pair": f"P{i + 1}-P{j + 1}",
                "angle_i_deg": a,
                "angle_j_deg": b,
                "min_center_distance_mm": distance,
                "clearance_lower_bound_mm": max(0.0, distance - 2 * position_error_mm)
                - g.propeller_diameter_mm,
            }
        )
    worst = min(pairs, key=lambda p: p["clearance_lower_bound_mm"])
    return {
        "min_gap_mm": worst["clearance_lower_bound_mm"],
        "worst_pair": worst["pair"],
        "pairs": pairs,
    }


def robust_clearance(g, length, low, high, angle_error, position_error):
    lo, hi = low - angle_error, high + angle_error
    if lo < 0 or hi > 90:
        return None  # Never silently truncate uncertainty and claim full coverage.
    return independent_clearance(g, length, lo, hi, position_error)


def smooth_motion(time_s, start_deg, end_deg, duration_s, delay_s=0):
    """Assumed quintic position trajectory; not a physical servo response."""
    u = min(1.0, max(0.0, (time_s - delay_s) / duration_s))
    delta = end_deg - start_deg
    # Symmetric evaluation avoids cancellation near u=1 and overshooting 0°.
    v = u if u <= 0.5 else 1 - u
    partial = v**3 * (10 + v * (-15 + 6 * v))
    s = partial if u <= 0.5 else 1 - partial
    s = min(1.0, max(0.0, s))
    speed = delta / duration_s * 30 * u**2 * (1 - u) ** 2
    acceleration = delta / duration_s**2 * 60 * u * (1 - u) * (1 - 2 * u)
    return (1 - s) * start_deg + s * end_deg, speed, acceleration
