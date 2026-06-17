"""Bilan énergétique : test de conservation d'énergie (diagnostic §5.2).

Vérifie que le moteur respecte une cohérence énergétique : l'énergie d'impact
(cinétique initiale + travail de la gravité) se retrouve, à un résidu près, dans
les énergies stockées (gaz, pneu, butée) et dissipées (hydraulique, friction).
Un résidu anormalement élevé signalerait une dérive numérique ou un bug.
"""
from __future__ import annotations

import numpy as np
import pytest

from dropsim import default_mlg_inputs, run_simulation
from dropsim.engine import OUTPUT_COLUMNS

# Seuil de tolérance sur le résidu de bilan, exprimé en fraction de l'énergie
# d'impact. Tous les chemins énergétiques étant désormais comptabilisés (gaz,
# hydraulique, friction, butée, pneu vertical, spin-up de la roue, glissement
# au contact, couplage longitudinal du balancier), le résidu se réduit à la
# seule erreur d'intégration d'Euler explicite : il vaut ~0,3 % au pas par
# défaut et décroît linéairement avec le pas de temps.
RESIDUAL_TOL = 0.02


@pytest.fixture(scope="module")
def df():
    return run_simulation(default_mlg_inputs()).df


def _col(df, key: str):
    return df[OUTPUT_COLUMNS[key]].to_numpy()


def test_energy_columns_present(df):
    for key in ("e_kin", "e_gas", "e_tyre", "e_hyd", "e_fric", "e_slip",
                "e_endstop", "e_input", "e_residual"):
        assert OUTPUT_COLUMNS[key] in df.columns


def test_impact_energy_positive(df):
    e_input0 = _col(df, "e_input")[0]
    assert e_input0 > 0.0


def test_dissipation_non_negative_and_monotonic(df):
    # Les énergies dissipées de l'amortisseur sont des intégrales de travaux de
    # frottement opposés au mouvement : elles doivent être ≥ 0 et croissantes
    # (à la tolérance d'arrondi près).
    for key in ("e_hyd", "e_fric"):
        series = _col(df, key)
        assert np.all(series >= -1e-6)
        assert np.all(np.diff(series) >= -1e-6), key


def test_slip_dissipation_non_negative(df):
    # La chaleur de glissement au contact pneu/sol est une dissipation : elle
    # doit rester ≥ 0 (la roue ne peut pas rendre d'énergie au sol).
    e_slip = _col(df, "e_slip")
    assert e_slip[-1] >= 0.0
    assert np.all(e_slip >= -1e-3)


def test_energy_residual_bounded(df):
    e_input0 = _col(df, "e_input")[0]
    residual_max = float(np.abs(_col(df, "e_residual")).max())
    assert residual_max <= RESIDUAL_TOL * e_input0, (
        f"Résidu de bilan {residual_max:.0f} J "
        f"({100 * residual_max / e_input0:.1f} %) au-delà du seuil "
        f"{100 * RESIDUAL_TOL:.0f} %"
    )


def test_residual_decreases_with_timestep():
    # Le résidu se réduisant à l'erreur d'intégration d'Euler explicite (O(Δt)),
    # diviser le pas de temps par deux doit réduire nettement le résidu max.
    base = default_mlg_inputs()
    df_coarse = run_simulation(base).df
    fine = default_mlg_inputs()
    fine.it = base.it / 2.0
    df_fine = run_simulation(fine).df
    res_coarse = float(np.abs(_col(df_coarse, "e_residual")).max())
    res_fine = float(np.abs(_col(df_fine, "e_residual")).max())
    assert res_fine < 0.75 * res_coarse, (
        f"Résidu fin {res_fine:.1f} J non réduit vs grossier {res_coarse:.1f} J"
    )
