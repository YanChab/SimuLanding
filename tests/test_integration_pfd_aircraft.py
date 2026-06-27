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
