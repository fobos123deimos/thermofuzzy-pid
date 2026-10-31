import numpy as np
from burnin_pid_fuzzy.fuzzy import (
    EXACT_SPARSE_RULES, FuzzyRuleBase, infer_normalized_gains,
    _dense_rules_from_sparse, membership_degrees,
)


def test_sparse_rule_matrix_structure():
    assert len(EXACT_SPARSE_RULES) == 7
    assert all(len(row) == 7 for row in EXACT_SPARSE_RULES)
    assert all(row[1] is None and row[5] is None for row in EXACT_SPARSE_RULES)
    assert EXACT_SPARSE_RULES[0][0] == ("M", "B", "S")
    assert EXACT_SPARSE_RULES[-1][-1] == ("B", "S", "B")
    assert EXACT_SPARSE_RULES[0][4][1] is None


def test_memberships_partition_unity():
    for x in np.linspace(-40, 40, 301):
        mu = membership_degrees(x, -40, 40)
        assert np.isclose(sum(mu), 1, atol=1e-10)
        assert (mu >= 0).all() and (mu <= 1).all()


def test_sparse_keeps_unspecified_integral_gain():
    p = np.array([.5, .17, .6])
    # At e=26.666... (PS) and delta error=-40 (NB): Ki rule absent.
    r = infer_normalized_gains(40*4/6, -40, previous=p)
    assert abs(r[1] - p[1]) < 1e-10


def test_dense_rules_are_fully_defined():
    dense = _dense_rules_from_sparse()
    assert all(all(isinstance(entry, tuple) and None not in entry for entry in row) for row in dense)
    r = infer_normalized_gains(25, 0, rule_base=FuzzyRuleBase("dense"))
    assert r.shape == (3,) and np.all(np.isfinite(r))
    assert np.all((r >= 0) & (r <= 1))


def test_zero_previous_used_on_no_active_rules():
    p = np.array([0.1, 0.2, 0.3])
    r = infer_normalized_gains(10, 0, previous=p)
    assert np.all((r >= 0) & (r <= 1))
