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

from .errors import ErrorCollector, ErrorLevel, SimError
from .gas import GasSpring
from .geometry import chgt_rep, deter_pos_bal_a, deter_pos_bal_r
from .hydraulic import _sign, calcul_hydrau
from .inputs import MLGParamsSI
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
    "mlg_v": "MLG.v (m/s)",
    "mlg_d": "MLG.d (m)",
    "mlg_ftot": "MLG.Ftot (N)",
    "mlg_fhyd": "MLG.Fhyd (N)",
    "mlg_ffrijoi": "MLG.FFriJoi (N)",
    "mlg_fgas": "MLG.FGas (N)",
    "ta_z": "TA_bal.RsolZ (N)",
    "ta_x": "TA_bal.RsolX (N)",
    "entraxe": "MLG.Entraxe (m)",
    "secbh": "Section de la BH (mm²)",
    "course_roue": "Course centre roue (m)",
    "tyre_alpha": "Tyre.Alpha (rad/s²)",
    "tyre_omega": "Tyre.Omega (rad/s)",
    "tr_x": "TR_bal.RsolX (N)",
    "tyre_mu": "Tyre.Mu",
    "tyre_slip": "Tyre.Slip",
    "pc": "MLG.Pc (bar)",
    "pd": "MLG.Pd (bar)",
    "pg": "MLG.Pg (bar)",
    "delta_pc": "MLG.DeltaPc (bar)",
    "delta_pd": "MLG.DeltaPd (bar)",
    "reaction_v": "Reaction sol verticale (N)",
    "reaction_h": "Reaction sol horizontale (N)",
}


@dataclass
class EngineOutput:
    """Résultats bruts du moteur (séries temporelles SI + bar pour les pressions)."""

    data: dict[str, np.ndarray]
    n_steps: int
    warnings: list[SimError] = field(default_factory=list)


def _endstop(d: float, course: float) -> float:
    """Effort de butée (raideur 1e8 N/m) hors de la plage [0, course]."""
    if d > course:
        return (d - course) * 1.0e8
    if d < 0.0:
        return d * 1.0e8
    return 0.0


def run_mlg(
    p: MLGParamsSI,
    collector: ErrorCollector | None = None,
    section_override: tuple[np.ndarray, np.ndarray] | None = None,
) -> EngineOutput:
    """Exécute la simulation de drop test du train à balancier.

    ``section_override`` permet d'imposer une table de section ``(tab_pos, tab_sec)``
    (en m et m²) à la place de celle recalculée par :func:`build_section_table`.
    Réservé à la validation (comparaison avec une référence Excel mise en cache).
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
    lg_ab = float(np.linalg.norm(B - A))
    lg_rb = math.hypot(B[0] - R[0], B[2] - R[2])
    lg_ra = math.hypot(A[0] - R[0], A[2] - R[2])

    # Changement de repère (pitch/roll) appliqué à A, C, R ; B reste inchangé.
    A = chgt_rep(A, p.pitch, p.roll)
    C = chgt_rep(C, p.pitch, p.roll)
    R = chgt_rep(R, p.pitch, p.roll)
    S = R.copy()
    S[2] = R[2] - p.unload_radius  # point de contact sol, dérivé de R

    pms_rlg_z = float(chgt_rep(np.array([0.0, 0.0, p.masse * G * (1.0 - p.lift)]), p.pitch, p.roll)[2])

    Ms = p.masse
    Jyy = p.jyy
    Vx = p.vx
    Vitesse = p.vz
    It = p.it

    if c.check(
        not (entraxe_init > 0),
        code="ENTRAXE_NUL",
        message="L'entraxe initial de l'amortisseur est nul (points A et C confondus).",
        level=ErrorLevel.PRECALCUL,
        hint="Vérifier les coordonnées des points A et C.",
    ):
        c.raise_if_any()

    # --- Stabilisation statique ------------------------------------------- #
    pgtamp = p.Pinitbp
    d = 0.0
    stabilized = False
    for _ in range(100000):
        d -= 1.0e-8
        pg = gas.pressure(d, pgtamp)
        ftot = p.St * pg + _endstop(d, p.course)  # v = 0 → ΔP = 0, FFriJoi = 0
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

    accms = 0.0
    vitms = -Vitesse
    depms = 0.0
    ta_x = ta_y = ta_z = 0.0
    tb_x = tb_y = tb_z = 0.0
    tr_x = tr_y = tr_z = 0.0
    al_y = om_y = 0.0
    omega = alpha = 0.0
    vitx = depx = 0.0
    defl = 0.0
    delta_pc = delta_pd = 0.0
    pg_prev = pg

    n_steps = n_it
    for i in range(n_out):
        try:
            # Dynamique de la masse suspendue (TA/TB du pas précédent)
            accms = (1.0 / Ms) * (-ta_z - tb_z - pms_rlg_z)
            vitms = vitms + accms * It
            depms = depms + vitms * It
            B[2] += vitms * It
            C[2] += vitms * It

            # Rotation du balancier
            al_y = (1.0 / Jyy) * (
                (A[2] - B[2]) * ta_x
                - (A[0] - B[0]) * ta_z
                + (R[2] - B[2]) * tr_x
                - (R[0] - B[0]) * tr_z
            )
            om_y = om_y + al_y * It
            th_ay = th_ay + om_y * It
            th_ry = th_ry + om_y * It

            # Position de R et écrasement du pneu
            R[0] = -lg_rb * math.sin(th_ry) + B[0]
            R[2] = -lg_rb * math.cos(th_ry) + B[2]
            defl = p.unload_radius - (R[2] - S[2])
            ftyre = f_tyre(defl, tyre_defl, tyre_load)
            tr_z = ftyre

            # Adhérence / spin-up / spring-back
            if Vx != 0.0:
                slip = (Vx - omega * r_eff(p.unload_radius, defl)) / abs(Vx)
            else:
                slip = 0.0
            mu_val = mu(slip, mu_x, mu_y)
            fspin = mu_val * tr_z * _sign(slip)
            fx_old = p.kx * depx + p.cx * vitx
            accx = (-fx_old + fspin) / p.wheelmass
            vitx = vitx + accx * It
            depx = depx + vitx * It
            tr_x = p.kx * depx + p.cx * vitx
            alpha = (fspin * (p.unload_radius - defl)) / p.wheel_inertia
            omega = omega + alpha * It

            # Position de A et cinématique de l'amortisseur
            A[0] = -lg_ab * math.sin(th_ay) + B[0]
            A[2] = -lg_ab * math.cos(th_ay) + B[2]
            dist_ca = math.sqrt(
                (C[0] - A[0]) ** 2 + (C[1] - A[1]) ** 2 + (C[2] - A[2]) ** 2
            )
            v = -(dist_ca - entraxe) / It
            entraxe = dist_ca
            d = entraxe_init - entraxe

            # Ressort gazeux + hydraulique
            pg = gas.pressure(d, pg_prev)
            sec = section_bh(d, tab_pos, tab_sec)
            if v != 0.0:
                delta_pc, delta_pd, _qc = calcul_hydrau(p, v, d, delta_pc, pg, sec)
            pc = pg + delta_pc
            pd = pc - delta_pd
            fgas = p.St * pg
            if v != 0.0:
                coeff_atte = 1.0 / math.sqrt(0.95 + 0.28 * math.sqrt(1.0 / (90.0 * abs(v))))
                ffrijoi = _sign(v) * 100.0 * coeff_atte
            else:
                ffrijoi = 0.0
            ftot = p.Sc * pc - p.Sd * pd + p.Sbh * pg + ffrijoi + _endstop(d, p.course)
            fhyd = p.Sc * (pc - pg) - p.Sd * (pd - pg)
            pg_prev = pg

            # Efforts dans l'amortisseur et le balancier (pour le pas suivant)
            ta_z = -ftot * ((C[2] - A[2]) / entraxe)
            ta_y = 0.0
            ta_x = -ftot * ((C[0] - A[0]) / entraxe)
            tb_x = -ta_x - tr_x
            tb_y = -ta_y - tr_y
            tb_z = -ta_z - tr_z

        except SimError as err:
            err.context.setdefault("iteration", i)
            err.context.setdefault("temps_s", i * It)
            raise

        if not math.isfinite(ftot) or not math.isfinite(pg):
            raise SimError(
                code="DIVERGENCE_NUMERIQUE",
                message="La simulation a divergé (valeur non finie) — résultat inexploitable.",
                level=ErrorLevel.RUNTIME,
                hint="Réduire le pas de temps ou vérifier les paramètres (gaz, hydraulique, pneu).",
                context={"iteration": i, "temps_s": i * It},
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
        out["mlg_v"][i] = v
        out["mlg_d"][i] = d
        out["mlg_ftot"][i] = ftot
        out["mlg_fhyd"][i] = fhyd
        out["mlg_ffrijoi"][i] = ffrijoi
        out["mlg_fgas"][i] = fgas
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
        out["reaction_v"][i] = ftyre
        out["reaction_h"][i] = tr_x

        # Arrêt anticipé (cf. VBA : remontée de l'amortisseur en fin de course)
        if v < 0.0 and i > 900000:
            n_steps = i
            for k in out:
                out[k] = out[k][: i + 1]
            break

    return EngineOutput(data=out, n_steps=n_steps, warnings=c.warnings)


__all__ = ["run_mlg", "EngineOutput", "OUTPUT_COLUMNS"]
