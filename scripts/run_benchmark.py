"""Run standard 3750 s temperature-control benchmark and export plots/metrics."""
from pathlib import Path
import sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from burnin_pid_fuzzy.models import simulate_methods, benchmark_scenario
from burnin_pid_fuzzy.metrics import evaluate


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / "images"
    output.mkdir(parents=True, exist_ok=True)
    scenario = benchmark_scenario()
    runs = simulate_methods(scenario=scenario)
    results = []
    fig, ax = plt.subplots(figsize=(11, 5))
    for name, run in runs.items():
        row = {"method": name, **evaluate(run, scenario)}
        results.append(row)
        ax.plot(run["time_s"], run["measurement_c"], label=name, lw=1.5)
    ax.axhline(scenario.reference, ls="--", color="black", lw=1, label="65 °C reference")
    for j, door in enumerate(scenario.doors):
        ax.axvspan(door.start, door.start + door.duration, alpha=.13, color="gray",
                   label="Synthetic door opening" if j == 0 else None)
    ax.set(xlabel="Time (s)", ylabel="Measured temperature (°C)",
           title="Synthetic burn-in control: IMC vs. sparse/dense Fuzzy PID")
    ax.grid(alpha=.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(output / "synthetic_controller_comparison.png", dpi=170)
    plt.close(fig)
    summary = pd.DataFrame(results)
    summary.to_csv(root / "data" / "synthetic" / "benchmark_metrics.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
