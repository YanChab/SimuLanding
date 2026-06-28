"""Tests du modèle StraitStrut + drag brace (cf. PFD §5b).

Principe vérifié : la tige et l'axe de coulisse étant identiques au StraitStrut,
la **dynamique est rigoureusement la même** ; seuls s'ajoutent les efforts
d'ancrage (rotule B1 + linéaire annulaire B2 + bielle C–D), obtenus par
l'équilibre 3D isostatique du corps.
"""
from __future__ import annotations

import numpy as np
import pytest

from dropsim import (
    default_aircraft_inputs,
    default_strait_strut_inputs,
    default_strait_strut_drag_brace_inputs,
    run_simulation,
)
from dropsim.engine_strait_strut import _drag_brace_reactions
from dropsim.inputs import Point3
from dropsim.storage import inputs_from_dict, inputs_to_dict


def test_solver_equilibrium():
    """Le solveur d'équilibre du corps respecte (4')(6') et la contrainte annulaire."""
    B1 = np.array([1650.0, 70.0, 1078.0])
    B2 = np.array([1650.0, -70.0, 1078.0])
    C = np.array([1620.0, 0.0, 700.0])
    D = np.array([1950.0, 0.0, 1120.0])
    R_int = np.array([-2000.0, 300.0, 25000.0])
    M_int = np.array([1.5e5, -8e5, 4e4])
    T, R_B1, R_B2 = _drag_brace_reactions(R_int, M_int, B1, B2, C, D)
    u_B = (B1 - B2) / np.linalg.norm(B1 - B2)
    u_CD = (D - C) / np.linalg.norm(D - C)
    # Résultante (4') et moment en B1 (6')
    res = R_B1 + R_B2 + T * u_CD + R_int
    mom = M_int + np.cross(B2 - B1, R_B2) + np.cross(C - B1, T * u_CD)
    assert np.linalg.norm(res) < 1e-6
    assert np.linalg.norm(mom) < 1e-6
    # Linéaire annulaire : pas d'effort selon l'axe B1-B2
    assert abs(float(R_B2 @ u_B)) < 1e-9


def test_standalone_dynamics_identical_to_strait_strut():
    """Drop test isolé : dynamique drag brace == StraitStrut (même coulisse)."""
    d_std = run_simulation(default_strait_strut_inputs()).df
    d_db = run_simulation(default_strait_strut_drag_brace_inputs()).df
    for col in ("StraitStrut.Ftot (N)", "Tyre.FTyre (N)", "StraitStrut.d (m)",
                "Reaction sol horizontale (N)"):
        assert np.allclose(d_std[col].to_numpy(), d_db[col].to_numpy(), atol=0.0, rtol=0.0)


def test_standalone_drag_brace_efforts_present():
    """Les efforts d'ancrage sont produits et non identiquement nuls."""
    df = run_simulation(default_strait_strut_drag_brace_inputs()).df
    for col in ("DragBrace.Effort bielle (N)", "DragBrace.B1 Fx (N)", "DragBrace.B2 Fz (N)"):
        assert col in df.columns
    assert np.any(df["DragBrace.Effort bielle (N)"].to_numpy() != 0.0)


def test_aircraft_dynamics_identical_with_drag_brace_nlg():
    """Avion : NLG drag brace → même dynamique que NLG encastré (torseur total
    identique), plus les colonnes d'efforts d'ancrage."""
    ac_ref = default_aircraft_inputs()
    ac_db = default_aircraft_inputs()
    ac_db.nlg = default_strait_strut_drag_brace_inputs()
    r_ref = run_simulation(ac_ref)
    r_db = run_simulation(ac_db)
    for key in ("Effort vertical total max Fz (N)", "Accélération CG max (g)",
                "Course max NLG (mm)"):
        assert r_db.summary[key] == pytest.approx(r_ref.summary[key], rel=1e-9, abs=1e-6)
    assert "NLG.DragBrace.Effort bielle (N)" in r_db.full_df.columns
    assert np.any(r_db.full_df["NLG.DragBrace.Effort bielle (N)"].to_numpy() != 0.0)


def test_storage_roundtrip():
    inp = default_strait_strut_drag_brace_inputs()
    inp.B1 = Point3(1700.0, 70.0, 1078.0)
    inp.Ddb = Point3(1950.0, 0.0, 1200.0)
    back = inputs_from_dict(inputs_to_dict(inp))
    assert back.model_kind == "strait_strut_drag_brace"
    assert back == inp
