"""First-order ARX system identification in the thesis' discrete-time setting.

For a known, *integer* delay m and zero-order-held sampled input:

    y[k] = a*y[k-1] + b*u[k-1-m] + epsilon[k]

where y is the temperature *deviation* from the chosen ambient level.
The mapping to a continuous FOPDT process is:

    tau = -dt / log(a), K = b/(1-a), theta = m*dt.

This mapping requires 0<a<1, b>0, a known sample period, consistent
actuator units, sufficiently exciting input, and a valid first-order model.
The original sensor measurements and MATLAB ARX experiment are not distributed.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class ARXEstimate:
    a: float
    b: float
    delay_samples: int
    sample_period_s: float
    ambient_c: float
    rmse_c: float
    n_samples: int

    @property
    def tau_s(self) -> float:
        return float(-self.sample_period_s / np.log(self.a))

    @property
    def steady_state_gain(self) -> float:
        return float(self.b / (1. - self.a))

    @property
    def dead_time_s(self) -> float:
        return self.delay_samples * self.sample_period_s


def fit_first_order_arx(
    input_u: np.ndarray,
    temperature_c: np.ndarray,
    *,
    dt: float,
    delay_samples: int,
    ambient_c: float = 30.0,
) -> ARXEstimate:
    """Least-squares ARX(1,1,m+1) for a known input delay.

    Inputs are equally sampled *at the same timestamps*. For constant inputs,
    the ARX parameters may be unidentifiable: the design matrix must have rank 2.
    No claim is made that the returned estimates match the thesis ARX model.
    """
    u = np.asarray(input_u, dtype=float)
    temperature = np.asarray(temperature_c, dtype=float)
    if u.ndim != 1 or temperature.ndim != 1 or len(u) != len(temperature):
        raise ValueError("input_u and temperature_c must be equal-length 1D arrays")
    if dt <= 0 or not np.isfinite(dt):
        raise ValueError("dt must be finite and strictly positive")
    if not isinstance(delay_samples, (int, np.integer)) or delay_samples < 0:
        raise ValueError("delay_samples must be a nonnegative integer")
    if len(u) - delay_samples - 1 < 5:
        raise ValueError("not enough samples for the specified dead time")
    if not (np.all(np.isfinite(u)) and np.all(np.isfinite(temperature))):
        raise ValueError("input data and temperature must be finite")
    y = temperature - float(ambient_c)
    # k = m+1,...,N-1 ensures the entire lagged input is observed.
    k = np.arange(delay_samples + 1, len(y))
    X = np.column_stack([y[k - 1], u[k - 1 - delay_samples]])
    if np.linalg.matrix_rank(X) < 2:
        raise ValueError("system is not identifiable: regressor matrix is rank deficient")
    a, b = np.linalg.lstsq(X, y[k], rcond=None)[0]
    if not (0 < a < 1 and b > 0):
        raise ValueError("estimated model is not a stable positive-gain first-order process")
    residual = y[k] - X @ np.array([a, b])
    return ARXEstimate(a=float(a), b=float(b), delay_samples=int(delay_samples),
                       sample_period_s=float(dt), ambient_c=float(ambient_c),
                       rmse_c=float(np.sqrt(np.mean(residual ** 2))), n_samples=len(k))


def simulate_sampled_arx(
    input_u: np.ndarray, *, K: float, tau_s: float, dt: float,
    delay_samples: int, ambient_c: float = 30.0,
) -> np.ndarray:
    """Exact ZOH samples for a deliberately *integer* input dead time.

    This educational generator is not raw burn-in-chamber measurement data.
    An implicit zero heater input is assumed for indices before the first sample.
    """
    u = np.asarray(input_u, dtype=float)
    if u.ndim != 1 or not np.all(np.isfinite(u)):
        raise ValueError("input_u must be a finite 1D array")
    if K <= 0 or tau_s <= 0 or dt <= 0 or delay_samples < 0:
        raise ValueError("K, tau_s, dt must be positive, delay nonnegative")
    if not isinstance(delay_samples, (int, np.integer)):
        raise ValueError("delay_samples must be an integer")
    a = float(np.exp(-dt / tau_s))
    y = np.zeros(len(u), dtype=float)
    for k in range(1, len(u)):
        idx = k - 1 - delay_samples
        y[k] = a * y[k - 1] + K * (1 - a) * (u[idx] if idx >= 0 else 0)
    return y + float(ambient_c)
