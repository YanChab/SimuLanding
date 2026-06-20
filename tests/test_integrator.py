"""Tests de non-régression pour le sélecteur d'intégrateur (euler|rk4)."""
from __future__ import annotations

from dropsim import default_mlg_inputs, run_simulation
from dropsim.engine import OUTPUT_COLUMNS


def _run_case(integrator: str, dt: float) -> tuple[float, float, float, float]:
    inp = default_mlg_inputs()
    inp.integrator = integrator
    inp.it = dt
    result = run_simulation(inp)
    summary = result.summary
    residual_col = OUTPUT_COLUMNS["e_residual"]
    res_max = float(result.df[residual_col].abs().max())
    return (
        summary["Effort vertical max Fz (N)"],
        summary["Course max (mm)"],
        summary["Accélération max (g)"],
        res_max,
    )


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
    fz_euler, course_euler, acc_euler, res_euler = _run_case("euler", 1.0e-4)
    fz_rk4, course_rk4, acc_rk4, res_rk4 = _run_case("rk4", 1.0e-4)

    # Les deux schémas ne sont pas identiques, mais doivent rester proches sur
    # les grandeurs de synthèse au pas nominal.
    assert abs(fz_rk4 - fz_euler) <= 0.005 * fz_euler
    assert abs(course_rk4 - course_euler) <= 0.5
    assert abs(acc_rk4 - acc_euler) <= 0.05

    # Le recalage énergétique RK4 ne doit pas dégrader fortement le bilan.
    assert res_rk4 <= 1.2 * res_euler


def test_timestep_convergence_comparison_euler_vs_rk4():
    euler_coarse = _run_case("euler", 1.0e-4)
    euler_fine = _run_case("euler", 5.0e-5)
    rk4_coarse = _run_case("rk4", 1.0e-4)
    rk4_fine = _run_case("rk4", 5.0e-5)

    # Pour les deux schémas, réduire dt doit réduire nettement le résidu énergétique.
    assert euler_fine[3] < 0.75 * euler_coarse[3]
    assert rk4_fine[3] < 0.75 * rk4_coarse[3]

    # Comparaison de convergence coarse/fine: le mode rk4 doit rester stable et
    # dans des écarts bornés sur les grandeurs de synthèse.
    dfz_rk4 = abs(rk4_coarse[0] - rk4_fine[0])
    dcourse_rk4 = abs(rk4_coarse[1] - rk4_fine[1])
    dacc_rk4 = abs(rk4_coarse[2] - rk4_fine[2])
    assert dfz_rk4 <= 100.0
    assert dcourse_rk4 <= 0.10
    assert dacc_rk4 <= 0.01
