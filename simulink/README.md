# Simulink: fully closed-loop model generation

Open MATLAB with **Simulink** and the MATLAB Function block capability (Stateflow). Run:

```matlab
cd('simulink');
build_burnin_simulink;
open_system('burnin_fuzzy_dense.slx');
sim('burnin_fuzzy_dense');
```

The script builds `burnin_imc.slx` and `burnin_fuzzy_dense.slx` with feedback, a thermal transfer function, transport delay, disturbances, a saturation-aware PID and To Workspace sinks. Both controllers are embedded MATLAB Function block algorithms; the Fuzzy model contains the dense/interpolated Mamdani rule matrix, M-o-M defuzzification, and gain smoothing. It does **not** require Fuzzy Logic Toolbox.

- Constant setpoint: 65 °C (from TCC Section 3.4).
- Identified combined-model parameters: `K=7.624`, `tau=151.6 s`, `theta=8.78 s` (TCC Section 3.1).
- Ambient `30 °C`, actuator units `0..10`, and disturbance amplitudes are *assumed* for synthetic experiments.
- Approximation: delay is represented in the sensor branch; the plant is a reduced-order single-temperature system.
- Time is seconds, solver uses fixed 1-second forward Euler (`ode1`).

**Validation status:** The `.m` generator scripts are provided; `.slx` files must be generated on a licensed MATLAB installation. MATLAB and Simulink were unavailable in the development environment, so compile/runtime verification is still pending. See the Python notebooks for executed tests and results.

## Reference

MathWorks documentation: [Programmatic Modeling](https://www.mathworks.com/help/simulink/programmatic-modeling.html), [Stateflow.EMChart Script property](https://www.mathworks.com/help/simulink/slref/stateflow.emchart.html).
