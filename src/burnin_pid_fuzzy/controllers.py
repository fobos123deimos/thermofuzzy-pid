"""Fixed IMC PID and fuzzy-adaptive PID with derivative filtering/anti-windup."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .fuzzy import FuzzyRuleBase, infer_normalized_gains


@dataclass(frozen=True)
class PIDGains:
    kp: float
    ki: float  # Parallel/independent gain, 1/s.
    kd: float  # Parallel/independent derivative gain, s.

    @classmethod
    def from_isa(cls, kp: float, ti: float, td: float) -> "PIDGains":
        if ti <= 0:
            raise ValueError("Ti must be > 0")
        return cls(kp=kp, ki=kp / ti, kd=kp * td)


def imc_pid_gains(K: float = 7.624, tau: float = 151.6,
                  theta: float = 8.78, lam: float = 35.3273) -> PIDGains:
    """2021 undergraduate thesis Table 2: IMC PID in independent/parallel convention.

    Kp=(tau+theta/2)/(K*(lambda+theta)), Ti=tau+theta/2,
    Td=tau*theta/(2*tau+theta); Ki=Kp/Ti, Kd=Kp*Td.
    """
    if min(K, tau, lam) <= 0 or theta < 0:
        raise ValueError("K, tau, lam positive; theta nonnegative")
    kp = (tau + theta / 2) / (K * (lam + theta))
    ti = tau + theta / 2
    td = tau * theta / (2 * tau + theta)
    return PIDGains.from_isa(kp, ti, td)


class FixedPID:
    """Discrete PI(D), derivative on measurement, with configurable anti-windup."""
    def __init__(self, gains: PIDGains, dt: float = 1., u_min: float = 0.,
                 u_max: float = 10., derivative_filter: float = 8.,
                 anti_windup: str = "conditional", tracking_time: float | None = None):
        if dt <= 0 or u_max <= u_min or derivative_filter <= 0:
            raise ValueError("dt, u limits or derivative filter invalid")
        if anti_windup not in {"conditional", "back_calculation"}:
            raise ValueError("anti_windup must be 'conditional' or 'back_calculation'")
        if tracking_time is not None and (not np.isfinite(tracking_time) or tracking_time < dt):
            raise ValueError("tracking_time must be finite and >= dt")
        self.anti_windup = anti_windup
        # Tt >= dt makes the explicit Euler back-calculation correction bounded.
        self.tracking_time = float(tracking_time if tracking_time is not None else max(dt, 10.0))
        self.gains = gains
        self.dt, self.u_min, self.u_max = dt, u_min, u_max
        self.derivative_filter = derivative_filter
        self.integral = 0.
        self.filtered_derivative = 0.
        self.previous_measurement = None
        self.previous_error = None

    def _calculate(self, setpoint: float, measurement: float, gains: PIDGains):
        error = float(setpoint - measurement)
        if self.previous_measurement is None:
            derivative_raw = 0.
        else:
            derivative_raw = (measurement - self.previous_measurement) / self.dt
        a = self.derivative_filter / (self.derivative_filter + self.dt)
        self.filtered_derivative = a * self.filtered_derivative + (1 - a) * derivative_raw
        proportional = gains.kp * error
        derivative = -gains.kd * self.filtered_derivative
        integral_candidate = self.integral + gains.ki * self.dt * error
        raw_candidate = proportional + integral_candidate + derivative
        if self.anti_windup == "conditional":
            # Reject integration only when it drives the output *further* into saturation.
            if not ((raw_candidate > self.u_max and error > 0) or
                    (raw_candidate < self.u_min and error < 0)):
                self.integral = integral_candidate
        else:
            # Back-calculation in independent gain convention, as described by
            # the preliminary PI/PID engineering report in the private archive:
            # I[k] = I[k-1] + dt*(Ki[k]*e[k] + (u_sat-u_raw)/Tt).
            # This is a new, explicit implementation; the source report does not
            # specify the original tracking time or digital discretization.
            limited = float(np.clip(raw_candidate, self.u_min, self.u_max))
            self.integral = integral_candidate + (self.dt / self.tracking_time) * (limited - raw_candidate)
        raw = proportional + self.integral + derivative
        output = float(np.clip(raw, self.u_min, self.u_max))
        self.previous_measurement = float(measurement)
        self.previous_error = error
        return output

    def step(self, setpoint: float, measurement: float) -> tuple[float, PIDGains]:
        return self._calculate(setpoint, measurement, self.gains), self.gains


class FuzzyPID(FixedPID):
    """Adaptive Mamdani MOM PID; gains are independently mapped Eq. (2.14).

    The "dense" variant fills omitted rules (new research extension).
    `smoothing < 1` low-pass filters the gains (new research extension).
    """
    GAIN_MIN = np.array([.35, .0008, 0.])
    GAIN_MAX = np.array([.90, .045, 2.])

    def __init__(self, mode: str = "sparse", smoothing: float = 1.0,
                 derivative_filter: float = 8., blend_imc: float = 1.0,
                 nominal: PIDGains | None = None, **kwargs):
        if not 0 < smoothing <= 1:
            raise ValueError("smoothing must be in (0,1]")
        if not 0 <= blend_imc <= 1:
            raise ValueError("blend_imc must be in [0,1]")
        super().__init__(PIDGains(*((self.GAIN_MIN + self.GAIN_MAX) / 2)),
                         derivative_filter=derivative_filter, **kwargs)
        self.rule_base = FuzzyRuleBase(mode=mode)
        self.smoothing = smoothing
        self.blend_imc = blend_imc
        self.nominal = nominal or imc_pid_gains()
        self.normalized = np.full(3, .5)

    def step(self, setpoint: float, measurement: float) -> tuple[float, PIDGains]:
        error = float(setpoint - measurement)
        de = 0. if self.previous_error is None else error - self.previous_error
        normalized = infer_normalized_gains(error, de,
                                            rule_base=self.rule_base,
                                            previous=self.normalized)
        self.normalized += self.smoothing * (normalized - self.normalized)
        gains = self.GAIN_MIN + (self.GAIN_MAX - self.GAIN_MIN) * self.normalized
        if self.blend_imc < 1:
            nominal = np.array([self.nominal.kp, self.nominal.ki, self.nominal.kd])
            gains = self.blend_imc * gains + (1 - self.blend_imc) * nominal
        self.gains = PIDGains(*map(float, gains))
        return self._calculate(setpoint, measurement, self.gains), self.gains
