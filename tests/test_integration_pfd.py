"""Validation du cœur d'assemblage IntegrationPFD contre les limites du PFD.

Cf. docs/PFD_trains.md — on vérifie les résultats analytiques (équations (1)–(10))
dans les cas limites où ils sont connus de façon fermée.
"""
import numpy as np

from dropsim.integration_pfd import (
    InterfaceLoad,
    fuselage_accelerations,
    point_A_strait_strut,
    strait_strut_interface,
    trailing_arm_interface,
)


def test_strait_strut_vertical_massless():
    """Jambe verticale (P = I), masses nulles → F_B,x = Fx, F_B,z = F_tot (§5.3)."""
    res = strait_strut_interface(
        P_sol_to_lg=np.eye(2),
        contact_sol=np.array([1234.0, 5678.0]),
        f_tot=9000.0,
        zeta_R=0.0, xi_R=0.0,
        zeta_Gt=0.30, zeta_Gb=0.10,
        zeta_B=0.50, xi_B=0.0,
        zeta_G1=0.15, xi_G1=0.0,
    )
    assert res.F_B[0] == 1234.0            # F_B,x = composante de contact (= fu)
    assert res.F_B[1] == 9000.0            # F_B,z = F_tot (exact, S₂ sans masse)
    assert abs(res.X_gt + res.X_gb + 1234.0) < 1e-9   # Xt + Xb = −fu


def test_strait_strut_wheel_offset_loads_guides():
    """Roue déportée (ξR ≠ 0) : le chargement vertical fw charge les bagues (§3.3)."""
    common = dict(
        P_sol_to_lg=np.eye(2), contact_sol=np.array([0.0, 5000.0]), f_tot=0.0,
        zeta_R=0.0, zeta_Gt=0.30, zeta_Gb=0.10, zeta_B=0.50, xi_B=0.0,
        zeta_G1=0.15, xi_G1=0.0,
    )
    coax = strait_strut_interface(xi_R=0.0, **common)
    offset = strait_strut_interface(xi_R=0.05, **common)
    # Sans décalage et sans effort horizontal : bagues non chargées.
    assert abs(coax.X_gt) < 1e-9 and abs(coax.X_gb) < 1e-9
    # Avec décalage : le vertical charge les bagues.
    assert abs(offset.X_gt) > 1.0


def test_point_A_geometry():
    """A = Gt + course·(Gt−Gb)/‖·‖, côté opposé à Gb (§2.4)."""
    Gt = np.array([0.0, 0.30])
    Gb = np.array([0.0, 0.10])
    A = point_A_strait_strut(Gt, Gb, course=0.05)
    assert np.allclose(A, np.array([0.0, 0.35]))   # au-dessus de Gt


def test_trailing_arm_resultant_is_contact():
    """Sans masse, F_B + F_C = T_R (résultante = réaction de contact, §6.6), en 3D."""
    ta = trailing_arm_interface(
        A=np.array([0.1, -1.19, 0.2]), B=np.array([0.0, -1.19, 0.6]),
        C=np.array([0.0, -1.19, 0.6]), R=np.array([0.3, -1.35, 0.0]),
        f_tot=8000.0, contact_sol=np.array([1500.0, 0.0, 60000.0]),
    )
    assert np.allclose(ta.F_B + ta.F_C, np.array([1500.0, 0.0, 60000.0]))
    assert np.allclose(ta.F_C, -ta.T_A)            # rotule : F_C = −T_A


def test_trailing_arm_y_offset_gives_moment():
    """Une roue déportée en Y (R_y ≠ B_y) produit des moments Mx, Mz au pivot (§6.5)."""
    common = dict(A=np.array([0.1, -1.19, 0.2]), B=np.array([0.0, -1.19, 0.6]),
                  C=np.array([0.0, -1.19, 0.6]), f_tot=8000.0,
                  contact_sol=np.array([1500.0, 0.0, 60000.0]))
    planar = trailing_arm_interface(R=np.array([0.3, -1.19, 0.0]), **common)
    offset = trailing_arm_interface(R=np.array([0.3, -1.35, 0.0]), **common)
    assert abs(planar.M_B[0]) < 1e-6 and abs(planar.M_B[2]) < 1e-6  # plan : pas de Mx,Mz
    assert abs(offset.M_B[0]) > 1.0                                  # déport Y → Mx ≠ 0


def test_fuselage_vertical_and_pitch():
    """PFD avion : translation verticale et tangage (§7.3, §7.4)."""
    # Effort vertical pur sous le CG, portance nulle → z̈ = Fz/m − g.
    zdd, thdd = fuselage_accelerations(
        loads=[InterfaceLoad(P=np.array([0.0, 0.0]), F=np.array([0.0, 120000.0]))],
        cg=np.array([0.0, 1.0]), mass=10000.0, jyy=50000.0, g=9.81, lift=0.0,
    )
    assert abs(zdd - (12.0 - 9.81)) < 1e-9
    assert abs(thdd) < 1e-9                          # centré → pas de tangage

    # Effort horizontal décalé verticalement → tangage non nul (§7.5).
    _, thdd2 = fuselage_accelerations(
        loads=[InterfaceLoad(P=np.array([0.0, 0.0]), F=np.array([1000.0, 0.0]))],
        cg=np.array([0.0, 1.0]), mass=10000.0, jyy=50000.0,
    )
    # m_pitch = −(z−zG)·Fx = −(0−1)·1000 = +1000 → θ̈ = 1000/50000
    assert abs(thdd2 - 1000.0 / 50000.0) < 1e-9
