"""Rebuild original teaching diagrams and model-derived pdoc figures."""
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from burnin_pid_fuzzy.models import PLANTS_FROM_THESIS, fopdt_step_response
from burnin_pid_fuzzy.controllers import imc_pid_gains
from burnin_pid_fuzzy.fuzzy import FuzzyRuleBase, infer_normalized_gains, membership_degrees, TERMS
from burnin_pid_fuzzy.robustness import linear_loop_response, assess_fixed_pid_robustness

OUT = ROOT / "docs/figures"
COLORS = ["#16697a", "#e17c37", "#6a4c93", "#4b8c62", "#ae4b65", "#64849b", "#75624c"]


def save(fig, name):
    """Write matching PNG/SVG previews without embedding machine paths."""
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / (name + ".png"), dpi=160, facecolor="white", bbox_inches="tight")
    fig.savefig(OUT / (name + ".svg"), facecolor="white", bbox_inches="tight",
                metadata={"Date": None})
    plt.close(fig)


def main():
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.prop_cycle": plt.cycler(color=COLORS)})
    fig, ax = plt.subplots(figsize=(12, 5.7))
    ax.set(xlim=(0, 12), ylim=(0, 5.7))
    ax.axis("off")
    ax.text(.15, 5.35, "A thermal loop with explicit information paths", size=19, weight="bold", color=COLORS[0])
    ax.text(.15, 4.91, "One-state synthetic model • Source parameters and added assumptions remain separate", size=11)
    def box(x, y, w, h, text):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.10", fc="#eef5f6", ec=COLORS[0], lw=1.5))
        ax.text(x+w/2, y+h/2, text, ha="center", va="center", linespacing=1.5)
    def arrow(a,b,label="",offset=(0,.18)):
        ax.annotate("", xy=b, xytext=a, arrowprops={"arrowstyle":"-|>","color":COLORS[0],"lw":1.8})
        if label:
            ax.text((a[0]+b[0])/2+offset[0],(a[1]+b[1])/2+offset[1],label,ha="center",size=10)
    box(.25,2.7,1.4,.9,"Reference\n65 °C")
    box(2.35,2.5,2.15,1.3,"PID + fuzzy gains\nerror / Δerror\nstate and anti-windup")
    box(5.15,2.7,1.55,.9,"Actuator\n0–10 units")
    box(7.45,2.45,2.5,1.4,"Thermal state T\nFirst-order dynamics\nambient + heat balance")
    box(7.6,.55,2.2,.95,"Measurement y\nsensor delay + noise")
    box(2.6,.55,2.3,.95,"Inference convention\n|error| and signed Δerror")
    arrow((1.65,3.15),(2.35,3.15))
    arrow((4.5,3.15),(5.15,3.15),"u")
    arrow((6.7,3.15),(7.45,3.15))
    arrow((9.95,3.15),(11.65,3.15),"T (°C)")
    arrow((8.7,2.45),(8.7,1.5))
    arrow((7.6,1.03),(4.9,1.03),"y (°C)")
    arrow((3.65,1.5),(3.65,2.5))
    ax.text(10.5,4.24,"Assumed door loss d",ha="center",color=COLORS[1])
    arrow((10.5,4.02),(9.7,3.85))
    ax.text(.2,.1,"Signal diagram, not a hardware wiring or safety architecture. Time is measured in seconds.",size=10,color="#52616b")
    save(fig,"thermal-loop")

    fig, ax = plt.subplots(figsize=(10.6,4.9),layout="constrained")
    t = np.linspace(0,1200,601)
    for name, plant in PLANTS_FROM_THESIS.items():
        ax.plot(t,fopdt_step_response(t,plant),label=name.replace("_"," "),lw=2)
    ax.set(title="Four source-parameter FOPDT predictions",xlabel="Time (s)",ylabel="Predicted sensor temperature (°C)")
    ax.grid(alpha=.2); ax.legend(title="One effective heater unit; ambient 30 °C")
    fig.text(.5,-.025,"Analytical model curves; these are not original measurement records.",ha="center",size=10)
    save(fig,"fopdt-responses")

    fig, axs = plt.subplots(2,2,figsize=(12,8),layout="constrained")
    for ax, low, high, title in [(axs[0,0],0,40,"Error magnitude |e| (°C)"),(axs[0,1],-40,40,"Per-sample error change Δe (°C)")]:
        xx=np.linspace(low,high,241)
        mu=np.array([membership_degrees(x,low,high) for x in xx])
        for k in range(7): ax.plot(xx,mu[:,k],label=TERMS[k],lw=1.8)
        ax.set(xlabel=title,ylabel="Membership degree",ylim=(-.03,1.08)); ax.grid(alpha=.15)
    axs[0,0].legend(ncol=4,fontsize=9,loc="upper center",bbox_to_anchor=(.5,1.28))
    errors=np.linspace(0,40,61); changes=np.linspace(-40,40,61)
    for ax,mode in zip(axs[1],("sparse","dense")):
        base=FuzzyRuleBase(mode=mode)
        grid=np.array([[infer_normalized_gains(e,de,rule_base=base,previous=np.full(3,.5))[0]
                        for e in errors] for de in changes])
        im=ax.imshow(grid,origin="lower",extent=(0,40,-40,40),aspect="auto",vmin=0,vmax=1,cmap="viridis")
        ax.set(title=mode.capitalize()+" normalized proportional output",xlabel="|e| (°C)",ylabel="Δe (°C per sample)")
        fig.colorbar(im,ax=ax,label="Normalized Kp output")
    fig.suptitle("Declared membership geometry and rule-table consequences",fontsize=16,color=COLORS[0])
    fig.text(.5,-.025,"Previous normalized gains = 0.5. Dense rules and membership breakpoints are explicit reconstruction choices.",ha="center",size=10)
    save(fig,"fuzzy-scheduling")

    plant=PLANTS_FROM_THESIS["mean_temperature"]
    gains=imc_pid_gains(plant.K,plant.tau,plant.delay)
    w=np.logspace(-6,1,5000)
    loop=linear_loop_response(plant,gains,w)
    margins=assess_fixed_pid_robustness(plant,gains,omega_rad_s=w)
    fig,axs=plt.subplots(2,1,figsize=(10.6,6.6),sharex=True,layout="constrained")
    axs[0].semilogx(w,20*np.log10(abs(loop)),lw=2)
    axs[0].axhline(0,color="#75808a",ls="--",lw=1)
    axs[0].set(title="Nominal fixed IMC loop: sampled linear frequency response",ylabel="Loop magnitude (dB)")
    sensitivity=abs(1/(1+loop))
    axs[1].semilogx(w,sensitivity,lw=2,color=COLORS[1])
    axs[1].scatter([margins.peak_frequency_rad_s],[margins.maximum_sensitivity],color=COLORS[1])
    axs[1].set(xlabel="Angular frequency (rad/s)",ylabel="Sensitivity magnitude |S|")
    axs[1].text(.03,.9,f"Sampled peak Ms = {margins.maximum_sensitivity:.3f}",transform=axs[1].transAxes)
    for ax in axs: ax.grid(alpha=.2)
    fig.text(.5,-.025,"Fixed gains; continuous linear model; no saturation. Not a stability certificate for adaptive fuzzy control.",ha="center",size=10)
    save(fig,"fixed-loop-response")


if __name__ == "__main__":
    main()
