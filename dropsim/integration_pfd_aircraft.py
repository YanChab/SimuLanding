"""Avion complet — assemblage de la structure selon le PFD (doc §7).

Réutilise le moteur avion historique (``engine_aircraft.run_aircraft``) pour la
simulation couplée (constitutif + noyaux locaux NLG/MLG + cinématique), puis
**recalcule la dynamique 2 DDL du fuselage strictement par le PFD**
(``integration_pfd.fuselage_accelerations``, équations (9)–(10)) à partir des
**efforts d'interface** transmis par les trois trains :

- NLG : encastrement en B → effort (Fx, Fz) **+ moment My** ;
- MLG gauche / droite : pivot B + rotule C → efforts (Fx, Fz), sans My.

Pour ``m_arm = 0`` (modèle historique), les accélérations (z̈_cg, θ̈) ainsi
reconstruites doivent reproduire celles du moteur avion à la précision machine —
ce qui valide le bouclage des équations de structure (§7).
"""
from __future__ import annotations

import numpy as np

from .engine_aircraft import run_aircraft
from .inputs import AircraftInputs
from .integration_pfd import InterfaceLoad, fuselage_accelerations


def run_aircraft_pfd(inp: AircraftInputs, *, m_arm: float = 0.0) -> dict[str, np.ndarray]:
    """Reconstruit (z̈_cg, θ̈) du fuselage par le PFD (§7) et compare à l'historique.

    ``m_arm`` : masse balancier MLG active dans la **dynamique avion couplée**
    (PFD §6.7). 0 ⇒ identique au moteur historique ; > 0 ⇒ change la trajectoire.
    """
    out = run_aircraft(inp.to_si(), mlg_arm_mass=m_arm)
    d = out.data
    g = out.geometry or {}

    mass = float(inp.body.masse)
    jyy = float(inp.body.jyy)
    lift = float(inp.body.lift)

    n = len(d["aircraft_cg_az"])
    res = {k: np.zeros(n) for k in
           ["temps", "z_ddot", "theta_ddot", "z_ddot_hist", "theta_ddot_hist"]}

    for _i in range(n):
        cg = np.array([g["cg_x"][_i], g["cg_z"][_i]])
        loads = [
            # NLG : encastrement (effort + moment My)
            InterfaceLoad(
                P=np.array([g["nlg_bx"][_i], g["nlg_bz"][_i]]),
                F=np.array([d["nlg_torsb_fx"][_i], d["nlg_torsb_fz"][_i]]),
                M_y=float(d["nlg_torsb_my"][_i]),
            ),
            # MLG gauche : pivot B + rotule C
            InterfaceLoad(
                P=np.array([g["mlg_left_bx"][_i], g["mlg_left_bz"][_i]]),
                F=np.array([d["mlg_left_torsb_fx"][_i], d["mlg_left_torsb_fz"][_i]]),
            ),
            InterfaceLoad(
                P=np.array([g["mlg_left_cx"][_i], g["mlg_left_cz"][_i]]),
                F=np.array([d["mlg_left_torsc_fx"][_i], d["mlg_left_torsc_fz"][_i]]),
            ),
            # MLG droite : pivot B + rotule C
            InterfaceLoad(
                P=np.array([g["mlg_right_bx"][_i], g["mlg_right_bz"][_i]]),
                F=np.array([d["mlg_right_torsb_fx"][_i], d["mlg_right_torsb_fz"][_i]]),
            ),
            InterfaceLoad(
                P=np.array([g["mlg_right_cx"][_i], g["mlg_right_cz"][_i]]),
                F=np.array([d["mlg_right_torsc_fx"][_i], d["mlg_right_torsc_fz"][_i]]),
            ),
        ]
        z_ddot, theta_ddot = fuselage_accelerations(
            loads=loads, cg=cg, mass=mass, jyy=jyy, lift=lift,
        )
        res["temps"][_i] = d["temps"][_i] if "temps" in d else _i
        res["z_ddot"][_i] = z_ddot
        res["theta_ddot"][_i] = theta_ddot
        res["z_ddot_hist"][_i] = d["aircraft_cg_az"][_i]
        res["theta_ddot_hist"][_i] = d["aircraft_pitch_acc"][_i]
    return res
