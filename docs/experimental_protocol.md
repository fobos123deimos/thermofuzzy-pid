# Reproducible experimental protocol

This repository is an **open engineering study**, not a reconstruction of the source's hardware data. The source was a 2021 thesis; code and illustrative data are newly generated.

The [six-plate visual atlas](DIAGRAMS.md) explains the physical boundary and the implemented protocols. Its [robustness](figures/tikz/05-robustness.pdf) and [optimization](figures/tikz/06-optimization-validation.pdf) plates separate paired synthetic comparisons, fixed return-ratio analysis, training and held-out evaluation. The 1 s configuration below is the baseline; notebook 03 uses 2 s and notebook 04 uses 3 s. The [identification plate](figures/tikz/02-identification.pdf) labels independent validation as a recommendation because notebooks 01/05 report in-sample fit residuals.

## 1. Define a matched scenario

- Nominal FOPDT source parameters: `(K,tau,theta)=(7.624,151.6 s,8.78 s)`.
- Setpoint: 65 °C (from the source).
- Synthetic ambient: 30 °C.
- Synthetic heater command: 0–10 effective input units, with saturation.
- Sampling: `dt=1 s`, duration 3750 s, exact ZOH thermal discretization.
- Two assumed door disturbances: −5 equivalent heater units during `[2000,2060)` s and `[3000,3300)` s. These events deliberately mirror the thesis's approximate opening periods but **not measured amplitudes**.
- One shared random seed per run; zero sensor noise unless otherwise indicated.

## 2. Compare controllers

1. **IMC fixed:** source-derived formula, nominal model identification parameters, derivative on measurement and conditional anti-windup.
2. **Fuzzy sparse:** manually transcribed original consequents, source-specified min/max gain bounds; 7×7 sparse rule table, missing gains held.
3. **Fuzzy dense:** newly interpolated missing consequents, gain-smoothing factor `gamma=0.18` for a transparent baseline; *not* asserted better.
4. **Hybrid/tuned (notebook 04):** optional model-assisted gain blend with differential evolution; train only on predefined training scenarios, hold out another independent scenario.

All controllers share the same plant, actuator limits, derivative filter and disturbance sequence for a fair engineering comparison.

## 3. Metrics and units

- **10–90% rise time:** difference between first crossings of 10% and 90% of the initial 30 °C to 65 °C step, **measured before the first door event**.
- **Time to 60 °C:** first pre-disturbance crossing in seconds, for context with the source's reported threshold.
- **Overshoot:** maximum above 65 °C prior to disturbances, clipped at zero.
- **IAE:** $\sum_k |65-y_k|\Delta t$ in °C·s over the full experiment.
- **Total variation:** $\sum_{k>0}|u_k-u_{k-1}|$ in effective heater units.
- **Door recovery:** elapsed time **after closure** until 30 seconds continuously within ±2 °C of setpoint. This is *not identical to the source paper's threshold-based 3% calculation.*
- **Saturation fraction:** proportion of commanded samples at the actuator minimum or maximum.

## 4. Reproduce results

```
python scripts/generate_data.py
python scripts/run_benchmark.py
python -m pytest -q
```

The table is written to `data/synthetic/benchmark_metrics.csv` and the figure to `images/synthetic_controller_comparison.png`. Recompute and review if you change the code. Notebook outputs are intentionally not committed so the notebooks stay lightweight and avoid confusion between derived figures and source measurements.

## 5. Limitations and next validation steps

A fair comparison against the thesis requires locating synchronized raw TH22/TH37/TH40/TH34 readings, original heater drive and disturbance magnitudes, full MF vertex coordinates, unknown actuator saturation settings, sample time and original Simulink models. Only then can the original reported fit percentages, MSE, 22% and 3% comparisons be independently reproduced. Deeper research should assess overshoot under model mismatch, robust stability, spatial nonuniformity and actuator energy.

## Additional theory-driven experiments (post-thesis extension)

The optional back-calculation anti-windup mode, known-integer-delay ARX estimator, and fixed-linear frequency-domain margin estimator were added after reviewing the researcher's archived theoretical sources. **These additions do not retroactively modify the originally published benchmark table**: its controller configurations and synthetic assumptions remain unchanged. Notebook 05 demonstrates the new routines independently, without reusing measured chamber data or claiming physical validation. See [theoretical foundations](theoretical_foundations.md).
