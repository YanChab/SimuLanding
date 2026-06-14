"""Ressort gazeux à double chambre (basse + haute pression).

Reproduit la propriété ``Pg`` de la classe VBA ``ClMLG`` : un système de trois
équations non linéaires est résolu par Newton-Raphson pour déterminer
simultanément les variations de volume des deux chambres et la pression de gaz,
en tenant compte de la compressibilité de l'huile.

Inconnues : x0 = ΔVbp, x1 = ΔVhp, x2 = Pg.
* Chaque chambre suit une loi polytropique ``P·Vᵞ = cte``.
* L'activation de la chambre haute pression est lissée par un arctangente
  (``k = 0.02``), qui agit comme un interrupteur très raide une fois exprimé en Pa.
* La compressibilité de l'huile est prise en compte via ``Vh·Pgtamp/Bulk``.
"""
from __future__ import annotations

import math

import numpy as np

from .errors import ErrorLevel, SimError
from .inputs import MLGParamsSI

_K_HP = 0.02  # coefficient de raideur de l'activation HP (cf. VBA)


class GasSpring:
    """État du ressort gazeux (volumes courants des deux chambres)."""

    def __init__(self, p: MLGParamsSI) -> None:
        self.p = p
        self.Vgbp = p.Vgbp
        self.Vghp = p.Vghp
        self.precision = 0.0

    def reset(self) -> None:
        self.Vgbp = self.p.Vgbp
        self.Vghp = self.p.Vghp

    def pressure(self, d: float, pgtamp: float, max_iter: int = 12, tol: float = 1.0e-3) -> float:
        """Pression de gaz pour une course ``d`` (m) et une pression tampon ``pgtamp`` (Pa).

        Met à jour ``self.Vgbp`` / ``self.Vghp`` (état des chambres).
        """
        p = self.p
        if d == 0.0:
            self.Vgbp = p.Vgbp
            self.Vghp = p.Vghp
            return p.Pinitbp

        g = p.gamma
        Vginitbp = p.Vgbp
        Vginithp = p.Vghp
        St = p.St
        pi = math.pi

        x = np.array([Vginitbp - self.Vgbp, Vginithp - self.Vghp, pgtamp], dtype=float)

        for _ in range(max_iter):
            base_bp = Vginitbp - x[0]
            base_hp = Vginithp - x[1]
            if base_bp <= 0.0 or base_hp <= 0.0:
                raise SimError(
                    code="GAZ_VOLUME_NEGATIF",
                    message="Le solveur du ressort gazeux a produit un volume de chambre négatif.",
                    level=ErrorLevel.RUNTIME,
                    field="Vgbp" if base_bp <= 0.0 else "Vghp",
                    hint="Vérifier les volumes/pressions initiaux de gaz et la course.",
                    context={"course_m": d, "base_bp": base_bp, "base_hp": base_hp},
                )

            switch = (math.atan(_K_HP * (x[2] - p.Pinithp)) + pi / 2.0) / pi
            f0 = d * St - (p.Vh * pgtamp / p.bulk) - x[0] - x[1] * switch
            f1 = x[2] * base_bp ** g - p.Pinitbp * Vginitbp ** g
            f2 = x[2] * base_hp ** g - p.Pinithp * Vginithp ** g

            dswitch = _K_HP / (1.0 + (_K_HP * (x[2] - p.Pinithp)) ** 2)
            jac = np.array(
                [
                    [-1.0, -switch, -x[1] / pi * dswitch],
                    [-x[2] * g * base_bp ** (g - 1.0), 0.0, base_bp ** g],
                    [0.0, -x[2] * g * base_hp ** (g - 1.0), base_hp ** g],
                ]
            )
            f = np.array([f0, f1, f2])
            self.precision = float(f0 + f1 + f2)

            det = np.linalg.det(jac)
            if det == 0.0:
                raise SimError(
                    code="GAZ_JACOBIEN_SINGULIER",
                    message="Le jacobien du solveur de ressort gazeux est singulier (déterminant nul).",
                    level=ErrorLevel.RUNTIME,
                    hint="Réduire le pas de temps ou vérifier les paramètres de gaz.",
                )
            x = x - np.linalg.solve(jac, f)

            if abs(f0) + abs(f1) + abs(f2) < tol:
                break

        self.Vgbp = Vginitbp - x[0]
        self.Vghp = Vginithp - x[1]
        return float(x[2])


__all__ = ["GasSpring"]
