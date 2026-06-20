"""Tests dédiés à la butée de course lissée."""
from __future__ import annotations

import pytest

from dropsim import default_trailing_arm_inputs, run_simulation
from dropsim.engine import _endstop


def test_endstop_smooth_softens_contact_onset():
    """En faible pénétration, la pente au contact doit rester douce."""
    course = 0.185
    x = 1.0e-4  # 0.1 mm de pénétration
    k = 1.0e8
    f_end = _endstop(course + x, course, smooth_len=2.0e-3, k_endstop=k)
    # Référence linéaire historique (non utilisée en production) pour borner.
    assert f_end < k * x


def test_endstop_smooth_matches_legacy_far_from_contact():
    """En forte pénétration, la loi lissée tend vers la loi linéaire asymptotique."""
    course = 0.185
    x = 2.0e-2  # 20 mm de pénétration (x >> smooth_len)
    k = 1.0e8
    f_smooth = _endstop(course + x, course, smooth_len=2.0e-3, k_endstop=k)
    assert f_smooth == pytest.approx(k * x, rel=1.0e-4)


def test_simulation_runs_with_smooth_endstop():
    """Le solveur complet doit tourner avec la butée lissée sans erreur."""
    inp = default_trailing_arm_inputs()
    inp.endstop_smooth_mm = 2.0
    result = run_simulation(inp)
    assert result.n_steps > 0
    assert not result.df.empty
