"""IntegrationPFD — reconstruction du modèle de calcul strictement conforme au PFD.

Ce module réimplémente, **à partir de zéro et indépendamment des moteurs
historiques** (``engine.py``, ``engine_strait_strut.py``, ``engine_aircraft.py``),
l'**assemblage de corps rigide** des trains et de la structure, en suivant
strictement le document ``docs/PFD_trains.md`` (équations numérotées (1)–(10)).

Périmètre de cette fondation : le **cœur d'assemblage** (bilans résultante + moment
→ efforts d'interface). Les efforts *constitutifs* (effort d'amortisseur ``F_tot``,
effort de contact pneu ``(Fx, Fz)``) sont reçus **en entrée** ; ils seront câblés
dans un second temps aux sous-modèles validés (gaz, hydraulique, pneu, butée).

Conventions (cf. doc §1, §2.3) :
- repère sol : X **vers l'arrière** de l'avion (avance vers −X, Vx < 0), Z vers le
  haut, Y = Z × X ; problème plan X–Z, moment porté par Y ;
- effort de liaison ``T`` = action *sur l'organe mobile* ; effort *transmis à la
  cellule* ``F = -T`` (3ᵉ loi) — c'est ``F`` qui dimensionne l'attache et qui entre
  dans le PFD avion.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


# ===========================================================================
#  StraitStrut (NLG) — doc §2 à §5
# ===========================================================================
@dataclass(frozen=True)
class StraitStrutInterface:
    """Résultat de l'assemblage StraitStrut (efforts transmis à la cellule)."""

    F_B: np.ndarray          # effort en B (sol, [Fx, Fz]) — train → cellule
    M_B: float               # moment d'encastrement en B (autour de Y)
    X_gt: float              # réaction bague haute (axe transverse jambe)
    X_gb: float              # réaction bague basse


def strait_strut_interface(
    *,
    P_sol_to_lg: np.ndarray,     # 2x2 : sol (X,Z) → jambe (x1,z1)
    contact_sol: np.ndarray,     # effort de contact pneu (Fx, Fz) en sol
    f_tot: float,                # effort d'amortisseur axial (frottements inclus)
    zeta_R: float, xi_R: float,  # roue : position axiale + décalage transverse (jambe)
    zeta_Gt: float, zeta_Gb: float,
    zeta_B: float, xi_B: float,  # attache B (peut être décalée)
    zeta_G1: float, xi_G1: float,  # centre d'inertie tige+roue = milieu(R, Gt)
    m1: float = 0.0,             # masse tige+roue (0 ⇒ statique transverse)
    accel_G1_lg: np.ndarray | None = None,  # accélération de G1 en repère jambe
    weight_lg: np.ndarray | None = None,    # poids tige+roue en repère jambe
) -> StraitStrutInterface:
    """Assemblage StraitStrut strictement conforme au PFD (doc §3–§5).

    Hypothèses du doc : **corps fixe S₂ sans masse** (équilibre), tige+roue S₁ de
    masse ``m1`` (inertie transverse optionnelle). Frottements de bague **déjà
    inclus dans ``f_tot``** (pas de double comptage).
    """
    a1 = np.zeros(2) if accel_G1_lg is None else np.asarray(accel_G1_lg, float)
    P1 = np.zeros(2) if weight_lg is None else np.asarray(weight_lg, float)

    # Effort de contact en repère jambe : (f_u, f_w)
    f_lg = np.asarray(P_sol_to_lg, float) @ np.asarray(contact_sol, float)
    f_u, f_w = float(f_lg[0]), float(f_lg[1])

    # --- S₁ : moment en Gb (3) → X_t ; résultante transverse (1) → X_t + X_b ----
    #  (3) : (ζt−ζb)·Xt + (ζR−ζb)·f_u − ξR·f_w + (ζ1−ζb)·P1u − ξ1·P1w = δ1y ≈ 0
    rhs3 = -(zeta_R - zeta_Gb) * f_u + xi_R * f_w \
        - (zeta_G1 - zeta_Gb) * P1[0] + xi_G1 * P1[1]
    X_gt = rhs3 / (zeta_Gt - zeta_Gb)
    # (1) : f_u + Xt + Xb + P1u = m1·γ1u  ⇒  Xt + Xb = m1·γ1u − f_u − P1u
    X_gb = (m1 * a1[0] - f_u - P1[0]) - X_gt

    # --- S₂ (sans masse) : équilibre (4),(5),(6) → B et M_B --------------------
    B_u = X_gt + X_gb                       # (4) : B_u − Xt − Xb = 0
    B_w = -f_tot                            # (5) : B_w + F_tot = 0
    #  (6) : M_B + ξB·F_tot − (ζt−ζB)·Xt − (ζb−ζB)·Xb = 0
    M_B_lg = (zeta_Gt - zeta_B) * X_gt + (zeta_Gb - zeta_B) * X_gb - xi_B * f_tot

    # Effort transmis à la cellule = −(action cellule→S₂), jambe → sol (= Pᵀ)
    F_B_lg = -np.array([B_u, B_w])
    F_B_sol = np.asarray(P_sol_to_lg, float).T @ F_B_lg
    return StraitStrutInterface(F_B=F_B_sol, M_B=M_B_lg, X_gt=X_gt, X_gb=X_gb)


def point_A_strait_strut(Gt: np.ndarray, Gb: np.ndarray, course: float) -> np.ndarray:
    """Point d'application de l'effort d'amortisseur (doc §2.4).

    A = Gt + course · (Gt − Gb)/‖Gt − Gb‖ — sur l'axe, décalé de la course depuis
    Gt, côté opposé à Gb.
    """
    Gt = np.asarray(Gt, float)
    Gb = np.asarray(Gb, float)
    u = Gt - Gb
    u = u / np.linalg.norm(u)
    return Gt + course * u


# ===========================================================================
#  TrailingArm (MLG) — doc §6  (balancier AVEC masse)
# ===========================================================================
@dataclass(frozen=True)
class TrailingArmInterface:
    F_B: np.ndarray          # effort au pivot B (sol) — train → cellule
    F_C: np.ndarray          # effort à la rotule C (sol)
    T_A: np.ndarray          # effort amortisseur sur le balancier en A


def trailing_arm_interface(
    *,
    A: np.ndarray, C: np.ndarray,        # points amortisseur (sol)
    f_tot: float,                        # effort axial amortisseur (le long de A-C)
    contact_sol: np.ndarray,             # (Fx, Fz) en R
    weight: np.ndarray | None = None,    # poids balancier+roue (sol)
    m_arm: float = 0.0,                  # masse balancier+roue
    accel_G: np.ndarray | None = None,   # accélération du CG balancier (sol)
) -> TrailingArmInterface:
    """Assemblage TrailingArm strictement conforme au PFD (doc §6).

    Amortisseur = **bielle à 2 forces** (effort le long de A-C). Balancier **avec
    masse** (m_arm, inertie de translation conservée — au-delà du code historique).
    """
    A = np.asarray(A, float)
    C = np.asarray(C, float)
    T_R = np.asarray(contact_sol, float)
    Pw = np.zeros(2) if weight is None else np.asarray(weight, float)
    aG = np.zeros(2) if accel_G is None else np.asarray(accel_G, float)

    # Amortisseur (§6.3) : T_A = F_tot · (A − C)/‖A − C‖
    u_CA = A - C
    u_CA = u_CA / np.linalg.norm(u_CA)
    T_A = f_tot * u_CA
    F_C = -T_A                      # effort sur la cellule à la rotule C

    # Balancier (§6.5), masse conservée : F_B = T_R + T_A + P' − m'·a_G'
    F_B = T_R + T_A + Pw - m_arm * aG
    return TrailingArmInterface(F_B=F_B, F_C=F_C, T_A=T_A)


# ===========================================================================
#  Structure (fuselage) — doc §7  (PFD avion 2 DDL)
# ===========================================================================
@dataclass(frozen=True)
class InterfaceLoad:
    """Un effort d'interface train → cellule, appliqué en P = (x, z)."""

    P: np.ndarray            # point d'application (sol)
    F: np.ndarray            # effort (Fx, Fz) sol
    M_y: float = 0.0         # moment propre autour de Y (encastrement NLG)


def fuselage_accelerations(
    *,
    loads: list[InterfaceLoad],
    cg: np.ndarray,          # (x_G, z_G) du centre de gravité
    mass: float,
    jyy: float,
    g: float = 9.81,
    lift: float = 0.0,       # coefficient de portance L ∈ [0,1]
) -> tuple[float, float]:
    """PFD avion 2 DDL (doc §7) → (z̈_cg, θ̈).

    (9)  m·z̈_cg = Σ F_z,i − m·g·(1−L)
    (10) J_yy·θ̈ = Σ[(x_i−x_G)·F_z,i − (z_i−z_G)·F_x,i] − Σ M_y,i
    """
    cg = np.asarray(cg, float)
    fz_total = sum(float(ld.F[1]) for ld in loads)
    z_ddot = (fz_total - mass * g * (1.0 - lift)) / mass

    m_pitch = 0.0
    for ld in loads:
        r = np.asarray(ld.P, float) - cg
        # convention doc §7.4 : m_pitch = −M_y = (x−xG)·Fz − (z−zG)·Fx − M_y
        m_pitch += r[0] * float(ld.F[1]) - r[1] * float(ld.F[0]) - float(ld.M_y)
    theta_ddot = m_pitch / jyy
    return z_ddot, theta_ddot
