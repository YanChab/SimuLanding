"""Tests de non-régression pour le sélecteur d'intégrateur (euler|rk4)."""
from __future__ import annotations

from dropsim import default_mlg_inputs, run_simulation
from dropsim.engine import OUTPUT_COLUMNS


def test_invalid_integrator_is_rejected():
    inp = default_mlg_inputs()
    inp.integrator = "invalid"
    collector = inp.validate()
    assert collector.has_errors
    assert any(err.code == "INTEGRATEUR_INVALIDE" for err in collector.errors)


def test_rk4_selection_emits_warning_and_runs():
    inp = default_mlg_inputs()
    inp.integrator = "rk4"
    result = run_simulation(inp)
    assert result.n_steps > 0
    assert not any(w.code == "INTEGRATEUR_RK4_INACTIF" for w in result.warnings)


def test_rk4_stays_close_to_euler_with_controlled_energy_residual():
    euler = default_mlg_inputs()
    rk4 = default_mlg_inputs()
    rk4.integrator = "rk4"

    euler_result = run_simulation(euler)
    rk4_result = run_simulation(rk4)

    euler_summary = euler_result.summary
    rk4_summary = rk4_result.summary
    fz_euler = euler_summary["Effort vertical max Fz (N)"]
    fz_rk4 = rk4_summary["Effort vertical max Fz (N)"]
    course_euler = euler_summary["Course max (mm)"]
    course_rk4 = rk4_summary["Course max (mm)"]
    acc_euler = euler_summary["Accélération max (g)"]
    acc_rk4 = rk4_summary["Accélération max (g)"]
    residual_col = OUTPUT_COLUMNS["e_residual"]
    res_euler = float(euler_result.df[residual_col].abs().max())
    res_rk4 = float(rk4_result.df[residual_col].abs().max())

    # Les deux schémas ne sont pas identiques, mais doivent rester proches sur
    # les grandeurs de synthèse au pas nominal.
    assert abs(fz_rk4 - fz_euler) <= 0.005 * fz_euler
    assert abs(course_rk4 - course_euler) <= 0.5
    assert abs(acc_rk4 - acc_euler) <= 0.05

    # Le recalage énergétique RK4 ne doit pas dégrader fortement le bilan.
    assert res_rk4 <= 1.2 * res_euler
