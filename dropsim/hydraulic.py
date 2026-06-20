"""Pertes de charge hydrauliques de l'amortisseur.

Reproduit la macro VBA ``CalculHydrau`` :

* En **compression** (Qc > 0), la perte de charge à travers la bague hydraulique
  est couplée à la compressibilité de l'huile via un Newton-Raphson sur (Pc, Qc).
* En **détente** (Qc ≤ 0), la perte de charge est calculée directement.
* Le côté détente combine les pertes à travers les trous du piston et du clapet,
  avec un coefficient de décharge ``Cd`` à deux régimes (laminaire / turbulent).
"""
from __future__ import annotations

import math

import numpy as np

from .errors import ErrorLevel, SimError
from .inputs import MLGParamsSI


def _sign(x: float) -> float:
    return float(np.sign(x))


def _cd(re_deq: float, s: float) -> float:
    """Coefficient de décharge à deux régimes (cf. corrélations du VBA)."""
    if re_deq <= 0.0:
        return 1.0e-9  # garde-fou ; ce cas n'arrive pas pour v ≠ 0
    if re_deq / s < 50.0:
        return (2.28 + 64.0 * s / re_deq) ** (-0.5)
    return (1.5 + 13.74 * (s / re_deq) ** 0.5) ** (-0.5)


def _flow_bh_from_dp(delta_p: float, rho: float, sec_bh: float, cd_bh: float) -> float:
    """Débit de la branche rainures BH à partir de ΔP (relation orifice)."""
    if sec_bh <= 0.0 or cd_bh <= 0.0 or rho <= 0.0:
        return 0.0
    return _sign(delta_p) * sec_bh * cd_bh * math.sqrt(2.0 * abs(delta_p) / rho)


def _eccentricity_factor(eccentricity: float, d_outer: float, d_inner: float) -> float:
    """Facteur correctif de Someya pour l'excentricité d'un anneau.

    Pour un jeu annulaire excentrique d'excentricité ``eccentricity`` (m),
    le débit réel est multiplié par ``(1 + 1.5 * eps_star**2)`` où
    ``eps_star = eccentricity / c_radial`` (rapport excentricité / jeu radial).
    ``eps_star`` est saturé à 1 (contact physique).

    - eps_star = 0 (concentrique) → facteur = 1 (aucune correction)
    - eps_star = 1 (contact)       → facteur = 2.5 (débit × 2.5 max)
    """
    c_radial = (d_inner - d_outer) / 2.0
    if c_radial <= 0.0 or eccentricity <= 0.0:
        return 1.0
    eps_star = min(eccentricity / c_radial, 1.0)
    return 1.0 + 1.5 * eps_star ** 2


def _flow_annular_hagen(
    delta_p: float,
    mu: float,
    length: float,
    d_outer: float,
    d_inner: float,
    eccentricity: float = 0.0,
) -> float:
    """Débit laminaire dans un anneau concentrique (Hagen-Poiseuille), avec
    correction d'excentricité de Someya (``eccentricity`` en m, 0 = concentrique)."""
    if mu <= 0.0 or length <= 0.0 or d_inner <= d_outer:
        return 0.0
    r1 = 0.5 * d_outer
    r2 = 0.5 * d_inner
    if r1 <= 0.0 or r2 <= r1:
        return 0.0
    log_ratio = math.log(r2 / r1)
    if log_ratio <= 0.0:
        return 0.0
    geom = r2**4 - r1**4 - ((r2**2 - r1**2) ** 2) / log_ratio
    if geom <= 0.0:
        return 0.0
    q_conc = (math.pi * delta_p * geom) / (8.0 * mu * length)
    return q_conc * _eccentricity_factor(eccentricity, d_outer, d_inner)


def _flow_annular_with_turbulence(
    delta_p: float,
    rho: float,
    visc_kin: float,
    length: float,
    d_outer: float,
    d_inner: float,
    eccentricity: float = 0.0,
    n_iter: int = 8,
) -> tuple[float, float]:
    """Débit dans la fuite annulaire avec extension turbulente (Darcy-Weisbach)
    et correction d'excentricité.

    Retourne ``(q_leak, re_leak)`` où ``q_leak`` garde le signe de ``delta_p``.
    """
    if rho <= 0.0 or visc_kin <= 0.0:
        return 0.0, 0.0
    if length <= 0.0 or d_inner <= d_outer:
        return 0.0, 0.0

    mu_dyn = rho * visc_kin
    area = math.pi * (d_inner * d_inner - d_outer * d_outer) / 4.0
    dh = d_inner - d_outer
    if area <= 0.0 or dh <= 0.0:
        return 0.0, 0.0

    ecc_factor = _eccentricity_factor(eccentricity, d_outer, d_inner)
    q_lam = _flow_annular_hagen(delta_p, mu_dyn, length, d_outer, d_inner, eccentricity)
    v_lam = abs(q_lam) / area if area > 0.0 else 0.0
    re_lam = rho * v_lam * dh / mu_dyn if mu_dyn > 0.0 else 0.0

    # Laminaire pur : on garde la loi analytique de Hagen-Poiseuille.
    if re_lam <= 2000.0:
        return q_lam, re_lam

    # Branche turbulente : inversion de Darcy-Weisbach par itération fixe sur Re,
    # puis application du facteur d'excentricité (valable aussi en turbulent).
    q_abs = max(abs(q_lam), 1.0e-12)
    for _ in range(n_iter):
        v = q_abs / area
        re = rho * v * dh / mu_dyn
        if re <= 1.0:
            f = 64.0
        else:
            # Blasius pour conduite hydrauliquement lisse.
            f = 0.3164 * re ** (-0.25)
        q_abs = area * math.sqrt(max(0.0, 2.0 * abs(delta_p) * dh / (rho * f * length))) * ecc_factor

    q_turb = _sign(delta_p) * q_abs
    v_turb = q_abs / area
    re_turb = rho * v_turb * dh / mu_dyn if mu_dyn > 0.0 else 0.0

    # Zone transitoire : interpolation continue entre laminaire et turbulent.
    if re_lam < 4000.0:
        w = (re_lam - 2000.0) / 2000.0
        q_mix = (1.0 - w) * q_lam + w * q_turb
        re_mix = (1.0 - w) * re_lam + w * re_turb
        return q_mix, re_mix

    return q_turb, re_turb


def calcul_hydrau(
    p: MLGParamsSI,
    v: float,
    d: float,
    delta_pc_prev: float,
    pg: float,
    sec_bh: float,
    dt: float | None = None,
    n_iter: int = 64,
    adaptive_newton: bool = False,
    metrics: dict[str, float] | None = None,
) -> tuple[float, float, float, float, float, float]:
    """Calcule (ΔPc, ΔPd, Qc_total, Qc_rainures, Qc_fuite, Re_fuite).

    Parameters
    ----------
    delta_pc_prev : float
        Perte de charge de compression ΔPc du pas précédent (Pa). Le VBA conserve
        ``mDeltaPc`` d'un pas à l'autre ; il est réinjecté ici car la propriété
        ``MLG.Pc = Pg + mDeltaPc`` sert de référence (évolutive) au terme de
        compressibilité du Newton-Raphson.
    pg : float
        Pression de gaz courante (Pa).
    sec_bh : float
        Section ouverte de la bague hydraulique à la course ``d`` (m²).

    Notes
    -----
    Le solveur applique un contrôle de convergence direct sur l'erreur
    résiduelle ``err`` avec la cible absolue ``hydraulic_error_tol``.
    """
    rho = p.rho
    visc = p.visc
    dt_eff = p.it if dt is None else dt

    if sec_bh <= 0.0:
        raise SimError(
            code="SECTION_BH_NULLE",
            message="La section de la bague hydraulique est nulle ou négative à cette course.",
            level=ErrorLevel.RUNTIME,
            hint="Vérifier la définition des rainures (début/fin/profondeur) et la course.",
            context={"course_m": d},
        )

    qc_total = p.Sc * v
    deq_bh = math.sqrt(math.pi * sec_bh / 4.0)
    re_bh = (abs(qc_total) * deq_bh / sec_bh) / visc
    cd_bh = _cd(re_bh * deq_bh, 0.003)
    q_bh = qc_total
    q_leak = 0.0
    re_leak = 0.0

    # --- Compression : couplage avec la compressibilité de l'huile -------- #
    if qc_total > 0.0:
        coupl = p.Sc * (p.course - d) / (p.bulk * dt_eff)
        m_delta_pc = delta_pc_prev          # mDeltaPc persistant du pas précédent
        x0 = pg + m_delta_pc                 # xRes(0) = MLG.Pc à l'entrée
        x1 = qc_total                        # xRes(1) = MLG.Qc = Sc·v
        leak_enabled = p.DInsidePalierBh > p.Dbh and p.LPalierBh > 0.0
        max_iter = max(4, int(n_iter)) if adaptive_newton else 4
        min_iter = min(2, max_iter)
        target_err = max(1.0e-14, float(getattr(p, "hydraulic_error_tol", 1.0e-1)))
        iterations_used = 0

        if not leak_enabled:
            # Mode historique : strictement identique au modèle existant.
            inv_scd2 = (1.0 / (sec_bh * cd_bh)) ** 2
            err_now = None

            def _residual_error(x0_val: float, x1_val: float, m_delta_pc_val: float) -> float:
                pc_ref_val = pg + m_delta_pc_val
                f0_val = x1_val - p.Sc * v + coupl * (x0_val - pc_ref_val)
                f1_val = (x0_val - pg) - 0.5 * rho * (x1_val ** 2) * inv_scd2 * _sign(x1_val)
                err0 = abs(f0_val) / max(abs(p.Sc * v), 1.0e-12)
                err1 = abs(f1_val) / max(abs(x0_val - pg), 1.0)
                return max(err0, err1)

            for it_idx in range(max_iter):
                pc_ref = pg + m_delta_pc
                f0 = x1 - p.Sc * v + coupl * (x0 - pc_ref)
                f1 = (x0 - pg) - 0.5 * rho * (x1 ** 2) * inv_scd2 * _sign(x1)
                j11 = -x1 * rho * inv_scd2 * _sign(x1)
                det = coupl * j11 - 1.0
                if det == 0.0:
                    raise SimError(
                        code="HYDRAU_JACOBIEN_SINGULIER",
                        message="Le jacobien du solveur hydraulique est singulier (déterminant nul).",
                        level=ErrorLevel.RUNTIME,
                        hint="Réduire le pas de temps ou vérifier la section de bague hydraulique.",
                    )
                dx0 = (j11 * f0 - 1.0 * f1) / det
                dx1 = (coupl * f1 - 1.0 * f0) / det
                x0 -= dx0
                x1 -= dx1
                m_delta_pc = x0 - pg
                iterations_used = it_idx + 1
                err_now = _residual_error(x0, x1, m_delta_pc)
                if adaptive_newton and it_idx + 1 >= min_iter and err_now is not None and err_now <= target_err:
                        break

            if metrics is not None:
                metrics["target_err"] = float(target_err)
                if err_now is not None:
                    metrics["final_err"] = float(err_now)
                metrics["iterations_used"] = float(iterations_used)

            delta_pc = x0 - pg
            qc_total = x1
            q_bh = qc_total
            q_leak = 0.0
            re_leak = 0.0
        else:
            # La fuite annulaire est une branche EN PARALLÈLE des rainures BH :
            # le débit total Qc se répartit entre les rainures (qbh) et la fuite
            # (q_leak) sous la même perte de charge ΔP = (x0 - Pg). On garde
            # strictement la structure du schéma sans fuite (même itération
            # auto-référente calée sur le VBA), la fuite venant simplement
            # retrancher du débit qui traverse les rainures : qbh_eff = x1 - q_leak.
            # Ainsi, lorsque la fuite → 0, on retombe EXACTEMENT sur le modèle
            # historique (continuité garantie).
            inv_scd2 = (1.0 / (sec_bh * cd_bh)) ** 2

            def _leak(delta_p: float) -> tuple[float, float]:
                return _flow_annular_with_turbulence(
                    delta_p,
                    rho,
                    visc,
                    p.LPalierBh,
                    p.Dbh,
                    p.DInsidePalierBh,
                    p.excentricite_palier_bh,
                )

            err_now = None

            def _residual_error(x0_val: float, x1_val: float, m_delta_pc_val: float) -> float:
                pc_ref_val = pg + m_delta_pc_val
                dp_val = x0_val - pg
                qf_val, _ = _leak(dp_val)
                qbh_val = x1_val - qf_val
                f0_val = x1_val - p.Sc * v + coupl * (x0_val - pc_ref_val)
                f1_val = (x0_val - pg) - 0.5 * rho * (qbh_val ** 2) * inv_scd2 * _sign(qbh_val)
                err0 = abs(f0_val) / max(abs(p.Sc * v), 1.0e-12)
                err1 = abs(f1_val) / max(abs(x0_val - pg), 1.0)
                return max(err0, err1)

            for it_idx in range(max_iter):
                pc_ref = pg + m_delta_pc         # MLG.Pc (propriété, évolutive)
                dp = x0 - pg
                qf_i, re_leak = _leak(dp)         # fuite annulaire au ΔP courant
                qbh_eff = x1 - qf_i               # le reste passe par les rainures BH
                f0 = x1 - p.Sc * v + coupl * (x0 - pc_ref)
                f1 = (x0 - pg) - 0.5 * rho * (qbh_eff ** 2) * inv_scd2 * _sign(qbh_eff)

                # Sensibilité de la fuite à la perte de charge ∂q_fuite/∂ΔP,
                # estimée par différence finie centrée. Ce terme MANQUAIT dans le
                # jacobien d'origine : sans lui, le Newton-Raphson suppose la fuite
                # CONSTANTE pendant le pas et diverge dès qu'elle devient dominante
                # (qbh_eff → 0). En l'incluant, le solveur reste stable et physique
                # même lorsque la quasi-totalité du débit passe par la fuite.
                h = max(abs(dp) * 1.0e-6, 1.0)
                qf_plus, _ = _leak(dp + h)
                qf_minus, _ = _leak(dp - h)
                dqf_ddp = (qf_plus - qf_minus) / (2.0 * h)

                # Jacobien 2×2 complet. j10 = ∂f1/∂x0 : la perte de charge (x0 − Pg)
                # agit directement (terme « 1 ») ET via la fuite, qui retranche du
                # débit rainures qbh_eff = x1 − q_fuite(x0 − Pg).
                j11 = -qbh_eff * rho * inv_scd2 * _sign(qbh_eff)
                j10 = 1.0 + rho * inv_scd2 * abs(qbh_eff) * dqf_ddp
                det = coupl * j11 - j10
                if det == 0.0:
                    raise SimError(
                        code="HYDRAU_JACOBIEN_SINGULIER",
                        message="Le jacobien du solveur hydraulique est singulier (déterminant nul).",
                        level=ErrorLevel.RUNTIME,
                        hint="Réduire le pas de temps ou vérifier la section de bague hydraulique.",
                    )
                dx0 = (j11 * f0 - 1.0 * f1) / det
                dx1 = (coupl * f1 - j10 * f0) / det
                x0 -= dx0
                x1 -= dx1
                m_delta_pc = x0 - pg             # MLG.DeltaPc = xRes(0) - Pg
                iterations_used = it_idx + 1
                err_now = _residual_error(x0, x1, m_delta_pc)
                if adaptive_newton and it_idx + 1 >= min_iter and err_now is not None and err_now <= target_err:
                        break

            if metrics is not None:
                metrics["target_err"] = float(target_err)
                if err_now is not None:
                    metrics["final_err"] = float(err_now)
                metrics["iterations_used"] = float(iterations_used)
            dp = x0 - pg
            q_leak, re_leak = _leak(dp)
            q_bh = x1 - q_leak
            delta_pc = dp
            qc_total = x1
    else:
        delta_pc = 0.5 * rho * (qc_total / (sec_bh * cd_bh)) ** 2 * _sign(qc_total)
        q_bh = qc_total
        q_leak = 0.0
        re_leak = 0.0

    # --- Détente : trous piston + clapet ---------------------------------- #
    qd = p.Sd * v
    re_pis = (abs(qd) * p.DTrouPis / p.STrouPis) / visc
    cd_pis = _cd(re_pis * p.DTrouPis, p.HauteurPisBh)
    re_diap = (abs(qd) * p.DTrouDiap / p.STrouDiap) / visc
    cd_diap = _cd(re_diap * p.DTrouDiap, 0.001)

    if qd < 0.0:
        delta_pd = (
            0.5 * rho * (qd / (p.STrouDiap * cd_diap)) ** 2 * _sign(qd)
            + 0.5 * rho * (qd / (p.STrouPis * cd_pis)) ** 2 * _sign(qd)
        )
    else:
        delta_pd = 0.5 * rho * (qd / (p.STrouPis * cd_pis)) ** 2 * _sign(qd)

    return (
        float(delta_pc),
        float(delta_pd),
        float(qc_total),
        float(q_bh),
        float(q_leak),
        float(re_leak),
    )


__all__ = ["calcul_hydrau", "_sign"]
