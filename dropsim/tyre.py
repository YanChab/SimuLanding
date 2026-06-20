"""Modèle de pneu : déflexion, effort vertical, adhérence (μ), spin-up, spring-back.

Reproduit la classe VBA ``cTyre`` :

* ``FTyre`` : effort vertical interpolé sur la table déflexion / charge.
* ``Mu`` : coefficient d'adhérence interpolé sur la table μ / glissement, affecté
  du facteur ``0.55`` (réduction dynamique).
* ``REff`` : rayon effectif ``UnRadius - Defl/3``.
* ``Fx`` : effort de rappel (spring-back) ``kx·Depx + cx·Vitx``.

Les tables sont augmentées comme dans ``RecupData`` : un point (-10 mm, 0) est
ajouté au début et un point (dernier + 1 mm, dernière charge × 3) à la fin.
"""
from __future__ import annotations

import numpy as np

from .inputs import TrailingArmParamsSI


def build_tyre_tables(p: TrailingArmParamsSI) -> tuple[np.ndarray, np.ndarray]:
    """Construit les tables augmentées (déflexion [m], charge [N]) du pneu."""
    defl = list(p.tyre_defl)
    load = list(p.tyre_load)
    aug_defl = [-0.01] + defl + [defl[-1] + 0.001]
    aug_load = [0.0] + load + [load[-1] * 3.0]
    return np.array(aug_defl), np.array(aug_load)


def f_tyre(defl: float, tab_defl: np.ndarray, tab_load: np.ndarray) -> float:
    """Effort vertical du pneu pour une déflexion ``defl`` (m)."""
    n = len(tab_defl)
    if defl < tab_defl[0]:
        return float(tab_defl[0])  # comportement reproduit du VBA (force ≈ 0)
    for i in range(n - 1):
        if tab_defl[i] <= defl < tab_defl[i + 1]:
            return float(
                tab_load[i]
                + (defl - tab_defl[i])
                * ((tab_load[i + 1] - tab_load[i]) / (tab_defl[i + 1] - tab_defl[i]))
            )
    return float(tab_load[-1])


def mu(slip: float, mu_x: np.ndarray, mu_y: np.ndarray) -> float:
    """Coefficient d'adhérence pour un taux de glissement ``slip`` (facteur 0.55)."""
    s = abs(slip)
    n = len(mu_x)
    for i in range(n - 1):
        if mu_x[i] <= s < mu_x[i + 1]:
            return float(
                (mu_y[i] + (s - mu_x[i]) * ((mu_y[i + 1] - mu_y[i]) / (mu_x[i + 1] - mu_x[i])))
                * 0.55
            )
    return float(mu_y[-1] * 0.55)


def r_eff(unload_radius: float, defl: float) -> float:
    """Rayon effectif du pneu."""
    return unload_radius - defl / 3.0


__all__ = ["build_tyre_tables", "f_tyre", "mu", "r_eff"]
