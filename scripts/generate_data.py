"""Generate deterministic *synthetic* step-test data. Not measurements from the 2021 work."""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from burnin_pid_fuzzy.models import PLANTS_FROM_THESIS, Plant, fopdt_step_response


def main():
    root = Path(__file__).resolve().parents[1]
    dst = root / "data" / "synthetic"
    dst.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(2021)
    times = np.arange(0, 3751, 5)
    # TH22 and TH40 were not individually quantified in the uploaded thesis;
    # their parameters below are explicitly assumptions for a 4-sensor example.
    assumed = {
        "TH22": Plant("TH22", 6.85, 135., 7.5, "assumed synthetic example"),
        "TH40": Plant("TH40", 7.1852, 155., 8.5, "assumed synthetic example"),
    }
    sensors = {**{k: PLANTS_FROM_THESIS[k] for k in ["TH37", "TH34"]}, **assumed}
    dataset = {"time_s": times, "heater_step_units": np.ones(len(times))}
    metadata = {"seed": 2021, "sample_interval_s": 5,
                "data_type": "synthetic simulation, not original readings",
                "noise_sd_c": 0.12,
                "model": "ambient + K * (1-exp(-(t-theta)/tau)) for t>theta",
                "sensors": {}}
    for name, p in sensors.items():
        curve = fopdt_step_response(times, p)
        dataset[f"{name}_temperature_c"] = curve + rng.normal(0., .12, len(times))
        metadata["sensors"][name] = {"K": p.K, "tau_s": p.tau,
                                     "theta_s": p.delay, "provenance": p.provenance}
    frame = pd.DataFrame(dataset)
    frame["mean_4_sensors_temperature_c"] = frame[[f"{n}_temperature_c" for n in sensors]].mean(axis=1)
    frame.to_csv(dst / "step_test_four_sensors.csv", index=False, float_format="%.8f")
    (dst / "provenance.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print(f"Wrote {len(frame)} synthetic samples to {dst}")


if __name__ == "__main__":
    main()
