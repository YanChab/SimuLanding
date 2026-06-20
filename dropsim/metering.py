"""Loi de section variable de la bague hydraulique (BH) — metering.

Reproduit la macro VBA ``CalculBH`` : pour chaque millimètre de course, on somme
l'aire de la « lentille » (intersection de deux disques) ouverte par chacune des
rainures usinées dans la bague, avec une progressivité linéaire en entrée et en
sortie de rainure. Le résultat est une table (position, section) interpolée
ensuite par :func:`section_bh`.

Toutes les aires sont calculées en mm² puis converties en m² ; les positions de
course sont exprimées en mètres. L'offset ``- section/2000`` sur la position
reproduit exactement le comportement du classeur d'origine.
"""
from __future__ import annotations

import math

import numpy as np

from .inputs import TrailingArmParamsSI


def _lens_area(e: float, r1: float, r2: float) -> float:
    """Aire d'intersection de deux disques de rayons ``r1``/``r2`` distants de ``e`` (mm²)."""
    a1 = (e * e + r1 * r1 - r2 * r2) / (2.0 * e * r1)
    a2 = (e * e + r2 * r2 - r1 * r1) / (2.0 * e * r2)
    # Protection numérique du domaine de acos
    a1 = min(1.0, max(-1.0, a1))
    a2 = min(1.0, max(-1.0, a2))
    rad = (-e + r1 + r2) * (e + r1 - r2) * (e - r1 + r2) * (e + r1 + r2)
    rad = max(0.0, rad)
    return r1 * r1 * math.acos(a1) + r2 * r2 * math.acos(a2) - 0.5 * math.sqrt(rad)


def build_section_table(p: TrailingArmParamsSI) -> tuple[np.ndarray, np.ndarray]:
    """Construit la table (position [m], section [m²]) de la bague hydraulique.

    Returns
    -------
    tab_pos : np.ndarray
        Positions de course en mètres (``m/1000 - section_mm²/2000``).
    tab_sec : np.ndarray
        Sections correspondantes en m².
    """
    r1 = p.Dbh / 2.0 * 1000.0          # mm
    r2 = p.diametre_rainure / 2.0      # mm
    course_mm = int(round(p.course * 1000.0))

    debut = p.rainures_debut
    fin = p.rainures_fin
    prof = p.rainures_profondeur
    n_rainure = len(debut)

    sec_mm2 = np.zeros(course_mm + 1)

    for k in range(n_rainure):
        e = prof[k] + r2
        # Longueur de progressivité (entier, comme dans le VBA)
        inner = r2 * r2 - (r2 - (r1 - prof[k])) ** 2
        long_prog = int(math.sqrt(inner)) if inner > 0 else 0
        full = _lens_area(e, r1, r2)
        for m in range(course_mm + 1):
            if debut[k] <= m <= fin[k]:
                sec_mm2[m] += full
            elif long_prog > 0 and (debut[k] - long_prog) <= m < debut[k]:
                sec_mm2[m] += ((long_prog - (debut[k] - m)) / long_prog) * full
            elif long_prog > 0 and fin[k] < m < (fin[k] + long_prog):
                sec_mm2[m] += ((long_prog - (m - fin[k])) / long_prog) * full
            # sinon : contribution nulle

    positions_mm = np.arange(course_mm + 1, dtype=float)
    tab_pos = positions_mm / 1000.0 - sec_mm2 / 2000.0
    tab_sec = sec_mm2 / 1.0e6
    return tab_pos, tab_sec


def section_bh(d: float, tab_pos: np.ndarray, tab_sec: np.ndarray) -> float:
    """Interpole la section de la bague hydraulique à la course ``d`` (m).

    Reproduit fidèlement le balayage linéaire de la propriété ``SecBh`` du VBA :
    saturation sous la première position, interpolation linéaire sinon.
    """
    n = len(tab_pos)
    if d < tab_pos[0]:
        return float(tab_sec[0])
    for i in range(n - 1):
        if tab_pos[i] <= d < tab_pos[i + 1]:
            frac = (d - tab_pos[i]) * (
                (tab_sec[i + 1] - tab_sec[i]) / (tab_pos[i + 1] - tab_pos[i])
            )
            return float(tab_sec[i] + frac)
    return float(tab_sec[-1])


__all__ = ["build_section_table", "section_bh"]
