"""Metrics for pre-disturbance step tracking and post-door recovery."""
from __future__ import annotations
import numpy as np
from .models import Scenario


def _first_crossing(t, x, threshold):
    idx = np.flatnonzero(x >= threshold)
    if len(idx) == 0:
        return np.nan
    i = int(idx[0])
    if i == 0:
        return float(t[0])
    if x[i] == x[i - 1]:
        return float(t[i])
    return float(t[i-1] + (t[i]-t[i-1]) * (threshold-x[i-1])/(x[i]-x[i-1]))


def evaluate(result: dict[str, np.ndarray], scenario: Scenario | None = None,
             recovery_tolerance_c: float = 2., recovery_hold_s: float = 30.) -> dict[str, float]:
    scenario = scenario or Scenario()
    t, y, u = result["time_s"], result["measurement_c"], result["control"]
    r = float(scenario.reference)
    ambient = float(scenario.ambient)
    first_door = min((d.start for d in scenario.doors), default=t[-1])
    mask = t < first_door
    initial_to_ref = r-ambient
    t10 = _first_crossing(t[mask], y[mask], ambient + .1 * initial_to_ref)
    t90 = _first_crossing(t[mask], y[mask], ambient + .9 * initial_to_ref)
    overshoot = max(0., float(np.max(y[mask]) - r))
    dt = float(np.median(np.diff(t)))
    iae = float(np.sum(np.abs(r-y)) * dt)
    tv = float(np.sum(np.abs(np.diff(u))))
    result_metrics = {
        "rise_time_10_90_s": t90 - t10 if np.isfinite(t90) and np.isfinite(t10) else np.nan,
        "time_to_60_c_s": _first_crossing(t[mask], y[mask], 60.),
        "overshoot_before_doors_c": overshoot,
        "IAE_c_s": iae,
        "actuator_total_variation": tv,
        "saturation_fraction": float(np.mean((u <= 1.e-7) | (u >= scenario.actuator_max - 1.e-7))),
    }
    # Recover only after door closure and require consecutive held-in-band samples.
    n_hold = max(1, int(np.ceil(recovery_hold_s / dt)))
    for j, door in enumerate(scenario.doors, start=1):
        close_t = door.start + door.duration
        end = scenario.doors[j].start if j < len(scenario.doors) else t[-1] + dt
        candidates = np.flatnonzero((t >= close_t) & (t < end))
        recovery = np.nan
        for idx in candidates:
            if idx + n_hold <= len(t) and t[idx + n_hold-1] < end and np.all(np.abs(y[idx:idx+n_hold] - r) <= recovery_tolerance_c):
                recovery = float(t[idx] - close_t)
                break
        result_metrics[f"door_{j}_recovery_s"] = recovery
    return result_metrics
