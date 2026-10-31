"""Regenerate 05_theory_arx_antiwindup_robustness.ipynb (source-based tutorial)."""
from pathlib import Path
import nbformat as nbf

root = Path(__file__).resolve().parents[1]
name = '05_theory_arx_antiwindup_robustness.ipynb'
url = f'https://colab.research.google.com/github/fobos123deimos/thermofuzzy-pid/blob/main/notebooks/{name}'
notebook = nbf.v4.new_notebook()


def md(src):
    notebook.cells.append(nbf.v4.new_markdown_cell(src))


def py(src):
    notebook.cells.append(nbf.v4.new_code_cell(src))


md(f'''# ThermoFuzzy-PID · 05 · Theory, ARX identification and robustness

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)]({url})

**Research-driven tutorial.** This notebook connects the original 2021 UFC thesis to *specific theoretical sources* in the author's Google Drive research archive and Dropbox MATLAB collection. The private source documents are **not included** here: their full titles and boundaries are listed in [`docs/theoretical_foundations.md`](https://github.com/fobos123deimos/thermofuzzy-pid/blob/main/docs/theoretical_foundations.md).

**Provenance:** only the model-parameter triples and described theoretical methods are source-reported. All waveforms, digital anti-windup variants, sampling intervals, sensor noise and robustness plots are **new synthetic examples**, not recovered chamber measurements. The output should not be cited as validation of the original thesis or evidence of an actual industrial system.''')
py('''from pathlib import Path
import sys, subprocess
local = next((p for p in [Path.cwd() / 'src', Path.cwd().parent / 'src']
              if (p / 'burnin_pid_fuzzy').is_dir()), None)
if local is not None:
    sys.path.insert(0, str(local.resolve()))
else:
    subprocess.check_call([sys.executable, '-m', 'pip', '-q', 'install',
                           'git+https://github.com/fobos123deimos/thermofuzzy-pid.git'])
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from burnin_pid_fuzzy.identification import simulate_sampled_arx, fit_first_order_arx
from burnin_pid_fuzzy.controllers import FixedPID, PIDGains, imc_pid_gains
from burnin_pid_fuzzy.models import PLANTS_FROM_THESIS, Scenario, DoorEvent, simulate
from burnin_pid_fuzzy.robustness import linear_loop_response, assess_fixed_pid_robustness
np.set_printoptions(precision=5, suppress=True)
''')
md(r'''## 1 · FOPDT and zero-order-hold sampling

The thesis fits a **combined plant/sensor** first-order-plus-dead-time model:

$$G(s)H(s)=\frac{K e^{-\theta s}}{\tau s +1}, \qquad K>0,\ \tau>0,\ \theta\geq0.$$

For a zero-order-held input over $\Delta t$ and *integer* input delay $m$, the **new instructional** first-order recursion for temperature deviation $x=T-T_a$ is

$$x[k]=a\,x[k-1]+b\,u[k-1-m], \qquad
 a=e^{-\Delta t/\tau}, \qquad b=K(1-a).$$

The historical research notes distinguish ARX, ARMAX, autoregressive and moving-average models. This notebook implements only the **ARX(1,1,m+1)** special case. Arbitrary original reported continuous delays must **not** be converted into integer $m$ without an explicit sampling convention.''')
md(r'''## 2 · Identify $a$ and $b$ with ordinary least squares

With $\phi_k=(x[k-1],u[k-1-m])^T$, minimize

$$\hat\beta=\arg\min_{\beta=(a,b)^T}\sum_k (x[k]-\phi_k^T\beta)^2,
\qquad\hat\beta=\Phi^+\mathbf{x}.$$

The parameters map back to FOPDT **only under the model assumptions**:

$$\boxed{\tau=-\frac{\Delta t}{\ln(a)},\quad K=\frac{b}{1-a},\quad\theta=m\Delta t},\qquad0<a<1,\ b>0.$$

A varying heater input supplies excitation. In the original work, the sampling period, original actuator units and raw sensor data are not available; the following is therefore a synthetic demonstration.''')
py('''p=PLANTS_FROM_THESIS['mean_temperature']
dt, m = 2.0, 5  # m*dt = 10 s, NOT the thesis-reported 8.78 s
n=1000
u=np.zeros(n)
u[30:200]=2
u[200:400]=4
u[400:600]=1
u[600:850]=5
u[850:]=2
synthetic=simulate_sampled_arx(u,K=p.K,tau_s=p.tau,dt=dt,delay_samples=m)
rng=np.random.default_rng(2026)
observed=synthetic+rng.normal(0,.01,n)
fit=fit_first_order_arx(u,observed,dt=dt,delay_samples=m)
summary=pd.DataFrame([{'quantity':'K (°C/effective input)', 'truth':p.K, 'estimate':fit.steady_state_gain},
                      {'quantity':'tau (s)','truth':p.tau,'estimate':fit.tau_s},
                      {'quantity':'theta (s)','truth':m*dt,'estimate':fit.dead_time_s},
                      {'quantity':'one-step RMSE (°C)','truth':np.nan,'estimate':fit.rmse_c}])
print(summary.round(4).to_string(index=False))
fig,ax=plt.subplots(figsize=(10,3.4))
ax.plot(np.arange(n)*dt,observed,label='Noisy synthetic readings',lw=1)
ax.plot(np.arange(n)*dt,synthetic,label='Exact synthetic ZOH model',ls='--',lw=1)
ax.set(xlabel='Time (s)',ylabel='Temperature (°C)',title='Excited ARX model: synthetic data only')
ax.grid(alpha=.25);ax.legend();plt.show()''')
md(r'''## 3 · Anti-windup: two mathematically distinct implementations

When the unsaturated command exceeds the actuator limits,

$$u_{\rm sat}[k]=\operatorname{clip}(u_{\rm raw}[k],u_{\min},u_{\max}),$$

the integral may accumulate even though the actuator cannot respond. The original **PI/PID preliminary report (Google Drive)** specifically discusses *back-calculation*. Our earlier Python implementation used conditional integration. Both are available for comparison:

- **Conditional integration:** discard the trial integral increment only if it would push further into saturation.
- **Back-calculation:** use $I[k]=I[k-1]+\Delta t(K_i[k]e[k]+[u_{\rm sat}^{\rm trial}-u_{\rm raw}^{\rm trial}]/T_t)$.

$T_t$ is a **new, user-selected tracking constant**, not a value recovered from the report. The results below are not guaranteed to be better for every operating condition.''')
py('''scenario=Scenario(duration=1100.,dt=1.,doors=(DoorEvent(700.,75.,-4.),))
methods={
  'Conditional integration': FixedPID(imc_pid_gains(),dt=1.,anti_windup='conditional'),
  'Back-calculation (Tt=10s)': FixedPID(imc_pid_gains(),dt=1.,anti_windup='back_calculation',tracking_time=10.),
}
results={name:simulate(ctrl,scenario=scenario) for name,ctrl in methods.items()}
fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True)
for name,res in results.items():
    axes[0].plot(res['time_s'],res['measurement_c'],label=name)
    axes[1].plot(res['time_s'],res['control'],label=name)
axes[0].axhline(scenario.reference,color='black',ls='--',lw=1)
for ax in axes:
    ax.grid(alpha=.25)
    ax.legend()
axes[0].set_ylabel('Temperature (°C)')
axes[1].set(xlabel='Time (s)',ylabel='Effective heater command')
plt.tight_layout();plt.show()''')
md(r'''## 4 · Frequency-domain robustness: $M_s$, gain margin, phase margin

The PI/PID preliminary report discusses **GM $>1.7$, $M_s<2.2$, PM $>30^\circ$** as *design recommendations*, not universal mathematical guarantees.

For a **fixed, linearized, unsaturated** PID with derivative measurement filtering,

$$C_y(j\omega)=K_p+\frac{K_i}{j\omega}+K_d\frac{j\omega}{1+T_f j\omega},$$
$$L(j\omega)=\frac{K e^{-j\omega\theta}}{1+j\omega\tau}C_y(j\omega),\qquad
S(j\omega)=\frac{1}{1+L(j\omega)},\qquad
M_s=\sup_{\omega\ge0}|S(j\omega)|.$$

GM and PM are evaluated at loop phase and unity-gain crossings, respectively. The computational approximations sample a **finite frequency grid**, select the first crossing, and can miss later crossings. These are **not** fuzzy-controller stability certifications.''')
py('''p=PLANTS_FROM_THESIS['mean_temperature']
omega=np.logspace(-5,0,1800)
models={}
for lam in [12.,35.3273,75.]:
    gains=imc_pid_gains(K=p.K,tau=p.tau,theta=p.delay,lam=lam)
    L=linear_loop_response(p,gains,omega)
    S=1/(1+L)
    model=assess_fixed_pid_robustness(p,gains)
    models[lam]=(S,model)
rows=[]
for lam,(_,margins) in models.items():
    rows.append({'lambda_s':lam,'Ms_grid':margins.maximum_sensitivity,
                 'gain_margin_ratio':margins.gain_margin,
                 'phase_margin_deg':margins.phase_margin_deg})
print(pd.DataFrame(rows).round(3).to_string(index=False))
fig,ax=plt.subplots(figsize=(9,3.7))
for lam,(S,margins) in models.items():
    ax.semilogx(omega,np.abs(S),label=f'IMC lambda={lam:.2f} s')
ax.axhline(2.2,ls='--',lw=1,color='gray',label='Historical report target Ms < 2.2')
ax.set(xlabel='Angular frequency (rad/s)',ylabel='|S(jω)|',title='Fixed linear sensitivity (synthetic nominal model)')
ax.grid(alpha=.3);ax.legend();plt.show()''')
md(r'''## 5 · What the available sources do *not* establish

The MATLAB/Simulink notes in Dropbox support the theoretical use of transfer functions, `bode`, `margin` and graphical simulation, but they do **not** prove that the generated modern `.slx` models run without validation. The De Luca (2004) dissertation highlights thermal-profile measurement and uncertainty: **mean-temperature tracking is not a proof of spatial uniformity, hardware reliability, or certification**.

The original reported **22% faster rise** and **3% faster disturbance recovery** belong to the thesis's historical experimental/simulation conditions. They have not been reproduced by this notebook.

### Source navigation

See [theory and evidence hierarchy](https://github.com/fobos123deimos/thermofuzzy-pid/blob/main/docs/theoretical_foundations.md), [source audit](https://github.com/fobos123deimos/thermofuzzy-pid/blob/main/docs/source_audit.md) and [full provenance table](https://github.com/fobos123deimos/thermofuzzy-pid/blob/main/docs/source_traceability.md). Bibliographic titles of private files are given there; no source PDF has been copied into GitHub.''')
notebook.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
                   'language_info':{'name':'python'},'colab':{'name':name,'provenance':[]}}
nbf.validate(notebook)
output=root/'notebooks'/name
output.write_text(nbf.writes(notebook),encoding='utf8')
print('Wrote',output,'with',len(notebook.cells),'cells')
