"""Small-signal frequency-domain analysis of fixed linear IMC/parallel PID.

This evaluates the *linear, unsaturated, fixed-gain* feedback model only.
It is not a stability certificate for gain-scheduled fuzzy PID or nonlinear
hardware with saturated actuators; margins depend on frequency grid coverage.

![Fixed-loop gain and sensitivity](../assets/fixed-loop-response.png)

The chart evaluates the nominal source-parameter plant and fixed IMC gains.
It displays the sampled range used to estimate margins, not a global nonlinear
stability certificate. Adaptive gains and actuator clipping are absent here.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .controllers import PIDGains
from .models import Plant


@dataclass(frozen=True)
class RobustnessMargins:
    """Grid-dependent fixed-loop sensitivity and approximate first margins.

    `maximum_sensitivity` and `gain_margin` are ratios, phase margin is in
    degrees, and peak frequency is rad/s. Infinite gain/phase margin means no
    crossing was detected on the sampled grid, not proof of infinite margin.
    """
    maximum_sensitivity: float
    gain_margin: float  # ratio, not dB; inf = no crossing on sampled grid
    phase_margin_deg: float  # inf = no crossing on sampled grid
    peak_frequency_rad_s: float


def linear_loop_response(
    plant: Plant, gains: PIDGains, omega_rad_s: np.ndarray,
    *, derivative_filter_time_s: float = 8.0,
) -> np.ndarray:
    """Return complex loop response on a positive finite rad/s frequency array.

    Evaluate `G(jω)[Kp+Ki/(jω)+Kd*jω/(1+jω*Tf)]` with exact FOPDT
    delay. Output has the same one-dimensional shape as `omega_rad_s`.
    `derivative_filter_time_s` is positive seconds. This is the continuous
    unsaturated fixed-gain model, not the discrete sampled PID implementation.
    """
    omega = np.asarray(omega_rad_s, dtype=float)
    if omega.ndim != 1 or len(omega) < 2 or not np.all(np.isfinite(omega)) or np.any(omega <= 0):
        raise ValueError("frequencies must be a 1D array of strictly positive finite values")
    if derivative_filter_time_s <= 0:
        raise ValueError("derivative filter time must be positive")
    s = 1j * omega
    G = plant.K * np.exp(-plant.delay * s) / (plant.tau * s + 1.)
    C = (gains.kp + gains.ki / s +
         gains.kd * s / (1. + derivative_filter_time_s * s))
    return C * G


def _first_log_crossing(omega, levels):
    """Locate a zero crossing by interpolation in log frequency, if observed."""
    signs = np.sign(levels)
    ids = np.flatnonzero(signs[:-1] * signs[1:] <= 0)
    if len(ids) == 0:
        return None
    j = int(ids[0])
    if levels[j] == 0:
        return j, 0.0
    weight = float(-levels[j] / (levels[j + 1] - levels[j]))
    return j, float(np.clip(weight, 0., 1.))


def assess_fixed_pid_robustness(
    plant: Plant,
    gains: PIDGains,
    *,
    omega_rad_s: np.ndarray | None = None,
    derivative_filter_time_s: float = 8.0,
) -> RobustnessMargins:
    """Numerical M_s and approximate gain/phase margins over an explicit grid.

    Report 2 of the original research program discusses GM>1.7,
    M_s<2.2 and PM>30 degrees as *design targets*. They are not guaranteed
    by this method. Multiple crossovers require detailed Nyquist review.
    """
    w = (np.logspace(-6, 1, 5000) if omega_rad_s is None
         else np.asarray(omega_rad_s, dtype=float))
    if len(w) < 3 or np.any(np.diff(w) <= 0):
        raise ValueError("frequency grid must be strictly increasing with at least 3 values")
    L = linear_loop_response(plant, gains, w, derivative_filter_time_s=derivative_filter_time_s)
    S = 1. / (1. + L)
    absS = np.abs(S)
    maxidx = int(np.argmax(absS))
    peak_ms = float(absS[maxidx])
    if not np.isfinite(peak_ms):
        raise ValueError("singular sampled loop sensitivity")
    phase = np.unwrap(np.angle(L))
    mag = np.abs(L)
    # Classical PM from the first unity-magnitude crossing.
    mag_cross = _first_log_crossing(w, np.log(mag))
    if mag_cross is None:
        pm = float("inf")
    else:
        j, a = mag_cross
        phase_at_crossover = (1. - a) * phase[j] + a * phase[j + 1]
        pm = float(180. + np.rad2deg(phase_at_crossover))
    # First -180° phase crossing. There may be several for delayed systems.
    phase_cross = _first_log_crossing(w, phase + np.pi)
    if phase_cross is None:
        gm = float("inf")
    else:
        j, a = phase_cross
        mag_at_phase_crossover = np.exp((1. - a) * np.log(mag[j]) + a * np.log(mag[j + 1]))
        gm = float(1. / mag_at_phase_crossover)
    return RobustnessMargins(maximum_sensitivity=peak_ms, gain_margin=gm,
                             phase_margin_deg=pm, peak_frequency_rad_s=float(w[maxidx]))
