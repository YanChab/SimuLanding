"""Non-régression : la sortie d'accélération de tige du NLG (StraitStrut) de
l'avion est bien l'accélération **axiale** (le long de l'axe de coulisse),
cohérente avec la vitesse `nlg_vitmns` intégrée et avec le moteur isolé.

Historique du bug : `nlg_accmns` était calculée avec le Fz **vertical** brut
(`(−ftot + Fz − m·G)/m`), alors que la dynamique intégrée (et `vitmns`/`depmns`)
est axiale. Pour une jambe inclinée, la sortie était donc incohérente avec sa
propre vitesse — ce qui faussait toute comparaison d'accélération de tige
avion vs train isolé.
"""
from __future__ import annotations

import numpy as np

from dropsim import default_aircraft_inputs
from dropsim.engine_aircraft import run_aircraft

G = 9.81


def _run(pitch_deg: float):
    inp = default_aircraft_inputs()
    inp.drop.pitch = pitch_deg          # assiette non nulle → jambe inclinée (axial ≠ vertical)
    inp.simulation.temps_simu = 0.15
    d = run_aircraft(inp.to_si()).data
    return inp, d


def test_nlg_accmns_integrates_to_vitmns():
    """∫ accmns dt reproduit vitmns : la sortie EST la dérivée de la vitesse."""
    _, d = _run(3.0)
    t = np.asarray(d["temps"]); acc = np.asarray(d["nlg_accmns"]); vit = np.asarray(d["nlg_vitmns"])
    vit_int = vit[0] + np.concatenate([[0.0], np.cumsum(0.5 * (acc[1:] + acc[:-1]) * np.diff(t))])
    assert np.max(np.abs(vit_int - vit)) < 0.05


def test_nlg_accmns_is_axial_not_vertical():
    """Garde anti-régression : avec une jambe inclinée, la sortie axiale diffère
    nettement de l'ancienne formule verticale (−ftot + Fz − m·G)/m."""
    inp, d = _run(3.0)
    m = inp.nlg.unsprung_mass
    Fz = np.asarray(d["nlg_tyre_ftyre"]); ft = np.asarray(d["nlg_ftot"])
    vertical = (-ft + Fz - m * G) / m
    acc = np.asarray(d["nlg_accmns"])
    assert np.sqrt(np.mean((acc - vertical) ** 2)) > 5.0
