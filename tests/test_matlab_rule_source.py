"""Basic static cross-language guard: MATLAB sparse rule table matches Python."""
from pathlib import Path
import re
import numpy as np
from burnin_pid_fuzzy.fuzzy import EXACT_SPARSE_RULES, LEVELS


def test_matlab_sparse_consequents_identical_to_python():
    matlab = (Path(__file__).resolve().parents[1] / "matlab" / "fuzzy_rule_matrix.m").read_text()
    for gain in range(3):
        match = re.search(r"R\(:,:," + str(gain + 1) + r"\) = \[(.*?)\];", matlab, re.S)
        assert match, f"MATLAB sparse matrix for gain {gain} missing"
        matrix = [list(map(int, row.strip().split())) for row in match.group(1).split(';')]
        expected = np.array([
            [0 if triple is None or triple[gain] is None else LEVELS[triple[gain]] + 1
             for triple in row] for row in EXACT_SPARSE_RULES
        ])
        assert np.array_equal(np.array(matrix), expected)
