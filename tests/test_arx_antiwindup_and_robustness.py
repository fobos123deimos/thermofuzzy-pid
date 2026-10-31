import numpy as np
import pytest

from burnin_pid_fuzzy.identification import fit_first_order_arx, simulate_sampled_arx
from burnin_pid_fuzzy.controllers import PIDGains, FixedPID, FuzzyPID, imc_pid_gains
from burnin_pid_fuzzy.models import PLANTS_FROM_THESIS, Scenario, DoorEvent, simulate
from burnin_pid_fuzzy.robustness import linear_loop_response, assess_fixed_pid_robustness


def sample_input(n=1000):
    u = np.zeros(n)
    u[30:200] = 2
    u[200:400] = 4
    u[400:600] = 1
    u[600:850] = 5
    u[850:] = 2
    return u


def test_arx_recovers_exact_first_order_parameters_with_known_integer_delay():
    dt, K, tau, m = 2.0, 7.624, 151.6, 5
    u = sample_input()
    measured = simulate_sampled_arx(u, K=K, tau_s=tau, dt=dt, delay_samples=m)
    estimated = fit_first_order_arx(u, measured, dt=dt, delay_samples=m)
    assert abs(estimated.steady_state_gain - K) < 1e-9
    assert abs(estimated.tau_s - tau) < 1e-9
    assert estimated.dead_time_s == 10.0
    assert estimated.rmse_c < 1e-11


def test_arx_requires_excitation_and_known_sample_period():
    u = np.zeros(300)
    with pytest.raises(ValueError, match="rank deficient"):
        fit_first_order_arx(u, np.full(300, 30.0), dt=1., delay_samples=1)
    with pytest.raises(ValueError, match="dt"):
        fit_first_order_arx(u, np.zeros(300), dt=0, delay_samples=1)


def test_arx_nonzero_ambient_and_synthetic_noise():
    rng = np.random.default_rng(2026)
    u = sample_input()
    y = simulate_sampled_arx(u, K=5., tau_s=100., dt=2., delay_samples=3, ambient_c=27.)
    est = fit_first_order_arx(u, y+rng.normal(0,.01,len(y)),
                              dt=2., delay_samples=3, ambient_c=27.)
    assert np.isclose(est.steady_state_gain, 5., rtol=.03)
    assert np.isclose(est.tau_s, 100., rtol=.1)
    assert est.rmse_c > 0


def test_antiwindup_backcalculation_lowers_integrator_after_heavy_saturation():
    gains = PIDGains(kp=2., ki=.8, kd=0.)
    cond = FixedPID(gains, anti_windup="conditional", dt=1., u_max=10.)
    back = FixedPID(gains, anti_windup="back_calculation", tracking_time=3., dt=1., u_max=10.)
    for _ in range(50):
        assert 0 <= cond.step(65,30)[0] <= 10
        assert 0 <= back.step(65,30)[0] <= 10
    assert back.integral < cond.integral  # more negative tracking correction
    # Under realistic closed-loop trajectories, both must remain bounded.
    sc=Scenario(duration=100, dt=1, doors=())
    for typ in ["conditional","back_calculation"]:
        out=simulate(FixedPID(imc_pid_gains(),dt=1.,anti_windup=typ),scenario=sc)
        assert np.isfinite(out["temperature_c"]).all()
        assert np.max(out["control"]) <= sc.actuator_max


def test_antiwindup_tracking_parameters_validated_and_fuzzy_inherits_option():
    with pytest.raises(ValueError):
        FixedPID(imc_pid_gains(),anti_windup="invalid")
    with pytest.raises(ValueError):
        FixedPID(imc_pid_gains(),anti_windup="back_calculation",tracking_time=0.1,dt=1.)
    pid = FuzzyPID(mode="sparse", anti_windup="back_calculation",tracking_time=5.)
    assert 0 <= pid.step(65,30.)[0] <= 10


def test_frequency_response_matches_fopdt_math_and_margin_bounds():
    plant=PLANTS_FROM_THESIS["mean_temperature"]
    gains=imc_pid_gains()
    w=np.array([.001,.01,.1])
    L=linear_loop_response(plant,gains,w)
    s=1j*w
    expected=plant.K*np.exp(-plant.delay*s)/(1+plant.tau*s)*(gains.kp+gains.ki/s+gains.kd*s/(1+8*s))
    np.testing.assert_allclose(L,expected)
    result=assess_fixed_pid_robustness(plant,gains)
    assert np.isfinite(result.maximum_sensitivity) and result.maximum_sensitivity>=1
    assert result.gain_margin > 0
    assert result.phase_margin_deg > 0
    with pytest.raises(ValueError):
        linear_loop_response(plant,gains,np.array([0.0,.1]))
