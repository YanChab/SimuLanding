"""Tests de non-régression pour le sélecteur d'intégrateur (euler|rk4)."""
from __future__ import annotations

from dropsim import default_mlg_inputs, run_simulation
from dropsim.engine import OUTPUT_COLUMNS, _select_damper_core_solver


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


def _run_case_with_solver(
    integrator: str,
    dt: float,
    damper_core_solver: str,
) -> tuple[float, float, float, float]:
    inp = default_mlg_inputs()
    inp.integrator = integrator
    inp.it = dt
    inp.damper_core_solver = damper_core_solver
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


def _run_auto_case(dt: float = 1.0e-4):
    inp = default_mlg_inputs()
    inp.integrator = "rk4"
    inp.damper_core_solver = "auto"
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


def _count_auto_implicit_steps(
    masse: float,
    vz: float,
    dt: float,
    temperature: float = 25.0,
) -> tuple[int, int]:
    inp = default_mlg_inputs()
    inp.integrator = "rk4"
    inp.damper_core_solver = "auto"
    inp.it = dt
    inp.masse = masse
    inp.vz = vz
    inp.temperature = temperature
    result = run_simulation(inp)
    si = inp.to_si()
    df = result.df
    implicit = 0
    for i in range(len(df)):
        d = float(df[OUTPUT_COLUMNS["mlg_d"]].iloc[i])
        v = float(df[OUTPUT_COLUMNS["mlg_v"]].iloc[i])
        pg = float(df[OUTPUT_COLUMNS["pg"]].iloc[i]) * 1e5
        ftot_prev = float(df[OUTPUT_COLUMNS["mlg_ftot"]].iloc[i - 1]) if i > 0 else 0.0
        if _select_damper_core_solver(si, d, v, pg, ftot_prev) == "implicit_adaptive":
            implicit += 1
    return implicit, len(df)


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


def test_invalid_damper_solver_is_rejected():
    inp = default_mlg_inputs()
    inp.damper_core_solver = "unknown"
    collector = inp.validate()
    assert collector.has_errors
    assert any(err.code == "SOLVEUR_AMORTISSEUR_INVALIDE" for err in collector.errors)


def test_auto_solver_heuristic_switches_on_stiff_states():
    inp = default_mlg_inputs()
    inp.damper_core_solver = "auto"
    si = inp.to_si()
    assert _select_damper_core_solver(si, 0.0005, 2.00, si.Pinitbp * 13.0, si.St * si.Pinitbp * 1.2) == "implicit_adaptive"
    assert _select_damper_core_solver(si, 0.10, 0.20, si.Pinitbp * 1.2, 0.0) == "legacy"


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


def test_implicit_adaptive_solver_runs_and_stays_close_to_legacy():
    fz_legacy, course_legacy, acc_legacy, _ = _run_case_with_solver(
        "rk4", 1.0e-4, "legacy"
    )
    fz_impl, course_impl, acc_impl, _ = _run_case_with_solver(
        "rk4", 1.0e-4, "implicit_adaptive"
    )

    assert abs(fz_impl - fz_legacy) <= 0.03 * fz_legacy
    assert abs(course_impl - course_legacy) <= 2.0
    assert abs(acc_impl - acc_legacy) <= 0.2


def test_implicit_adaptive_solver_timestep_refinement_reduces_residual():
    coarse = _run_case_with_solver("rk4", 1.0e-4, "implicit_adaptive")
    fine = _run_case_with_solver("rk4", 5.0e-5, "implicit_adaptive")
    assert fine[3] < 0.80 * coarse[3]


def test_auto_solver_runs_and_stays_close_to_legacy_on_nominal_case():
    fz_legacy, course_legacy, acc_legacy, _ = _run_case_with_solver(
        "rk4", 1.0e-4, "legacy"
    )
    fz_auto, course_auto, acc_auto, _ = _run_auto_case(1.0e-4)

    assert abs(fz_auto - fz_legacy) <= 0.01 * fz_legacy
    assert abs(course_auto - course_legacy) <= 0.5
    assert abs(acc_auto - acc_legacy) <= 0.05


def test_auto_solver_stays_efficient_on_stiffer_valid_case():
    fz_legacy, course_legacy, acc_legacy, res_legacy = _run_case_with_solver(
        "rk4", 5.0e-5, "legacy"
    )
    fz_auto, course_auto, acc_auto, res_auto = _run_auto_case(5.0e-5)

    # L'heuristique auto doit rester très proche du chemin historique tout en
    # évitant le coût du noyau implicite pur.
    assert abs(fz_auto - fz_legacy) <= 0.01 * fz_legacy
    assert abs(course_auto - course_legacy) <= 0.5
    assert abs(acc_auto - acc_legacy) <= 0.05
    assert res_auto <= 1.01 * res_legacy
