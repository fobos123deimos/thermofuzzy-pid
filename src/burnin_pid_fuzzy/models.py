"""Reduced-order thermal model, synthetic scenarios, and experiment runner.

The thesis estimated a *combined* model G(s)H(s) = K exp(-theta*s)/(tau*s+1).
Here the delay is assigned to the sensor path for a physical-temperature state,
with the same step response for input/output identification. Nonuniform sensor
fields and door dynamics are not identified and are therefore modeled separately.

![Thermal feedback structure](../assets/thermal-loop.png)

The heater/door channels drive one hypothetical chamber temperature. Sensor
delay and noise affect the measurement used by the controller, not the thermal
state. See `simulate` before comparing the state with measured-temperature
metrics. Door pulses and the allocation of delay are explicit assumptions.

![FOPDT source-parameter step responses](../assets/fopdt-responses.png)

These curves evaluate `fopdt_step_response` for the four source-reported
parameter sets. They are model predictions for a one-unit input, not recovered
experimental records. TH22 and TH40 are not independently identified here.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable
import numpy as np
from .controllers import FixedPID, FuzzyPID, imc_pid_gains


@dataclass(frozen=True)
class Plant:
    """Positive-gain first-order-plus-dead-time parameter record.

    `K` is degrees Celsius per effective heater unit; `tau` and `delay` are
    seconds. The provenance string distinguishes source-reported parameters
    from custom assumptions. Construction rejects nonpositive gain/time
    constant and negative delay; it does not establish physical calibration.
    """
    name: str
    K: float
    tau: float
    delay: float
    provenance: str = "2021 undergraduate thesis, Table/Section 3.1"

    def __post_init__(self):
        if self.K <= 0 or self.tau <= 0 or self.delay < 0:
            raise ValueError("invalid FOPDT parameter")


PLANTS_FROM_THESIS = {
    "TH37": Plant("TH37", 8.7135, 326.18, 13.677),
    "TH34": Plant("TH34", 7.7473, 177.95, 13.064),
    "mean_temperature": Plant("mean_temperature", 7.624, 151.6, 8.78),
    "mean_parameters": Plant("mean_parameters", 8.028, 186.5, 12.5),
}


@dataclass(frozen=True)
class DoorEvent:
    """Assumed input-equivalent cooling pulse on a half-open time interval.

    `start` and `duration` are seconds; `severity <= 0` uses the same effective
    heater units as the controller output. Simultaneous events add. These
    pulses are not an identified door heat-transfer model.
    """
    start: float
    duration: float
    severity: float  # Negative input-equivalent heater demand, assumed.

    def __post_init__(self):
        if self.start < 0 or self.duration <= 0 or self.severity > 0:
            raise ValueError("Door event: start >=0, duration>0, severity<=0")


@dataclass(frozen=True)
class Scenario:
    """Synthetic simulation settings in seconds, Celsius and heater units.

    The default reference is 65 degrees Celsius from a 30-degree ambient.
    `measurement_noise_std` is a Celsius standard deviation for independent
    Gaussian measurement noise. `actuator_max` describes the benchmark and
    metric convention: `simulate_methods` passes it into fresh controllers;
    when calling `simulate` directly, set the controller's own output bounds.
    """
    duration: float = 3750.
    dt: float = 1.
    ambient: float = 30.
    reference: float = 65.
    actuator_max: float = 10.
    measurement_noise_std: float = 0.
    doors: tuple[DoorEvent, ...] = field(default_factory=lambda: (
        DoorEvent(2000., 60., -5.0), DoorEvent(3000., 300., -5.0)))

    def __post_init__(self):
        if self.dt <= 0 or self.duration <= 0 or self.actuator_max <= 0:
            raise ValueError("invalid scenario")
        if self.measurement_noise_std < 0:
            raise ValueError("negative noise std")


def benchmark_scenario() -> Scenario:
    """Return the declared 3750-second, two-door-pulse synthetic scenario."""
    return Scenario()


def simulate(controller: FixedPID | FuzzyPID, plant: Plant | None = None,
             scenario: Scenario | None = None, seed: int = 2021) -> dict[str, np.ndarray]:
    """Exact-ZOH plant discretization with fractional sensor delay interpolation.

    Simulation uses Celsius, seconds and *effective heater units*. All door
    severities, ambient values and actuator limits are illustrative assumptions.

    `controller` is stateful and is advanced in place, without a reset; create
    a fresh instance for each independent run. Its sample period must match
    `scenario.dt`. The seed controls independent Gaussian sensor noise.
    Return equal-length one-dimensional arrays: `time_s`, `temperature_c`
    (physical state), `measurement_c` (delayed/noisy), `control`, `disturbance`,
    parallel gains `kp`, `ki`, `kd`, and `reference_c`. Only the controller
    applies actuator saturation. No hardware or output-temperature protection
    is implemented by this numerical experiment.
    """
    plant = plant or PLANTS_FROM_THESIS["mean_temperature"]
    scenario = scenario or benchmark_scenario()
    if not np.isclose(controller.dt, scenario.dt):
        raise ValueError("controller.dt must equal scenario.dt")
    t = np.arange(0., scenario.duration + scenario.dt * .25, scenario.dt)
    n = len(t)
    temperature = np.empty(n)
    temperature[0] = scenario.ambient
    measurement = np.empty(n)
    heat = np.empty(n)
    disturbance = np.zeros(n)
    gains = np.empty((n, 3))
    rng = np.random.default_rng(seed)
    for event in scenario.doors:
        disturbance[(t >= event.start) & (t < event.start + event.duration)] += event.severity
    alpha = np.exp(-scenario.dt / plant.tau)
    for k in range(n):
        delayed_index = (t[k] - plant.delay) / scenario.dt
        if delayed_index <= 0:
            sensed = temperature[0]
        else:
            lower = min(int(np.floor(delayed_index)), k)
            higher = min(lower + 1, k)
            frac = float(delayed_index - lower) if higher > lower else 0.
            sensed = (1. - frac) * temperature[lower] + frac * temperature[higher]
        measurement[k] = sensed + rng.normal(0., scenario.measurement_noise_std)
        heat[k], g = controller.step(scenario.reference, measurement[k])
        gains[k] = [g.kp, g.ki, g.kd]
        if k < n - 1:
            # Identified model is a first-order *deviation* from ambient.
            effective_input = heat[k] + disturbance[k]
            temperature[k + 1] = (scenario.ambient +
                                  (temperature[k] - scenario.ambient) * alpha +
                                  plant.K * effective_input * (1. - alpha))
    return {"time_s": t, "temperature_c": temperature,
            "measurement_c": measurement, "control": heat,
            "disturbance": disturbance, "kp": gains[:, 0],
            "ki": gains[:, 1], "kd": gains[:, 2],
            "reference_c": np.full(n, scenario.reference)}


def simulate_methods(plant=None, scenario=None, seed: int = 2021):
    """Return three matched synthetic runs with fresh controller state.

    Dictionary keys identify fixed IMC, source-derived sparse Fuzzy-PID and a
    new dense/smoothed rule variant. Each value follows `simulate`'s array
    schema. All methods receive the same seed, plant, scenario and actuator
    bounds. The experiment does not reproduce the thesis timing percentages.
    """
    scenario = scenario or benchmark_scenario()
    plant = plant or PLANTS_FROM_THESIS["mean_temperature"]
    methods = {
        "IMC-PID": FixedPID(imc_pid_gains(plant.K, plant.tau, plant.delay),
                            dt=scenario.dt, u_max=scenario.actuator_max),
        "Thesis Fuzzy-PID (sparse)": FuzzyPID(mode="sparse", smoothing=1., dt=scenario.dt,
                                     u_max=scenario.actuator_max),
        "Fuzzy-dense-smoothed": FuzzyPID(mode="dense", smoothing=.18, dt=scenario.dt,
                                         u_max=scenario.actuator_max),
    }
    return {name: simulate(ctrl, plant, scenario, seed) for name, ctrl in methods.items()}


def fopdt_step_response(t: Iterable[float], plant: Plant, amplitude: float = 1.,
                        ambient: float = 30.) -> np.ndarray:
    """Evaluate the delayed analytical input/output step response in Celsius.

    `t` is a one-dimensional sequence in seconds; output has the same shape.
    `amplitude` uses effective heater units. The pre-delay response equals
    `ambient`. This combined process/sensor response is useful for visualizing
    a parameter set, not for validating the assumed physical delay allocation.
    """
    t = np.asarray(t, dtype=float)
    active = np.maximum(t - plant.delay, 0.)
    return ambient + plant.K * amplitude * (1. - np.exp(-active / plant.tau))
