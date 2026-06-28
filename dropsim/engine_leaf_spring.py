"""Moteur du modèle « Train à lame » (leaf spring) — cf. PFD §6c.

Modèle le plus simple : une **lame** se comporte comme un **ressort vertical**
(raideur k) en parallèle d'un **amortisseur visqueux** (c), monté entre
l'encastrement **B** (structure) et le centre roue **R** (extrémité de lame).
La roue/pneu (spring-back, spin-up) est **identique** au StraitStrut ; il n'y a
ni oléo, ni ressort gaz, ni bagues de guidage.

Dynamique verticale à 2 masses : masse suspendue Ms (à B) et masse non suspendue
Mns (à R). La déflexion de lame ``d`` (compression) suit ``ḋ = vz_mns − vz_ms`` ;
l'effort de lame vaut ``F_lame = k·d + c·ḋ``. Le PFD de la lame (sans masse
propre) réduit l'effort appliqué en R en un **torseur d'encastrement** en B.
"""
from __future__ import annotations

import math

import numpy as np

from .engine import EngineOutput, _integrate_const_acc
from .errors import ErrorCollector
from .inputs import TrailingArmParamsSI
from .tyre import build_tyre_tables, f_tyre, mu, r_eff
from .units import G


# Colonnes de sortie : les clés PARTAGÉES avec TrailingArm/StraitStrut gardent le
# même nom interne (trailing_arm_*, tyre_*, pg/pc/pd, accms…) pour que le résumé
# et l'affichage fonctionnent sans modification. Les libellés portent le préfixe
# « LeafSpring. » et le torseur en B reprend les noms du StraitStrut (encastrement).
OUTPUT_COLUMNS_LS: dict[str, str] = {
    "temps": "Temps (s)",
    # Dynamique des masses
    "accms": "AccMs.RsolZ (m/s²)",
    "vitms": "VitMs.RsolZ (m/s)",
    "depms": "DepMs.RsolZ (m)",
    "accmns": "AccMns.RsolZ (m/s²)",
    "vitmns": "VitMns.RsolZ (m/s)",
    "depmns": "DepMns.RsolZ (m)",
    # Lame (clés internes partagées pour le résumé)
    "trailing_arm_v": "LeafSpring.v (m/s)",
    "trailing_arm_d": "LeafSpring.d (m)",
    "trailing_arm_ftot": "LeafSpring.Ftot (N)",
    "f_spring": "LeafSpring.FRessort (N)",
    "f_damp": "LeafSpring.FAmortisseur (N)",
    # Pneu
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
    # Torseur d'encastrement en B (mêmes libellés que StraitStrut)
    "tors_res_x": "Torseur.Resultante X (N)",
    "tors_res_y": "Torseur.Resultante Y (N)",
    "tors_res_z": "Torseur.Resultante Z (N)",
    "tors_res_norm": "Torseur.Resultante norme (N)",
    "torsB_fx": "Torseur@B (pivot).Effort X (N)",
    "torsB_fy": "Torseur@B (pivot).Effort Y (N)",
    "torsB_fz": "Torseur@B (pivot).Effort Z (N)",
    "torsB_mx": "Torseur@B (pivot).Moment X (N·m)",
    "torsB_mz": "Torseur@B (pivot).Moment Z (N·m)",
    # Bilan énergétique (convention travail)
    "e_kin": "Énergie.Cinétique masse susp. (J)",
    "e_kin_mns": "Énergie.Cinétique masse non susp. (J)",
    "e_kin_spin": "Énergie.Cinétique rotation roue (J)",
    "e_kin_horiz": "Énergie.Cinétique horizontale roue (J)",
    "e_spring": "Énergie.Stockée lame (J)",
    "e_tyre": "Énergie.Stockée pneu vertical (J)",
    "e_spring_x": "Énergie.Stockée ressort horizontal (J)",
    "e_damp": "Énergie.Dissipée amortisseur lame (J)",
    "e_damp_x": "Énergie.Dissipée amortisseur horizontal (J)",
    "e_slip": "Énergie.Dissipée glissement pneu (J)",
    "e_input": "Énergie.Apport total (J)",
    "e_residual": "Énergie.Résidu de bilan (J)",
}

# Clés présentes dans la sortie brute mais SANS colonne affichée (compat. résumé
# / avertissements pression : le leaf spring n'a pas de pression hydraulique).
_RAW_EXTRA_KEYS = ("pg", "pc", "pd")


def leaf_spring_step(d: float, v_damper: float, k_leaf: float, c_leaf: float) -> tuple[float, float, float]:
    """Effort de lame = ressort (k·d) + amortisseur (c·ḋ). Renvoie (F_lame, F_ressort, F_amort)."""
    f_spring = k_leaf * d
    f_damp = c_leaf * v_damper
    return f_spring + f_damp, f_spring, f_damp


def run_leaf_spring(
    p: TrailingArmParamsSI,
    collector: ErrorCollector | None = None,
    progress_callback: callable | None = None,
    *,
    k_leaf: float,
    c_leaf: float,
    B_pos: np.ndarray,
    R_pos: np.ndarray,
) -> EngineOutput:
    """Simulation de drop test « Train à lame ».

    ``k_leaf`` (N/m), ``c_leaf`` (N·s/m) : raideur et amortissement de la lame.
    ``B_pos`` / ``R_pos`` : positions (m, repère avion) de l'encastrement B et du
    centre roue R — seuls leurs écarts (bras de levier BR) interviennent.
    """
    c = collector or ErrorCollector()

    tyre_defl_tbl, tyre_load_tbl = build_tyre_tables(p)
    mu_x, mu_y = p.mu_x, p.mu_y

    dt = p.it
    n_steps = max(1, round(p.temps_simu / dt))
    method = p.integrator

    masse = p.masse
    mns = p.unsprung_mass
    poids_ms = masse * G * (1.0 - p.lift)
    unload_r = p.unload_radius

    # Bras de levier initial BR (repère avion, m). Composantes X/Y figées ; la
    # composante Z varie avec la compression d (BR_z = BR_z0 + d).
    BR0 = np.asarray(R_pos, float) - np.asarray(B_pos, float)
    br_x, br_y, br_z0 = float(BR0[0]), float(BR0[1]), float(BR0[2])

    # --- État initial : roue au contact, tout le train à la vitesse de chute --- #
    z_ms = 0.0
    vz_ms = -p.vz
    z_mns = 0.0
    vz_mns = -p.vz
    d = 0.0
    v_damper = 0.0
    tyre_omega = 0.0
    tyre_vx = 0.0
    tyre_depx = 0.0
    tyre_defl_val = 0.0  # contact initial (R à z = unload_r)

    # Énergies (convention travail)
    e_kin_init = 0.5 * masse * vz_ms ** 2 + 0.5 * mns * vz_mns ** 2
    e_tyre_acc = 0.0
    e_damp_acc = 0.0
    e_damp_x_acc = 0.0
    e_slip_acc = 0.0
    e_fwd_acc = 0.0
    e_grav_acc = 0.0
    d_prev = d
    defl_prev = tyre_defl_val
    z_ms_prev = z_ms
    z_mns_prev = z_mns
    omega_prev = tyre_omega

    n_out = n_steps + 1
    out: dict[str, np.ndarray] = {k: np.zeros(n_out) for k in OUTPUT_COLUMNS_LS}
    for k in _RAW_EXTRA_KEYS:
        out[k] = np.zeros(n_out)

    for i in range(n_out):
        t = i * dt

        # Effort de lame (ressort + amortisseur) = effort d'amortisseur équivalent.
        ftot, f_spring, f_damp = leaf_spring_step(d, v_damper, k_leaf, c_leaf)

        # Pneu : effort vertical, slip, spin-up, spring-back (identique StraitStrut).
        tyre_ftyre_i = max(0.0, f_tyre(tyre_defl_val, tyre_defl_tbl, tyre_load_tbl))
        r_eff_val = r_eff(unload_r, tyre_defl_val)
        slip = 0.0
        if abs(p.vx) > 1.0e-9:
            slip = (p.vx - tyre_omega * r_eff_val) / abs(p.vx)
        mu_val = mu(slip, mu_x, mu_y)
        fspin = mu_val * tyre_ftyre_i * math.copysign(1.0, slip) if tyre_ftyre_i > 0 else 0.0
        tyre_alpha_i = (fspin * r_eff_val) / p.wheel_inertia if tyre_ftyre_i > 0 else 0.0
        fx_spring_wheel = -p.kx * tyre_depx - p.cx * tyre_vx
        tr_x = -fx_spring_wheel
        acc_tyre_x = (fx_spring_wheel + fspin) / p.wheelmass

        # Effort de contact sol (repère sol, vertical car lame verticale).
        tr_sol = np.array([fx_spring_wheel, 0.0, tyre_ftyre_i])

        # Torseur transmis à la structure en B (encastrement) : résultante = effort
        # transmis (horizontal contact + vertical lame), moment = BR × tr_sol.
        tb_res_x = -float(fx_spring_wheel)   # = tr_x (convention TrailingArm/Excel)
        tb_res_y = 0.0
        tb_res_z = float(ftot)
        tb_norm = math.sqrt(tb_res_x ** 2 + tb_res_y ** 2 + tb_res_z ** 2)
        br_z = br_z0 + d
        mom_B_y = br_z * float(tr_sol[0]) - br_x * float(tr_sol[2])   # (z_R−z_B)·fx − (x_R−x_B)·fz

        # --- Bilan énergétique (travail) ---------------------------------- #
        e_kin_new = 0.5 * masse * vz_ms ** 2
        e_kin_mns_new = 0.5 * mns * vz_mns ** 2
        e_kin_spin_new = 0.5 * p.wheel_inertia * tyre_omega ** 2
        e_kin_horiz_new = 0.5 * p.wheelmass * tyre_vx ** 2
        e_spring_new = 0.5 * k_leaf * d ** 2                       # stocké (ressort lame)
        e_spring_x_acc = 0.5 * p.kx * tyre_depx ** 2              # stocké (ressort horizontal)
        dd = d - d_prev
        ddefl = tyre_defl_val - defl_prev
        e_tyre_acc += tyre_ftyre_i * ddefl
        e_damp_acc += f_damp * dd                                 # dissipé (amortisseur lame)
        e_damp_x_acc += p.cx * tyre_vx ** 2 * dt
        dke_spin = 0.5 * p.wheel_inertia * (tyre_omega ** 2 - omega_prev ** 2)
        if abs(p.vx) > 1.0e-9:
            e_fwd_acc += fspin * p.vx * dt
            e_slip_acc += fspin * (p.vx - tyre_vx) * dt - dke_spin
        e_grav_acc += (-poids_ms * (z_ms - z_ms_prev) - mns * G * (z_mns - z_mns_prev))
        d_prev = d
        defl_prev = tyre_defl_val
        z_ms_prev = z_ms
        z_mns_prev = z_mns
        omega_prev = tyre_omega

        e_input_total = e_kin_init + e_grav_acc + e_fwd_acc
        e_residual = e_input_total - (
            e_kin_new + e_kin_mns_new + e_kin_spin_new + e_kin_horiz_new
            + e_spring_new + e_tyre_acc + e_spring_x_acc
            + e_damp_acc + e_damp_x_acc + e_slip_acc
        )

        # --- Enregistrement ----------------------------------------------- #
        out["temps"][i] = t
        out["accms"][i] = (ftot - poids_ms) / masse
        out["vitms"][i] = vz_ms
        out["depms"][i] = z_ms
        out["accmns"][i] = (-ftot + tyre_ftyre_i - mns * G) / mns
        out["vitmns"][i] = vz_mns
        out["depmns"][i] = z_mns
        out["trailing_arm_v"][i] = v_damper
        out["trailing_arm_d"][i] = d
        out["trailing_arm_ftot"][i] = ftot
        out["f_spring"][i] = f_spring
        out["f_damp"][i] = f_damp
        out["tyre_defl"][i] = tyre_defl_val
        out["tyre_ftyre"][i] = tyre_ftyre_i
        out["tyre_alpha"][i] = tyre_alpha_i
        out["tyre_omega"][i] = tyre_omega
        out["tyre_mu"][i] = mu_val
        out["tyre_slip"][i] = slip
        out["tr_x"][i] = tr_x
        out["reaction_v"][i] = tyre_ftyre_i
        out["reaction_h"][i] = tr_x
        out["tors_res_x"][i] = tb_res_x
        out["tors_res_y"][i] = tb_res_y
        out["tors_res_z"][i] = tb_res_z
        out["tors_res_norm"][i] = tb_norm
        out["torsB_fx"][i] = tb_res_x
        out["torsB_fy"][i] = tb_res_y
        out["torsB_fz"][i] = tb_res_z
        out["torsB_mx"][i] = 0.0
        out["torsB_mz"][i] = mom_B_y   # moment de tangage (autour de Y) reporté en Mz/My selon convention
        out["e_kin"][i] = e_kin_new
        out["e_kin_mns"][i] = e_kin_mns_new
        out["e_kin_spin"][i] = e_kin_spin_new
        out["e_kin_horiz"][i] = e_kin_horiz_new
        out["e_spring"][i] = e_spring_new
        out["e_tyre"][i] = e_tyre_acc
        out["e_spring_x"][i] = e_spring_x_acc
        out["e_damp"][i] = e_damp_acc
        out["e_damp_x"][i] = e_damp_x_acc
        out["e_slip"][i] = e_slip_acc
        out["e_input"][i] = e_input_total
        out["e_residual"][i] = e_residual

        if progress_callback is not None and (i % 10 == 0 or i == n_steps):
            progress_callback(i, n_steps)

        if i == n_steps:
            break

        # --- Intégration i → i+1 ------------------------------------------ #
        acc_ms = (ftot - poids_ms) / masse
        acc_mns = (-ftot + tyre_ftyre_i - mns * G) / mns
        z_ms, vz_ms = _integrate_const_acc(z_ms, vz_ms, acc_ms, dt, method)
        z_mns, vz_mns = _integrate_const_acc(z_mns, vz_mns, acc_mns, dt, method)
        v_damper = vz_mns - vz_ms
        d = d + v_damper * dt
        # Le centre roue suit le déplacement vertical de Mns.
        tyre_defl_val = max(0.0, unload_r - (unload_r + z_mns))   # = max(0, -z_mns)
        # Pneu : intégration spin-up / spring-back.
        tyre_omega = tyre_omega + tyre_alpha_i * dt
        tyre_vx = tyre_vx + acc_tyre_x * dt
        tyre_depx = tyre_depx + (tyre_vx - acc_tyre_x * dt) * dt  # dépl. avec vx du pas courant

    return EngineOutput(data=out, n_steps=n_steps, warnings=list(c.warnings))


__all__ = ["run_leaf_spring", "OUTPUT_COLUMNS_LS", "leaf_spring_step"]
