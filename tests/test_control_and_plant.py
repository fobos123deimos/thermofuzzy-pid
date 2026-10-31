import numpy as np
from burnin_pid_fuzzy.controllers import FixedPID, PIDGains, FuzzyPID, imc_pid_gains
from burnin_pid_fuzzy.models import (PLANTS_FROM_THESIS, Scenario, DoorEvent,
                                      simulate, simulate_methods, fopdt_step_response)
from burnin_pid_fuzzy.metrics import evaluate


def test_imc_matches_thesis_reported_isa_gains():
    g = imc_pid_gains()
    assert np.isclose(g.kp, .4640, atol=.001)
    assert np.isclose(g.ki, .4640/156.0254, atol=.0001)
    assert np.isclose(g.kd, .4640*4.2655, atol=.02)


def test_open_loop_step_matches_fopdt_steady_state():
    p = PLANTS_FROM_THESIS["mean_temperature"]
    y = fopdt_step_response([0, p.delay, 10000], p, amplitude=1)
    assert np.isclose(y[0], 30)
    assert np.isclose(y[1], 30)
    assert np.isclose(y[2], 30+p.K, atol=1.e-4)


def test_imc_and_adaptive_controllers_are_finite_and_bounded():
    sc = Scenario(duration=600, dt=2, doors=(DoorEvent(200, 40, -2),))
    for ctrl in [FixedPID(imc_pid_gains(), dt=2),
                 FuzzyPID(mode="sparse", dt=2),
                 FuzzyPID(mode="dense", dt=2, smoothing=.18)]:
        r = simulate(ctrl, scenario=sc)
        assert np.all(np.isfinite(r["temperature_c"]))
        assert np.all(np.isfinite(r["control"]))
        assert np.min(r["control"]) >= 0
        assert np.max(r["control"]) <= sc.actuator_max
        assert np.all((r["kp"] >= 0) & (r["ki"] >= 0) & (r["kd"] >= 0))
        assert r["temperature_c"][-1] < 150.


def test_repeatable_noise_and_metrics():
    sc = Scenario(duration=500, dt=1, measurement_noise_std=.2, doors=())
    a = simulate(FixedPID(imc_pid_gains()), scenario=sc, seed=17)
    b = simulate(FixedPID(imc_pid_gains()), scenario=sc, seed=17)
    assert np.array_equal(a["temperature_c"], b["temperature_c"])
    m = evaluate(a, sc)
    assert m["IAE_c_s"] > 0 and 0 <= m["saturation_fraction"] <= 1


def test_hybrid_blend_zero_recovers_nominal_imc_gains():
    nominal = imc_pid_gains()
    controller = FuzzyPID(mode="dense", smoothing=.12, blend_imc=0., nominal=nominal)
    for temperature in [30., 42., 60., 67., 64.]:
        _, got = controller.step(65., temperature)
        assert np.allclose([got.kp, got.ki, got.kd],
                           [nominal.kp, nominal.ki, nominal.kd], atol=1.e-12)


def test_hybrid_blend_out_of_range_raises():
    import pytest
    with pytest.raises(ValueError):
        FuzzyPID(mode="dense", blend_imc=1.1)
