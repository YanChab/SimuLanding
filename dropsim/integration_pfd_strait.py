"""Moteur StraitStrut (NLG) reconstruit strictement selon le PFD.

Réutilise les **sous-modèles constitutifs validés** (gaz, hydraulique, metering,
pneu, frottements, butée) du moteur historique, mais remplace **l'assemblage de
corps rigide** par ``integration_pfd.strait_strut_interface`` — c.-à-d. les
équations (1)–(6) de ``docs/PFD_trains.md``.

Différence de fond avec ``engine_strait_strut.run_strait_strut`` :
- l'effort d'interface en B est calculé par bilan PFD explicite (corps fixe sans
  masse, décalages ξR/ξB possibles, frottements déjà inclus dans F_tot) ;
- le signe horizontal `Fx@B` suit la convention `reaction_h` / TrailingArm
  (effort transmis à la cellule), conforme au PFD.
"""
from __future__ import annotations

import numpy as np

from .engine import _endstop
from .engine_strait_strut import (
    BagFrictionDP4,
    DEFAULT_BAG_FRICTION_DP4,
    _ffribag_nlg,
    _ffrijoi_nlg,
    _init_strait_strut_local_state,
    _rot_sol_to_lg,
    _strait_strut_advance_local_state,
    _strait_strut_resolve_damper_step,
)
from .gas import GasSpring
from .inputs import TrailingArmParamsSI
from .integration_pfd import strait_strut_interface
from .metering import build_section_table
from .tyre import build_tyre_tables, f_tyre
from .units import G


def run_strait_strut_pfd(
    p: TrailingArmParamsSI,
    *,
    seal_precomp_pa: float = 110_649.0,
    bague_guide_m: float = 0.05,
    bague_piston_m: float = 0.05,
    bag_friction=DEFAULT_BAG_FRICTION_DP4,
    alfap: float = 0.0,
    alfar: float = 0.0,
    h_pivot_z_m: float = 0.60,
    h_guide_top_z_m: float = 0.50,
    h_guide_bot_z_m: float = 0.20,
    r_offset_m: tuple[float, float] = (0.0, 0.0),
    b_offset_m: tuple[float, float] = (0.0, 0.0),
) -> dict[str, np.ndarray]:
    """Drop test NLG, assemblage rigide strictement conforme au PFD (doc §2–§5)."""
    _bag_coeffs = (bag_friction if isinstance(bag_friction, BagFrictionDP4)
                   else BagFrictionDP4(*bag_friction))
    gas = GasSpring(p)
    tab_pos, tab_sec = build_section_table(p)
    tyre_defl_tbl, tyre_load_tbl = build_tyre_tables(p)

    R_sol_to_lg = _rot_sol_to_lg(alfap, alfar)
    R_lg_to_sol = R_sol_to_lg.T
    # Rotation plane (X,Z) sol → jambe (x1,z1)
    P_sol_to_lg = R_sol_to_lg[np.ix_([0, 2], [0, 2])]

    state = _init_strait_strut_local_state(
        p, gas, R_sol_to_lg, R_lg_to_sol,
        h_pivot_z_m=h_pivot_z_m,
        h_guide_top_z_m=h_guide_top_z_m,
        h_guide_bot_z_m=h_guide_bot_z_m,
        r_offset_m=r_offset_m,
        b_offset_m=b_offset_m,
    )

    dt = p.it
    n_steps = max(1, round(p.temps_simu / dt))
    method = p.integrator
    poids_ms = p.masse * G * (1.0 - p.lift)
    n_out = n_steps + 1

    keys = ["temps", "d", "v", "ftot", "fz_tyre", "fx_b", "fz_b", "m_b",
            "reaction_h", "accms", "pg", "pc", "pd", "tyre_defl", "x_gt", "x_gb"]
    out = {k: np.zeros(n_out) for k in keys}

    for i in range(n_out):
        damp = _strait_strut_resolve_damper_step(p, gas, tab_pos, tab_sec, state)
        pg, pc, pd = damp["pg"], damp["pc"], damp["pd"]
        state.delta_pc = damp["delta_pc"]
        state.delta_pd = damp["delta_pd"]
        state.pg_prev = pg

        ffrijoi = _ffrijoi_nlg(state.v_damper, pd, p, seal_precomp_pa)
        fendstop = _endstop(state.d, p.course, smooth_len=p.endstop_smooth)

        # --- Effort de contact pneu (convention reaction_h : Fx = tr_x) ---------
        tyre_ftyre = max(0.0, f_tyre(state.tyre_defl_val, tyre_defl_tbl, tyre_load_tbl))
        fx_spring_wheel = -p.kx * state.tyre_depx - p.cx * state.tyre_vx
        tr_x = -fx_spring_wheel
        contact_sol = np.array([tr_x, tyre_ftyre])

        # --- Géométrie (repère jambe : ζ = axial idx2, ξ = transverse idx0) -----
        zeta_R, xi_R = float(state.ptR_lg[2]), float(state.ptR_lg[0])
        zeta_Gt = float(state.ptGt_lg[2])
        zeta_Gb = float(state.ptGb_lg[2])
        zeta_B, xi_B = float(state.ptB_lg[2]), float(state.ptB_lg[0])
        zeta_G1, xi_G1 = 0.5 * (zeta_R + zeta_Gt), 0.5 * xi_R

        geom = dict(
            P_sol_to_lg=P_sol_to_lg, contact_sol=contact_sol,
            zeta_R=zeta_R, xi_R=xi_R, zeta_Gt=zeta_Gt, zeta_Gb=zeta_Gb,
            zeta_B=zeta_B, xi_B=xi_B, zeta_G1=zeta_G1, xi_G1=xi_G1,
        )

        # 1) Réactions de bague (indépendantes de F_tot) → friction de bague
        prelim = strait_strut_interface(f_tot=0.0, **geom)
        ffribag = _ffribag_nlg(state.v_damper, prelim.X_gt, prelim.X_gb,
                               p.Dt, p.Dpis, bague_guide_m, bague_piston_m, _bag_coeffs)

        # 2) Effort d'amortisseur (frottements inclus) puis interface PFD complète
        ftot = p.Sc * pc - p.Sd * pd + p.Sbh * pg + ffrijoi + ffribag + fendstop
        iface = strait_strut_interface(f_tot=ftot, **geom)
        F_B = iface.F_B
        accms = (F_B[1] - poids_ms) / p.masse

        out["temps"][i] = i * dt
        out["d"][i] = max(0.0, state.d)
        out["v"][i] = state.v_damper
        out["ftot"][i] = ftot
        out["fz_tyre"][i] = tyre_ftyre
        out["fx_b"][i] = F_B[0]
        out["fz_b"][i] = F_B[1]
        out["m_b"][i] = iface.M_B
        out["reaction_h"][i] = tr_x
        out["accms"][i] = accms
        out["pg"][i] = pg / 1.0e5
        out["pc"][i] = pc / 1.0e5
        out["pd"][i] = pd / 1.0e5
        out["tyre_defl"][i] = state.tyre_defl_val
        out["x_gt"][i] = iface.X_gt
        out["x_gb"][i] = iface.X_gb

        state = _strait_strut_advance_local_state(
            p, state, R_sol_to_lg, R_lg_to_sol,
            support_acc_ms_z=accms, ftot=ftot, tyre_ftyre_i=tyre_ftyre,
            dt=dt, method=method,
        )

    return out
