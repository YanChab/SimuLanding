"""Non-régression : le StraitStrut isolé démarre au **contact net** (déflexion
pneu nulle à t=0), comme le moteur avion, sans le transitoire parasite dû au
rake / déport de la roue.

Historique : le calcul de déflexion prenait ``unload_radius`` comme référence
brute (``defl = unload_radius - R_z``). Avec une jambe rakée / une roue déportée,
``R_z`` de départ ≠ ``unload_radius`` → déflexion (et effort pneu) parasite dès
t=0 (~3 à 7 mm selon la géométrie). La déflexion est désormais référencée sur la
hauteur réelle du centre roue au contact initial.
"""
from __future__ import annotations

import numpy as np
import pytest

from dropsim import (
    default_strait_strut_inputs,
    default_strait_strut_drag_brace_inputs,
    run_simulation,
)


def _defl_col(df):
    return next(c for c in df.columns if "Defl" in c)


def _ftyre_col(df):
    return next(c for c in df.columns if "FTyre" in c)


def _ftot_col(df):
    return next(c for c in df.columns if "Ftot" in c)


def _v_col(df):
    return next(c for c in df.columns if ".v (m/s)" in c)


@pytest.mark.parametrize(
    "factory",
    [default_strait_strut_inputs, default_strait_strut_drag_brace_inputs],
    ids=["strait_strut", "strait_strut_drag_brace"],
)
def test_initial_tyre_deflection_is_zero(factory):
    """À t=0, la roue est juste au contact : déflexion et effort pneu nuls."""
    df = run_simulation(factory()).df
    assert df[_defl_col(df)].iloc[0] == pytest.approx(0.0, abs=1e-9)
    assert df[_ftyre_col(df)].iloc[0] == pytest.approx(0.0, abs=1e-6)


def test_deflection_stays_non_negative_and_grows_then_returns():
    """La déflexion reste ≥ 0 et a bien un pic strictement positif (le pneu se
    comprime), preuve que la référence de contact n'a pas cassé la physique."""
    df = run_simulation(default_strait_strut_inputs()).df
    defl = df[_defl_col(df)].to_numpy(dtype=float)
    assert np.all(defl >= -1e-12)
    assert float(defl.max()) > 1e-3  # pic de compression franc (> 1 mm)


@pytest.mark.parametrize(
    "factory",
    [default_strait_strut_inputs, default_strait_strut_drag_brace_inputs],
    ids=["strait_strut", "strait_strut_drag_brace"],
)
def test_initial_damper_force_balanced(factory):
    """À pleine extension, la précharge gaz est reprise par la BUTÉE DE DÉTENTE :
    l'effort amortisseur initial est ≈ 0 (comme le MLG/TrailingArm), et non la
    précharge gaz brute (~500 N). Sinon la tige partirait en extension à t=0."""
    df = run_simulation(factory()).df
    assert abs(df[_ftot_col(df)].iloc[0]) < 5.0


def test_no_spurious_extension_at_start():
    """Le strut ne part pas en extension : la vitesse amortisseur ne plonge pas
    négative au démarrage. L'ancien départ non équilibré (précharge gaz ~500 N
    non reprise) donnait v ≈ −0,013 m/s pendant ~1,5 ms."""
    df = run_simulation(default_strait_strut_inputs()).df
    v = df[_v_col(df)].to_numpy(dtype=float)
    assert v[:10].min() > -1.0e-3
