"""Avion complet — cohérence du couplage du slot TrailingArm (MLG).

Garde-fou contre un bug de base de temps : dans l'avion complet, la boucle
structure pilote le temps au pas fin ``dt = it`` et le gear doit s'intégrer au
même pas. Si le « coarsening » ``auto_fast`` (×1.8, destiné au train ISOLÉ dont la
boucle avance réellement ``it·1.8`` par pas) est appliqué au gear sans coarsening
de la structure, alors ``It = dt·1.8`` et la vitesse d'amortisseur du MLG
(``v = −Δ|C−A|/It``, le déplacement support étant accumulé sur ``dt``) est
sous-estimée d'un facteur ~1.8.

Conséquence observable : le résultat MLG dépendait fortement du mode de solveur
(``auto_fast`` vs ``auto_precise``) — écart ~48 % sur la vitesse d'amortisseur.
Après correction (``fast_time_scale = 1.0`` côté avion), les deux modes coïncident.
"""
from dataclasses import replace

import numpy as np
import pytest

from dropsim.inputs import default_aircraft_inputs
from dropsim.simulation import run_simulation


def _run(solver: str):
    base = default_aircraft_inputs()
    # Chute douce : la course MLG reste sous la butée (sinon le talonnage
    # masquerait la comparaison).
    inp = replace(
        base,
        drop=replace(base.drop, vz=1.2),
        simulation=replace(base.simulation, damper_core_solver=solver),
    )
    r = run_simulation(inp)
    v = float(np.max(np.abs(r.df["MLG left.v (m/s)"])))
    stroke_mm = float(np.max(r.df["MLG left.d (m)"])) * 1000.0
    course_mm = float(base.mlg.course)
    return v, stroke_mm, course_mm


@pytest.mark.slow
@pytest.mark.regression
def test_aircraft_mlg_velocity_independent_of_solver_speed_mode():
    v_fast, stroke_fast, course = _run("auto_fast")
    v_prec, stroke_prec, _ = _run("auto_precise")

    # Comparaison valable seulement hors talonnage.
    assert stroke_fast < course - 1.0 and stroke_prec < course - 1.0, (
        f"Configuration en butée (stroke {stroke_fast:.1f}/{stroke_prec:.1f} mm "
        f">= course {course:.1f} mm) : réduire vz pour le test."
    )
    # La vitesse d'amortisseur MLG ne doit pas dépendre de l'échelle de temps du
    # solveur : avant correction l'écart était ~48 %.
    assert v_fast == pytest.approx(v_prec, rel=0.05), (
        f"Vitesse amortisseur MLG dépendante du solveur (bug base de temps ?) : "
        f"auto_fast={v_fast:.3f} m/s vs auto_precise={v_prec:.3f} m/s"
    )
    # Sanity : le MLG travaille réellement (test non vide).
    assert v_prec > 0.1
