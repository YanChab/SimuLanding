"""Moteur TrailingArm PFD (torseur 3D) : équivalence historique + effet de masse.

Cf. docs/PFD_trains.md §6. Le moteur historique calcule déjà l'interface 3D dans
la limite balancier sans masse ; le moteur PFD doit reproduire **efforts ET
moments** (Fx, Fy, Fz, Mx, Mz) à la précision machine pour m_arm = 0.
"""
import numpy as np

from dropsim import default_trailing_arm_inputs
from dropsim.engine import run_trailing_arm
from dropsim.integration_pfd_trailing import run_trailing_arm_pfd


def test_pfd_3d_torsor_matches_legacy_when_massless():
    p = default_trailing_arm_inputs().to_si()
    hist = run_trailing_arm(p).data
    pfd = run_trailing_arm_pfd(p, m_arm=0.0)

    pairs = [
        ("fb_x", "torsB_fx"), ("fb_y", "torsB_fy"), ("fb_z", "torsB_fz"),
        ("mb_x", "torsB_mx"), ("mb_z", "torsB_mz"),
        ("fc_x", "torsC_fx"), ("fc_y", "torsC_fy"), ("fc_z", "torsC_fz"),
    ]
    n = min(len(pfd["fb_x"]), len(hist["torsB_fx"]))
    for kp, kh in pairs:
        a = np.asarray(pfd[kp])[:n]
        b = np.asarray(hist[kh])[:n]
        scale = max(1.0, float(np.max(np.abs(b))))
        assert np.max(np.abs(a - b)) / scale < 1e-9, f"{kp} ≠ {kh}"


def test_pfd_recovers_pivot_moments():
    """Roue déportée en Y du cas par défaut → Mx, Mz non nuls et retrouvés."""
    pfd = run_trailing_arm_pfd(default_trailing_arm_inputs().to_si(), m_arm=0.0)
    assert np.max(np.abs(pfd["mb_x"])) > 100.0   # Mx réel (déport Y de la roue)


def test_balancier_mass_changes_interface():
    """La masse du balancier (§6.5, au-delà du code) modifie l'effort au pivot."""
    p = default_trailing_arm_inputs().to_si()
    pfd0 = run_trailing_arm_pfd(p, m_arm=0.0)
    pfd_m = run_trailing_arm_pfd(p, m_arm=80.0)
    assert np.max(np.abs(pfd_m["fb_z"] - pfd0["fb_z"])) > 100.0
    # La rotule C (bielle seule) n'est PAS affectée par la masse du bras.
    assert np.allclose(pfd_m["fc_z"], pfd0["fc_z"])
