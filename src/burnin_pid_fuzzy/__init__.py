r"""ThermoFuzzy-PID: thermal models, adaptive control and inspectable experiments.

Python reference for the research software accompanying the repository's
independent reconstruction of Matheus Gomes Cordeiro's 2021 undergraduate
thesis, *Projeto de um Controlador PID-Fuzzy para a Câmara de Burn-in*.
Reported model parameters, reconstructed assumptions and new experiments are
kept distinct. All generated time series are synthetic.

## Start with the physical loop

![Thermal process and information paths](assets/thermal-loop.png)

The single-state thermal approximation uses temperature in degrees Celsius,
time in seconds, and effective heater input units:

$$
\tau\dot T=-(T-T_a)+K(u+d),\qquad
y(t)=T(t-\theta)+\eta(t).
$$

This allocation of the combined fitted delay to measurement is an explicit
modeling choice. The actuator scale and door-loss pulses are assumptions;
there are no original sensor records in this package.

## Follow a complete experiment

After installing the repository with `python -m pip install -e .`:

```python
from burnin_pid_fuzzy import Plant, Scenario, FixedPID, imc_pid_gains, simulate, evaluate

plant = Plant("declared model", K=7.624, tau=151.6, delay=8.78)
scenario = Scenario()
controller = FixedPID(imc_pid_gains(plant.K, plant.tau, plant.delay), dt=scenario.dt)
trace = simulate(controller, plant, scenario, seed=2021)
metrics = evaluate(trace, scenario)
assert len(trace["time_s"]) == 3751
assert metrics["IAE_c_s"] > 0
```

Construct a new controller for each run: controller state is advanced in place.
Use `burnin_pid_fuzzy.models.simulate_methods` for the matched three-controller
comparison shown below.

![Synthetic matched controller comparison](assets/synthetic_controller_comparison.png)

Read the curve and the metric together: lower integrated error, faster first
rise and faster door recovery are different criteria. Filling missing fuzzy
rules is an experiment and does not guarantee a better result.

## API map

| Module | Question answered |
|---|---|
| `burnin_pid_fuzzy.models` | Which thermal state, delay, input and disturbance are simulated? |
| `burnin_pid_fuzzy.controllers` | How are IMC gains, saturation, anti-windup and fuzzy scheduling applied? |
| `burnin_pid_fuzzy.fuzzy` | Which rules fire, which outputs are held and how is mean-of-maxima evaluated? |
| `burnin_pid_fuzzy.identification` | How is a stable first-order ARX model fitted for a known integer delay? |
| `burnin_pid_fuzzy.metrics` | Which trajectory interval and information define each reported metric? |
| `burnin_pid_fuzzy.robustness` | What do sampled fixed-linear-loop margins establish? |

## Learn, inspect and reproduce

- [Five notebooks and Colab links](https://github.com/fobos123deimos/thermofuzzy-pid#google-colab-notebooks)
- [Theoretical foundations](https://github.com/fobos123deimos/thermofuzzy-pid/blob/main/docs/theoretical_foundations.md)
- [Experimental protocol](https://github.com/fobos123deimos/thermofuzzy-pid/blob/main/docs/experimental_protocol.md)
- [Source traceability](https://github.com/fobos123deimos/thermofuzzy-pid/blob/main/docs/source_traceability.md)
- [MATLAB implementations](https://github.com/fobos123deimos/thermofuzzy-pid/tree/main/matlab)
- [Simulink generator and execution limits](https://github.com/fobos123deimos/thermofuzzy-pid/blob/main/simulink/README.md)
- [Rebuilding this illustrated reference](https://github.com/fobos123deimos/thermofuzzy-pid/blob/main/docs/API_DOCUMENTATION.md)

The package's functions are exported below for convenience; each module page
adds its full implementation context. Numerical checks do not certify hardware
safety, reproduce the thesis's measured timing claims or validate adaptive
controller stability. The fixed-loop analysis applies only to its declared
linear, unsaturated, fixed-gain model.
"""
from .models import PLANTS_FROM_THESIS, Plant, DoorEvent, Scenario, simulate, benchmark_scenario
from .controllers import PIDGains, FixedPID, FuzzyPID, imc_pid_gains
from .fuzzy import FuzzyRuleBase, infer_normalized_gains
from .metrics import evaluate
from .identification import ARXEstimate, fit_first_order_arx, simulate_sampled_arx
from .robustness import RobustnessMargins, assess_fixed_pid_robustness, linear_loop_response

__all__ = [
    "PLANTS_FROM_THESIS", "Plant", "DoorEvent", "Scenario", "simulate",
    "benchmark_scenario", "PIDGains", "FixedPID", "FuzzyPID", "imc_pid_gains",
    "FuzzyRuleBase", "infer_normalized_gains", "evaluate",
    "ARXEstimate", "fit_first_order_arx", "simulate_sampled_arx",
    "RobustnessMargins", "assess_fixed_pid_robustness", "linear_loop_response"
]
