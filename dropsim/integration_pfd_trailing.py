"""Moteur TrailingArm (MLG) reconstruit selon le PFD — torseur **3D**.

Le moteur historique ``engine.run_trailing_arm`` calcule déjà l'interface dans la
limite **balancier sans masse** (``fb = ta + tr``, ``fc = -ta``, plus les moments
``mb_x``/``mb_z``), qui est exactement l'assemblage PFD (doc §6, m_arm = 0). Ce
module réutilise donc le moteur historique pour tout le **constitutif + géométrie
+ rotation du balancier** (validés), et recalcule l'interface **strictement par le
PFD en 3D** (``integration_pfd.trailing_arm_interface``) :

- efforts **3D** F_B, F_C (composantes Fy non nulles si l'amortisseur est oblique) ;
- **moments Mx, Mz** au pivot (non nuls dès qu'il y a un décalage en Y, ex. roue
  déportée R_y ≠ B_y) ; My n'est pas transmis (rotation, eq (8)) ;
- option **masse du balancier** (+P' − m'·a_G', au-delà du code historique — H8).

Les coordonnées Y sont **constantes** pendant la simulation (rotation autour de
Y) ; on les reconstruit depuis la géométrie initiale (après attitude pitch/roll).
"""
from __future__ import annotations

import math

import numpy as np

from .engine import (
    TrailingArmLocalState,
    _endstop,
    _integrate_const_acc,
    _trailing_arm_local_step,
    run_trailing_arm,
)
from .errors import ErrorCollector, OVERSTROKE_CODES, SimError
from .gas import GasSpring
from .geometry import chgt_rep, deter_pos_bal_a, deter_pos_bal_r, rotate_about
from .inputs import TrailingArmParamsSI
from .integration_pfd import trailing_arm_interface
from .metering import build_section_table
from .tyre import build_tyre_tables
from .units import G


def _constant_y(p: TrailingArmParamsSI) -> dict[str, float]:
    """Y constants des points A, B, C, R après la mise en attitude initiale."""
    A = p.A.astype(float).copy()
    B = p.B.astype(float).copy()
    C = p.C.astype(float).copy()
    R = p.R.astype(float).copy()
    S = R.copy()
    S[2] = R[2] - p.unload_radius
    A = rotate_about(A, S, p.pitch, p.roll)
    B = rotate_about(B, S, p.pitch, p.roll)
    C = rotate_about(C, S, p.pitch, p.roll)
    R = rotate_about(R, S, p.pitch, p.roll)
    return {"A": float(A[1]), "B": float(B[1]), "C": float(C[1]), "R": float(R[1])}


def run_trailing_arm_pfd(
    p: TrailingArmParamsSI,
    *,
    m_arm: float = 0.0,
    collector: ErrorCollector | None = None,
) -> dict[str, np.ndarray]:
    """Drop test MLG, torseur d'interface 3D recalculé strictement par le PFD (§6).

    ``m_arm`` : masse balancier+roue. 0 ⇒ reproduit le moteur historique. > 0 ⇒
    ajoute le terme PFD d'inertie/poids (a_G' par différence finie de G' =
    milieu(B, R), de composante Y nulle car le mouvement est plan X-Z).
    """
    out = run_trailing_arm(p, collector=collector)
    d = out.data
    geom = out.geometry or {}
    y = _constant_y(p)

    n = len(d["trailing_arm_ftot"])
    t = np.asarray(d.get("temps", np.arange(n) * p.it), float)

    ax, az = np.asarray(geom["ax"], float), np.asarray(geom["az"], float)
    bx, bz = np.asarray(geom["bx"], float), np.asarray(geom["bz"], float)
    cx, cz = np.asarray(geom["cx"], float), np.asarray(geom["cz"], float)
    rx, rz = np.asarray(geom["rx"], float), np.asarray(geom["rz"], float)
    ftot = np.asarray(d["trailing_arm_ftot"], float)
    tr_x = np.asarray(d["tr_x"], float)
    tr_z = np.asarray(d["tyre_ftyre"], float)

    # Accélération 3D du CG balancier+roue G' = milieu(B, R) (Y constant ⇒ a_y = 0).
    gx, gz = 0.5 * (bx + rx), 0.5 * (bz + rz)
    if m_arm != 0.0 and n >= 3:
        a_gx = np.gradient(np.gradient(gx, t), t)
        a_gz = np.gradient(np.gradient(gz, t), t)
    else:
        a_gx = np.zeros(n)
        a_gz = np.zeros(n)

    keys = ["temps", "fb_x", "fb_y", "fb_z", "mb_x", "mb_z",
            "fc_x", "fc_y", "fc_z", "ftot"]
    res = {k: np.zeros(n) for k in keys}
    weight = np.array([0.0, 0.0, -m_arm * G])
    for i in range(n):
        iface = trailing_arm_interface(
            A=np.array([ax[i], y["A"], az[i]]),
            B=np.array([bx[i], y["B"], bz[i]]),
            C=np.array([cx[i], y["C"], cz[i]]),
            R=np.array([rx[i], y["R"], rz[i]]),
            f_tot=float(ftot[i]),
            contact_sol=np.array([tr_x[i], 0.0, tr_z[i]]),
            weight=weight,
            m_arm=m_arm,
            accel_G=np.array([a_gx[i], 0.0, a_gz[i]]),
        )
        res["temps"][i] = t[i]
        res["fb_x"][i], res["fb_y"][i], res["fb_z"][i] = iface.F_B
        res["fc_x"][i], res["fc_y"][i], res["fc_z"][i] = iface.F_C
        res["mb_x"][i], res["mb_z"][i] = iface.M_B[0], iface.M_B[2]
        res["ftot"][i] = ftot[i]
    return res


# ===========================================================================
#  Ré-intégration COUPLÉE — balancier corps rigide (masse active, doc §6.7)
# ===========================================================================
def run_trailing_arm_pfd_coupled(
    p: TrailingArmParamsSI,
    *,
    m_arm: float = 0.0,
) -> dict[str, np.ndarray]:
    """Drop test MLG ré-intégré avec le **balancier corps rigide** (doc §6.7).

    Réutilise le constitutif + la géométrie via ``_trailing_arm_local_step`` (avec
    override de l'accélération angulaire), mais pilote la dynamique par le modèle
    rigide : rotation (6b) avec I_B = jyy, G′ = milieu(B, R) ; effort pivot par
    (6a). ``m_arm = 0`` reproduit le moteur historique (validation).
    """
    gas = GasSpring(p)
    tab_pos, tab_sec = build_section_table(p)
    tyre_defl, tyre_load = build_tyre_tables(p)
    mu_x, mu_y = p.mu_x, p.mu_y

    B = p.B.astype(float).copy()
    A = p.A.astype(float).copy()
    C = p.C.astype(float).copy()
    R = p.R.astype(float).copy()
    entraxe_init = float(np.linalg.norm(C - A))
    lg_ab = math.hypot(B[0] - A[0], B[2] - A[2])
    lg_rb = math.hypot(B[0] - R[0], B[2] - R[2])
    lg_ra = math.hypot(A[0] - R[0], A[2] - R[2])

    S = R.copy()
    S[2] = R[2] - p.unload_radius
    A = rotate_about(A, S, p.pitch, p.roll)
    B = rotate_about(B, S, p.pitch, p.roll)
    C = rotate_about(C, S, p.pitch, p.roll)
    R = rotate_about(R, S, p.pitch, p.roll)
    S = R.copy()
    S[2] = R[2] - p.unload_radius
    pms_rlg_z = float(chgt_rep(np.array([0.0, 0.0, p.masse * G * (1.0 - p.lift)]), p.pitch, p.roll)[2])
    dy_ca = float(C[1] - A[1])

    Ms, Jyy = p.masse, p.jyy
    fast_time_scale = 1.8 if p.damper_core_solver == "auto_fast" else 1.0
    It = p.it * fast_time_scale
    integrator_mode = "euler" if p.damper_core_solver == "auto_fast" else p.integrator

    # Stabilisation statique (identique au moteur historique)
    pgtamp = p.Pinitbp
    d = 0.0
    for _ in range(100000):
        d -= 1.0e-8
        pg = gas.pressure(d, pgtamp)
        ftot0 = p.St * pg + _endstop(d, p.course, smooth_len=p.endstop_smooth)
        if abs(ftot0) < 1.0:
            break
    entraxe = entraxe_init - d
    deter_pos_bal_a(A, B, C, entraxe, lg_ab)
    deter_pos_bal_r(R, A, B, lg_ra, lg_rb)
    th_ry = math.atan((R[0] - B[0]) / (R[2] - B[2]))
    th_ay = math.atan((A[0] - B[0]) / (A[2] - B[2]))

    n_it = int(p.temps_simu / It)
    n_out = n_it + 1
    state = TrailingArmLocalState(
        A=A, B=B, C=C, R=R, S=S, accms=0.0, vitms=-p.vz, depms=0.0,
        ta_x=0.0, ta_y=0.0, ta_z=0.0, tb_x=0.0, tb_y=0.0, tb_z=0.0,
        tr_x=0.0, tr_y=0.0, tr_z=0.0, al_y=0.0, om_y=0.0, omega=0.0, alpha=0.0,
        vitx=0.0, depx=0.0, defl=0.0, delta_pc=0.0, delta_pd=0.0,
        qc_total=0.0, qc_bh=0.0, qc_leak=0.0, leak_ratio=0.0, re_leak=0.0,
        hyd_conv_err=0.0, hyd_conv_iter=0.0, pg_prev=pg, ftot=p.St * pg,
        v_prev=0.0, entraxe=entraxe, th_ay=th_ay, th_ry=th_ry, d=0.0, v=0.0,
    )

    keys = ["temps", "d", "ftot", "fb_x", "fb_z", "fc_x", "fc_z", "al_y", "om_y"]
    out = {k: np.zeros(n_out) for k in keys}

    for i in range(n_out):
        # --- (6b) Accélération angulaire rigide, à partir des efforts du pas
        #     précédent (état) et de la géométrie courante. G' = milieu(B, R) ---
        # --- Dynamique masse suspendue (tb du pas précédent, mass-couplé) -------
        support_accms = (1.0 / Ms) * (-state.ta_z - state.tb_z - pms_rlg_z)
        support_depms, support_vitms = _integrate_const_acc(
            state.depms, state.vitms, support_accms, It, integrator_mode)
        dz = support_depms - state.depms

        # --- (6b) Accélération angulaire rigide, avec B décalé de support_dz
        #     (comme l'historique : B[2]+=support_dz AVANT le calcul de al_y) -----
        B_shift = state.B.copy()
        B_shift[2] += dz
        Gp = 0.5 * (B_shift + state.R)
        rBG = Gp - B_shift
        I_G = Jyy - m_arm * (rBG[0] ** 2 + rBG[2] ** 2)   # I_B=jyy ⇒ I_{G'}=jyy−m'·d²
        TA = np.array([state.ta_x, state.ta_y, state.ta_z])
        TR = np.array([state.tr_x, state.tr_y, state.tr_z])
        TB = np.array([state.tb_x, state.tb_y, state.tb_z])
        moment_y = 0.0
        for P, T in ((state.A, TA), (state.R, TR), (B_shift, TB)):
            r = P - Gp
            moment_y += r[2] * T[0] - r[0] * T[2]
        al_y = moment_y / I_G

        try:
            step = _trailing_arm_local_step(
                p, gas, tab_pos, tab_sec, tyre_defl, tyre_load, mu_x, mu_y, state,
                support_dz=dz, support_vitms=support_vitms, support_accms=support_accms,
                entraxe_init=entraxe_init, lg_ab=lg_ab, lg_rb=lg_rb, dy_ca=dy_ca,
                fast_time_scale=fast_time_scale, integrator_mode=integrator_mode, It=It,
                al_y_override=al_y,
            )
        except SimError as exc:
            if exc.code in OVERSTROKE_CODES:
                # Sur-enfoncement (masse balancier trop forte) : on tronque.
                out = {k: v[:i] for k, v in out.items()}
                break
            raise

        # --- (6a) Effort pivot rigide : T_B = m'·a_G' − T_A − T_R − P' ----------
        Gp = 0.5 * (state.B + state.R)
        rBG = Gp - state.B
        a_B = np.array([0.0, 0.0, support_accms])
        omega_cross = al_y * np.array([rBG[2], 0.0, -rBG[0]])   # ŷ × r_BG
        a_G = a_B + omega_cross - state.om_y ** 2 * rBG
        TA = np.array([state.ta_x, state.ta_y, state.ta_z])
        TR = np.array([state.tr_x, state.tr_y, state.tr_z])
        P_weight = np.array([0.0, 0.0, -m_arm * G])
        TB = m_arm * a_G - TA - TR - P_weight
        state.tb_x, state.tb_y, state.tb_z = float(TB[0]), float(TB[1]), float(TB[2])

        F_B, F_C = -TB, -TA
        out["temps"][i] = i * It
        out["d"][i] = state.d
        out["ftot"][i] = state.ftot
        out["fb_x"][i], out["fb_z"][i] = F_B[0], F_B[2]
        out["fc_x"][i], out["fc_z"][i] = F_C[0], F_C[2]
        out["al_y"][i] = al_y
        out["om_y"][i] = state.om_y

    return out
