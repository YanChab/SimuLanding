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


def calcul_hydrau(
    p: MLGParamsSI,
    v: float,
    d: float,
    delta_pc_prev: float,
    pg: float,
    sec_bh: float,
    n_iter: int = 4,
) -> tuple[float, float, float]:
    """Calcule (ΔPc, ΔPd, Qc) pour une vitesse de tige ``v`` et une course ``d``.

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
    La boucle reproduit *exactement* la macro VBA ``CalculHydrau`` : 4 itérations
    fixes (``For i = 0 To 3``), et la référence de pression ``MLG.Pc`` est
    recalculée à chaque itération comme ``Pg + mDeltaPc`` où ``mDeltaPc`` vient
    d'être réassigné à ``xRes(0) - Pg`` à l'itération précédente. Ce couplage
    auto-référent (et non un Newton-Raphson convergé classique) est essentiel
    pour retrouver les pressions de compression du classeur d'origine.
    """
    rho = p.rho
    visc = p.visc

    if sec_bh <= 0.0:
        raise SimError(
            code="SECTION_BH_NULLE",
            message="La section de la bague hydraulique est nulle ou négative à cette course.",
            level=ErrorLevel.RUNTIME,
            hint="Vérifier la définition des rainures (début/fin/profondeur) et la course.",
            context={"course_m": d},
        )

    qc = p.Sc * v
    deq_bh = math.sqrt(math.pi * sec_bh / 4.0)
    re_bh = (abs(qc) * deq_bh / sec_bh) / visc
    cd_bh = _cd(re_bh * deq_bh, 0.003)

    # --- Compression : couplage avec la compressibilité de l'huile -------- #
    if qc > 0.0:
        coupl = p.Sc * (p.course - d) / (p.bulk * p.it)
        inv_scd2 = (1.0 / (sec_bh * cd_bh)) ** 2
        m_delta_pc = delta_pc_prev          # mDeltaPc persistant du pas précédent
        x0 = pg + m_delta_pc                 # xRes(0) = MLG.Pc à l'entrée
        x1 = qc                              # xRes(1) = MLG.Qc = Sc·v
        for _ in range(n_iter):
            pc_ref = pg + m_delta_pc         # MLG.Pc (propriété, évolutive)
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
            # Résolution 2x2 : [[coupl, 1], [1, j11]] · dx = [f0, f1]
            dx0 = (j11 * f0 - 1.0 * f1) / det
            dx1 = (coupl * f1 - 1.0 * f0) / det
            x0 -= dx0
            x1 -= dx1
            m_delta_pc = x0 - pg             # MLG.DeltaPc = xRes(0) - Pg
        delta_pc = x0 - pg
        qc = x1
    else:
        delta_pc = 0.5 * rho * (qc / (sec_bh * cd_bh)) ** 2 * _sign(qc)

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

    return float(delta_pc), float(delta_pd), float(qc)


__all__ = ["calcul_hydrau", "_sign"]
