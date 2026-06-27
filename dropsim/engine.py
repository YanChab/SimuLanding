"""Boucle d'intégration temporelle du drop test MLG (Euler explicite).

Reproduit fidèlement la macro VBA ``DropCalcul`` du module ``Feuil1`` :
stabilisation statique initiale, puis intégration explicite pas à pas couplant la
dynamique de la masse suspendue, la rotation du balancier, l'écrasement du pneu,
le ressort gazeux et les pertes hydrauliques.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .errors import ErrorCollector, ErrorLevel, OVERSTROKE_CODES, SimError, make_overstroke_warning
from .gas import GasSpring
from .geometry import chgt_rep, deter_pos_bal_a, deter_pos_bal_r, rotate_about
from .hydraulic import _sign, calcul_hydrau
from .inputs import TrailingArmParamsSI
from .metering import build_section_table, section_bh
from .tyre import build_tyre_tables, f_tyre, mu, r_eff
from .units import G


# Colonnes de sortie (clé interne -> libellé d'affichage avec unité)
OUTPUT_COLUMNS: dict[str, str] = {
    "temps": "Temps (s)",
    "accms": "AccMs.RsolZ (m/s²)",
    "vitms": "VitMs.RsolZ (m/s)",
    "depms": "DepMs.RsolZ (m)",
    "aly": "AlY (rad/s²)",
    "omy": "OmY (rad/s)",
    "thay": "ThAY (rad)",
    "thry": "ThRY (rad)",
    "tyre_defl": "Tyre.Defl (m)",
    "tyre_ftyre": "Tyre.FTyre (N)",
    "trailing_arm_v": "TrailingArm.v (m/s)",
    "trailing_arm_d": "TrailingArm.d (m)",
    "trailing_arm_ftot": "TrailingArm.Ftot (N)",
    "trailing_arm_fhyd": "TrailingArm.Fhyd (N)",
    "trailing_arm_ffrijoi": "TrailingArm.FFriJoi (N)",
    "trailing_arm_fgas": "TrailingArm.FGas (N)",
    "ta_z": "TA_bal.RsolZ (N)",
    "ta_x": "TA_bal.RsolX (N)",
    "entraxe": "TrailingArm.Entraxe (m)",
    "secbh": "Section de la BH (mm²)",
    "course_roue": "Course centre roue (m)",
    "tyre_alpha": "Tyre.Alpha (rad/s²)",
    "tyre_omega": "Tyre.Omega (rad/s)",
    "tr_x": "TR_bal.RsolX (N)",
    "tyre_mu": "Tyre.Mu",
    "tyre_slip": "Tyre.Slip",
    "pc": "TrailingArm.Pc (bar)",
    "pd": "TrailingArm.Pd (bar)",
    "pg": "TrailingArm.Pg (bar)",
    "delta_pc": "TrailingArm.DeltaPc (bar)",
    "delta_pd": "TrailingArm.DeltaPd (bar)",
    "hyd_qc_total": "Hydrau.Qc total (m³/s)",
    "hyd_qc_bh": "Hydrau.Qc rainures BH (m³/s)",
    "hyd_qc_leak": "Hydrau.Qc fuite annulaire (m³/s)",
    "hyd_leak_ratio": "Hydrau.Part fuite (-)",
    "hyd_re_leak": "Hydrau.Re fuite annulaire (-)",
    "hyd_conv_err": "Hydrau.Erreur convergence (-)",
    "hyd_conv_iter": "Hydrau.Itérations convergence (-)",
    "reaction_v": "Reaction sol verticale (N)",
    "reaction_h": "Reaction sol horizontale (N)",
    # Torseur d'effort transmis par le train à la masse suspendue via ses deux
    # attaches : C (tête d'amortisseur) est une ROTULE → effort seul, aucun
    # moment ; B (pivot du balancier) est un PIVOT d'axe Y → effort + moments
    # de liaison autour de X et Z uniquement (axe Y libre en rotation).
    # La résultante (somme des deux efforts) est égale à la réaction sol.
    "tors_res_x": "Torseur.Resultante X (N)",
    "tors_res_y": "Torseur.Resultante Y (N)",
    "tors_res_z": "Torseur.Resultante Z (N)",
    "tors_res_norm": "Torseur.Resultante norme (N)",
    "torsC_fx": "Torseur@C (rotule).Effort X (N)",
    "torsC_fy": "Torseur@C (rotule).Effort Y (N)",
    "torsC_fz": "Torseur@C (rotule).Effort Z (N)",
    "torsB_fx": "Torseur@B (pivot).Effort X (N)",
    "torsB_fy": "Torseur@B (pivot).Effort Y (N)",
    "torsB_fz": "Torseur@B (pivot).Effort Z (N)",
    "torsB_mx": "Torseur@B (pivot).Moment X (N·m)",
    "torsB_mz": "Torseur@B (pivot).Moment Z (N·m)",
    # Bilan énergétique (diagnostic, purement passif) : bilan COMPLET du
    # système (masse suspendue + balancier + roue + amortisseur). On suit les
    # réservoirs cinétiques (translation verticale de la masse suspendue,
    # rotation du balancier, spin-up et translation horizontale de la roue),
    # les énergies stockées (gaz, pneu vertical, ressort horizontal, butée),
    # les énergies dissipées (hydraulique, friction joint, amortisseur
    # horizontal, glissement au contact) et les apports (cinétique d'impact,
    # gravité, et travail puisé dans l'énergie d'avancement par le spin-up).
    # Le résidu (apport − stocké − dissipé) doit rester ≈ 0 → détecteur de bugs.
    "e_kin": "Énergie.Cinétique masse susp. (J)",
    "e_kin_bal": "Énergie.Cinétique rotation balancier (J)",
    "e_kin_spin": "Énergie.Cinétique rotation roue (J)",
    "e_kin_horiz": "Énergie.Cinétique horizontale roue (J)",
    "e_gas": "Énergie.Stockée gaz (J)",
    "e_tyre": "Énergie.Stockée pneu vertical (J)",
    "e_spring_x": "Énergie.Stockée ressort horizontal (J)",
    "e_hyd": "Énergie.Dissipée hydraulique (J)",
    "e_fric": "Énergie.Dissipée friction joint (J)",
    "e_damp_x": "Énergie.Dissipée amortisseur horizontal (J)",
    "e_slip": "Énergie.Dissipée glissement pneu (J)",
    "e_endstop": "Énergie.Emmagasinée butée (J)",
    "e_input": "Énergie.Apport total (J)",
    "e_residual": "Énergie.Résidu de bilan (J)",
}


@dataclass
class EngineOutput:
    """Résultats bruts du moteur (séries temporelles SI + bar pour les pressions)."""

    data: dict[str, np.ndarray]
    n_steps: int
    warnings: list[SimError] = field(default_factory=list)
    geometry: dict[str, np.ndarray] = field(default_factory=dict)


@dataclass
class TrailingArmLocalState:
    """État local réutilisable du train TrailingArm sur un pas global."""

    A: np.ndarray
    B: np.ndarray
    C: np.ndarray
    R: np.ndarray
    S: np.ndarray
    accms: float
    vitms: float
    depms: float
    ta_x: float
    ta_y: float
    ta_z: float
    tb_x: float
    tb_y: float
    tb_z: float
    tr_x: float
    tr_y: float
    tr_z: float
    al_y: float
    om_y: float
    omega: float
    alpha: float
    vitx: float
    depx: float
    defl: float
    delta_pc: float
    delta_pd: float
    qc_total: float
    qc_bh: float
    qc_leak: float
    leak_ratio: float
    re_leak: float
    hyd_conv_err: float
    hyd_conv_iter: float
    pg_prev: float
    ftot: float
    v_prev: float
    entraxe: float
    th_ay: float
    th_ry: float
    d: float
    v: float
    sec: float = 0.0


def _trailing_arm_local_step(
    p: TrailingArmParamsSI,
    gas: GasSpring,
    tab_pos: np.ndarray,
    tab_sec: np.ndarray,
    tyre_defl: np.ndarray,
    tyre_load: np.ndarray,
    mu_x: np.ndarray,
    mu_y: np.ndarray,
    state: TrailingArmLocalState,
    *,
    support_dz: float,
    support_vitms: float,
    support_accms: float,
    entraxe_init: float,
    lg_ab: float,
    lg_rb: float,
    dy_ca: float,
    fast_time_scale: float,
    integrator_mode: str,
    It: float,
) -> dict[str, float]:
    """Avance le noyau local TrailingArm sous cinématique support imposée."""
    state.accms = support_accms
    state.depms += support_dz
    state.vitms = support_vitms
    state.B[2] += support_dz
    state.C[2] += support_dz

    state.al_y = (1.0 / p.jyy) * (
        (state.A[2] - state.B[2]) * state.ta_x
        - (state.A[0] - state.B[0]) * state.ta_z
        + (state.R[2] - state.B[2]) * state.tr_x
        - (state.R[0] - state.B[0]) * state.tr_z
    )
    om_prev = state.om_y
    if integrator_mode == "rk4":
        state.om_y = om_prev + state.al_y * It
        dtheta = om_prev * It + 0.5 * state.al_y * It * It
        state.th_ay += dtheta
        state.th_ry += dtheta
    else:
        state.om_y = om_prev + state.al_y * It
        state.th_ay += state.om_y * It
        state.th_ry += state.om_y * It

    state.R[0] = -lg_rb * math.sin(state.th_ry) + state.B[0]
    state.R[2] = -lg_rb * math.cos(state.th_ry) + state.B[2]
    state.defl = p.unload_radius - (state.R[2] - state.S[2])
    ftyre = f_tyre(state.defl, tyre_defl, tyre_load)
    state.tr_z = ftyre

    if p.vx != 0.0:
        slip = (p.vx - state.omega * r_eff(p.unload_radius, state.defl)) / abs(p.vx)
    else:
        slip = 0.0
    mu_val = mu(slip, mu_x, mu_y)
    fspin = mu_val * state.tr_z * _sign(slip)
    fx_old = p.kx * state.depx + p.cx * state.vitx
    accx = (-fx_old + fspin) / p.wheelmass
    state.depx, state.vitx = _integrate_const_acc(state.depx, state.vitx, accx, It, integrator_mode)
    state.tr_x = p.kx * state.depx + p.cx * state.vitx
    state.alpha = (fspin * (p.unload_radius - state.defl)) / p.wheel_inertia
    state.omega = state.omega + state.alpha * It

    state.A[0] = -lg_ab * math.sin(state.th_ay) + state.B[0]
    state.A[2] = -lg_ab * math.cos(state.th_ay) + state.B[2]
    dist_ca = math.sqrt(
        (state.C[0] - state.A[0]) ** 2 + (state.C[1] - state.A[1]) ** 2 + (state.C[2] - state.A[2]) ** 2
    )
    state.v = -(dist_ca - state.entraxe) / It
    state.entraxe = dist_ca
    state.d = entraxe_init - state.entraxe

    solver_mode = _select_damper_core_solver(p, state.d, state.v, state.pg_prev, state.ftot)
    non_implicit_dt_scale = (
        fast_time_scale * 1.10
        if p.damper_core_solver == "auto_fast" and solver_mode != "implicit_adaptive"
        else 1.0
    )
    if solver_mode == "implicit_adaptive":
        min_h = 1.0 / 32.0 if p.damper_core_solver == "auto_fast" else 1.0 / 128.0
        damp = damper_force_step_implicit_adaptive(
            p,
            gas,
            tab_pos,
            tab_sec,
            max(0.0, state.d - state.v * It),
            state.v_prev,
            state.d,
            state.v,
            state.delta_pc,
            state.delta_pd,
            state.pg_prev,
            min_h=min_h,
            auto_fast_mode=(p.damper_core_solver == "auto_fast"),
            implicit_dt_scale=(2.0 * fast_time_scale) if p.damper_core_solver == "auto_fast" else 1.0,
        )
    elif p.damper_core_solver == "auto_fast":
        damp = damper_force_step(
            p,
            gas,
            tab_pos,
            tab_sec,
            state.d,
            state.v,
            state.delta_pc,
            state.delta_pd,
            state.pg_prev,
            dt=p.it * non_implicit_dt_scale,
        )
    elif p.integrator == "rk4":
        damp = damper_force_step_rk4_coupled(
            p,
            gas,
            tab_pos,
            tab_sec,
            max(0.0, state.d - state.v * It),
            state.v_prev,
            state.d,
            state.v,
            state.delta_pc,
            state.delta_pd,
            state.pg_prev,
            dt_scale=non_implicit_dt_scale,
        )
    else:
        damp = damper_force_step(
            p,
            gas,
            tab_pos,
            tab_sec,
            state.d,
            state.v,
            state.delta_pc,
            state.delta_pd,
            state.pg_prev,
            dt=p.it * non_implicit_dt_scale,
        )

    pg = damp["pg"]
    pc = damp["pc"]
    pd = damp["pd"]
    state.delta_pc = damp["delta_pc"]
    state.delta_pd = damp["delta_pd"]
    state.qc_total = damp["qc_total"]
    state.qc_bh = damp["qc_bh"]
    state.qc_leak = damp["qc_leak"]
    state.re_leak = damp["re_leak"]
    state.leak_ratio = damp["leak_ratio"]
    state.hyd_conv_err = damp.get("hyd_conv_err", 0.0)
    state.hyd_conv_iter = damp.get("hyd_conv_iter", 0.0)
    state.sec = damp["sec"]
    fgas = damp["fgas"]
    ffrijoi = damp["ffrijoi"]
    fhyd = damp["fhyd"]
    state.ftot = damp["ftot"]
    state.pg_prev = pg

    state.ta_z = -state.ftot * ((state.C[2] - state.A[2]) / state.entraxe)
    state.ta_y = -state.ftot * ((state.C[1] - state.A[1]) / state.entraxe)
    state.ta_x = -state.ftot * ((state.C[0] - state.A[0]) / state.entraxe)
    state.tb_x = -state.ta_x - state.tr_x
    state.tb_y = -state.ta_y - state.tr_y
    state.tb_z = -state.ta_z - state.tr_z

    fc_x, fc_y, fc_z = -state.ta_x, -state.ta_y, -state.ta_z
    fb_x, fb_y, fb_z = -state.tb_x, -state.tb_y, -state.tb_z
    res_x = fb_x + fc_x
    res_y = fb_y + fc_y
    res_z = fb_z + fc_z
    res_norm = math.sqrt(res_x * res_x + res_y * res_y + res_z * res_z)
    bax, bay, baz = state.A[0] - state.B[0], state.A[1] - state.B[1], state.A[2] - state.B[2]
    brx, bry, brz = state.R[0] - state.B[0], state.R[1] - state.B[1], state.R[2] - state.B[2]
    mb_x = (bay * state.ta_z - baz * state.ta_y) + (bry * state.tr_z - brz * state.tr_y)
    mb_z = (bax * state.ta_y - bay * state.ta_x) + (brx * state.tr_y - bry * state.tr_x)

    state.v_prev = state.v

    return {
        "pg": pg,
        "pc": pc,
        "pd": pd,
        "fgas": fgas,
        "ffrijoi": ffrijoi,
        "fhyd": fhyd,
        "ftyre": ftyre,
        "slip": slip,
        "mu_val": mu_val,
        "fspin": fspin,
        "fc_x": fc_x,
        "fc_y": fc_y,
        "fc_z": fc_z,
        "fb_x": fb_x,
        "fb_y": fb_y,
        "fb_z": fb_z,
        "res_x": res_x,
        "res_y": res_y,
        "res_z": res_z,
        "res_norm": res_norm,
        "mb_x": mb_x,
        "mb_z": mb_z,
    }


# Positions géométriques enregistrées pour l'animation (repère train, en mm).
GEOMETRY_KEYS: tuple[str, ...] = (
    "ax", "az", "bx", "bz", "cx", "cz", "rx", "rz", "ground_z", "wheel_radius",
)


def _integrate_const_acc(
    x: float,
    v: float,
    a: float,
    dt: float,
    method: str,
) -> tuple[float, float]:
    """Intègre ``x' = v`` et ``v' = a`` sur ``dt``.

    Le moteur emploie des efforts explicites (évalués au pas précédent) :
    l'accélération est donc tenue constante pendant le pas. Dans ce cadre,
    ``rk4`` correspond à l'intégration d'ordre 4 de ce système affine,
    équivalente à la primitive exacte sur un pas (position avec terme 1/2 a dt²).
    """
    if method == "rk4":
        v_new = v + a * dt
        x_new = x + v * dt + 0.5 * a * dt * dt
        return x_new, v_new

    # Euler (comportement historique du modèle)
    v_new = v + a * dt
    x_new = x + v_new * dt
    return x_new, v_new


def _endstop(
    d: float,
    course: float,
    smooth_len: float = 2.0e-3,
    k_endstop: float = 1.0e8,
) -> float:
    """Effort de butée lissé hors plage [0, course].

    Loi progressive ``k*x*(1-exp(-x/s))`` avec même asymptote qu'une loi
    linéaire en grande pénétration et pente nulle à l'entrée en contact.
    """
    if d > course:
        x = d - course
        s = max(smooth_len, 1.0e-9)
        return k_endstop * x * (1.0 - math.exp(-x / s))
    if d < 0.0:
        x = -d
        s = max(smooth_len, 1.0e-9)
        return -k_endstop * x * (1.0 - math.exp(-x / s))
    return 0.0


def damper_force_step(
    p: TrailingArmParamsSI,
    gas: GasSpring,
    tab_pos: np.ndarray,
    tab_sec: np.ndarray,
    d: float,
    v: float,
    delta_pc_prev: float,
    delta_pd_prev: float,
    pg_prev: float,
    dt: float | None = None,
) -> dict[str, float]:
    """Calcule un pas local de loi d'amortisseur avec EXACTEMENT le modele moteur.

    Cette fonction reprend le bloc de calcul utilise dans la boucle temporelle :
    gaz, hydraulique, friction de joint et butees. Les etats ``delta_pc`` /
    ``delta_pd`` / ``pg`` renvoyes doivent etre reinjectes au pas suivant pour
    reproduire la meme dynamique numerique (memoire hydraulique et gaz).
    """
    pg = gas.pressure(d, pg_prev)
    sec = section_bh(d, tab_pos, tab_sec)
    delta_pc = delta_pc_prev
    delta_pd = delta_pd_prev
    hyd_conv_err = 0.0
    hyd_conv_iter = 0.0
    if v != 0.0:
        hyd_metrics: dict[str, float] = {}
        (
            delta_pc,
            delta_pd,
            qc_total,
            qc_bh,
            qc_leak,
            re_leak,
        ) = calcul_hydrau(
            p,
            v,
            d,
            delta_pc_prev,
            pg,
            sec,
            dt=dt,
            n_iter=int(getattr(p, "hydraulic_max_iter", 64)),
            adaptive_newton=True,
            metrics=hyd_metrics,
        )
        leak_ratio = abs(qc_leak) / abs(qc_total) if abs(qc_total) > 1.0e-12 else 0.0
        hyd_conv_err = float(hyd_metrics.get("final_err", 0.0))
        hyd_conv_iter = float(hyd_metrics.get("iterations_used", 0.0))
    else:
        qc_total = qc_bh = qc_leak = leak_ratio = re_leak = 0.0
    pc = pg + delta_pc
    pd = pc - delta_pd
    fgas = p.St * pg
    if v != 0.0:
        coeff_atte = 1.0 / math.sqrt(0.95 + 0.28 * math.sqrt(1.0 / (90.0 * abs(v))))
        s_seal = math.pi / 4.0 * (p.ASeal ** 2 - p.Dt ** 2)
        ffrijoi = _sign(v) * coeff_atte * (
            p.fc * p.Dt * math.pi + p.fh * pd * s_seal
        )
    else:
        ffrijoi = 0.0
    ftot = p.Sc * pc - p.Sd * pd + p.Sbh * pg + ffrijoi + _endstop(
        d,
        p.course,
        smooth_len=p.endstop_smooth,
    )
    fhyd = p.Sc * (pc - pg) - p.Sd * (pd - pg)
    return {
        "pg": pg,
        "pc": pc,
        "pd": pd,
        "delta_pc": delta_pc,
        "delta_pd": delta_pd,
        "qc_total": qc_total,
        "qc_bh": qc_bh,
        "qc_leak": qc_leak,
        "re_leak": re_leak,
        "leak_ratio": leak_ratio,
        "sec": sec,
        "hyd_conv_err": hyd_conv_err,
        "hyd_conv_iter": hyd_conv_iter,
        "fgas": fgas,
        "ffrijoi": ffrijoi,
        "fhyd": fhyd,
        "ftot": ftot,
    }


def damper_force_step_rk4_coupled(
    p: TrailingArmParamsSI,
    gas: GasSpring,
    tab_pos: np.ndarray,
    tab_sec: np.ndarray,
    d_start: float,
    v_start: float,
    d_end: float,
    v_end: float,
    delta_pc_prev: float,
    delta_pd_prev: float,
    pg_prev: float,
    dt_scale: float = 1.0,
) -> dict[str, float]:
    """Évalue l'amortisseur sur les 4 stages RK4 avec couplage complet.

    Les stages RK4 échantillonnent la loi couplée gaz/hydraulique sur la
    trajectoire locale du pas, puis on met à jour l'état interne une seule fois
    en fin de pas (mémoire hydraulique/gaz au niveau du pas de temps global).
    """
    c_nodes = (0.0, 0.5, 0.5, 1.0)
    weights = (1.0 / 6.0, 1.0 / 3.0, 1.0 / 3.0, 1.0 / 6.0)

    weighted = {
        "ftot": 0.0,
        "fhyd": 0.0,
        "ffrijoi": 0.0,
        "fgas": 0.0,
        "pc": 0.0,
        "pd": 0.0,
        "pg": 0.0,
        "qc_total": 0.0,
        "qc_bh": 0.0,
        "qc_leak": 0.0,
        "re_leak": 0.0,
        "leak_ratio": 0.0,
        "sec": 0.0,
    }
    start_vgbp = gas.Vgbp
    start_vghp = gas.Vghp

    d_span = d_end - d_start
    v_span = v_end - v_start
    dt_stage = 0.5 * p.it * dt_scale

    for c_i, w_i in zip(c_nodes, weights):
        # Chaque stage repart du même état mémoire de début de pas pour éviter
        # un sur-cumul numérique sur ce solveur couplé hérité du VBA.
        gas.Vgbp = start_vgbp
        gas.Vghp = start_vghp
        d_i = d_start + c_i * d_span
        v_i = v_start + c_i * v_span
        stage = damper_force_step(
            p,
            gas,
            tab_pos,
            tab_sec,
            d_i,
            v_i,
            delta_pc_prev,
            delta_pd_prev,
            pg_prev,
            dt=dt_stage,
        )
        for key in weighted:
            weighted[key] += w_i * stage[key]

    # Mise à jour mémoire en fin de pas pour l'itération suivante.
    gas.Vgbp = start_vgbp
    gas.Vghp = start_vghp
    end_step = damper_force_step(
        p,
        gas,
        tab_pos,
        tab_sec,
        d_end,
        v_end,
        delta_pc_prev,
        delta_pd_prev,
        pg_prev,
        dt=p.it * dt_scale,
    )

    out = dict(end_step)
    for key, value in weighted.items():
        out[key] = value
    return out


def _gas_state(gas: GasSpring) -> tuple[float, float]:
    return gas.Vgbp, gas.Vghp


def _set_gas_state(gas: GasSpring, state: tuple[float, float]) -> None:
    gas.Vgbp, gas.Vghp = state


def _select_damper_core_solver(
    p: TrailingArmParamsSI,
    d: float,
    v: float,
    pg_prev: float,
    ftot_prev: float,
) -> str:
    """Sélectionne le noyau de solveur selon un critère de raideur simple.

    En mode ``auto``, on réserve ``implicit_adaptive`` aux zones où la loi est
    la plus raide: proximité immédiate de butée, ou combinaison de plusieurs
    indices forts (vitesse, compression gaz, effort déjà élevé).
    """
    if p.damper_core_solver not in {"auto", "auto_fast", "auto_precise"}:
        return p.damper_core_solver

    if p.damper_core_solver == "auto_fast":
        near_stop = d <= 0.004 * p.course or d >= 0.996 * p.course
        fast_motion = abs(v) >= 1.4
        gas_loaded = abs(pg_prev - p.Pinitbp) >= 10.0 * p.Pinitbp
        force_spike = abs(ftot_prev) >= 1.0 * (p.St * p.Pinitbp)
        score = int(near_stop) + int(fast_motion) + int(gas_loaded) + int(force_spike)
        if near_stop or score >= 3:
            return "implicit_adaptive"
        return "legacy"

    if p.damper_core_solver == "auto_precise":
        return "implicit_adaptive"

    near_stop = d <= 0.005 * p.course or d >= 0.995 * p.course
    fast_motion = abs(v) >= 1.8
    gas_loaded = abs(pg_prev - p.Pinitbp) >= 12.0 * p.Pinitbp
    force_spike = abs(ftot_prev) >= 1.05 * (p.St * p.Pinitbp)

    score = int(near_stop) + int(fast_motion) + int(gas_loaded) + int(force_spike)
    if near_stop or score >= 3:
        return "implicit_adaptive"
    return "legacy"


def _damper_force_step_implicit_endpoint(
    p: TrailingArmParamsSI,
    gas: GasSpring,
    tab_pos: np.ndarray,
    tab_sec: np.ndarray,
    d: float,
    v: float,
    dt_local: float,
    delta_pc_prev: float,
    delta_pd_prev: float,
    pg_prev: float,
    gas_state_prev: tuple[float, float],
) -> tuple[dict[str, float], tuple[float, float]]:
    """Sous-pas implicite local (évaluation en fin de sous-pas)."""
    # Point fixe léger sur la pression tampon de gaz (stabilisation locale).
    pg_guess = pg_prev
    for _ in range(4):
        _set_gas_state(gas, gas_state_prev)
        pg_new = gas.pressure(d, pg_guess)
        scale = max(1.0, abs(pg_new))
        if abs(pg_new - pg_guess) <= 1.0e-7 * scale:
            pg_guess = pg_new
            break
        pg_guess = 0.5 * (pg_new + pg_guess)

    _set_gas_state(gas, gas_state_prev)
    step = damper_force_step(
        p,
        gas,
        tab_pos,
        tab_sec,
        d,
        v,
        delta_pc_prev,
        delta_pd_prev,
        pg_guess,
        dt=dt_local,
    )
    return step, _gas_state(gas)


def damper_force_step_implicit_adaptive(
    p: TrailingArmParamsSI,
    gas: GasSpring,
    tab_pos: np.ndarray,
    tab_sec: np.ndarray,
    d_start: float,
    v_start: float,
    d_end: float,
    v_end: float,
    delta_pc_prev: float,
    delta_pd_prev: float,
    pg_prev: float,
    min_h: float = 1.0 / 64.0,
    auto_fast_mode: bool = False,
    implicit_dt_scale: float = 1.0,
) -> dict[str, float]:
    """Chemin implicite/adaptatif sur le noyau gaz+hydraulique.

    On avance par sous-pas adaptatifs sur [0, 1] en utilisant une estimation
    d'erreur par comparaison 1 sous-pas vs 2 demi-sous-pas, puis on accepte la
    solution raffinée (deux demi-sous-pas) quand l'erreur est sous seuil.
    """
    if auto_fast_mode:
        gas_state = _gas_state(gas)
        step, gas_end = _damper_force_step_implicit_endpoint(
            p,
            gas,
            tab_pos,
            tab_sec,
            d_end,
            v_end,
            p.it * implicit_dt_scale,
            delta_pc_prev,
            delta_pd_prev,
            pg_prev,
            gas_state,
        )
        _set_gas_state(gas, gas_end)
        return step

    tol_rel = 0.02
    max_substeps = 256

    tau = 0.0
    h = 0.5
    substeps = 0

    delta_pc_state = delta_pc_prev
    delta_pd_state = delta_pd_prev
    pg_state = pg_prev
    gas_state = _gas_state(gas)
    last_step: dict[str, float] | None = None

    d_span = d_end - d_start
    v_span = v_end - v_start

    while tau < 1.0 and substeps < max_substeps:
        h = min(h, 1.0 - tau)
        dt_local = h * p.it

        seg_delta_pc = delta_pc_state
        seg_delta_pd = delta_pd_state
        seg_pg = pg_state
        seg_gas = gas_state

        tau_mid = tau + 0.5 * h
        tau_end = tau + h
        d_mid = d_start + tau_mid * d_span
        v_mid = v_start + tau_mid * v_span
        d_seg_end = d_start + tau_end * d_span
        v_seg_end = v_start + tau_end * v_span

        # Chemin A: un seul sous-pas.
        one_step, _ = _damper_force_step_implicit_endpoint(
            p,
            gas,
            tab_pos,
            tab_sec,
            d_seg_end,
            v_seg_end,
            dt_local,
            seg_delta_pc,
            seg_delta_pd,
            seg_pg,
            seg_gas,
        )

        # Chemin B: deux demi-sous-pas (solution retenue quand acceptée).
        half_1, gas_half = _damper_force_step_implicit_endpoint(
            p,
            gas,
            tab_pos,
            tab_sec,
            d_mid,
            v_mid,
            0.5 * dt_local,
            seg_delta_pc,
            seg_delta_pd,
            seg_pg,
            seg_gas,
        )
        half_2, gas_end = _damper_force_step_implicit_endpoint(
            p,
            gas,
            tab_pos,
            tab_sec,
            d_seg_end,
            v_seg_end,
            0.5 * dt_local,
            half_1["delta_pc"],
            half_1["delta_pd"],
            half_1["pg"],
            gas_half,
        )

        # Estimateur d'erreur relatif sur l'effort total (grandeur pilotante).
        scale = max(1.0, abs(one_step["ftot"]), abs(half_2["ftot"]))
        err_rel = abs(half_2["ftot"] - one_step["ftot"]) / scale

        if err_rel <= tol_rel or h <= min_h:
            tau = tau_end
            delta_pc_state = half_2["delta_pc"]
            delta_pd_state = half_2["delta_pd"]
            pg_state = half_2["pg"]
            gas_state = gas_end
            last_step = half_2
            if err_rel < 0.3 * tol_rel:
                h = min(1.0 - tau, h * 1.5)
        else:
            h *= 0.5

        substeps += 1

    if last_step is None:
        _set_gas_state(gas, gas_state)
        return damper_force_step(
            p,
            gas,
            tab_pos,
            tab_sec,
            d_end,
            v_end,
            delta_pc_prev,
            delta_pd_prev,
            pg_prev,
            dt=p.it,
        )

    _set_gas_state(gas, gas_state)
    return last_step


def run_trailing_arm(
    p: TrailingArmParamsSI,
    collector: ErrorCollector | None = None,
    section_override: tuple[np.ndarray, np.ndarray] | None = None,
    progress_callback: callable | None = None,
) -> EngineOutput:
    """Exécute la simulation de drop test du train à balancier.

    ``section_override`` permet d'imposer une table de section ``(tab_pos, tab_sec)``
    (en m et m²) à la place de celle recalculée par :func:`build_section_table`.
    Réservé à la validation (comparaison avec une référence Excel mise en cache).
    
    ``progress_callback`` est une fonction optionnelle appelée à chaque itération
    avec (étape_courante, nombre_total_étapes) pour afficher la progression.
    """
    c = collector or ErrorCollector()

    # --- Préparation (équivalent RecupData / CalculBH) -------------------- #
    gas = GasSpring(p)
    if section_override is not None:
        tab_pos, tab_sec = section_override
    else:
        tab_pos, tab_sec = build_section_table(p)
    tyre_defl, tyre_load = build_tyre_tables(p)
    mu_x, mu_y = p.mu_x, p.mu_y

    B = p.B.astype(float).copy()
    A = p.A.astype(float).copy()
    C = p.C.astype(float).copy()
    R = p.R.astype(float).copy()

    entraxe_init = float(np.linalg.norm(C - A))
    lg_ab = math.hypot(B[0] - A[0], B[2] - A[2])  # rayon planaire (X-Z) du bras B-A
    lg_rb = math.hypot(B[0] - R[0], B[2] - R[2])
    lg_ra = math.hypot(A[0] - R[0], A[2] - R[2])

    # Attitude (pitch/roll) : rotation RIGIDE de tout le train autour du point
    # de contact au sol S (et non autour de l'origine du repère avion, très
    # éloignée, ce qui déformait la géométrie). Le train pivote ainsi sur place.
    # Avec pitch = roll = 0, cette transformation est l'identité (cas validé).
    S = R.copy()
    S[2] = R[2] - p.unload_radius  # point de contact initial (sous la roue)
    A = rotate_about(A, S, p.pitch, p.roll)
    B = rotate_about(B, S, p.pitch, p.roll)
    C = rotate_about(C, S, p.pitch, p.roll)
    R = rotate_about(R, S, p.pitch, p.roll)
    S = R.copy()
    S[2] = R[2] - p.unload_radius  # contact recalculé sous la roue pivotée
    pms_rlg_z = float(chgt_rep(np.array([0.0, 0.0, p.masse * G * (1.0 - p.lift)]), p.pitch, p.roll)[2])

    # Écart en Y entre C (sur la masse suspendue) et A (sur le balancier). Constant
    # pendant la simulation : il rend l'amortisseur oblique et réduit la part de son
    # effort qui entraîne le balancier (projection 3D sur le plan X-Z).
    dy_ca = float(C[1] - A[1])

    Ms = p.masse
    Jyy = p.jyy
    Vx = p.vx
    Vitesse = p.vz
    fast_time_scale = 1.8 if p.damper_core_solver == "auto_fast" else 1.0
    It = p.it * fast_time_scale
    integrator_mode = "euler" if p.damper_core_solver == "auto_fast" else p.integrator

    if c.check(
        not (entraxe_init > 0),
        code="ENTRAXE_NUL",
        message="L'entraxe initial de l'amortisseur est nul (points A et C confondus).",
        level=ErrorLevel.PRECALCUL,
        hint="Vérifier les coordonnées des points A et C.",
    ):
        c.raise_if_any()

    if c.check(
        not (entraxe_init > abs(dy_ca)),
        code="AMORTISSEUR_TROP_COURT",
        message="La longueur d'amortisseur est inférieure à l'écart en Y entre A et C "
        "(amortisseur géométriquement impossible).",
        level=ErrorLevel.PRECALCUL,
        hint="Augmenter la distance A-C ou réduire l'écart en Y entre A et C.",
    ):
        c.raise_if_any()

    # --- Stabilisation statique ------------------------------------------- #
    pgtamp = p.Pinitbp
    d = 0.0
    stabilized = False
    for _ in range(100000):
        d -= 1.0e-8
        pg = gas.pressure(d, pgtamp)
        ftot = p.St * pg + _endstop(
            d,
            p.course,
            smooth_len=p.endstop_smooth,
        )  # v = 0 → ΔP = 0, FFriJoi = 0
        if abs(ftot) < 1.0:
            stabilized = True
            break
    if not stabilized:
        c.warn(
            SimError(
                code="STABILISATION_NON_CONVERGEE",
                message="La stabilisation statique initiale n'a pas convergé en 100000 itérations.",
                level=ErrorLevel.RUNTIME,
                hint="Vérifier la pression de gaz et la géométrie de l'amortisseur.",
            )
        )

    entraxe = entraxe_init - d
    deter_pos_bal_a(A, B, C, entraxe, lg_ab)
    deter_pos_bal_r(R, A, B, lg_ra, lg_rb)
    th_ry = math.atan((R[0] - B[0]) / (R[2] - B[2]))
    th_ay = math.atan((A[0] - B[0]) / (A[2] - B[2]))

    # --- État initial de la boucle ---------------------------------------- #
    n_it = int(p.temps_simu / It)  # RoundDown
    n_out = n_it + 1

    out = {k: np.zeros(n_out) for k in OUTPUT_COLUMNS}
    geom = {k: np.zeros(n_out) for k in GEOMETRY_KEYS}
    ground_z = float(S[2])  # niveau du sol (fixe dans le repère train)

    state = TrailingArmLocalState(
        A=A,
        B=B,
        C=C,
        R=R,
        S=S,
        accms=0.0,
        vitms=-Vitesse,
        depms=0.0,
        ta_x=0.0,
        ta_y=0.0,
        ta_z=0.0,
        tb_x=0.0,
        tb_y=0.0,
        tb_z=0.0,
        tr_x=0.0,
        tr_y=0.0,
        tr_z=0.0,
        al_y=0.0,
        om_y=0.0,
        omega=0.0,
        alpha=0.0,
        vitx=0.0,
        depx=0.0,
        defl=0.0,
        delta_pc=0.0,
        delta_pd=0.0,
        qc_total=0.0,
        qc_bh=0.0,
        qc_leak=0.0,
        leak_ratio=0.0,
        re_leak=0.0,
        hyd_conv_err=0.0,
        hyd_conv_iter=0.0,
        pg_prev=pg,
        ftot=p.St * pg,
        v_prev=0.0,
        entraxe=entraxe,
        th_ay=th_ay,
        th_ry=th_ry,
        d=0.0,
        v=0.0,
    )

    # --- Accumulateurs du bilan énergétique (diagnostic) ------------------ #
    # Énergie cinétique initiale d'impact de la masse suspendue ; sert de
    # référence pour le résidu. La gravité et le spin-up ajoutent un travail au
    # fil du temps.
    e_kin_init = 0.5 * Ms * state.vitms * state.vitms
    e_gas_acc = 0.0       # travail réversible du gaz (∑ Fgas·dd)
    e_tyre_acc = 0.0      # énergie élastique stockée dans le pneu (∑ Ftyre·d(defl))
    e_hyd_acc = 0.0       # dissipation hydraulique (∑ |Fhyd·v|·dt)
    e_fric_acc = 0.0      # dissipation friction joint (∑ |Ffrijoi·v|·dt)
    e_damp_x_acc = 0.0    # dissipation amortisseur horizontal (∑ cx·vitx²·dt)
    e_endstop_acc = 0.0   # énergie emmagasinée en butée (∑ Fbutee·dd)
    e_grav_acc = 0.0      # travail de la gravité sur la masse suspendue
    e_fwd_acc = 0.0       # travail puisé dans l'énergie d'avancement (spin-up)
    e_slip_acc = 0.0      # chaleur dissipée par glissement au contact pneu/sol
    d_prev = 0.0          # course de l'amortisseur au pas précédent
    defl_prev = 0.0       # déflexion du pneu au pas précédent
    depms_prev = state.depms    # déplacement masse suspendue au pas précédent
    omega_prev = 0.0      # vitesse de rotation roue au pas précédent
    rx_prev = float(state.R[0])  # position horizontale du moyeu R au pas précédent
    fgas_prev = p.St * pg
    fhyd_prev = 0.0
    ffrijoi_prev = 0.0
    ftyre_prev = 0.0
    endstop_prev = _endstop(d_prev, p.course, smooth_len=p.endstop_smooth)
    tr_x_prev = 0.0
    fspin_prev = 0.0
    vitx_prev = state.vitx

    n_steps = n_it
    bottomed = None  # (i_fail, exc) si l'amortisseur atteint sa butée de compression
    for i in range(n_out):
        # Appel au callback de progression
        if progress_callback:
            progress_callback(i + 1, n_out)

        try:
            # Dynamique de la masse suspendue (TA/TB du pas précédent)
            support_accms = (1.0 / Ms) * (-state.ta_z - state.tb_z - pms_rlg_z)
            support_depms, support_vitms = _integrate_const_acc(
                state.depms,
                state.vitms,
                support_accms,
                It,
                integrator_mode,
            )
            dz = support_depms - state.depms
            step = _trailing_arm_local_step(
                p,
                gas,
                tab_pos,
                tab_sec,
                tyre_defl,
                tyre_load,
                mu_x,
                mu_y,
                state,
                support_dz=dz,
                support_vitms=support_vitms,
                support_accms=support_accms,
                entraxe_init=entraxe_init,
                lg_ab=lg_ab,
                lg_rb=lg_rb,
                dy_ca=dy_ca,
                fast_time_scale=fast_time_scale,
                integrator_mode=integrator_mode,
                It=It,
            )
            pg = step["pg"]
            pc = step["pc"]
            pd = step["pd"]
            fgas = step["fgas"]
            ffrijoi = step["ffrijoi"]
            fhyd = step["fhyd"]
            ftyre = step["ftyre"]
            slip = step["slip"]
            mu_val = step["mu_val"]
            fspin = step["fspin"]
            fc_x = step["fc_x"]
            fc_y = step["fc_y"]
            fc_z = step["fc_z"]
            fb_x = step["fb_x"]
            fb_y = step["fb_y"]
            fb_z = step["fb_z"]
            res_x = step["res_x"]
            res_y = step["res_y"]
            res_z = step["res_z"]
            res_norm = step["res_norm"]
            mb_x = step["mb_x"]
            mb_z = step["mb_z"]

            accms = state.accms
            vitms = state.vitms
            depms = state.depms
            ta_x = state.ta_x
            ta_y = state.ta_y
            ta_z = state.ta_z
            tb_x = state.tb_x
            tb_y = state.tb_y
            tb_z = state.tb_z
            tr_x = state.tr_x
            tr_y = state.tr_y
            tr_z = state.tr_z
            al_y = state.al_y
            om_y = state.om_y
            omega = state.omega
            alpha = state.alpha
            vitx = state.vitx
            depx = state.depx
            defl = state.defl
            delta_pc = state.delta_pc
            delta_pd = state.delta_pd
            qc_total = state.qc_total
            qc_bh = state.qc_bh
            qc_leak = state.qc_leak
            leak_ratio = state.leak_ratio
            re_leak = state.re_leak
            hyd_conv_err = state.hyd_conv_err
            hyd_conv_iter = state.hyd_conv_iter
            pg_prev = state.pg_prev
            ftot = state.ftot
            v_prev = state.v_prev
            entraxe = state.entraxe
            th_ay = state.th_ay
            th_ry = state.th_ry
            d = state.d
            v = state.v
            sec = state.sec
            A = state.A
            B = state.B
            C = state.C
            R = state.R
            S = state.S

        except SimError as err:
            err.context.setdefault("iteration", i)
            err.context.setdefault("temps_s", i * It)
            if err.code in OVERSTROKE_CODES:
                bottomed = (i, err)
                break
            raise

        if not math.isfinite(ftot) or not math.isfinite(pg):
            raise SimError(
                code="DIVERGENCE_NUMERIQUE",
                message="La simulation a divergé (valeur non finie) — résultat inexploitable.",
                level=ErrorLevel.RUNTIME,
                hint="Réduire le pas de temps ou vérifier les paramètres (gaz, hydraulique, pneu).",
                context={"iteration": i, "temps_s": i * It},
            )

        # --- Bilan énergétique (diagnostic, purement passif) -------------- #
        # Bilan COMPLET du système, cohérent avec les ÉQUATIONS DISCRÈTES du
        # modèle (théorème de l'énergie cinétique appliqué à chaque DDL), de
        # sorte que le résidu ne reflète que l'erreur d'intégration (Euler).
        # Travaux incrémentaux le long de la course (dd), de la déflexion et du
        # temps (dt) :
        #   - stockés : gaz, pneu vertical, ressort horizontal, butée ;
        #   - dissipés : hydraulique, friction joint, amortisseur horizontal ;
        #   - apports : gravité + travail de la friction de contact puisé dans
        #     l'énergie d'avancement (qui lance la roue et la freine au sol).
        dd = d - d_prev
        endstop_cur = _endstop(d, p.course, smooth_len=p.endstop_smooth)
        ddefl = defl - defl_prev
        if p.integrator == "rk4":
            e_gas_acc += 0.5 * (fgas_prev + fgas) * dd
            e_endstop_acc += 0.5 * (endstop_prev + endstop_cur) * dd
            e_tyre_acc += 0.5 * (ftyre_prev + ftyre) * ddefl
        else:
            e_gas_acc += fgas * dd
            e_endstop_acc += endstop_cur * dd
            e_tyre_acc += ftyre * ddefl
        # Dissipations de l'amortisseur : on utilise le travail SIGNÉ de chaque
        # composante d'effort le long de la course (F·dd) et non |F·v|·dt. Comme
        # l'effort total se décompose en Ftot = Fgas + Fhyd + Ffrijoi + Fbutée,
        # la somme des travaux se télescope EXACTEMENT avec le travail de la
        # réaction d'amortisseur sur les corps (→ résidu = simple erreur Euler).
        # Le léger retard (lag) du calcul de ΔP rendrait |Fhyd·v|·dt ≠ −Fhyd·dd.
        if p.integrator == "rk4":
            e_hyd_acc += 0.5 * (fhyd_prev + fhyd) * dd
            e_fric_acc += 0.5 * (ffrijoi_prev + ffrijoi) * dd
        else:
            e_hyd_acc += fhyd * dd
            e_fric_acc += ffrijoi * dd
        # Amortisseur horizontal du pneu (spring-back) : Pdiss = cx·vitx².
        if p.integrator == "rk4":
            e_damp_x_acc += 0.5 * p.cx * (vitx_prev * vitx_prev + vitx * vitx) * It
        else:
            e_damp_x_acc += p.cx * vitx * vitx * It
        # Énergie d'avancement et glissement au contact pneu/sol.
        #   • Apport : la friction de contact Fspin puise dans l'énergie
        #     d'avancement de l'aéronef à la VITESSE SOL Vx (puissance Fspin·Vx).
        #   • Cette énergie se répartit en quatre parts :
        #       – gain d'énergie cinétique de rotation de la roue ΔEc_rot,
        #       – travail sur la translation propre de la roue (Fspin·vitx),
        #       – travail de l'effort longitudinal tr_x sur le moyeu R lorsque
        #         le balancier pivote (tr_x·vR_x) : l'effort de contact pousse
        #         le moyeu horizontalement et injecte ainsi de l'énergie dans le
        #         mécanisme (balancier → amortisseur → masse suspendue),
        #       – chaleur dissipée par glissement au contact (le reste).
        # On évalue ΔEc_rot par sa variation EXACTE ½J(ω²−ω₀²) plutôt que par
        # Fspin·(R0−δ)·ω·It : le couple de spin-up étant quasi-impulsionnel
        # (α≫1), seule la variation exacte se referme avec le réservoir
        # cinétique Ec_rot, sinon le résidu garde une erreur O(It²) constante.
        # En définissant ainsi e_slip = Fspin·(Vx−vitx)·It − ΔEc_rot − tr_x·vR_x·It,
        # le bilan du chemin d'avancement se ferme par construction.
        vr_x = (R[0] - rx_prev) / It
        dke_spin = 0.5 * p.wheel_inertia * (omega * omega - omega_prev * omega_prev)
        if p.integrator == "rk4":
            fspin_avg = 0.5 * (fspin_prev + fspin)
            tr_x_avg = 0.5 * (tr_x_prev + tr_x)
            vitx_avg = 0.5 * (vitx_prev + vitx)
            e_fwd_acc += fspin_avg * Vx * It
            e_slip_acc += fspin_avg * (Vx - vitx_avg) * It - dke_spin - tr_x_avg * vr_x * It
        else:
            e_fwd_acc += fspin * Vx * It
            e_slip_acc += fspin * (Vx - vitx) * It - dke_spin - tr_x * vr_x * It
        # Poids (le long de Z, dirigé vers le bas) × déplacement de la masse.
        e_grav_acc += -pms_rlg_z * (depms - depms_prev)
        d_prev = d
        v_prev = v
        defl_prev = defl
        depms_prev = depms
        omega_prev = omega
        rx_prev = float(R[0])
        fgas_prev = fgas
        fhyd_prev = fhyd
        ffrijoi_prev = ffrijoi
        ftyre_prev = ftyre
        endstop_prev = endstop_cur
        tr_x_prev = tr_x
        fspin_prev = fspin
        vitx_prev = vitx

        # Réservoirs cinétiques courants.
        e_kin = 0.5 * Ms * vitms * vitms
        e_kin_bal = 0.5 * Jyy * om_y * om_y
        e_kin_spin = 0.5 * p.wheel_inertia * omega * omega
        e_kin_horiz = 0.5 * p.wheelmass * vitx * vitx
        e_spring_x = 0.5 * p.kx * depx * depx

        e_input = e_kin_init + e_grav_acc + e_fwd_acc
        e_residual = e_input - (
            e_kin + e_kin_bal + e_kin_spin + e_kin_horiz
            + e_gas_acc + e_tyre_acc + e_spring_x + e_endstop_acc
            + e_hyd_acc + e_fric_acc + e_damp_x_acc + e_slip_acc
        )

        # Enregistrement
        out["temps"][i] = i * It
        out["accms"][i] = accms
        out["vitms"][i] = vitms
        out["depms"][i] = depms
        out["aly"][i] = al_y
        out["omy"][i] = om_y
        out["thay"][i] = th_ay
        out["thry"][i] = th_ry
        out["tyre_defl"][i] = defl
        out["tyre_ftyre"][i] = ftyre
        out["trailing_arm_v"][i] = v
        out["trailing_arm_d"][i] = d
        out["trailing_arm_ftot"][i] = ftot
        out["trailing_arm_fhyd"][i] = fhyd
        out["trailing_arm_ffrijoi"][i] = ffrijoi
        out["trailing_arm_fgas"][i] = fgas
        out["ta_z"][i] = -ta_z
        out["ta_x"][i] = -ta_x
        out["entraxe"][i] = entraxe
        out["secbh"][i] = sec * 1.0e6
        out["course_roue"][i] = R[2] - B[2]
        out["tyre_alpha"][i] = alpha
        out["tyre_omega"][i] = omega
        out["tr_x"][i] = tr_x
        out["tyre_mu"][i] = mu_val
        out["tyre_slip"][i] = slip
        out["pc"][i] = pc * 1.0e-5
        out["pd"][i] = pd * 1.0e-5
        out["pg"][i] = pg * 1.0e-5
        out["delta_pc"][i] = delta_pc * 1.0e-5
        out["delta_pd"][i] = delta_pd * 1.0e-5
        out["hyd_qc_total"][i] = qc_total
        out["hyd_qc_bh"][i] = qc_bh
        out["hyd_qc_leak"][i] = qc_leak
        out["hyd_leak_ratio"][i] = leak_ratio
        out["hyd_re_leak"][i] = re_leak
        out["hyd_conv_err"][i] = hyd_conv_err
        out["hyd_conv_iter"][i] = hyd_conv_iter
        out["reaction_v"][i] = ftyre
        out["reaction_h"][i] = tr_x

        # Torseur d'effort transmis à la masse suspendue (réduit en B et en C)
        out["tors_res_x"][i] = res_x
        out["tors_res_y"][i] = res_y
        out["tors_res_z"][i] = res_z
        out["tors_res_norm"][i] = res_norm
        out["torsC_fx"][i] = fc_x
        out["torsC_fy"][i] = fc_y
        out["torsC_fz"][i] = fc_z
        out["torsB_fx"][i] = fb_x
        out["torsB_fy"][i] = fb_y
        out["torsB_fz"][i] = fb_z
        out["torsB_mx"][i] = mb_x
        out["torsB_mz"][i] = mb_z

        # Bilan énergétique (diagnostic)
        out["e_kin"][i] = e_kin
        out["e_kin_bal"][i] = e_kin_bal
        out["e_kin_spin"][i] = e_kin_spin
        out["e_kin_horiz"][i] = e_kin_horiz
        out["e_gas"][i] = e_gas_acc
        out["e_tyre"][i] = e_tyre_acc
        out["e_spring_x"][i] = e_spring_x
        out["e_hyd"][i] = e_hyd_acc
        out["e_fric"][i] = e_fric_acc
        out["e_damp_x"][i] = e_damp_x_acc
        out["e_slip"][i] = e_slip_acc
        out["e_endstop"][i] = e_endstop_acc
        out["e_input"][i] = e_input
        out["e_residual"][i] = e_residual

        # Positions géométriques (mm) pour l'animation
        geom["ax"][i] = A[0]
        geom["az"][i] = A[2]
        geom["bx"][i] = B[0]
        geom["bz"][i] = B[2]
        geom["cx"][i] = C[0]
        geom["cz"][i] = C[2]
        geom["rx"][i] = R[0]
        geom["rz"][i] = R[2]
        geom["ground_z"][i] = ground_z
        geom["wheel_radius"][i] = R[2] - ground_z

        # Arrêt anticipé (cf. VBA : remontée de l'amortisseur en fin de course)
        if v < 0.0 and i > 900000:
            n_steps = i
            for k in out:
                out[k] = out[k][: i + 1]
            for k in geom:
                geom[k] = geom[k][: i + 1]
            break

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
        warnings.append(make_overstroke_warning("le train (TrailingArm)", valid * It, last_stroke, course, exc))

    return EngineOutput(data=out, n_steps=n_steps, warnings=warnings, geometry=geom)

__all__ = ["run_trailing_arm", "EngineOutput", "OUTPUT_COLUMNS", "GEOMETRY_KEYS"]
