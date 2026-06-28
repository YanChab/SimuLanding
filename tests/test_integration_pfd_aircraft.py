"""Avion complet : la structure PFD (§7) reproduit la dynamique 2 DDL historique.

Les accélérations (z̈_cg, θ̈) reconstruites par ``fuselage_accelerations`` à partir
des efforts d'interface des trois trains doivent reproduire celles du moteur avion
(``run_aircraft``) à la précision machine — validation du bouclage (9)–(10).
"""
import numpy as np

from dropsim import storage as ds
from dropsim.integration_pfd_aircraft import run_aircraft_pfd

_REF = "saved_simulations/référence_avion_complet/Simulation_avion_complet_reférence.json"


def test_fuselage_pfd_matches_aircraft_dynamics():
    inp, _res, _meta = ds.load_simulation(_REF)
    r = run_aircraft_pfd(inp)
    for kp, kh, scale in [
        ("z_ddot", "z_ddot_hist", float(np.max(np.abs(r["z_ddot_hist"])))),
        ("theta_ddot", "theta_ddot_hist", float(np.max(np.abs(r["theta_ddot_hist"])))),
    ]:
        sc = max(1.0, scale)
        assert np.max(np.abs(r[kp] - r[kh])) / sc < 1e-9, f"{kp} ne reproduit pas {kh}"


def test_aircraft_arm_mass_coupling():
    """Masse balancier MLG active dans la dynamique avion couplée (§6.7)."""
    inp, _r, _m = ds.load_simulation(_REF)
    base = run_aircraft_pfd(inp, m_arm=0.0)
    heavy = run_aircraft_pfd(inp, m_arm=20.0)
    # La fermeture PFD (9)-(10) reste exacte même avec masse active.
    sc = max(1.0, float(np.max(np.abs(heavy["theta_ddot_hist"]))))
    assert np.max(np.abs(heavy["theta_ddot"] - heavy["theta_ddot_hist"])) / sc < 1e-9
    # La masse change bien la trajectoire avion.
    assert np.max(np.abs(heavy["z_ddot"] - base["z_ddot"])) > 1e-2
