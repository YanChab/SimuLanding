"""Moteur de simulation de drop test pour train avant à jambe de force directe (StraitStrut / NLG).

Reproduit fidèlement la macro VBA ``DropCalcul`` du module ``Feuil2`` du classeur
Excel DROSIM. Différences clés par rapport au TrailingArm :

* **Deux corps** : masse suspendue Ms (fuselage) + masse non suspendue Mns
  (jambe basse + roue) intégrées séparément.
* **Pas de balancier** : cinématique linéaire directe de la jambe.
* **Transformation repère sol / repère jambe** via les angles de rake ``alfap``
  (tangage) et ``alfar`` (roulis) suivant la convention du VBA cRot.
* **Friction de guidage** ``FFriBag`` : bagues de guidage et piston, calculée
  à partir des efforts transverses ``XGt`` / ``XGb``.
* **Joint** : formule NLG avec terme de pré-compression séparé (``seal_precomp_pa``).

Les sous-fonctions hydraulique, gaz, pneu et bague hydraulique (metering) sont
réutilisées sans modification depuis les modules TrailingArm.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import NamedTuple

import numpy as np

from .engine import (
    EngineOutput,
    _endstop,
    _integrate_const_acc,
    _select_damper_core_solver,
    damper_force_step,
    damper_force_step_implicit_adaptive,
)
from .errors import ErrorCollector, OVERSTROKE_CODES, SimError, make_overstroke_warning
from .gas import GasSpring
from .hydraulic import _sign
from .inputs import TrailingArmParamsSI
from .metering import build_section_table
from .tyre import build_tyre_tables, f_tyre, mu, r_eff
from .units import G


# --------------------------------------------------------------------------- #
#  Colonnes de sortie StraitStrut (clé interne → libellé)
#
#  Les clés PARTAGÉES avec TrailingArm gardent le même nom interne afin que
#  simulation.py puisse générer le résumé et les graphes sans modification.
# --------------------------------------------------------------------------- #
OUTPUT_COLUMNS_SS: dict[str, str] = {
    # Temps et dynamique masse suspendue (repère sol)
    "temps": "Temps (s)",
    "accms": "AccMs.RsolZ (m/s²)",
    "vitms": "VitMs.RsolZ (m/s)",
    "depms": "DepMs.RsolZ (m)",
    # Dynamique masse non suspendue (repère jambe)
    "accmns": "AccMns.RlgZ (m/s²)",
    "vitmns": "VitMns.RlgZ (m/s)",
    "depmns": "DepMns.RlgZ (m)",
    # Amortisseur (mêmes clés internes que TrailingArm → résumé automatique)
    "trailing_arm_v": "StraitStrut.v (m/s)",
    "trailing_arm_d": "StraitStrut.d (m)",
    "trailing_arm_ftot": "StraitStrut.Ftot (N)",
    "trailing_arm_fhyd": "StraitStrut.Fhyd (N)",
    "trailing_arm_ffrijoi": "StraitStrut.FFriJoi (N)",
    "trailing_arm_ffribag": "StraitStrut.FFriBag (N)",
    "trailing_arm_fgas": "StraitStrut.FGas (N)",
    # Pressions (mêmes clés internes)
    "pg": "StraitStrut.Pg (bar)",
    "pc": "StraitStrut.Pc (bar)",
    "pd": "StraitStrut.Pd (bar)",
    "delta_pc": "StraitStrut.DeltaPc (bar)",
    "delta_pd": "StraitStrut.DeltaPd (bar)",
    # Section BH
    "secbh": "Section de la BH (mm²)",
    # Hydraulique (convergence)
    "hyd_conv_err": "Hydrau.Erreur convergence (-)",
    "hyd_conv_iter": "Hydrau.Itérations convergence (-)",
    "hyd_qc_total": "Hydrau.Qc total (m³/s)",
    "hyd_qc_bh": "Hydrau.Qc rainures BH (m³/s)",
    "hyd_qc_leak": "Hydrau.Qc fuite annulaire (m³/s)",
    "hyd_leak_ratio": "Hydrau.Part fuite (-)",
    "hyd_re_leak": "Hydrau.Re fuite annulaire (-)",
    # Pneu (mêmes clés internes)
    "tyre_defl": "Tyre.Defl (m)",
    "tyre_ftyre": "Tyre.FTyre (N)",
    "tyre_alpha": "Tyre.Alpha (rad/s²)",
    "tyre_omega": "Tyre.Omega (rad/s)",
    "tyre_mu": "Tyre.Mu",
    "tyre_slip": "Tyre.Slip",
    # Effort horizontal (spin-up / spring-back)
    "tr_x": "TR_sol.RsolX (N)",
    "reaction_v": "Reaction sol verticale (N)",
    "reaction_h": "Reaction sol horizontale (N)",
    # Guidage NLG (spécifique StraitStrut)
    "xgt": "StraitStrut.XGt (N)",
    "xgb": "StraitStrut.XGb (N)",
    # Pression de contact aux bagues (MPa) : alimente le coefficient de friction.
    # Gt : |XGt|/(Dt·Lguide) ; Gb : |XGb|/(Dpis·Lpiston).
    "p_bag_guide": "StraitStrut.PcontactGt (MPa)",
    "p_bag_piston": "StraitStrut.PcontactGb (MPa)",
    # Coefficient de friction de bague DP4 calculé (μ_Gt, μ_Gb).
    "mu_bag_guide": "StraitStrut.MuGt (-)",
    "mu_bag_piston": "StraitStrut.MuGb (-)",
    # Ancrage drag brace (cf. PFD §5b) : efforts STRUCTURE→CORPS, repère jambe.
    "db_brace_T": "DragBrace.Effort bielle (N)",
    "db_b1_fx": "DragBrace.B1 Fx (N)",
    "db_b1_fy": "DragBrace.B1 Fy (N)",
    "db_b1_fz": "DragBrace.B1 Fz (N)",
    "db_b2_fx": "DragBrace.B2 Fx (N)",
    "db_b2_fy": "DragBrace.B2 Fy (N)",
    "db_b2_fz": "DragBrace.B2 Fz (N)",
    "db_brace_fx": "DragBrace.Bielle@D Fx (N)",
    "db_brace_fy": "DragBrace.Bielle@D Fy (N)",
    "db_brace_fz": "DragBrace.Bielle@D Fz (N)",
    # Torseur à l'attache fuselage B (torseur transmis au fuselage)
    "tors_res_x": "Torseur.Resultante X (N)",
    "tors_res_y": "Torseur.Resultante Y (N)",
    "tors_res_z": "Torseur.Resultante Z (N)",
    "tors_res_norm": "Torseur.Resultante norme (N)",
    "torsB_fx": "Torseur@B (pivot).Effort X (N)",
    "torsB_fy": "Torseur@B (pivot).Effort Y (N)",
    "torsB_fz": "Torseur@B (pivot).Effort Z (N)",
    "torsB_mx": "Torseur@B (pivot).Moment X (N·m)",
    "torsB_mz": "Torseur@B (pivot).Moment Z (N·m)",
    # Bilan énergétique (bilan simplifié par rapport au balancier)
    "e_kin": "Énergie.Cinétique masse susp. (J)",
    "e_kin_mns": "Énergie.Cinétique masse non susp. (J)",
    "e_kin_spin": "Énergie.Cinétique rotation roue (J)",
    "e_kin_horiz": "Énergie.Cinétique horizontale roue (J)",
    "e_gas": "Énergie.Stockée gaz (J)",
    "e_tyre": "Énergie.Stockée pneu vertical (J)",
    "e_spring_x": "Énergie.Stockée ressort horizontal (J)",
    "e_hyd": "Énergie.Dissipée hydraulique (J)",
    "e_fric": "Énergie.Dissipée friction joint (J)",
    "e_fribag": "Énergie.Dissipée friction bagues (J)",
    "e_damp_x": "Énergie.Dissipée amortisseur horizontal (J)",
    "e_slip": "Énergie.Dissipée glissement pneu (J)",
    "e_endstop": "Énergie.Emmagasinée butée (J)",
    "e_input": "Énergie.Apport total (J)",
    "e_residual": "Énergie.Résidu de bilan (J)",
}


# Positions géométriques enregistrées pour l'animation (repère sol, en m). Points
# caractéristiques de la jambe droite : attache B, bagues haute Gt / basse Gb,
# centre roue R. ground_z = niveau du sol ; wheel_radius = rayon « effectif » de la
# roue (= R_z − ground_z), qui se comprime visuellement avec la déflexion pneu.
GEOMETRY_KEYS_SS: tuple[str, ...] = (
    "bx", "bz", "gtx", "gtz", "gbx", "gbz", "rx", "rz", "ground_z", "wheel_radius",
)
# Points d'ancrage drag brace (§5b), ajoutés seulement si la config en comporte.
GEOMETRY_KEYS_SS_DB: tuple[str, ...] = (
    "b1x", "b1z", "b2x", "b2z", "cdbx", "cdbz", "ddbx", "ddbz",
)


@dataclass
class StraitStrutLocalState:
    """État local réutilisable du train StraitStrut sur un pas global."""

    ptR_lg: np.ndarray
    ptGt_lg: np.ndarray
    ptGb_lg: np.ndarray
    ptB_lg: np.ndarray
    z_ms: float
    vz_ms: float
    z_mns_lg: float
    vz_mns_lg: float
    d: float
    v_damper: float
    delta_pc: float
    delta_pd: float
    pg_prev: float
    ftot: float
    tyre_omega: float
    tyre_vx: float
    tyre_depx: float
    tyre_defl_val: float


def _bushing_reaction_vectors(tr_lg, ptR_lg, ptGt_lg, ptGb_lg):
    """Réactions de bague SIGNÉES sur la TIGE (repère jambe, ⊥ à l'axe ; composante
    axiale nulle). Voir :func:`_bushing_loads` pour le modèle (équilibre 2D de la
    tige avec décalage de R relatif à l'axe Gt-Gb)."""
    Rx = float(ptR_lg[0]) - float(ptGb_lg[0])
    Ry = float(ptR_lg[1]) - float(ptGb_lg[1])
    z_r, z_gt, z_gb = float(ptR_lg[2]), float(ptGt_lg[2]), float(ptGb_lg[2])
    fx, fy, fz = float(tr_lg[0]), float(tr_lg[1]), float(tr_lg[2])
    h = z_gt - z_gb
    if abs(h) < 1.0e-9:
        return np.zeros(3), np.zeros(3)
    m_x = Ry * fz - (z_r - z_gb) * fy
    m_y = (z_r - z_gb) * fx - Rx * fz
    gty = m_x / h
    gtx = -m_y / h
    gbx = -fx - gtx
    gby = -fy - gty
    return np.array([gtx, gty, 0.0]), np.array([gbx, gby, 0.0])


def _bushing_loads(tr_lg, ptR_lg, ptGt_lg, ptGb_lg) -> tuple[float, float]:
    """Charges normales (magnitudes) aux bagues Gt (sur tige) et Gb (sur fût) qui
    équilibrent la tige sous l'effort de contact ``tr_lg`` (repère jambe).

    Généralisation 2D du cas colinéaire : l'axe de coulisse est porté par Gt-Gb.
    Le centre roue R peut être DÉCALÉ de cet axe : son offset perpendiculaire est
    pris RELATIVEMENT à l'axe (``ptR - ptGb``), car la cinématique translate tous
    les points ensemble (l'axe se déplace, l'offset relatif reste constant).
    L'effort de contact crée alors un moment sur la tige via (i) ses composantes
    latérales et (ii) l'effort AXIAL agissant au bras de levier du décalage. On
    résout la flexion dans les deux plans (jambe-x, jambe-y) indépendamment ; pour
    R sur l'axe et effort purement jambe-x on retrouve exactement la formule
    historique.
    """
    gt, gb = _bushing_reaction_vectors(tr_lg, ptR_lg, ptGt_lg, ptGb_lg)
    return math.hypot(gt[0], gt[1]), math.hypot(gb[0], gb[1])


def _drag_brace_reactions(R_int, M_int_B1, B1, B2, C, D):
    """Équilibre 3D du corps (sans masse) ancré par **rotule B1** + **linéaire
    annulaire B2** (axe B1-B2) + **drag brace** (bielle C-D). Variante §5b du PFD.

    ``R_int`` / ``M_int_B1`` : torseur des actions INTERNES (oléo + bagues) de la
    tige sur le corps, réduit en B1. ``B1, B2, C, D`` : positions. Tous les vecteurs
    et points sont exprimés dans le **même repère**.

    Résout (4')(6') : R_B1 + R_B2 + T·û_CD = −R_int ; et le moment en B1.
    Retourne (T, R_B1, R_B2) = efforts **structure→corps** (T = traction de la
    bielle si > 0). ``None`` si géométrie dégénérée.
    """
    u_B = np.asarray(B1, float) - np.asarray(B2, float)
    u_CD = np.asarray(D, float) - np.asarray(C, float)
    nB, nCD = float(np.linalg.norm(u_B)), float(np.linalg.norm(u_CD))
    if nB < 1.0e-9 or nCD < 1.0e-9:
        return None
    u_B /= nB
    u_CD /= nCD
    # Base orthonormale ⊥ û_B (pour R_B2, sans composante axiale annulaire).
    tmp = np.array([1.0, 0.0, 0.0]) if abs(u_B[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = np.cross(u_B, tmp)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(u_B, e1)
    # Inconnues x = [X1, Y1, Z1, a2, b2, T] ; R_B2 = a2·e1 + b2·e2.
    A = np.zeros((6, 6))
    rhs = np.zeros(6)
    A[0:3, 0:3] = np.eye(3)
    A[0:3, 3] = e1
    A[0:3, 4] = e2
    A[0:3, 5] = u_CD
    rhs[0:3] = -np.asarray(R_int, float)
    rBB2 = np.asarray(B2, float) - np.asarray(B1, float)
    rBC = np.asarray(C, float) - np.asarray(B1, float)
    A[3:6, 3] = np.cross(rBB2, e1)
    A[3:6, 4] = np.cross(rBB2, e2)
    A[3:6, 5] = np.cross(rBC, u_CD)
    rhs[3:6] = -np.asarray(M_int_B1, float)
    x = np.linalg.solve(A, rhs)
    return float(x[5]), x[0:3], x[3] * e1 + x[4] * e2


def _drag_brace_step(course_m, state, F_tot, tr_lg, db):
    """Efforts d'ancrage drag brace au pas courant (repère jambe). ``db`` = dict des
    positions jambe (m) relatives à Gb : B1, B2, C, D. Réutilise le torseur interne
    (oléo + bagues) sur le corps. Retourne (T, R_B1, R_B2) ou None."""
    gt_vec, gb_vec = _bushing_reaction_vectors(tr_lg, state.ptR_lg, state.ptGt_lg, state.ptGb_lg)
    z_lg = np.array([0.0, 0.0, 1.0])
    Gt_rel = state.ptGt_lg - state.ptGb_lg          # Gb_rel = 0 (origine en Gb)
    A_rel = Gt_rel + course_m * z_lg                # oléo : A = Gt + course·ẑ
    R_int = F_tot * z_lg - gt_vec - gb_vec          # action interne (rod→corps)
    B1 = db["B1"]
    M_int = (np.cross(A_rel - B1, F_tot * z_lg)
             + np.cross(Gt_rel - B1, -gt_vec)
             + np.cross(-B1, -gb_vec))
    res = _drag_brace_reactions(R_int, M_int, B1, db["B2"], db["C"], db["D"])
    if res is None:
        return None
    T, R_B1, R_B2 = res
    # Effort de la bielle au point de fixation structure D : −T·û_CD (réaction sur
    # la structure ; même repère que R_B1/R_B2).
    u_CD = np.asarray(db["D"], float) - np.asarray(db["C"], float)
    n = float(np.linalg.norm(u_CD))
    F_brace = (-T / n) * u_CD if n > 1.0e-9 else np.zeros(3)
    return T, R_B1, R_B2, F_brace


def _init_strait_strut_local_state(
    p: TrailingArmParamsSI,
    gas: GasSpring,
    R_sol_to_lg: np.ndarray,
    R_lg_to_sol: np.ndarray,
    *,
    h_pivot_z_m: float,
    h_guide_top_z_m: float,
    h_guide_bot_z_m: float,
    r_offset_m: tuple[float, float] = (0.0, 0.0),
    b_offset_m: tuple[float, float] = (0.0, 0.0),
) -> StraitStrutLocalState:
    """Construit l'état local initial réutilisable du modèle StraitStrut.

    ``r_offset_m`` / ``b_offset_m`` : décalages perpendiculaires (jambe-x, jambe-y)
    du centre roue R et du pivot B par rapport à l'axe de coulisse (Gt-Gb). Nuls
    par défaut (modèle colinéaire historique).
    """
    unload_r = p.unload_radius
    ptR_lg = np.array([r_offset_m[0], r_offset_m[1], unload_r])
    ptGt_lg = np.array([0.0, 0.0, unload_r + h_guide_top_z_m])
    ptGb_lg = np.array([0.0, 0.0, unload_r + h_guide_bot_z_m])
    ptB_lg = np.array([b_offset_m[0], b_offset_m[1], unload_r + h_pivot_z_m])

    k_endstop = 1.0e8
    pg_init = gas.pressure(0.0, p.Pinitbp)
    d0 = -pg_init * p.St / k_endstop
    ptB_lg[2] -= d0
    ptGb_lg[2] -= d0

    ptR_sol = R_lg_to_sol @ ptR_lg
    vz_ms = -p.vz
    v_ms_sol = np.array([0.0, 0.0, vz_ms])
    v_ms_lg = R_sol_to_lg @ v_ms_sol
    vz_mns_lg = float(v_ms_lg[2])
    tyre_defl_val = max(0.0, unload_r - float(ptR_sol[2]))

    return StraitStrutLocalState(
        ptR_lg=ptR_lg,
        ptGt_lg=ptGt_lg,
        ptGb_lg=ptGb_lg,
        ptB_lg=ptB_lg,
        z_ms=0.0,
        vz_ms=vz_ms,
        z_mns_lg=0.0,
        vz_mns_lg=vz_mns_lg,
        d=float(d0),
        v_damper=0.0,
        delta_pc=0.0,
        delta_pd=0.0,
        pg_prev=pg_init,
        ftot=p.St * pg_init + _endstop(float(d0), p.course, smooth_len=p.endstop_smooth),
        tyre_omega=0.0,
        tyre_vx=0.0,
        tyre_depx=0.0,
        tyre_defl_val=tyre_defl_val,
    )


def _strait_strut_resolve_damper_step(
    p: TrailingArmParamsSI,
    gas: GasSpring,
    tab_pos: np.ndarray,
    tab_sec: np.ndarray,
    state: StraitStrutLocalState,
) -> dict[str, float]:
    """Résout le noyau gaz/hydraulique local à partir de l'état courant."""
    solver_mode = _select_damper_core_solver(
        p,
        state.d,
        state.v_damper,
        state.pg_prev,
        state.ftot,
    )
    non_implicit_dt_scale = (
        1.10
        if p.damper_core_solver == "auto_fast" and solver_mode != "implicit_adaptive"
        else 1.0
    )
    if solver_mode == "implicit_adaptive":
        min_h = 1.0 / 32.0 if p.damper_core_solver == "auto_fast" else 1.0 / 128.0
        return damper_force_step_implicit_adaptive(
            p,
            gas,
            tab_pos,
            tab_sec,
            state.d,
            state.v_damper,
            state.d,
            state.v_damper,
            state.delta_pc,
            state.delta_pd,
            state.pg_prev,
            min_h=min_h,
            auto_fast_mode=(p.damper_core_solver == "auto_fast"),
            implicit_dt_scale=2.0 if p.damper_core_solver == "auto_fast" else 1.0,
        )
    return damper_force_step(
        p,
        gas,
        tab_pos,
        tab_sec,
        state.d,
        state.v_damper,
        state.delta_pc,
        state.delta_pd,
        state.pg_prev,
        dt=p.it * non_implicit_dt_scale,
    )


def _strait_strut_advance_local_state(
    p: TrailingArmParamsSI,
    state: StraitStrutLocalState,
    R_sol_to_lg: np.ndarray,
    R_lg_to_sol: np.ndarray,
    *,
    support_acc_ms_z: float,
    ftot: float,
    tyre_ftyre_i: float,
    dt: float,
    method: str,
    contact_axial: float | None = None,
) -> StraitStrutLocalState:
    """Avance l'état local StraitStrut d'un pas sous cinématique support imposée.

    ``contact_axial`` : composante de l'effort de contact projetée sur l'axe de
    coulisse (= tr_lg[2]). Si None, on utilise l'effort pneu vertical (legacy,
    exact pour une jambe verticale).
    """
    poids_ms = p.masse * G * (1.0 - p.lift)
    mns = p.unsprung_mass
    # Gravité du rod PROJETÉE sur l'axe de coulisse (composante z repère jambe du
    # poids vertical) — exacte pour une jambe inclinée (cf. audit énergétique).
    poids_mns_lg_z = float((R_sol_to_lg @ np.array([0.0, 0.0, mns * G]))[2])

    z_ms, vz_ms = _integrate_const_acc(state.z_ms, state.vz_ms, support_acc_ms_z, dt, method)
    v_ms_sol_vec = np.array([0.0, 0.0, vz_ms])
    v_ms_lg_vec = R_sol_to_lg @ v_ms_sol_vec
    vz_ms_lg = float(v_ms_lg_vec[2])

    # Effort de contact projeté sur l'axe de coulisse (composante axiale). À défaut
    # (appel legacy), on retombe sur l'effort pneu vertical (jambe verticale).
    contact_axial = tyre_ftyre_i if contact_axial is None else contact_axial
    acc_mns_lg_z = (-ftot + contact_axial - poids_mns_lg_z) / mns
    z_mns_lg, vz_mns_lg = _integrate_const_acc(
        state.z_mns_lg,
        state.vz_mns_lg,
        acc_mns_lg_z,
        dt,
        method,
    )

    # Cinématique cohérente pour jambe inclinée : le cylindre (B, Gb) suit le
    # mouvement vertical COMPLET de Ms ; le rod (R, Gt) suit Ms + glisse le long de
    # l'axe. Le modèle historique ne prenait que la projection AXIALE du mouvement
    # de Ms (·cos²β côté sol) → mouvement latéral relatif parasite aux bagues →
    # travail latéral parasite (non-conservation d'énergie pour β ≠ 0).
    v_damper = -(vz_ms_lg - vz_mns_lg)
    d = state.d + v_damper * dt
    col_vert = R_sol_to_lg @ np.array([0.0, 0.0, 1.0])   # vertical sol exprimé en repère jambe
    ms_disp = (vz_ms * dt) * col_vert                    # déplacement de Ms (complet)
    slide = np.array([0.0, 0.0, v_damper * dt])          # glissement axial relatif du rod
    ptB_lg = state.ptB_lg + ms_disp
    ptGb_lg = state.ptGb_lg + ms_disp                    # bague basse : sur le fût (corps fixe)
    ptR_lg = state.ptR_lg + ms_disp + slide
    ptGt_lg = state.ptGt_lg + ms_disp + slide            # bague haute : sur la TIGE

    ptR_sol = R_lg_to_sol @ ptR_lg
    tyre_defl_val = max(0.0, p.unload_radius - float(ptR_sol[2]))

    r_eff_val = r_eff(p.unload_radius, state.tyre_defl_val)
    slip = 0.0
    if abs(p.vx) > 1.0e-9:
        slip = (p.vx - state.tyre_omega * r_eff_val) / abs(p.vx)
    mu_val = mu(slip, p.mu_x, p.mu_y)
    fspin = mu_val * tyre_ftyre_i * math.copysign(1.0, slip) if tyre_ftyre_i > 0 else 0.0
    tyre_alpha_i = (fspin * r_eff_val) / p.wheel_inertia if tyre_ftyre_i > 0 else 0.0
    fx_spring_wheel = -p.kx * state.tyre_depx - p.cx * state.tyre_vx
    acc_tyre_x = (fx_spring_wheel + fspin) / p.wheelmass

    tyre_omega = state.tyre_omega + tyre_alpha_i * dt
    tyre_vx = state.tyre_vx + acc_tyre_x * dt
    tyre_depx = state.tyre_depx + state.tyre_vx * dt

    return StraitStrutLocalState(
        ptR_lg=ptR_lg,
        ptGt_lg=ptGt_lg,
        ptGb_lg=ptGb_lg,
        ptB_lg=ptB_lg,
        z_ms=z_ms,
        vz_ms=vz_ms,
        z_mns_lg=z_mns_lg,
        vz_mns_lg=vz_mns_lg,
        d=d,
        v_damper=v_damper,
        delta_pc=state.delta_pc,
        delta_pd=state.delta_pd,
        pg_prev=state.pg_prev,
        ftot=ftot,
        tyre_omega=tyre_omega,
        tyre_vx=tyre_vx,
        tyre_depx=tyre_depx,
        tyre_defl_val=tyre_defl_val,
    )


# --------------------------------------------------------------------------- #
#  Transformation de repère sol ↔ jambe (reproduction exacte du VBA cRot)
# --------------------------------------------------------------------------- #

def _rot_sol_to_lg(alfap: float, alfar: float) -> np.ndarray:
    """Matrice de rotation sol → jambe (Rodrigues, identique à cRot.Pt_Rsol_Rlg).

    Première rotation : Ry(-alfap) autour de Y.
    Deuxième rotation : Rodrigues autour du nouvel axe X (= rot1 @ [1,0,0]) par -alfar.
    """
    c1, s1 = math.cos(-alfap), math.sin(-alfap)
    # rot1 = Ry(-alfap)
    rot1 = np.array([
        [c1,  0.0, s1],
        [0.0, 1.0, 0.0],
        [-s1, 0.0, c1],
    ])
    # Nouvel axe X après rot1
    u2 = rot1 @ np.array([1.0, 0.0, 0.0])
    # rot2 = Rodrigues autour de u2 par -alfar
    c2, s2 = math.cos(-alfar), math.sin(-alfar)
    ux, uy, uz = u2
    rot2 = np.array([
        [ux*ux*(1-c2)+c2,       ux*uy*(1-c2)-uz*s2,  ux*uz*(1-c2)+uy*s2],
        [uy*ux*(1-c2)+uz*s2,    uy*uy*(1-c2)+c2,      uy*uz*(1-c2)-ux*s2],
        [uz*ux*(1-c2)-uy*s2,    uz*uy*(1-c2)+ux*s2,   uz*uz*(1-c2)+c2   ],
    ])
    return rot2 @ rot1


def _rot_lg_to_sol(alfap: float, alfar: float) -> np.ndarray:
    """Matrice de rotation jambe → sol (= R_sol_to_lg.T car R est orthogonale)."""
    return _rot_sol_to_lg(alfap, alfar).T


# --------------------------------------------------------------------------- #
#  Friction de joint spécifique NLG (ClNLG.FFriJoi, formule avec pré-compression)
# --------------------------------------------------------------------------- #

def _ffrijoi_nlg(
    v: float,
    pd_pa: float,
    p: TrailingArmParamsSI,
    seal_precomp_pa: float,
) -> float:
    """Friction du joint (formule VBA ClNLG.FFriJoi).

    Différence avec le TrailingArm : terme de pré-compression du joint ``seal_precomp_pa``
    en plus du terme de pression de détente ``fh * Pd``.

    ``seal_precomp_pa`` ≈ 110 649 Pa (VBA hardcodé, exposé comme paramètre).
    """
    if v == 0.0:
        return 0.0
    coeff = 1.0 / math.sqrt(0.95 + 0.28 * math.sqrt(1.0 / (90.0 * abs(v))))
    s_seal = math.pi / 4.0 * (p.ASeal ** 2 - p.Dt ** 2)
    # Formule VBA : (fh*Pd + seal_precomp) * S_seal + 2 * fc * Dt * pi
    return _sign(v) * coeff * (
        (p.fh * pd_pa + seal_precomp_pa) * s_seal
        + 2.0 * p.fc * p.Dt * math.pi
    )


# --------------------------------------------------------------------------- #
#  Friction des bagues de guidage — modèle DP4 (exp/log)
# --------------------------------------------------------------------------- #
# Coefficient de friction de bague μ(p, v), calé sur les bagues GGB DP4 (métal-
# polymère auto-lubrifiantes, fonctionnement LUBRIFIÉ). Forme retenue d'après la
# littérature tribologique (cf. docs/Dossier_de_calcul_complet.md, §friction de
# bague) :
#   - dépendance en PRESSION : décroissance exponentielle (μ baisse quand la
#     pression de contact augmente — film de transfert, aire réelle sous-linéaire),
#     plus défendable que la droite VBA hors du domaine ~<21 MPa ;
#   - dépendance en VITESSE : montée asymptotique (saturante) type
#     Constantinou/Mokha, μ croît avec |v| puis sature.
# Coefficients DP4 (μ_p0, μ_p∞, p_ref [MPa], μ_v,min, μ_v,max, α [s/m]). Valeurs
# par défaut calées sur GGB DP4 lubrifié — désormais exposées comme paramètres de
# configuration StraitStrut (saisie) et transportés via ``StraitStrutGeomSI``.
class BagFrictionDP4(NamedTuple):
    mu_p0: float = 0.12     # μ à pression de contact nulle (-)
    mu_pinf: float = 0.04   # μ asymptotique à haute pression (-)
    p_ref: float = 20.0     # pression caractéristique de décroissance (MPa)
    mu_vmin: float = 0.05   # μ à vitesse nulle (-)
    mu_vmax: float = 0.12   # μ asymptotique à haute vitesse (-)
    alpha: float = 16.0     # raideur de la montée en vitesse (s/m)


DEFAULT_BAG_FRICTION_DP4 = BagFrictionDP4()


def _mu_bague_dp4(p_contact_mpa: float, v_abs: float,
                  c: BagFrictionDP4 = DEFAULT_BAG_FRICTION_DP4) -> float:
    """Coefficient de friction de bague DP4 : μ = ½[μ_p(p) + μ_v(v)].

    ``p_contact_mpa`` : pression de contact à la bague (MPa) ; ``v_abs`` : |vitesse
    amortisseur| (m/s) ; ``c`` : coefficients DP4. Décroissance exponentielle en
    pression + montée asymptotique en vitesse."""
    mu_p = c.mu_pinf + (c.mu_p0 - c.mu_pinf) * math.exp(-p_contact_mpa / max(c.p_ref, 1.0e-9))
    mu_v = c.mu_vmin + (c.mu_vmax - c.mu_vmin) * (1.0 - math.exp(-c.alpha * v_abs))
    return 0.5 * (mu_p + mu_v)


def _ffribag_nlg(
    v: float,
    xgt: float,
    xgb: float,
    Dt: float,
    Dpis: float,
    bague_guide_m: float,
    bague_piston_m: float,
    bag_coeffs: BagFrictionDP4 = DEFAULT_BAG_FRICTION_DP4,
) -> float:
    """Friction des bagues de guidage NLG — **modèle DP4 (exp/log)**.

    Remplace la formule linéaire VBA d'origine (``ClNLG.FFriBag``) par un modèle
    μ(p, v) calé sur les bagues GGB DP4 lubrifiées (cf. ``_mu_bague_dp4``). La
    structure d'assemblage est conservée :
    - pressions de contact : bague guide sur la **tige** (``Dt``), bague piston sur
      le **piston** (``Dpis``) ;
    - appariement effort : ``μ_guide·|XGb| + μ_piston·|XGt|`` ;
    - facteur d'atténuation statique→dynamique ``coeff`` (régularise v→0).

    ``bague_guide_m``, ``bague_piston_m`` : longueurs des bagues en mètres.
    ``xgt``, ``xgb`` : efforts transverses aux bagues haute et basse (N).
    ``bag_coeffs`` : coefficients DP4 (saisis dans la config StraitStrut)."""
    if v == 0.0:
        return 0.0
    coeff = 1.0 / math.sqrt(0.95 + 0.28 * math.sqrt(1.0 / (90.0 * abs(v))))
    eps = 1.0e-9  # évite la division par zéro
    p_contact_guide = abs(xgt) / max(Dt * bague_guide_m * 1.0e6, eps)       # MPa
    p_contact_piston = abs(xgb) / max(Dpis * bague_piston_m * 1.0e6, eps)   # MPa
    mu_guide = _mu_bague_dp4(p_contact_guide, abs(v), bag_coeffs)
    mu_piston = _mu_bague_dp4(p_contact_piston, abs(v), bag_coeffs)
    return _sign(v) * (mu_guide * abs(xgb) + mu_piston * abs(xgt)) * coeff


# --------------------------------------------------------------------------- #
#  Moteur principal StraitStrut
# --------------------------------------------------------------------------- #

def run_strait_strut(
    p: TrailingArmParamsSI,
    collector: ErrorCollector | None = None,
    progress_callback: callable | None = None,
    *,
    seal_precomp_pa: float = 110_649.0,
    bague_guide_m: float = 0.05,
    bague_piston_m: float = 0.05,
    bag_friction: BagFrictionDP4 = DEFAULT_BAG_FRICTION_DP4,
    alfap: float = 0.0,
    alfar: float = 0.0,
    h_pivot_z_m: float = 0.60,
    h_guide_top_z_m: float = 0.50,
    h_guide_bot_z_m: float = 0.20,
    r_offset_m: tuple[float, float] = (0.0, 0.0),
    b_offset_m: tuple[float, float] = (0.0, 0.0),
    drag_brace: dict | None = None,
) -> EngineOutput:
    """Exécute la simulation de drop test NLG (StraitStrut / jambe de force directe).

    Paramètres spécifiques NLG (au-delà de ``TrailingArmParamsSI``) :
      alfap, alfar    : angles pitch/roll de la jambe (rad), total = structural + avion.
      h_pivot_z_m     : hauteur pivot B au-dessus du centre roue (m, repère jambe).
      h_guide_top_z_m : hauteur bague haute Gt au-dessus du centre roue (m).
      h_guide_bot_z_m : hauteur bague basse Gb au-dessus du centre roue (m).
      r_offset_m      : décalage perpendiculaire (jambe-x, jambe-y) du centre roue R.
      b_offset_m      : décalage perpendiculaire (jambe-x, jambe-y) du pivot B.
      bague_guide_m   : longueur bague de guidage (m).
      bague_piston_m  : longueur bague piston (m).
      seal_precomp_pa : pression de pré-compression du joint (Pa).
      bag_friction    : coefficients DP4 de friction de bague (BagFrictionDP4 ou tuple).
    """
    if not isinstance(bag_friction, BagFrictionDP4):
        bag_friction = BagFrictionDP4(*bag_friction)
    c = collector or ErrorCollector()

    # --- Préparation ------------------------------------------------------ #
    gas = GasSpring(p)
    tab_pos, tab_sec = build_section_table(p)
    tyre_defl_tbl, tyre_load_tbl = build_tyre_tables(p)
    mu_x, mu_y = p.mu_x, p.mu_y

    # Matrices de rotation (fixes sur toute la simulation)
    R_sol_to_lg = _rot_sol_to_lg(alfap, alfar)
    R_lg_to_sol = R_lg_to_sol_mat = R_sol_to_lg.T

    state = _init_strait_strut_local_state(
        p,
        gas,
        R_sol_to_lg,
        R_lg_to_sol,
        h_pivot_z_m=h_pivot_z_m,
        h_guide_top_z_m=h_guide_top_z_m,
        h_guide_bot_z_m=h_guide_bot_z_m,
        r_offset_m=r_offset_m,
        b_offset_m=b_offset_m,
    )

    # --- État initial ------------------------------------------------------ #
    dt = p.it
    n_steps = max(1, round(p.temps_simu / dt))
    method = p.integrator

    # Masse suspendue Ms (repère sol)
    poids_ms = p.masse * G * (1.0 - p.lift)  # N (poids effectif sol)

    mns = p.unsprung_mass           # masse non suspendue totale (kg)
    poids_mns_lg_z = float((R_sol_to_lg @ np.array([0.0, 0.0, mns * G]))[2])  # gravité rod projetée sur l'axe

    # Pneu / sol
    unload_r = p.unload_radius
    ptS_sol = np.zeros(3)

    # Effort amortisseur initial (TB_sl)
    tb_lg_z = 0.0  # effort jambe dans le repère jambe (Z), init 0
    tb_sol = R_lg_to_sol @ np.array([0.0, 0.0, tb_lg_z])

    # Énergies cumulées
    # Bilan énergétique en TRAVAIL — même démarche que engine.py/MLG
    # (cf. docs/Bilan_energetique.md) : travaux signés F·dd (télescopage), apport
    # d'avancement, ΔEc_rot exact. Réservoirs = ressorts + pièces en mouvement.
    e_kin_init = 0.5 * p.masse * state.vz_ms ** 2 + 0.5 * mns * state.vz_mns_lg ** 2
    e_gas_acc = 0.0
    e_tyre_acc = 0.0
    e_spring_x_acc = 0.0
    e_hyd_acc = 0.0
    e_fric_acc = 0.0
    e_fribag_acc = 0.0
    e_damp_x_acc = 0.0
    e_slip_acc = 0.0
    e_endstop_acc = 0.0
    e_fwd_acc = 0.0
    e_grav_acc = 0.0
    # Trackers du pas précédent (pour les travaux signés)
    d_prev = max(0.0, state.d)
    defl_prev = state.tyre_defl_val
    z_ms_prev = state.z_ms
    z_mns_prev = state.z_mns_lg
    omega_prev = state.tyre_omega

    # --- Tableaux de sortie ----------------------------------------------- #
    n_out = n_steps + 1
    out: dict[str, np.ndarray] = {k: np.zeros(n_out) for k in OUTPUT_COLUMNS_SS}
    geom_keys = GEOMETRY_KEYS_SS + (GEOMETRY_KEYS_SS_DB if drag_brace is not None else ())
    geom: dict[str, np.ndarray] = {k: np.zeros(n_out) for k in geom_keys}

    # --- Boucle d'intégration --------------------------------------------- #
    bottomed = None  # (i_fail, exc) si l'amortisseur atteint sa butée de compression
    for i in range(n_out):
        t = i * dt

        # --- Enregistrement de l'état au pas i ----------------------------- #
        try:
            damp_step = _strait_strut_resolve_damper_step(p, gas, tab_pos, tab_sec, state)
        except SimError as exc:
            if exc.code in OVERSTROKE_CODES:
                bottomed = (i, exc)
                break
            raise
        pg = damp_step["pg"]
        pc = damp_step["pc"]
        pd = damp_step["pd"]
        state.delta_pc = damp_step["delta_pc"]
        state.delta_pd = damp_step["delta_pd"]
        state.pg_prev = pg

        fgas = damp_step["fgas"]
        ffrijoi = _ffrijoi_nlg(state.v_damper, pd, p, seal_precomp_pa)
        fendstop = _endstop(state.d, p.course, smooth_len=p.endstop_smooth)

        # Effort pneu vertical
        tyre_ftyre_i = max(0.0, f_tyre(state.tyre_defl_val, tyre_defl_tbl, tyre_load_tbl))
        # Force ressort/amortisseur horizontal APPLIQUEE A LA ROUE (repère sol).
        # La convention interne historique du moteur utilise ce signe pour les
        # projections repère sol ↔ repère jambe. En revanche, les sorties
        # utilisateur ``tr_x`` / ``reaction_h`` suivent la convention Excel et
        # TrailingArm : réaction transmise à la structure, donc signe opposé.
        fx_spring_wheel = -p.kx * state.tyre_depx - p.cx * state.tyre_vx
        tr_x = -fx_spring_wheel
        # Torseur utilisé par la dynamique interne (convention historique).
        tr_sol = np.array([fx_spring_wheel, 0.0, tyre_ftyre_i])
        # Conversion en repère jambe pour les efforts de guidage
        tr_lg = R_sol_to_lg @ tr_sol

        # Réactions aux bagues de guidage (équilibre 2D de la tige, décalage R inclus)
        xgt, xgb = _bushing_loads(tr_lg, state.ptR_lg, state.ptGt_lg, state.ptGb_lg)

        ffribag = _ffribag_nlg(state.v_damper, xgt, xgb, p.Dt, p.Dpis,
                               bague_guide_m, bague_piston_m, bag_friction)

        ftot = p.Sc * pc - p.Sd * pd + p.Sbh * pg + ffrijoi + ffribag + fendstop
        state.ftot = ftot
        fhyd = damp_step["fhyd"]

        # Effort de jambe en repère sol (pour la dynamique Ms)
        tb_lg = np.array([tr_lg[0], 0.0, ftot])
        tb_sol_cur = R_lg_to_sol @ tb_lg

        # Pneu : slip, mu, spin-up, spring-back
        r_eff_val = r_eff(p.unload_radius, state.tyre_defl_val)
        slip = 0.0
        if abs(p.vx) > 1.0e-9:
            slip = (p.vx - state.tyre_omega * r_eff_val) / abs(p.vx)
        mu_val = mu(slip, mu_x, mu_y)
        fspin = mu_val * tyre_ftyre_i * math.copysign(1.0, slip) if tyre_ftyre_i > 0 else 0.0
        tyre_alpha_i = (fspin * r_eff_val) / p.wheel_inertia if tyre_ftyre_i > 0 else 0.0
        # Spring-back : force de rappel horizontal (sol) -> accélération roue
        acc_tyre_x = (fx_spring_wheel + fspin) / p.wheelmass

        # Torseur à l'attache fuselage B
        # Signe horizontal corrigé : l'effort transmis à la cellule suit la même
        # convention que ``reaction_h`` et que le TrailingArm (MLG), cf. PFD
        # (docs/PFD_trains.md §5.3). Le code historique reportait +tb_sol_cur[0].
        tb_res_x = -float(tb_sol_cur[0])
        tb_res_y = float(tb_sol_cur[1])
        tb_res_z = float(tb_sol_cur[2])
        tb_norm = math.sqrt(tb_res_x**2 + tb_res_y**2 + tb_res_z**2)
        # Moment en B = (ptR_sol - ptB_sol) × TR_sol (moment de la réaction sol)
        ptB_sol = R_lg_to_sol @ state.ptB_lg
        ptR_sol_cur = R_lg_to_sol @ state.ptR_lg
        r_b = ptR_sol_cur - ptB_sol
        mom_B = np.cross(r_b, tr_sol)

        # Bilan énergétique en TRAVAIL (doc Bilan_energetique.md §3)
        e_kin_new = 0.5 * p.masse * state.vz_ms ** 2
        # Cinétique du rod : vitesse ABSOLUE = mouvement vertical de Ms + glissement
        # axial (|v|² = vz_ms² + v_damper² + 2·vz_ms·v_damper·cosβ), pas seulement
        # la composante axiale vz_mns_lg (sinon sous-compte de ½m·vz_ms²·sin²β).
        _cosb = float(R_lg_to_sol[2, 2])
        e_kin_mns_new = 0.5 * mns * (state.vz_ms ** 2 + state.v_damper ** 2
                                     + 2.0 * state.vz_ms * state.v_damper * _cosb)
        e_kin_spin_new = 0.5 * p.wheel_inertia * state.tyre_omega ** 2
        e_kin_horiz_new = 0.5 * p.wheelmass * state.tyre_vx ** 2
        e_spring_x_acc = 0.5 * p.kx * state.tyre_depx ** 2          # stocké (ressort horizontal)
        d_cur = max(0.0, state.d)
        dd = d_cur - d_prev                                         # variation de course
        ddefl = state.tyre_defl_val - defl_prev
        # Travaux signés : Ftot = Fgas + Fhyd + Ffrijoi + Ffribag + Fbutée → télescopage exact
        e_gas_acc += fgas * dd
        e_endstop_acc += fendstop * dd
        e_tyre_acc += tyre_ftyre_i * ddefl
        e_hyd_acc += fhyd * dd
        e_fric_acc += ffrijoi * dd
        e_fribag_acc += ffribag * dd
        e_damp_x_acc += p.cx * state.tyre_vx ** 2 * dt
        # Spin-up : apport d'avancement + glissement avec ΔEc_rot EXACT
        # (R sur la tige ne se déplace pas horizontalement → pas de couplage hub).
        dke_spin = 0.5 * p.wheel_inertia * (state.tyre_omega ** 2 - omega_prev ** 2)
        if abs(p.vx) > 1.0e-9:
            e_fwd_acc += fspin * p.vx * dt
            e_slip_acc += fspin * (p.vx - state.tyre_vx) * dt - dke_spin
        # Couplage moyeu (jambe inclinée) : R se déplace horizontalement avec le
        # glissement axial (vR_x = v_damper·û_x). La réaction horizontale tr_x y
        # travaille → travail à reverser dans le bilan (cf. engine.py MLG, terme
        # tr_x·vR_x). Nul pour jambe verticale (û_x = 0).
        e_slip_acc += tr_x * state.v_damper * float(R_lg_to_sol[0, 2]) * dt
        # Travail de la pesanteur. Ms : déplacement vertical sol. Rod : déplacement
        # vertical ABSOLU = Δz_ms (suit le cylindre) + Δd·cosβ (glissement axial
        # projeté), et non le déplacement axial seul (qui sous-compterait de
        # mns·g·vz_ms·sin²β·dt pour β ≠ 0).
        rod_vert_disp = (state.z_ms - z_ms_prev) + _cosb * dd
        e_grav_acc += (-poids_ms * (state.z_ms - z_ms_prev)
                       - mns * G * rod_vert_disp)
        d_prev = d_cur
        defl_prev = state.tyre_defl_val
        z_ms_prev = state.z_ms
        z_mns_prev = state.z_mns_lg
        omega_prev = state.tyre_omega

        e_input_total = e_kin_init + e_grav_acc + e_fwd_acc
        e_residual = e_input_total - (
            e_kin_new + e_kin_mns_new + e_kin_spin_new + e_kin_horiz_new
            + e_gas_acc + e_tyre_acc + e_spring_x_acc + e_endstop_acc
            + e_hyd_acc + e_fric_acc + e_fribag_acc + e_damp_x_acc + e_slip_acc
        )

        # Enregistrement
        out["temps"][i] = t
        out["accms"][i] = float(tb_sol_cur[2] - poids_ms) / p.masse
        out["vitms"][i] = state.vz_ms
        out["depms"][i] = state.z_ms
        out["accmns"][i] = (-ftot + float(tr_lg[2]) - poids_mns_lg_z) / mns
        out["vitmns"][i] = state.vz_mns_lg
        out["depmns"][i] = state.z_mns_lg
        out["trailing_arm_v"][i] = state.v_damper
        out["trailing_arm_d"][i] = max(0.0, state.d)
        out["trailing_arm_ftot"][i] = ftot
        out["trailing_arm_fhyd"][i] = fhyd
        out["trailing_arm_ffrijoi"][i] = ffrijoi
        out["trailing_arm_ffribag"][i] = ffribag
        out["trailing_arm_fgas"][i] = fgas
        out["pg"][i] = pg / 1.0e5          # Pa → bar
        out["pc"][i] = pc / 1.0e5
        out["pd"][i] = pd / 1.0e5
        out["delta_pc"][i] = state.delta_pc / 1.0e5
        out["delta_pd"][i] = state.delta_pd / 1.0e5
        out["secbh"][i] = damp_step["sec"] * 1.0e6  # m² → mm²
        out["hyd_conv_err"][i] = damp_step["hyd_conv_err"]
        out["hyd_conv_iter"][i] = damp_step["hyd_conv_iter"]
        out["hyd_qc_total"][i] = damp_step["qc_total"]
        out["hyd_qc_bh"][i] = damp_step["qc_bh"]
        out["hyd_qc_leak"][i] = damp_step["qc_leak"]
        out["hyd_leak_ratio"][i] = damp_step["leak_ratio"]
        out["hyd_re_leak"][i] = damp_step["re_leak"]
        out["tyre_defl"][i] = state.tyre_defl_val
        out["tyre_ftyre"][i] = tyre_ftyre_i
        out["tyre_alpha"][i] = tyre_alpha_i
        out["tyre_omega"][i] = state.tyre_omega
        out["tyre_mu"][i] = mu_val
        out["tyre_slip"][i] = slip
        out["tr_x"][i] = tr_x
        out["reaction_v"][i] = tyre_ftyre_i
        out["reaction_h"][i] = tr_x
        out["xgt"][i] = xgt
        out["xgb"][i] = xgb
        # Pressions de contact aux bagues (MPa), mêmes définitions que la friction.
        _pcg = abs(xgt) / max(p.Dt * bague_guide_m * 1.0e6, 1.0e-9)
        _pcp = abs(xgb) / max(p.Dpis * bague_piston_m * 1.0e6, 1.0e-9)
        out["p_bag_guide"][i] = _pcg
        out["p_bag_piston"][i] = _pcp
        # Coefficient de friction DP4 effectivement appliqué à chaque bague.
        out["mu_bag_guide"][i] = _mu_bague_dp4(_pcg, abs(state.v_damper), bag_friction)
        out["mu_bag_piston"][i] = _mu_bague_dp4(_pcp, abs(state.v_damper), bag_friction)
        if drag_brace is not None:
            _db = _drag_brace_step(p.course, state, ftot, tr_lg, drag_brace)
            if _db is not None:
                _T, _RB1, _RB2, _FB = _db
                out["db_brace_T"][i] = _T
                out["db_b1_fx"][i] = _RB1[0]
                out["db_b1_fy"][i] = _RB1[1]
                out["db_b1_fz"][i] = _RB1[2]
                out["db_b2_fx"][i] = _RB2[0]
                out["db_b2_fy"][i] = _RB2[1]
                out["db_b2_fz"][i] = _RB2[2]
                out["db_brace_fx"][i] = _FB[0]
                out["db_brace_fy"][i] = _FB[1]
                out["db_brace_fz"][i] = _FB[2]
        out["tors_res_x"][i] = tb_res_x
        out["tors_res_y"][i] = tb_res_y
        out["tors_res_z"][i] = tb_res_z
        out["tors_res_norm"][i] = tb_norm
        out["torsB_fx"][i] = tb_res_x
        out["torsB_fy"][i] = tb_res_y
        out["torsB_fz"][i] = tb_res_z
        out["torsB_mx"][i] = float(mom_B[0])
        out["torsB_mz"][i] = float(mom_B[2])
        out["e_kin"][i] = e_kin_new
        out["e_kin_mns"][i] = e_kin_mns_new
        out["e_kin_spin"][i] = e_kin_spin_new
        out["e_kin_horiz"][i] = e_kin_horiz_new
        out["e_gas"][i] = e_gas_acc
        out["e_tyre"][i] = e_tyre_acc
        out["e_spring_x"][i] = e_spring_x_acc
        out["e_hyd"][i] = e_hyd_acc
        out["e_fric"][i] = e_fric_acc
        out["e_fribag"][i] = e_fribag_acc
        out["e_damp_x"][i] = e_damp_x_acc
        out["e_slip"][i] = e_slip_acc
        out["e_endstop"][i] = e_endstop_acc
        out["e_input"][i] = e_input_total
        out["e_residual"][i] = e_residual

        # Positions géométriques (m, repère sol) pour l'animation. Mêmes points et
        # mêmes transformations que le moteur avion (cf. StraitStrutSlot).
        b_sol = R_lg_to_sol @ state.ptB_lg
        gt_sol = R_lg_to_sol @ state.ptGt_lg
        gb_sol = R_lg_to_sol @ state.ptGb_lg
        r_sol = R_lg_to_sol @ state.ptR_lg
        geom["bx"][i] = b_sol[0]; geom["bz"][i] = b_sol[2]
        geom["gtx"][i] = gt_sol[0]; geom["gtz"][i] = gt_sol[2]
        geom["gbx"][i] = gb_sol[0]; geom["gbz"][i] = gb_sol[2]
        geom["rx"][i] = r_sol[0]; geom["rz"][i] = r_sol[2]
        geom["ground_z"][i] = 0.0  # sol fixe à z=0 (contact initial roue à unload_radius)
        geom["wheel_radius"][i] = float(p.unload_radius)  # rayon constant (cf. moteur avion)
        if drag_brace is not None:
            # Points solidaires du corps, placés rigidement par rapport à Gb.
            for key, rel in (("b1", drag_brace["B1"]), ("b2", drag_brace["B2"]),
                             ("cdb", drag_brace["C"]), ("ddb", drag_brace["D"])):
                disp = R_lg_to_sol @ np.asarray(rel, dtype=float)
                geom[key + "x"][i] = gb_sol[0] + float(disp[0])
                geom[key + "z"][i] = gb_sol[2] + float(disp[2])

        if progress_callback is not None and (i % 10 == 0 or i == n_steps):
            progress_callback(i, n_steps)

        if i == n_steps:
            break

        # --- Intégration du pas i→i+1 ------------------------------------- #
        # 1. Dynamique masse suspendue Ms (repère sol)
        acc_ms_z = (float(tb_sol_cur[2]) - poids_ms) / p.masse
        state = _strait_strut_advance_local_state(
            p,
            state,
            R_sol_to_lg,
            R_lg_to_sol,
            support_acc_ms_z=acc_ms_z,
            ftot=ftot,
            tyre_ftyre_i=tyre_ftyre_i,
            dt=dt,
            method=method,
            contact_axial=float(tr_lg[2]),
        )

    warnings = list(c.warnings)
    if bottomed is not None:
        i_fail, exc = bottomed
        course = float(p.course)
        over = np.where(out["trailing_arm_d"][:i_fail] > course)[0]
        valid = int(over[0]) if over.size else i_fail
        if valid < 1:
            raise exc
        last_stroke = float(out["trailing_arm_d"][valid - 1])
        out = {k: v[:valid] for k, v in out.items()}
        geom = {k: v[:valid] for k, v in geom.items()}
        n_steps = valid - 1
        warnings.append(make_overstroke_warning("le train (StraitStrut)", valid * dt, last_stroke, course, exc))

    return EngineOutput(data=out, n_steps=n_steps, warnings=warnings, geometry=geom)
