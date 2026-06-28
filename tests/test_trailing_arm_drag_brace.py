"""Tests du modèle TrailingArm + jambe/bielle (cf. PFD §6b).

La dynamique (balancier + amortisseur) est identique au TrailingArm ; s'ajoutent
les efforts d'ancrage de la jambe (rotule F1 + linéaire annulaire F2 + bielle D–E),
par équilibre 3D isostatique de la jambe.
"""
from __future__ import annotations

import numpy as np
import pytest

from dropsim import (
    default_aircraft_inputs,
    default_trailing_arm_inputs,
    default_trailing_arm_drag_brace_inputs,
    run_simulation,
)
from dropsim.inputs import Point3
from dropsim.storage import inputs_from_dict, inputs_to_dict


def test_standalone_dynamics_identical_to_trailing_arm():
    """Drop test isolé : dynamique jambe == TrailingArm (mêmes B/A/C/R/S)."""
    d_std = run_simulation(default_trailing_arm_inputs()).df
    d_jb = run_simulation(default_trailing_arm_drag_brace_inputs()).df
    for col in ("TrailingArm.Ftot (N)", "Tyre.FTyre (N)", "TrailingArm.d (m)",
                "Torseur@B (pivot).Effort Z (N)"):
        assert np.allclose(d_std[col].to_numpy(), d_jb[col].to_numpy(), atol=0.0, rtol=0.0)


def test_standalone_jambe_efforts_present():
    df = run_simulation(default_trailing_arm_drag_brace_inputs()).df
    for col in ("DragBrace.Effort bielle (N)", "DragBrace.F1 Fx (N)", "DragBrace.F2 Fz (N)"):
        assert col in df.columns
    assert np.any(df["DragBrace.Effort bielle (N)"].to_numpy() != 0.0)


def test_aircraft_dynamics_identical_with_jambe_mlg():
    """Avion : MLG jambe/bielle → même dynamique que MLG standard + efforts F1/F2."""
    ac_ref = default_aircraft_inputs()
    ac_jb = default_aircraft_inputs()
    ac_jb.mlg = default_trailing_arm_drag_brace_inputs()
    r_ref = run_simulation(ac_ref)
    r_jb = run_simulation(ac_jb)
    for key in ("Effort vertical total max Fz (N)", "Accélération CG max (g)",
                "Course max NLG (mm)"):
        assert r_jb.summary[key] == pytest.approx(r_ref.summary[key], rel=1e-9, abs=1e-6)
    assert "MLG left.DragBrace.Effort bielle (N)" in r_jb.full_df.columns
    assert np.any(r_jb.full_df["MLG left.DragBrace.Effort bielle (N)"].to_numpy() != 0.0)


def test_storage_roundtrip():
    inp = default_trailing_arm_drag_brace_inputs()
    inp.F1 = Point3(5300.0, -1200.0, 1000.0)
    inp.Ebr = Point3(5550.0, -600.0, 1100.0)
    back = inputs_from_dict(inputs_to_dict(inp))
    assert back.model_kind == "trailing_arm_drag_brace"
    assert back == inp
