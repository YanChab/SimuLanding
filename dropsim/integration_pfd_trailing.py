"""Moteur TrailingArm (MLG) reconstruit selon le PFD.

Le moteur historique ``engine.run_trailing_arm`` calcule déjà l'interface dans la
limite **balancier sans masse** (``fb = ta + tr``, ``fc = -ta``), qui est
exactement l'assemblage PFD (doc §6, m_arm = 0). Ce module réutilise donc le
moteur historique pour tout le **constitutif + géométrie + rotation du balancier**
(validés), et recalcule l'interface **strictement par le PFD**
(``integration_pfd.trailing_arm_interface``), avec en option la **masse du
balancier** (terme +P' − m'·a_G', au-delà du code historique — cf. retrait de H8).

Hypothèse plane : amortisseur dans le plan X–Z (dy_ca = 0). L'obliquité en Y est
une raffinement ultérieur.
"""
from __future__ import annotations

import numpy as np

from .engine import run_trailing_arm
from .errors import ErrorCollector
from .inputs import TrailingArmParamsSI
from .integration_pfd import trailing_arm_interface
from .units import G


def run_trailing_arm_pfd(
    p: TrailingArmParamsSI,
    *,
    m_arm: float = 0.0,
    collector: ErrorCollector | None = None,
) -> dict[str, np.ndarray]:
    """Drop test MLG, interface recalculée strictement par le PFD (doc §6).

    ``m_arm`` : masse du balancier+roue. 0 ⇒ reproduit le moteur historique
    (balancier sans masse). > 0 ⇒ ajoute le terme d'inertie/poids PFD à l'effort
    au pivot (a_G' estimé par différence finie de G' = milieu(B, R)).
    """
    out = run_trailing_arm(p, collector=collector)
    d = out.data
    geom = out.geometry or {}

    n = len(d["trailing_arm_ftot"])
    t = np.asarray(d.get("temps", np.arange(n) * p.it), float)

    ax = np.asarray(geom["ax"], float); az = np.asarray(geom["az"], float)
    cx = np.asarray(geom["cx"], float); cz = np.asarray(geom["cz"], float)
    bx = np.asarray(geom["bx"], float); bz = np.asarray(geom["bz"], float)
    rx = np.asarray(geom["rx"], float); rz = np.asarray(geom["rz"], float)
    ftot = np.asarray(d["trailing_arm_ftot"], float)
    tr_x = np.asarray(d["tr_x"], float)
    tr_z = np.asarray(d["tyre_ftyre"], float)

    # Accélération du CG balancier+roue G' = milieu(B, R), par différence finie.
    gx, gz = 0.5 * (bx + rx), 0.5 * (bz + rz)
    if m_arm != 0.0 and n >= 3:
        a_gx = np.gradient(np.gradient(gx, t), t)
        a_gz = np.gradient(np.gradient(gz, t), t)
    else:
        a_gx = np.zeros(n); a_gz = np.zeros(n)

    res = {k: np.zeros(n) for k in
           ["temps", "fb_x", "fb_z", "fc_x", "fc_z", "ftot", "tr_x", "tr_z"]}
    weight = np.array([0.0, -m_arm * G])
    for i in range(n):
        iface = trailing_arm_interface(
            A=np.array([ax[i], az[i]]),
            C=np.array([cx[i], cz[i]]),
            f_tot=float(ftot[i]),
            contact_sol=np.array([tr_x[i], tr_z[i]]),
            weight=weight,
            m_arm=m_arm,
            accel_G=np.array([a_gx[i], a_gz[i]]),
        )
        res["temps"][i] = t[i]
        res["fb_x"][i], res["fb_z"][i] = iface.F_B[0], iface.F_B[1]
        res["fc_x"][i], res["fc_z"][i] = iface.F_C[0], iface.F_C[1]
        res["ftot"][i] = ftot[i]
        res["tr_x"][i] = tr_x[i]
        res["tr_z"][i] = tr_z[i]
    return res
