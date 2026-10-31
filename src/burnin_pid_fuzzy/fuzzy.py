"""Rule-based Mamdani fuzzy gain scheduler with mean-of-maxima defuzzification.

The sparse consequents below were transcribed from TCC Figure 15 (page 36 of
printed numbering). The implementation uses a stated *assumption* for the exact
membership breakpoints: equally spaced, triangular interior with shoulder
endpoints. Their complete coordinates are not tabulated in the thesis.

Input error is |r-y|, in [0, 40]; delta error is signed, in [-40, 40].
This resolves the thesis's ambiguity between its absolute-error description,
its signed error formula (Eq. 2.13) and its nonnegative e membership domain.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

TERMS = ("NB", "NM", "NS", "Z", "PS", "PM", "PB")
OUTPUT_TERMS = ("S", "MS", "M", "MB", "B")
LEVELS = {name: j for j, name in enumerate(OUTPUT_TERMS)}

# Indexed by signed delta-error rows and nonnegative error-magnitude columns.
# Each triple denotes (Kp', Ki', Kd'); None means "retain last value".
# "..." in the original = unspecified; full NM/PM *columns* were omitted.
EXACT_SPARSE_RULES = [
    [("M", "B", "S"), None, ("MS", "S", "MS"), ("M", "S", "M"), ("MS", None, "MB"), None, ("B", "S", "B")],
    [("MS", "MB", "S"), None, ("MS", "S", "MS"), ("M", "S", "MS"), ("MS", "S", "M"), None, ("B", "S", "M")],
    [("S", "M", "S"), None, ("MS", "S", "S"), ("M", "S", "S"), ("MS", "S", "MS"), None, ("B", "S", "S")],
    [("S", "S", "S"), None, ("MS", "S", "S"), ("M", "S", "S"), ("MS", "S", "S"), None, ("B", "S", "S")],
    [("S", "S", "S"), None, ("MS", "S", "S"), ("M", "S", "S"), ("MS", "S", "MS"), None, ("B", "S", "S")],
    [("MS", "MB", "S"), None, ("MS", "S", "MS"), ("M", "S", "MS"), ("MS", "S", "M"), None, ("B", "S", "M")],
    [("M", "B", "S"), None, ("MS", "S", "MS"), ("M", "S", "M"), ("MS", None, "MB"), None, ("B", "S", "B")],
]


def membership_degrees(x: float, low: float, high: float) -> np.ndarray:
    """7 overlapping fuzzy sets: trapezoid shoulders and triangular interiors."""
    x = float(np.clip(x, low, high))
    centers = np.linspace(low, high, 7)
    w = centers[1] - centers[0]
    return np.maximum(1.0 - np.abs(x - centers) / w, 0.0)


def _dense_rules_from_sparse() -> list[list[tuple[str, str, str]]]:
    """Research extension: deterministic linear interpolation of absent entries.

    For whole missing columns NM/PM, interpolate adjacent known categories.
    For isolated gain omissions (at PS for Ki), interpolate adjacent known
    columns. These invented rules are *not* attributed to the 2021 TCC.
    """
    table = np.full((7, 7, 3), np.nan)
    for i, row in enumerate(EXACT_SPARSE_RULES):
        for j, triple in enumerate(row):
            if triple is not None:
                for k, term in enumerate(triple):
                    if term is not None:
                        table[i, j, k] = LEVELS[term]
    for i in range(7):
        for k in range(3):
            known = np.flatnonzero(~np.isnan(table[i, :, k]))
            table[i, :, k] = np.interp(np.arange(7), known, table[i, known, k])
    return [[tuple(OUTPUT_TERMS[int(np.floor(v + 0.5))] for v in table[i, j])
             for j in range(7)] for i in range(7)]


@dataclass(frozen=True)
class FuzzyRuleBase:
    mode: str = "sparse"
    output_resolution: int = 201

    def __post_init__(self):
        if self.mode not in {"sparse", "dense"}:
            raise ValueError("mode must be 'sparse' or 'dense'")
        if self.output_resolution < 11:
            raise ValueError("output_resolution must be at least 11")

    @property
    def rules(self):
        return EXACT_SPARSE_RULES if self.mode == "sparse" else _dense_rules_from_sparse()


def infer_normalized_gains(error: float, delta_error: float,
                           *, rule_base: FuzzyRuleBase | None = None,
                           previous: np.ndarray | None = None) -> np.ndarray:
    """Mamdani min/max inference; Mean-of-Maxima over discretized [0,1].

    For undefined outputs, the corresponding previous normalized gain is held.
    Rules with absent antecedent combinations contribute zero activation.
    """
    base = rule_base or FuzzyRuleBase()
    previous = np.full(3, 0.5) if previous is None else np.asarray(previous, dtype=float)
    if previous.shape != (3,) or not np.all(np.isfinite(previous)):
        raise ValueError("previous must be a finite array of shape (3,)")
    e_mu = membership_degrees(abs(error), 0.0, 40.0)
    de_mu = membership_degrees(delta_error, -40.0, 40.0)
    # A single membership of each input is zero outside adjacent sets.
    heights = np.zeros((3, 5))
    for i, row in enumerate(base.rules):
        if de_mu[i] <= 0:
            continue
        for j, outputs in enumerate(row):
            if outputs is None or e_mu[j] <= 0:
                continue
            strength = min(de_mu[i], e_mu[j])
            for k, term in enumerate(outputs):
                if term is not None:
                    col = LEVELS[term]
                    heights[k, col] = max(heights[k, col], strength)

    universe = np.linspace(0., 1., base.output_resolution)
    # Discretized isosceles output triangles, half triangles at the edges.
    centers = np.linspace(0., 1., 5)
    output_memberships = np.maximum(1 - np.abs(universe[:, None] - centers[None, :]) / 0.25, 0)
    gains = previous.copy()
    for k in range(3):
        if np.max(heights[k]) <= 0:
            continue
        mu = np.max(np.minimum(output_memberships, heights[k][None, :]), axis=1)
        maximum = np.max(mu)
        positions = universe[np.isclose(mu, maximum, rtol=0, atol=1.e-10)]
        gains[k] = float(positions.mean())  # Mean of ALL maxima, not a centroid.
    return gains
