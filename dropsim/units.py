"""Conversions entre unités d'affichage (celles de l'Excel) et unités SI internes.

Le moteur travaille intégralement en SI. Les facteurs ci-dessous reproduisent
exactement les conversions effectuées par la macro VBA ``RecupData``.
"""
from __future__ import annotations

# Longueurs : millimètre <-> mètre
MM_TO_M = 1.0e-3
M_TO_MM = 1.0e3

# Pressions : bar <-> pascal
BAR_TO_PA = 1.0e5
PA_TO_BAR = 1.0e-5

# Volumes : centimètre cube <-> mètre cube
CC_TO_M3 = 1.0e-6
M3_TO_CC = 1.0e6

# Viscosité cinématique : centistokes <-> m²/s
CST_TO_M2S = 1.0e-6
M2S_TO_CST = 1.0e6

# Module de compressibilité : mégapascal <-> pascal
MPA_TO_PA = 1.0e6
PA_TO_MPA = 1.0e-6

# Angles : degré <-> radian
DEG_TO_RAD = 3.141592653589793 / 180.0
RAD_TO_DEG = 180.0 / 3.141592653589793

# Accélération de la pesanteur utilisée dans le modèle VBA (valeur exacte)
G = 9.81

__all__ = [
    "MM_TO_M",
    "M_TO_MM",
    "BAR_TO_PA",
    "PA_TO_BAR",
    "CC_TO_M3",
    "M3_TO_CC",
    "CST_TO_M2S",
    "M2S_TO_CST",
    "MPA_TO_PA",
    "PA_TO_MPA",
    "DEG_TO_RAD",
    "RAD_TO_DEG",
    "G",
]
