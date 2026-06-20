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

import numpy as np

from .engine import (
    EngineOutput,
    _endstop,
    _integrate_const_acc,
    damper_force_step,
)
from .errors import ErrorCollector, SimError
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
#  Friction des bagues de guidage (ClNLG.FFriBag)
# --------------------------------------------------------------------------- #

def _ffribag_nlg(
    v: float,
    xgt: float,
    xgb: float,
    Dt: float,
    bague_guide_m: float,
    bague_piston_m: float,
) -> float:
    """Friction des bagues de guidage (formule VBA ClNLG.FFriBag).

    ``bague_guide_m``, ``bague_piston_m`` : longueurs des bagues en mètres.
    ``xgt``, ``xgb`` : efforts transverses aux bagues haute et basse (N).
    """
    if v == 0.0:
        return 0.0
    coeff = 1.0 / math.sqrt(0.95 + 0.28 * math.sqrt(1.0 / (90.0 * abs(v))))
    # Coefficient de friction bague guide (dépend de la pression de contact en MPa)
    eps = 1.0e-9  # évite la division par zéro
    p_contact_guide = abs(xgt) / max(Dt * bague_guide_m * 1.0e6, eps)
    p_contact_piston = abs(xgt) / max(Dt * bague_piston_m * 1.0e6, eps)
    mu_guide = ((-0.0007 * p_contact_guide + 0.1248) + 0.0825 * abs(v) + 0.0898) / 2.0
    mu_piston = ((-0.0007 * p_contact_piston + 0.1248) + 0.0825 * abs(v) + 0.0898) / 2.0
    return _sign(v) * (mu_piston * abs(xgt) + mu_guide * abs(xgb)) * coeff


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
    alfap: float = 0.0,
    alfar: float = 0.0,
    h_pivot_z_m: float = 0.60,
    h_guide_top_z_m: float = 0.50,
    h_guide_bot_z_m: float = 0.20,
) -> EngineOutput:
    """Exécute la simulation de drop test NLG (StraitStrut / jambe de force directe).

    Paramètres spécifiques NLG (au-delà de ``TrailingArmParamsSI``) :
      alfap, alfar    : angles pitch/roll de la jambe (rad), total = structural + avion.
      h_pivot_z_m     : hauteur pivot B au-dessus du centre roue (m, repère jambe).
      h_guide_top_z_m : hauteur bague haute Gt au-dessus du centre roue (m).
      h_guide_bot_z_m : hauteur bague basse Gb au-dessus du centre roue (m).
      bague_guide_m   : longueur bague de guidage (m).
      bague_piston_m  : longueur bague piston (m).
      seal_precomp_pa : pression de pré-compression du joint (Pa).
    """
    c = collector or ErrorCollector()

    # --- Préparation ------------------------------------------------------ #
    gas = GasSpring(p)
    tab_pos, tab_sec = build_section_table(p)
    tyre_defl_tbl, tyre_load_tbl = build_tyre_tables(p)
    mu_x, mu_y = p.mu_x, p.mu_y

    # Matrices de rotation (fixes sur toute la simulation)
    R_sol_to_lg = _rot_sol_to_lg(alfap, alfar)
    R_lg_to_sol = R_lg_to_sol_mat = R_sol_to_lg.T

    # --- Géométrie initiale jambe (repère jambe) --------------------------- #
    # Positions des points dans le repère jambe
    # Z = hauteur au-dessus de l'origine repère jambe (sol = 0 au contact pneu)
    unload_r = p.unload_radius  # rayon libre (m)
    # Position initiale du centre de roue dans le repère jambe (Rlg):
    ptR_lg = np.array([0.0, 0.0, unload_r])  # roue sur sol, Z = rayon libre
    # Points géométriques de guidage (positions au-dessus du centre de roue initial)
    ptGt_lg = np.array([0.0, 0.0, unload_r + h_guide_top_z_m])
    ptGb_lg = np.array([0.0, 0.0, unload_r + h_guide_bot_z_m])
    ptB_lg = np.array([0.0, 0.0, unload_r + h_pivot_z_m])
    ptS_sol = np.zeros(3)  # sol : origine (repère sol)

    # --- Stabilisation statique initial ------------------------------------ #
    # Trouver d0 tel que Ftot ≈ 0 (équilibre initial sans vitesse).
    # Ftot(v=0, d<0) = Sc*Pg - Sd*Pg + Sbh*Pg + d * k_endstop = Pg*St + d*k_endstop
    # → d0 = -Pg_init * St / k_endstop
    k_endstop = 1.0e8  # N/m (identique à `_endstop`)
    pg_init = gas.pressure(0.0, p.Pinitbp)
    d0 = -pg_init * p.St / k_endstop  # négatif (légère extension)
    # Ajuster les positions initiales des points (équivalent VBA stabilisation)
    ptB_lg[2] -= d0
    ptGb_lg[2] -= d0

    # Convertir les points initiaux en repère sol
    ptR_sol = R_lg_to_sol @ ptR_lg
    ptS_sol = np.zeros(3)

    # --- État initial ------------------------------------------------------ #
    dt = p.it
    n_steps = max(1, round(p.temps_simu / dt))
    method = p.integrator

    # Masse suspendue Ms (repère sol)
    vz_ms = -p.vz             # vitesse verticale initiale (chute = négative)
    z_ms = 0.0                # déplacement vertical (m)
    poids_ms = p.masse * G * (1.0 - p.lift)  # N (poids effectif sol)

    # Masse non suspendue Mns (repère jambe)
    # Vitesse initiale Mns = même vitesse que Ms dans le repère jambe
    v_ms_sol = np.array([0.0, 0.0, vz_ms])
    v_ms_lg = R_sol_to_lg @ v_ms_sol
    vz_mns_lg = float(v_ms_lg[2])
    z_mns_lg = 0.0
    mns = p.unsprung_mass           # masse non suspendue totale (kg)
    poids_mns_lg_z = mns * G       # N (poids Mns dans repère jambe, projeté)

    # Amortisseur
    d = float(d0)
    v_damper = 0.0
    delta_pc = 0.0
    delta_pd = 0.0
    pg_prev = pg_init

    # Pneu
    tyre_omega = 0.0
    tyre_vx = 0.0
    tyre_depx = 0.0
    tyre_defl_val = unload_r - (float(ptR_sol[2]) - float(ptS_sol[2]))
    tyre_defl_val = max(0.0, tyre_defl_val)

    # Effort amortisseur initial (TB_sl)
    tb_lg_z = 0.0  # effort jambe dans le repère jambe (Z), init 0
    tb_sol = R_lg_to_sol @ np.array([0.0, 0.0, tb_lg_z])

    # Énergies cumulées
    e_kin_prev = 0.5 * p.masse * vz_ms ** 2
    e_kin_mns_prev = 0.5 * mns * vz_mns_lg ** 2
    e_kin_spin_prev = 0.5 * p.wheel_inertia * tyre_omega ** 2
    e_kin_horiz_prev = 0.5 * p.wheelmass * tyre_vx ** 2
    e_gas_acc = 0.0
    e_tyre_acc = 0.0
    e_spring_x_acc = 0.0
    e_hyd_acc = 0.0
    e_fric_acc = 0.0
    e_fribag_acc = 0.0
    e_damp_x_acc = 0.0
    e_slip_acc = 0.0
    e_endstop_acc = 0.0
    # Apport initial (cinétique + Mns)
    e_input_0 = e_kin_prev + e_kin_mns_prev

    # --- Tableaux de sortie ----------------------------------------------- #
    n_out = n_steps + 1
    out: dict[str, np.ndarray] = {k: np.zeros(n_out) for k in OUTPUT_COLUMNS_SS}

    # --- Boucle d'intégration --------------------------------------------- #
    for i in range(n_out):
        t = i * dt

        # --- Enregistrement de l'état au pas i ----------------------------- #
        damp_step = damper_force_step(
            p, gas, tab_pos, tab_sec,
            d, v_damper, delta_pc, delta_pd, pg_prev, dt=dt,
        )
        pg = damp_step["pg"]
        pc = damp_step["pc"]
        pd = damp_step["pd"]
        delta_pc = damp_step["delta_pc"]
        delta_pd = damp_step["delta_pd"]
        pg_prev = pg

        fgas = damp_step["fgas"]
        ffrijoi = _ffrijoi_nlg(v_damper, pd, p, seal_precomp_pa)
        fendstop = _endstop(d, p.course, smooth_len=p.endstop_smooth)

        # Effort pneu vertical
        tyre_ftyre_i = max(0.0, f_tyre(tyre_defl_val, tyre_defl_tbl, tyre_load_tbl))
        # Effort horizontal spring-back (repère sol)
        fx_spring = -p.kx * tyre_depx - p.cx * tyre_vx
        # Torseur sol au contact : (Fx, 0, Fz)
        tr_sol = np.array([fx_spring, 0.0, tyre_ftyre_i])
        # Conversion en repère jambe pour les efforts de guidage
        tr_lg = R_sol_to_lg @ tr_sol
        tr_lg_x = float(tr_lg[0])  # composante latérale (pour guide force)
        xr = abs(tr_lg_x)  # effort latéral résultant sur la roue dans le repère jambe

        # Réactions aux bagues de guidage (équilibre statique du bras de guidage)
        z_r_lg = float(ptR_lg[2])
        z_gt_lg = float(ptGt_lg[2])
        z_gb_lg = float(ptGb_lg[2])
        if abs(z_gb_lg - z_gt_lg) > 1.0e-9:
            xgb = -(z_r_lg - z_gt_lg) * xr / (z_gb_lg - z_gt_lg)
        else:
            xgb = 0.0
        xgt = -xgb - xr

        ffribag = _ffribag_nlg(v_damper, xgt, xgb, p.Dt, bague_guide_m, bague_piston_m)

        ftot = p.Sc * pc - p.Sd * pd + p.Sbh * pg + ffrijoi + ffribag + fendstop
        fhyd = damp_step["fhyd"]

        # Effort de jambe en repère sol (pour la dynamique Ms)
        tb_lg = np.array([tr_lg[0], 0.0, ftot])
        tb_sol_cur = R_lg_to_sol @ tb_lg

        # Pneu : slip, mu, spin-up, spring-back
        r_eff_val = r_eff(p.unload_radius, tyre_defl_val)
        slip = 0.0
        if abs(p.vx) > 1.0e-9:
            slip = (p.vx - tyre_omega * r_eff_val) / abs(p.vx)
        mu_val = mu(slip, mu_x, mu_y)
        fspin = mu_val * tyre_ftyre_i * math.copysign(1.0, slip) if tyre_ftyre_i > 0 else 0.0
        tyre_alpha_i = (fspin * r_eff_val) / p.wheel_inertia if tyre_ftyre_i > 0 else 0.0
        # Spring-back : force de rappel horizontal (sol) -> accélération roue
        acc_tyre_x = (fx_spring + fspin) / p.wheelmass

        # Torseur à l'attache fuselage B
        tb_res_x = float(tb_sol_cur[0])
        tb_res_y = float(tb_sol_cur[1])
        tb_res_z = float(tb_sol_cur[2])
        tb_norm = math.sqrt(tb_res_x**2 + tb_res_y**2 + tb_res_z**2)
        # Moment en B = (ptR_sol - ptB_sol) × TR_sol (moment de la réaction sol)
        ptB_sol = R_lg_to_sol @ ptB_lg
        ptR_sol_cur = R_lg_to_sol @ ptR_lg
        r_b = ptR_sol_cur - ptB_sol
        mom_B = np.cross(r_b, tr_sol)

        # Bilan énergétique (simplifié — diagnostic)
        e_kin_new = 0.5 * p.masse * vz_ms ** 2
        e_kin_mns_new = 0.5 * mns * vz_mns_lg ** 2
        e_kin_spin_new = 0.5 * p.wheel_inertia * tyre_omega ** 2
        e_kin_horiz_new = 0.5 * p.wheelmass * tyre_vx ** 2
        e_gas_acc += fgas * v_damper * dt
        e_tyre_acc += tyre_ftyre_i * max(0.0, vz_mns_lg) * dt
        e_spring_x_acc = 0.5 * p.kx * tyre_depx ** 2
        e_hyd_acc += abs(fhyd * v_damper * dt)
        e_fric_acc += abs(ffrijoi * v_damper * dt)
        e_fribag_acc += abs(ffribag * v_damper * dt)
        e_damp_x_acc += p.cx * tyre_vx ** 2 * dt
        e_slip_acc += abs(fspin * p.vx * dt) if abs(p.vx) > 1.0e-9 else 0.0
        e_endstop_acc += abs(fendstop * v_damper * dt)
        e_input_total = (e_kin_new + e_kin_mns_new + e_kin_spin_new + e_kin_horiz_new
                         + e_gas_acc + e_tyre_acc + e_hyd_acc + e_fric_acc
                         + e_fribag_acc + e_damp_x_acc + e_slip_acc + e_endstop_acc)
        e_residual = e_input_0 + p.masse * G * abs(z_ms) + mns * G * abs(z_mns_lg) - e_input_total

        # Enregistrement
        out["temps"][i] = t
        out["accms"][i] = float(tb_sol_cur[2] - poids_ms) / p.masse
        out["vitms"][i] = vz_ms
        out["depms"][i] = z_ms
        out["accmns"][i] = (-ftot + tyre_ftyre_i - poids_mns_lg_z) / mns
        out["vitmns"][i] = vz_mns_lg
        out["depmns"][i] = z_mns_lg
        out["trailing_arm_v"][i] = v_damper
        out["trailing_arm_d"][i] = max(0.0, d)
        out["trailing_arm_ftot"][i] = ftot
        out["trailing_arm_fhyd"][i] = fhyd
        out["trailing_arm_ffrijoi"][i] = ffrijoi
        out["trailing_arm_ffribag"][i] = ffribag
        out["trailing_arm_fgas"][i] = fgas
        out["pg"][i] = pg / 1.0e5          # Pa → bar
        out["pc"][i] = pc / 1.0e5
        out["pd"][i] = pd / 1.0e5
        out["delta_pc"][i] = delta_pc / 1.0e5
        out["delta_pd"][i] = delta_pd / 1.0e5
        out["secbh"][i] = damp_step["sec"] * 1.0e6  # m² → mm²
        out["hyd_conv_err"][i] = damp_step["hyd_conv_err"]
        out["hyd_conv_iter"][i] = damp_step["hyd_conv_iter"]
        out["hyd_qc_total"][i] = damp_step["qc_total"]
        out["hyd_qc_bh"][i] = damp_step["qc_bh"]
        out["hyd_qc_leak"][i] = damp_step["qc_leak"]
        out["hyd_leak_ratio"][i] = damp_step["leak_ratio"]
        out["hyd_re_leak"][i] = damp_step["re_leak"]
        out["tyre_defl"][i] = tyre_defl_val
        out["tyre_ftyre"][i] = tyre_ftyre_i
        out["tyre_alpha"][i] = tyre_alpha_i
        out["tyre_omega"][i] = tyre_omega
        out["tyre_mu"][i] = mu_val
        out["tyre_slip"][i] = slip
        out["tr_x"][i] = float(tr_sol[0])
        out["reaction_v"][i] = tyre_ftyre_i
        out["reaction_h"][i] = abs(float(tr_sol[0]))
        out["xgt"][i] = xgt
        out["xgb"][i] = xgb
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

        if progress_callback is not None and (i % 10 == 0 or i == n_steps):
            progress_callback(i, n_steps)

        if i == n_steps:
            break

        # --- Intégration du pas i→i+1 ------------------------------------- #
        # 1. Dynamique masse suspendue Ms (repère sol)
        acc_ms_z = (float(tb_sol_cur[2]) - poids_ms) / p.masse
        z_ms, vz_ms = _integrate_const_acc(z_ms, vz_ms, acc_ms_z, dt, method)

        # 2. Convertir VitMs sol → repère jambe
        v_ms_sol_vec = np.array([0.0, 0.0, vz_ms])
        v_ms_lg_vec = R_sol_to_lg @ v_ms_sol_vec
        vz_ms_lg = float(v_ms_lg_vec[2])

        # 3. Dynamique masse non suspendue Mns (repère jambe)
        acc_mns_lg_z = (-ftot + tyre_ftyre_i - poids_mns_lg_z) / mns
        z_mns_lg, vz_mns_lg = _integrate_const_acc(z_mns_lg, vz_mns_lg, acc_mns_lg_z, dt, method)

        # 4. Mise à jour position roue dans le repère jambe
        ptR_lg = ptR_lg.copy()
        ptR_lg[2] += vz_mns_lg * dt
        ptB_lg = ptB_lg.copy()
        ptB_lg[2] += vz_ms_lg * dt
        ptGb_lg = ptGb_lg.copy()
        ptGb_lg[2] += vz_ms_lg * dt
        ptGt_lg = ptGt_lg.copy()
        ptGt_lg[2] += vz_ms_lg * dt

        # 5. Position roue en repère sol → déflexion pneu
        ptR_sol = R_lg_to_sol @ ptR_lg
        tyre_defl_val = max(0.0, unload_r - (float(ptR_sol[2]) - float(ptS_sol[2])))

        # 6. Vitesse amortisseur = -(vMs_lg_Z - vMns_lg_Z)
        v_damper = -(vz_ms_lg - vz_mns_lg)
        d += v_damper * dt

        # 7. Spin-up / spring-back pneu
        tyre_omega_new = tyre_omega + tyre_alpha_i * dt
        tyre_vx_new = tyre_vx + acc_tyre_x * dt
        tyre_depx_new = tyre_depx + tyre_vx * dt
        tyre_omega = tyre_omega_new
        tyre_vx = tyre_vx_new
        tyre_depx = tyre_depx_new

    return EngineOutput(data=out, n_steps=n_steps)
