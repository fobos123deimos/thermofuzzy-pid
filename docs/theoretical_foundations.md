# Theoretical foundations and research-source audit

**Scope.** This document develops the mathematical foundation of ThermoFuzzy-PID from the 2021 undergraduate thesis and related material found in the researcher's connected Google Drive and Dropbox archives. These private study files are **not distributed**; descriptions below are paraphrases, not copies. Sections explicitly distinguish **source-reported claims**, **derived mathematics**, and **new implementations/hypotheses**. The test environment contains no original chamber measurements or MATLAB/Simulink runtime.

## 1. Source hierarchy and provenance

| Evidence type | Source reviewed | Use in this project |
|---|---|---|
| **Primary thesis** | M. G. Cordeiro, *Projeto de um Controlador PID-Fuzzy para a Câmara de Burn-in*, UFC, 2021 | Identified parameter tables, controller comparison, fuzzy rules, gain bounds, simulation description |
| **Research-group preliminary note (Google Drive, `TCC`)** | *Relatório Parcial 1 — Controle de Temperatura Média em Câmara de Burn-in* | Nonuniform temperature, system identification, ARX structures, IMC trade-offs; earlier draft may differ from final thesis |
| **Research-group preliminary note (Google Drive, `TCC`)** | *Relatório Parcial 2 — Implementação de Algoritmos PI e PID em CLP — Versão 2* | Anti-windup by back-calculation, robustness criteria, Bode/Nyquist margins, PLC implementation context |
| **Teaching references (Google Drive, `TCC`)** | *Identificação de Sistemas Dinâmicos — Slides*; *Identificação de Sistemas — Aula 5*; *Modelos de Processos e de Perturbação — AR, MA, ARX, ARMA e ARMAX* | Discrete model structure, input excitation, least squares, offline vs recursive identification |
| **Source-rule corroboration (Google Drive, `TCC`)** | *Tabela Verdade* (editable Google Doc) | A second textual copy of the sparse linguistic rule base; the published thesis figure remains the primary source |
| **Thermal reliability (Google Drive, `TCC`)** | L. V. De Luca, *Recomendações para a Implementação de Ensaios de Estresse Térmico Voltados à Confiabilidade de Hardwares Eletrônicos*, UFSC, **master's dissertation**, 2004 | Distinguish chamber tracking from uniformity, measurement uncertainty and reliability qualification |
| **MATLAB/Simulink study (Dropbox, shared technical archive)** | *Apostila de MATLAB 8.1 — PET Engenharia Elétrica UFC*, 2014, esp. chs. 14–15 | MATLAB transfer functions, `bode`, `margin`, `stepinfo`, block-diagram simulation |
| **Numerical methods (Dropbox, shared technical archive)** | *Curso de MATLAB 5.1 — Introdução à Solução de Problemas de Engenharia*, UERJ, 2nd ed. | Matrix/least-squares computational workflow, integration and difference equations; historical software-version context |

**Access and copyright.** Links to personal/shared-archive files and the files themselves have intentionally **not** been placed in the public repository. Scientific references identify works without giving an impression that their complete texts are openly redistributable. Bibliographic titles retain their original language for provenance.

## 2. Thermal model and physical interpretation

The thesis approximates the **combined process and temperature-sensor dynamics** with a first-order-plus-dead-time (FOPDT) transfer function:

$$
\frac{Y_s(s)}{U(s)}=G(s)H(s)=\frac{K e^{-\theta s}}{\tau s+1}.
$$

Here $K$ is the gain, $\tau>0$ (seconds) the effective time constant, and $\theta\geq0$ (seconds) the effective delay. The source reports **four fitted cases**; the *mean measured temperature* case is $K=7.624$, $\tau=151.6\,\mathrm s$, $\theta=8.78\,\mathrm s$. **The mean of four sensor readings is not equivalent to the mean of four fitted transfer-function parameters**; the thesis lists these as different cases.

A convenient **new simulation assumption** is to put the delay in the sensor path and model a single chamber state $T(t)$:

$$
\tau \dot T(t)=-(T(t)-T_a)+K\big[u(t)+d(t)\big],\qquad
 y(t)=T(t-\theta)+\eta(t).
$$

The original identified $G(s)H(s)$ does **not** uniquely determine whether the delay belongs to the plant, sensor, transport or a combination. Door-opening heat loss $d(t)$, ambient $T_a$, and heater command units are not calibrated by the provided data. We explicitly label these values synthetic. With constant sampled input over $\Delta t$ (zero-order hold),

$$
T[k+1]-T_a=a\,[T[k]-T_a]+K(1-a)\,[u[k]+d[k]],\qquad
 a=e^{-\Delta t/\tau}.
$$

The single-zone approximation does not represent spatial nonuniformity: $\bar T(t)=\tfrac14\sum_{j=1}^4 T_j(t)$ may track a setpoint even when some locations do not. De Luca's dissertation discusses thermal profiling, measurement uncertainty and how uniformity affects credible stress testing. **Regulating average temperature is not proof of thermal uniformity, stress qualification, or electronic-device reliability.**

## 3. ARX: discrete identification before controller tuning

The preliminary notes and two identification slide sets motivate an **autoregressive model with exogenous input (ARX)**. For a known integer input delay $m\geq0$, define $x[k]=T[k]-T_a$ and

$$
x[k]=a\,x[k-1]+b\,u[k-1-m]+\varepsilon[k],
\quad \phi[k]=\begin{bmatrix}x[k-1] & u[k-1-m]\end{bmatrix}^{\!T}.
$$

Minimizing one-step prediction error gives the ordinary least-squares estimator

$$
\hat{\boldsymbol\beta}
=\underset{\boldsymbol\beta}{\arg\min}
\sum_{k=m+1}^{N-1}\big(x[k]-\phi[k]^T\boldsymbol\beta\big)^2,
\quad\boldsymbol\beta=(a,b)^T,
\quad\hat{\boldsymbol\beta}=\Phi^+\mathbf x.
$$

Use a rank-aware least-squares solver instead of directly inverting $\Phi^T\Phi$. The toy ARX model is identifiable only when the input excites it sufficiently and the regressors have full column rank. For exact zero-order-held FOPDT dynamics **and** a known integer delay, the physically constrained mapping is

$$
\boxed{\tau=-\frac{\Delta t}{\ln a}},\quad
\boxed{K=\frac{b}{1-a}},\quad
\boxed{\theta=m\Delta t},\qquad 0<a<1,\ b>0.
$$

`src/burnin_pid_fuzzy/identification.py` implements this limited structure. **It is not identical to the original MATLAB System Identification Toolbox setup**: the 2021 thesis lists discrete numerator/denominator coefficients and noninteger delays, but the original sample period, raw input trajectories, and full identification configuration are unavailable. Its numeric coefficients therefore cannot be transformed unambiguously into a new estimated parameter table. White noise on the *output* can also bias ordinary least squares through noisy lagged output regressors; use independent validation and more appropriate identification methods when that matters. Our notebook tests integer delays with newly generated inputs and synthetic measurements.

## 4. PID conventions and anti-windup

The thesis's ISA/standard parameters can be expressed as a **parallel (independent) PID**:

$$
u_{\rm raw}(t)=K_pe(t)+I(t)-K_d\,\frac{d y_f(t)}{dt},\qquad
\dot I(t)=K_i e(t),\qquad
K_i=K_p/T_i,\quad K_d=K_pT_d.
$$

Derivative action on the measurement, rather than the setpoint, is an implementation convention chosen to avoid derivative kick. A filter attenuates measurement-noise amplification; with $T_f>0$, its small-signal transfer factor is $s/(1+T_fs)$. In the **discrete, adaptive** implementation, integral action is the *sum of individual $K_i[k]e[k]\Delta t$ increments*; it is not a varying $K_i[k]$ multiplied by the full error-history integral.

The actuator output satisfies $u[k]=\operatorname{clip}(u_{\rm raw}[k],u_{\min},u_{\max})$. The existing project uses **conditional integration** as its default: when the proposed integral update would drive the controller further into saturation, reject that increment. This is *not* the same method described in the Drive's *Relatório Parcial 2*, which explicitly mentions **back-calculation**. We have therefore added it as a separately selectable research implementation:

$$
\boxed{I[k]=I[k-1]+\Delta t\left(K_i[k]e[k]+\frac{u_{\rm sat}^{\rm trial}[k]-u_{\rm raw}^{\rm trial}[k]}{T_t}\right)}.
$$

$T_t$ (seconds) is the **tracking time constant**, distinct from $T_i$ (integral time) and $T_f$ (derivative filter). The note supports the strategy, not a unique discretization or $T_t$ value; these are explicitly **new design decisions**. Both methods are bounded by the same actuator saturation and neither is guaranteed to outperform the other across all nonlinear operating conditions.

**Implementation:** `FixedPID(..., anti_windup="conditional")` (default) or `FixedPID(..., anti_windup="back_calculation", tracking_time=10.0)`; `FuzzyPID` inherits these options.

## 5. IMC and robustness in time and frequency domains

The thesis gives the IMC tuning relationships:

$$
K_p=\frac{\tau+\theta/2}{K(\lambda+\theta)},\qquad
T_i=\tau+\theta/2,\qquad
T_d=\frac{\tau\theta}{2\tau+\theta}.
$$

The filter/tuning constant $\lambda>0$ sets a trade-off between closed-loop speed and model sensitivity; it is **not** a universal optimum. The earlier PI/PID engineering report considers gain margin (GM), phase margin (PM) and maximum sensitivity $M_s$ and quotes **design recommendations** (not system guarantees): $\mathrm{GM}>1.7$, $\mathrm{PM}>30^\circ$, and $M_s<2.2$.

For a fixed-gain linear feedback loop, write

$$
G(j\omega)=\frac{Ke^{-j\omega\theta}}{1+j\omega\tau},\quad
C_y(j\omega)=K_p+\frac{K_i}{j\omega}+\frac{K_dj\omega}{1+T_fj\omega},\quad
L=GC_y.
$$

The sensitivity function is

$$
S(j\omega)=\frac{1}{1+L(j\omega)},\qquad
M_s=\sup_{\omega\geq0}|S(j\omega)|.
$$

A practical numerical estimate computes $\max_{\omega\in\Omega}|S(j\omega)|$ on an explicit frequency grid $\Omega$. Gain margin is the reciprocal loop magnitude at a phase crossing of $-180^\circ$; phase margin is $180^\circ+\arg L$ at a unity-magnitude crossing, if these are present and appropriately selected. Our Python function computes **first-crossing, grid-dependent approximations**, and the MATLAB companion uses `margin` and `freqresp` with the Control System Toolbox. **Neither method establishes global stability of the nonlinear, saturated, time-varying fuzzy controller.** Multiple crossovers and delay require careful Nyquist inspection.

In `src/burnin_pid_fuzzy/robustness.py`, only **fixed linear gains** are assessed. The Matlab counterpart is `matlab/assess_fixed_pid_robustness.m`. Time-domain robustness comparisons in notebook 03 remain explicitly synthetic Monte Carlo exercises with assumed uncertainties.

## 6. Fuzzy inference: what comes from the thesis

The thesis uses two inputs, nonnegative $|e|$ and signed $\Delta e$, a 7-term linguistic partition for each input, and three normalized output gains $K'_p,K'_i,K'_d\in[0,1]$ with 5 output terms. Mamdani inference uses min for AND/implication and max for aggregation:

$$
\alpha_j=\min\left[\mu_{A_j}(|e|),\mu_{B_j}(\Delta e)\right],\qquad
\mu_{\rm out}(z)=\max_j\min\left[\alpha_j,\mu_{C_j}(z)\right].
$$

With a sampled output grid, the **mean of maxima** (M-o-M) yields

$$
z^*=\frac{1}{|\mathcal M|}\sum_{z\in\mathcal M}z,
\qquad \mathcal M=\arg\max_z\mu_{\rm out}(z),
$$

then $K_j=K_{j,\min}+(K_{j,\max}-K_{j,\min})K'_j$. The original rule table deliberately omits two full columns and several individual gain assignments. Our `sparse` mode holds those gains; the optional `dense` interpolation mode and gain-smoothing filter are **new research hypotheses**, not rules recovered from the thesis or Drive document. The exact numeric coordinates for all triangular/trapezoidal membership-function breakpoints are not tabulated in the original source and remain assumed.

The editable *Tabela Verdade* document in Drive corroborates the presence of omitted columns and the overall linguistic rule structure; one cell is textually ambiguous (repeated derivative-gain label), so the final thesis figure remains the primary reference. We do not silently fill ambiguous cells using assumptions.

## 7. Source discrepancies and responsible interpretation

1. **Draft versus thesis:** *Relatório Parcial 1* describes preliminary models and different headings/numbers in places. The final thesis is authoritative for the figures and tabulated parameters used in `PLANTS_FROM_THESIS`.
2. **Validation MSE:** An earlier partial note has a value rendered as `0.1112` in one place; the final thesis gives `0.01112` for the TH34 validation. Neither can be verified without the raw measurements; the program **does not silently resolve** this discrepancy or claim to reproduce the original MSE.
3. **Adapting ARX:** Discrete coefficient lists and their printed delays cannot be treated as directly reconstructible without sampling, preprocessing and excitation details.
4. **Historical anti-windup:** The earlier engineering report uses back-calculation. The Python program originally used conditional integration. These are explicitly separate implementations with adjustable tracking and filtering parameters.
5. **Reliability source type:** De Luca (2004) is identified as a **master's dissertation** in the recovered title pages, whereas the thesis reference list characterizes it differently. The public theoretical reference uses the verified dissertation status without altering the archived thesis.
6. **Computational sources:** The PET/UFC and UERJ MATLAB documents describe MATLAB syntax and mathematics. They are supporting **study resources**, not proof that a generated Simulink file works in a recent licensed MATLAB release.

## 8. Reproducible checks and next empirical validation

```bash
python -m pip install -e '.[notebook,test]'
python -m pytest -q
```

To validate on real equipment, collect synchronized logged measurements from sensors TH22/TH34/TH37/TH40, actual heater actuator units, sensor calibrations, door-opening schedules, ambient heat-loss parameters, sample period and fault-interlock information. Use distinct identification, tuning and held-out physical validation periods. Compare multiple controllers under identical qualified conditions before making performance, reliability or energy claims. **No uncontrolled thermal-hardware tests are prescribed by this repository.**
