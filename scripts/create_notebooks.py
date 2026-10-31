"""Create the teaching/research notebooks with Markdown and Colab entry points.

Notebooks are checked in to the repository. Re-run only to regenerate sources.
"""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://colab.research.google.com/github/fobos123deimos/thermofuzzy-pid/blob/main/notebooks/"


def make(name, title, intro, cells):
    badge = f'[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)]({BASE}{name})'
    start = f'# ThermoFuzzy-PID · {title}\n\n{badge}\n\n{intro}\n\n> **Data provenance:** experiments use deterministic synthetic thermal signals and parameters reported in a 2021 undergraduate thesis. No original sensor time series have been recovered; numerical results do not reproduce or validate the published curves.'
    setup = '''# Import local editable source, or install the repository in Google Colab.
from pathlib import Path
import sys, subprocess
candidates = [Path.cwd() / "src", Path.cwd().parent / "src"]
local_src = next((p for p in candidates if (p / "burnin_pid_fuzzy").exists()), None)
if local_src is not None:
    sys.path.insert(0, str(local_src.resolve()))
else:
    subprocess.check_call([sys.executable, "-m", "pip", "-q", "install", "git+https://github.com/fobos123deimos/thermofuzzy-pid.git"])
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from burnin_pid_fuzzy.models import (Plant, Scenario, DoorEvent, PLANTS_FROM_THESIS,
                                      fopdt_step_response, simulate, simulate_methods)
from burnin_pid_fuzzy.controllers import FuzzyPID, FixedPID, imc_pid_gains
from burnin_pid_fuzzy.fuzzy import FuzzyRuleBase, infer_normalized_gains, membership_degrees
from burnin_pid_fuzzy.metrics import evaluate
np.set_printoptions(precision=4, suppress=True)
'''
    doc = nbf.v4.new_notebook()
    doc.cells = [nbf.v4.new_markdown_cell(start), nbf.v4.new_code_cell(setup)]
    for kind, content in cells:
        doc.cells.append(nbf.v4.new_markdown_cell(content) if kind == "md" else nbf.v4.new_code_cell(content))
    doc.metadata = {"kernelspec": {"name": "python3", "language": "python", "display_name": "Python 3"},
                    "language_info": {"name": "python"},
                    "colab": {"name": name, "provenance": []}}
    nbf.validate(doc)
    target = ROOT / "notebooks" / name
    target.write_text(nbf.writes(doc), encoding="utf8")
    print("Wrote", target)


make("01_thermal_model_identification.ipynb", "01 · Thermal model & system identification",
     "From the first-order-plus-dead-time model of the burn-in chamber to a reproducible synthetic step-test and nonlinear least-squares identification.", [
("md", r'''## 1. Physical model and thesis provenance

The 2021 undergraduate thesis used a first-order-plus-dead-time approximation for the **combined plant and sensor** response (Eq. 2.1):

$$G(s)H(s)=\frac{K e^{-\theta s}}{\tau s+1}.\tag{1}$$

For a single unit heater step $u(t)=\Delta u\,1_{t\ge0}$ starting from ambient temperature $T_a$, the assumed scalar step response is

$$T_{\mathrm{sensor}}(t)=T_a+K\Delta u\left(1-e^{-(t-\theta)_+/\tau}\right),\quad (x)_+=\max(x,0).\tag{2}$$

The parameters reported in **Section 3.1 of the thesis, pages 30–32** are shown below. These are *reported estimates*, not raw training measurements.'''),
("code", '''reported = pd.DataFrame([{"case": key, "K": p.K, "tau_s": p.tau, "theta_s": p.delay}
                         for key,p in PLANTS_FROM_THESIS.items()])
print(reported.to_string(index=False))'''),
("md", "## 2. Construct an explicitly synthetic four-sensor dataset\n\nTH37 and TH34 use published parameter estimates. TH22 and TH40 parameter choices are **new assumptions** (their individual values were not listed). Gaussian noise and random seed are fixed for teaching purposes. The four-sensor average should **not** be interpreted as matching the paper's separately identified mean-temperature transfer function."),
("code", '''rng = np.random.default_rng(2021)
t = np.arange(0,3751,5,dtype=float)
assumed = {"TH22": Plant("TH22",6.85,135.,7.5,"synthetic assumption"),
           "TH40": Plant("TH40",7.1852,155.,8.5,"synthetic assumption")}
models = {"TH37": PLANTS_FROM_THESIS["TH37"],"TH34": PLANTS_FROM_THESIS["TH34"],**assumed}
df = pd.DataFrame({"time_s":t})
for key,plant in models.items():
    df[key] = fopdt_step_response(t,plant) + rng.normal(0,.12,len(t))
df["mean_four_sensors"] = df[list(models)].mean(axis=1)
print(df.head(6).to_string(index=False))
fig,ax=plt.subplots(figsize=(10,4))
for name in models: ax.plot(t,df[name],label=name,alpha=.8,lw=1)
ax.set(xlabel="Time (s)",ylabel="Temperature (°C)",title="Synthetic sensor step responses")
ax.grid(alpha=.25);ax.legend();plt.show()'''),
("md", r'''## 3. Identify $K,\tau,\theta$ by least squares

We estimate the model from **synthetic observations only**. Let $\boldsymbol\beta=(K,\tau,\theta)$. Optimize:

$$\hat{\boldsymbol\beta}=\underset{K>0,\tau>0,\theta\ge0}{\arg\min}\sum_i\left[T_i^{\mathrm{synthetic}}-\hat T(t_i;\boldsymbol\beta)\right]^2.\tag{3}$$

This is a **new open implementation**, not a reconstruction of the original MATLAB System Identification Toolbox ARX pipeline.'''),
("code", '''from scipy.optimize import least_squares
from burnin_pid_fuzzy.models import Plant
y = df["TH37"].to_numpy()
def residual(z):
    p = Plant("fit",float(z[0]),float(z[1]),float(z[2]))
    return fopdt_step_response(t,p)-y
fit=least_squares(residual,[7.,250.,10.],bounds=([.01,1.,0.],[30.,2000.,100.]))
truth=PLANTS_FROM_THESIS["TH37"]
print("Fitted (synthetic):",dict(zip(["K","tau_s","theta_s"],fit.x.round(4))))
print("Thesis-reported parameters:",truth)
print("RMSE (C):",np.sqrt(np.mean(fit.fun**2)))
fig,ax=plt.subplots(figsize=(10,3.5))
ax.plot(t,y,'.',ms=2,alpha=.45,label="synthetic noisy TH37")
ax.plot(t,fopdt_step_response(t,Plant("fit",*fit.x)),lw=2,label="identified FOPDT")
ax.grid(alpha=.2);ax.legend();ax.set(xlabel="Time (s)",ylabel="Temperature (°C)");plt.show()'''),
("md", "## 4. Critical discussion\n\n1. A combined transfer-function fit does not uniquely separate actuator delay from sensor delay.\n2. The original identified four cases used different averaging strategies; the mean of four synthetic curves is not automatically equivalent.\n3. A step response does not identify spatial thermal gradients. A real deployment needs multi-point validation, heater limits, door instrumentation and safety interlocks.\n\n**Next:** [02 · Mamdani Fuzzy PID](02_fuzzy_pid_and_benchmark.ipynb).")
])

make("02_fuzzy_pid_and_benchmark.ipynb", "02 · Mamdani Fuzzy PID & benchmark",
     "Faithful transcription of the sparse rules in Figure 15, an experimental rule-completion variant and closed-loop comparisons with IMC-PID.", [
("md", r'''## 1. Controller equations and representation

The independent PID implementation is

$$u_{\mathrm{raw}}[k]=K_p[k]e[k]+I[k]-K_d[k]\dot y_f[k],\qquad e[k]=r[k]-y[k],\tag{4}$$
$$I[k]=I[k-1]+K_i[k]\Delta t\,e[k].\tag{5}$$

The derivative is on the **measurement**, filtered to avoid setpoint kick. The control is constrained to $u\in[0,10]$ with **conditional anti-windup**. These implementation choices are openly documented extensions, not exact replications of the original Simulink block.

For a reference IMC-PID, the undergraduate thesis (Table 2) uses

$$K_p=\frac{\tau+\theta/2}{K(\lambda+\theta)},\quad T_i=\tau+\theta/2,\quad T_d=\frac{\tau\theta}{2\tau+\theta}.$$

Thus $K_i=K_p/T_i$, $K_d=K_pT_d$ in the independent form. The paper reports $K_p\approx0.4640$, $T_i\approx156.0254$, $T_d\approx4.2655$ for $\lambda=35.3273$.'''),
("code", '''p=PLANTS_FROM_THESIS["mean_temperature"]
imc=imc_pid_gains(p.K,p.tau,p.delay,lam=35.3273)
print(imc)
print("ISA form:","Kp=",round(imc.kp,4),"Ti=",round(imc.kp/imc.ki,4),"Td=",round(imc.kd/imc.kp,4))'''),
("md", r'''## 2. Fuzzification and M-o-M output

The thesis-based fuzzy inference system has two inputs: $|e|\in[0,40]$, $\Delta e\in[-40,40]$ and three normalized outputs $K'_p,K'_i,K'_d\in[0,1]$ (Eqs. 2.13–2.14). Each input has **7** linguistic terms, and each output has **5**.

For each rule $j$, the min-AND firing strength is $w_j=\min(\mu_{A_j}(|e|),\mu_{B_j}(\Delta e))$. Aggregation of clipped Mamdani output sets is

$$\mu_{\mathrm{out}}(z)=\max_j\min(w_j,\mu_{C_j}(z)).$$

The mean-of-maxima (M-o-M) defuzzified value is

$$z^*=\frac{1}{|\mathcal M|}\sum_{z\in\mathcal M}z,\quad\mathcal M=\arg\max_{z\in\{0,.005,\dots,1\}}\mu_{\mathrm{out}}(z).\tag{6}$$

Output gain mapping: $K_j=K_{j,\min}+(K_{j,\max}-K_{j,\min})K'_j$. The precise MF breakpoints are **assumed equally spaced**, because the thesis illustrates but does not tabulate all coordinates.'''),
("code", '''fig, ax=plt.subplots(1,2,figsize=(11,3.5))
for x0,x1,a,title in [(0,40,ax[0],"Error magnitude"),(-40,40,ax[1],"Signed delta-error")]:
    grid=np.linspace(x0,x1,250)
    for j,name in enumerate(("NB","NM","NS","Z","PS","PM","PB")):
        a.plot(grid,[membership_degrees(x,x0,x1)[j] for x in grid],label=name)
    a.set(xlabel=title,ylabel="Membership",ylim=(0,1.05));a.grid(alpha=.2)
ax[1].legend(ncol=7,loc="upper center",bbox_to_anchor=(.5,-.17),fontsize=9)
plt.tight_layout();plt.show()'''),
("md", "## 3. Sparse rule base vs. new dense rule-completion experiment\n\nThe original Figure 15 omits all NM and PM **columns** and some isolated output gains. In sparse mode an undefined gain is retained. Dense mode interpolates neighboring consequent categories, which is a **new assumption** and must be judged experimentally."),
("code", '''for mode in ["sparse","dense"]:
    base=FuzzyRuleBase(mode)
    print(mode,"(e=26.67, delta=-40):",infer_normalized_gains(40*4/6,-40,rule_base=base,previous=np.array([.5,.17,.6])).round(4))
E=np.linspace(0,40,61)
fig,ax=plt.subplots(1,3,figsize=(12,3.3),sharex=True)
for mode,style in [("sparse","--"),("dense","-")]:
    values=np.array([infer_normalized_gains(e,0,rule_base=FuzzyRuleBase(mode)) for e in E])
    for j,name in enumerate(["Kp'","Ki'","Kd'"]):
        ax[j].plot(E,values[:,j],style,label=mode)
        ax[j].set(xlabel="|error| (°C)",ylabel=name,ylim=(0,1));ax[j].grid(alpha=.2)
ax[0].legend();plt.tight_layout();plt.show()'''),
("md", "## 4. Closed-loop experiment: original sparse vs. proposed variants\n\nThe original thesis specifies a 65 °C setpoint, ~3750 s identification horizon and door perturbations around 2000 and 3000 s. Here we use explicitly **synthetic** 30 °C ambient, effective heater output 0–10, and two assumed -5 input-unit door events lasting 60 and 300 s. This is *not* the original test bench."),
("code", '''scenario=Scenario()
runs=simulate_methods(scenario=scenario)
summary=pd.DataFrame([{"controller":name,**evaluate(result,scenario)} for name,result in runs.items()])
print(summary.round(3).to_string(index=False))
fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
for name,result in runs.items():
    axes[0].plot(result["time_s"],result["measurement_c"],label=name)
    axes[1].plot(result["time_s"],result["control"],label=name)
axes[0].axhline(65,ls="--",color="black",lw=1)
for a in axes:
    for d in scenario.doors:a.axvspan(d.start,d.start+d.duration,color="gray",alpha=.12)
    a.grid(alpha=.2);a.legend()
axes[0].set_ylabel("Temperature (°C)");axes[1].set_ylabel("Heater units")
axes[1].set_xlabel("Time (s)");plt.tight_layout();plt.show()'''),
("md", "## 5. Reading these results correctly\n\nThe 2021 undergraduate thesis *reported* a roughly **22%** faster time-to-60 °C and a **3%** faster disturbance recovery for its PID-Fuzzy versus IMC, based on its own Simulink cases (Section 4). The fresh synthetic benchmark above can give **different rankings**, due to assumed actuator saturation, disturbance strengths, sensor model, fuzzy memberships, anti-windup, derivative treatment and missing original measurements. Do not present these outputs as independent confirmation of the published percentages.\n\n**Next:** [03 · Robustness](03_uncertainty_and_robustness.ipynb).")
])

make("03_uncertainty_and_robustness.ipynb", "03 · Robustness & uncertainty",
     "Monte Carlo stress-testing of gain-scheduled PID under uncertain thermal parameters, sensor noise and door disturbances; includes uncertainty-aware comparative metrics.", [
("md", r'''## 1. Why uncertainty matters

The 2021 thesis points to uncertainty and robust disturbance rejection, but does not give raw parameter distributions. The ranges below are **illustrative hypotheses**, not confidence intervals or uncertainty estimates from the original identification campaign.

We perturb $K$, $\tau$ and $\theta$ by multiplicative factors and keep the IMC gains fixed at the nominal identified plant. We apply **identical plant draws and random seeds** to every controller for a fair paired comparison.'''),
("code", '''rng=np.random.default_rng(2026)
nominal=PLANTS_FROM_THESIS["mean_temperature"]
n_trials=12 # raise to 50+ for deeper study; seeded for reproducibility
records=[]
for trial in range(n_trials):
    p=Plant(f"MC_{trial}",nominal.K*rng.uniform(.8,1.2),
            nominal.tau*rng.uniform(.7,1.3),nominal.delay*rng.uniform(.5,1.5),"assumed distribution")
    severity=-rng.uniform(3.5,6.)
    sc=Scenario(duration=2200,dt=2.,measurement_noise_std=.15,
                doors=(DoorEvent(800,60,severity),DoorEvent(1500,180,severity)))
    methods={
      "IMC-fixed-nominal":FixedPID(imc_pid_gains(),dt=sc.dt),
      "Thesis-sparse-fuzzy":FuzzyPID(mode="sparse",dt=sc.dt),
      "Dense-smoothed-fuzzy":FuzzyPID(mode="dense",smoothing=.18,dt=sc.dt)
    }
    for name,ctrl in methods.items():
        output=simulate(ctrl,p,sc,seed=trial)
        metrics=evaluate(output,sc)
        records.append({"trial":trial,"method":name,"K":p.K,"tau":p.tau,"theta":p.delay,
                        "door_severity":severity,**metrics})
robust=pd.DataFrame.from_records(records)
print(robust.groupby("method")["IAE_c_s"].agg(["median","mean","std"]).round(1))
print("Finished",n_trials,"paired synthetic scenarios.")'''),
("md", r'''## 2. Paired distributions and effect sizes

The **integral absolute error (IAE)** and **total variation** quantify different objectives:

$$\mathrm{IAE}=\sum_{k=0}^{N-1}|r[k]-y[k]|\Delta t,\qquad
\mathrm{TV}(u)=\sum_{k=1}^{N-1}|u[k]-u[k-1]|.\tag{7}$$

*Lower is better*, but overshoot, settling and sensor/actuator constraints matter too. Statistical uncertainty is meaningful only relative to the artificial parameter distributions chosen above.'''),
("code", '''piv=robust.pivot(index="trial",columns="method",values="IAE_c_s")
fig,ax=plt.subplots(figsize=(10,3.6))
labels=piv.columns.tolist();ax.boxplot([piv[c].dropna() for c in labels],tick_labels=labels)
ax.set(ylabel="IAE (°C·s)",title="Monte Carlo: synthetic parameter uncertainty")
ax.grid(alpha=.2,axis="y");plt.xticks(rotation=10);plt.tight_layout();plt.show()
for candidate in ["Thesis-sparse-fuzzy","Dense-smoothed-fuzzy"]:
    delta=piv[candidate]-piv["IMC-fixed-nominal"]
    print(candidate,"median paired delta IAE (candidate - IMC):",round(float(delta.median()),2),
          "fraction of scenarios with less IAE:",round(float(np.mean(delta<0)),2))'''),
("md", "## 3. Engineering limitations\n\nThis single-zone thermal model cannot support certification, actuator safety decisions or claims about spatial uniformity. Real experiments should log four synchronized sensor traces, input power, opening/closing timestamps, ambient temperature, electrical heater constraints and independent validation runs. Use paired seeds only to reduce *synthetic* Monte Carlo sampling noise.\n\n**Next:** [04 · Optimization](04_fuzzy_optimization.ipynb).")
])

make("04_fuzzy_optimization.ipynb", "04 · Tune and audit the adaptive controller",
     "An explicit, reproducible hyperparameter search over fuzzy/IMC mixing and gain smoothing, with a held-out synthetic scenario and ablation.", [
("md", r'''## 1. New research idea: smooth, model-assisted fuzzy scheduling

The base fuzzy scheduler implements the 2021 thesis gain mapping. An *optional research extension* interpolates fuzzy and model-based IMC gains:

$$\boldsymbol{K}^{\mathrm{hybrid}}_k=\beta\,\boldsymbol{K}^{\mathrm{fuzzy}}_k+(1-\beta)\,\boldsymbol{K}^{\mathrm{IMC}},\quad \beta\in[0,1].\tag{8}$$

Gain jumps can also be filtered:

$$\boldsymbol K'_k\leftarrow (1-\gamma)\boldsymbol K'_{k-1}+\gamma\,\boldsymbol K'_{\mathrm{MOM},k},\quad\gamma\in(0,1].\tag{9}$$

We jointly tune $(\beta,\gamma)$ under assumed synthetic conditions. **Small synthetic experiments are prone to overfitting.** This does *not* imply superior physical performance.'''),
("code", '''from scipy.optimize import differential_evolution
from burnin_pid_fuzzy.models import simulate
training=[
    (Plant("train1",7.624*.90,151.6*1.10,8.78*1.20),-4.),
    (Plant("train2",7.624*1.10,151.6*.90,8.78*.80),-5.)
]
def objective(x):
    beta,gamma=map(float,x)
    penalties=[]
    for p,severity in training:
        sc=Scenario(duration=1150,dt=3,measurement_noise_std=0,
                    doors=(DoorEvent(450,60,severity),DoorEvent(840,120,severity)))
        res=simulate(FuzzyPID(mode="dense",blend_imc=beta,smoothing=gamma,dt=sc.dt),
                     p,sc,seed=2021)
        m=evaluate(res,sc,recovery_hold_s=15)
        # Units normalized so weights are interpretable.
        penalties.append(m["IAE_c_s"]/1000 + 0.01*m["actuator_total_variation"]
                         + m["overshoot_before_doors_c"]/2)
    return float(np.mean(penalties))
result=differential_evolution(objective,bounds=[(0.,1.),(.05,1.)],seed=42,
                              maxiter=2,popsize=4,polish=False)
beta,gamma=map(float,result.x)
print("Synthetic training optimum (beta,gamma):",(round(beta,3),round(gamma,3)))
print("Training objective:",round(result.fun,4),"evaluations:",result.nfev)'''),
("md", "## 2. Held-out stress test: do not select hyperparameters on this data\n\nWe now evaluate on *different* $K$, $\\tau$, $\\theta$, door timing and severity, without retuning. We measure a vector of outcomes rather than collapsing the result into a single success percentage."),
("code", '''heldout_plant=Plant("heldout",7.624*1.15,151.6*.85,8.78*1.4)
heldout=Scenario(duration=2200,dt=3,doors=(DoorEvent(640,80,-5.5),DoorEvent(1450,220,-4.5)))
choices={
    "IMC fixed":FixedPID(imc_pid_gains(),dt=3),
    "Fuzzy sparse (original rules)":FuzzyPID(mode="sparse",dt=3),
    "Fuzzy dense (smoothing .18)":FuzzyPID(mode="dense",smoothing=.18,dt=3),
    "Fuzzy hybrid (train-only tuning)":FuzzyPID(mode="dense",smoothing=gamma,blend_imc=beta,dt=3)
}
outcomes={name:simulate(ctrl,heldout_plant,heldout,seed=12) for name,ctrl in choices.items()}
report=pd.DataFrame([{"method":name,**evaluate(x,heldout)} for name,x in outcomes.items()])
print(report.round(2).to_string(index=False))
fig,ax=plt.subplots(figsize=(11,4.1))
for name,d in outcomes.items():ax.plot(d["time_s"],d["measurement_c"],label=name,lw=1.5)
ax.axhline(65,color="black",ls="--",lw=1)
for door in heldout.doors:ax.axvspan(door.start,door.start+door.duration,color="gray",alpha=.13)
ax.set(xlabel="Time (s)",ylabel="Measured temperature (°C)");ax.grid(alpha=.2)
ax.legend();plt.tight_layout();plt.show()'''),
("md", "## 3. Extensions for a subsequent research project\n\n- Include acceleration $\\Delta^2 e[k]$ in a **3-input fuzzy system**, as suggested in Section 5 of the thesis.\n- Tune missing rules with constrained Bayesian optimization or population heuristics; enforce smoothness/monotonicity and validate on held-out events.\n- Compare GA/PSO/neuro-fuzzy approaches under **the same uncertainty scenarios**, computation budgets and safety constraints.\n- Replace the single-zone approximation with identified multiple sensors and spatial models.\n- Compare tracking quality *and* actuator energy/variation; no current claim of energy savings is validated.\n\nAll extensions must be experimentally vetted before a physical burn-in chamber is driven by the controller.")
])
