"""Moteur TrailingArm (MLG) reconstruit selon le PFD — torseur **3D**.

Le moteur historique ``engine.run_trailing_arm`` calcule déjà l'interface dans la
limite **balancier sans masse** (``fb = ta + tr``, ``fc = -ta``, plus les moments
``mb_x``/``mb_z``), qui est exactement l'assemblage PFD (doc §6, m_arm = 0). Ce
module réutilise donc le moteur historique pour tout le **constitutif + géométrie
+ rotation du balancier** (validés), et recalcule l'interface **strictement par le
PFD en 3D** (``integration_pfd.trailing_arm_interface``) :

- efforts **3D** F_B, F_C (composantes Fy non nulles si l'amortisseur est oblique) ;
- **moments Mx, Mz** au pivot (non nuls dès qu'il y a un décalage en Y, ex. roue
  déportée R_y ≠ B_y) ; My n'est pas transmis (rotation, eq (8)) ;
- option **masse du balancier** (+P' − m'·a_G', au-delà du code historique — H8).

Les coordonnées Y sont **constantes** pendant la simulation (rotation autour de
Y) ; on les reconstruit depuis la géométrie initiale (après attitude pitch/roll).
"""
from __future__ import annotations

import numpy as np

from .engine import run_trailing_arm
from .errors import ErrorCollector
from .geometry import rotate_about
from .inputs import TrailingArmParamsSI
from .integration_pfd import trailing_arm_interface
from .units import G


def _constant_y(p: TrailingArmParamsSI) -> dict[str, float]:
    """Y constants des points A, B, C, R après la mise en attitude initiale."""
    A = p.A.astype(float).copy()
    B = p.B.astype(float).copy()
    C = p.C.astype(float).copy()
    R = p.R.astype(float).copy()
    S = R.copy()
    S[2] = R[2] - p.unload_radius
    A = rotate_about(A, S, p.pitch, p.roll)
    B = rotate_about(B, S, p.pitch, p.roll)
    C = rotate_about(C, S, p.pitch, p.roll)
    R = rotate_about(R, S, p.pitch, p.roll)
    return {"A": float(A[1]), "B": float(B[1]), "C": float(C[1]), "R": float(R[1])}


def run_trailing_arm_pfd(
    p: TrailingArmParamsSI,
    *,
    m_arm: float = 0.0,
    collector: ErrorCollector | None = None,
) -> dict[str, np.ndarray]:
    """Drop test MLG, torseur d'interface 3D recalculé strictement par le PFD (§6).

    ``m_arm`` : masse balancier+roue. 0 ⇒ reproduit le moteur historique. > 0 ⇒
    ajoute le terme PFD d'inertie/poids (a_G' par différence finie de G' =
    milieu(B, R), de composante Y nulle car le mouvement est plan X-Z).
    """
    out = run_trailing_arm(p, collector=collector)
    d = out.data
    geom = out.geometry or {}
    y = _constant_y(p)

    n = len(d["trailing_arm_ftot"])
    t = np.asarray(d.get("temps", np.arange(n) * p.it), float)

    ax, az = np.asarray(geom["ax"], float), np.asarray(geom["az"], float)
    bx, bz = np.asarray(geom["bx"], float), np.asarray(geom["bz"], float)
    cx, cz = np.asarray(geom["cx"], float), np.asarray(geom["cz"], float)
    rx, rz = np.asarray(geom["rx"], float), np.asarray(geom["rz"], float)
    ftot = np.asarray(d["trailing_arm_ftot"], float)
    tr_x = np.asarray(d["tr_x"], float)
    tr_z = np.asarray(d["tyre_ftyre"], float)

    # Accélération 3D du CG balancier+roue G' = milieu(B, R) (Y constant ⇒ a_y = 0).
    gx, gz = 0.5 * (bx + rx), 0.5 * (bz + rz)
    if m_arm != 0.0 and n >= 3:
        a_gx = np.gradient(np.gradient(gx, t), t)
        a_gz = np.gradient(np.gradient(gz, t), t)
    else:
        a_gx = np.zeros(n)
        a_gz = np.zeros(n)

    keys = ["temps", "fb_x", "fb_y", "fb_z", "mb_x", "mb_z",
            "fc_x", "fc_y", "fc_z", "ftot"]
    res = {k: np.zeros(n) for k in keys}
    weight = np.array([0.0, 0.0, -m_arm * G])
    for i in range(n):
        iface = trailing_arm_interface(
            A=np.array([ax[i], y["A"], az[i]]),
            B=np.array([bx[i], y["B"], bz[i]]),
            C=np.array([cx[i], y["C"], cz[i]]),
            R=np.array([rx[i], y["R"], rz[i]]),
            f_tot=float(ftot[i]),
            contact_sol=np.array([tr_x[i], 0.0, tr_z[i]]),
            weight=weight,
            m_arm=m_arm,
            accel_G=np.array([a_gx[i], 0.0, a_gz[i]]),
        )
        res["temps"][i] = t[i]
        res["fb_x"][i], res["fb_y"][i], res["fb_z"][i] = iface.F_B
        res["fc_x"][i], res["fc_y"][i], res["fc_z"][i] = iface.F_C
        res["mb_x"][i], res["mb_z"][i] = iface.M_B[0], iface.M_B[2]
        res["ftot"][i] = ftot[i]
    return res
