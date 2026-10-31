"""FOPDT burn-in chamber models and PID/Fuzzy control experiments."""
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
