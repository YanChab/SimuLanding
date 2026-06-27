"""Équivalence du moteur StraitStrut PFD avec le moteur historique (corrigé).

Pour la géométrie coaxiale par défaut, l'assemblage PFD
(``run_strait_strut_pfd``) doit reproduire le moteur historique
(``run_strait_strut``, signe Fx@B déjà corrigé) à la précision machine.
"""
import numpy as np

from dropsim import default_strait_strut_inputs
from dropsim.engine_strait_strut import run_strait_strut
from dropsim.integration_pfd_strait import run_strait_strut_pfd


def test_pfd_matches_legacy_strait_strut():
    p = default_strait_strut_inputs().to_si()
    hist = run_strait_strut(p).data
    pfd = run_strait_strut_pfd(p)

    pairs = [
        ("d", "trailing_arm_d"),
        ("ftot", "trailing_arm_ftot"),
        ("fz_tyre", "tyre_ftyre"),
        ("fx_b", "torsB_fx"),
        ("fz_b", "torsB_fz"),
        ("reaction_h", "reaction_h"),
    ]
    n = min(len(pfd["d"]), len(hist["trailing_arm_d"]))
    for kp, kh in pairs:
        a = np.asarray(pfd[kp])[:n]
        b = np.asarray(hist[kh])[:n]
        scale = max(1.0, float(np.max(np.abs(b))))
        assert np.max(np.abs(a - b)) / scale < 1e-9, (
            f"{kp} ≠ {kh} (écart relatif trop grand)"
        )


def test_pfd_fx_b_matches_reaction_h_sign():
    """Fx@B du moteur PFD est cohérent (même signe que reaction_h)."""
    pfd = run_strait_strut_pfd(default_strait_strut_inputs().to_si())
    k = int(np.argmax(np.abs(pfd["reaction_h"])))
    assert np.sign(pfd["fx_b"][k]) == np.sign(pfd["reaction_h"][k])
