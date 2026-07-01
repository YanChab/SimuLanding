"""Non-régression : l'assiette de chute (pitch/roll) est appliquée au StraitStrut
isolé par ROTATION RIGIDE des points, avec le **bon signe** — cohérent avec le
moteur avion (rotation rigide de tout l'aéronef).

Historique du bug : le chemin isolé faisait ``alfap = strut_pitch + pitch``,
soit l'assiette appliquée à l'envers. Un pitch nez-haut (+) doit **diminuer**
l'angle de la jambe par rapport au sol (``strut_pitch − pitch``), comme le fait
le moteur avion via sa rotation de corps rigide. Cf. dropsim/geometry.rotate_about
(méthodologie déjà utilisée par le TrailingArm) et inputs.strut_inputs_at_attitude.
"""
from __future__ import annotations

import math
from dataclasses import replace

import pytest

from dropsim import (
    default_strait_strut_inputs,
    default_strait_strut_drag_brace_inputs,
    run_simulation,
)


def _leg_angle_deg(inp) -> float:
    """Angle SIGNÉ (deg) de l'axe de coulisse Gt→Gb par rapport à la verticale
    sol, au premier pas (avant dynamique)."""
    g = run_simulation(inp).geometry
    dx = float(g["gtx"].iloc[0] - g["gbx"].iloc[0])
    dz = float(g["gtz"].iloc[0] - g["gbz"].iloc[0])
    return math.degrees(math.atan2(dx, dz))


@pytest.mark.parametrize(
    "factory",
    [default_strait_strut_inputs, default_strait_strut_drag_brace_inputs],
    ids=["strait_strut", "strait_strut_drag_brace"],
)
@pytest.mark.parametrize("pitch", [-3.0, -1.0, 2.0, 4.0])
def test_pitch_is_rigid_rotation_correct_sign(factory, pitch):
    """L'angle jambe/sol à pitch p vaut (rake à pitch 0) − p (rotation rigide
    nez-haut), et surtout PAS + p (ancien bug de signe)."""
    rake0 = _leg_angle_deg(replace(factory(), pitch=0.0))
    ang = _leg_angle_deg(replace(factory(), pitch=pitch))
    assert ang == pytest.approx(rake0 - pitch, abs=0.05)
    # Garde-fou explicite contre le retour du bug (signe opposé).
    assert abs(ang - (rake0 + pitch)) > 0.1 or abs(pitch) < 1e-9


def test_pitch_zero_is_identity():
    """À pitch 0, la rotation est l'identité : le rake vaut la géométrie brute."""
    inp = default_strait_strut_inputs()
    ang = _leg_angle_deg(inp)
    # Rake purement géométrique dérivé des points Gt/Gb (repère avion, pitch 0).
    dx = inp.Gt.x - inp.Gb.x
    dz = inp.Gt.z - inp.Gb.z
    assert ang == pytest.approx(math.degrees(math.atan2(dx, dz)), abs=0.05)
