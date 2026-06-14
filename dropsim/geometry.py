"""Géométrie du mécanisme à balancier et changement de repère.

Reproduit les routines VBA ``cRot`` (changement de repère sol → train),
``DeterPosBalA`` et ``DeterPosBalR`` (intersection de deux cercles résolue par
Newton-Raphson pour localiser les points A et R du balancier).
"""
from __future__ import annotations

import math

import numpy as np


def _rot_axis(u: np.ndarray, c: float, s: float) -> np.ndarray:
    """Matrice de rotation de Rodrigues autour de l'axe unitaire ``u`` (cos=c, sin=s)."""
    u0, u1, u2 = u
    return np.array(
        [
            [u0 * u0 * (1 - c) + c, u0 * u1 * (1 - c) - u2 * s, u0 * u2 * (1 - c) + u1 * s],
            [u0 * u1 * (1 - c) + u2 * s, u1 * u1 * (1 - c) + c, u1 * u2 * (1 - c) - u0 * s],
            [u0 * u2 * (1 - c) - u1 * s, u1 * u2 * (1 - c) + u0 * s, u2 * u2 * (1 - c) + c],
        ]
    )


def chgt_rep(v: np.ndarray, pitch: float, roll: float) -> np.ndarray:
    """Transforme un vecteur du repère sol vers le repère train (rotation -pitch puis -roll)."""
    c1, s1 = math.cos(-pitch), math.sin(-pitch)
    rot1 = _rot_axis(np.array([0.0, 1.0, 0.0]), c1, s1)
    u2 = rot1 @ np.array([1.0, 0.0, 0.0])
    c2, s2 = math.cos(-roll), math.sin(-roll)
    rot2 = _rot_axis(u2, c2, s2)
    return rot2 @ (rot1 @ v)


def deter_pos_bal_a(
    A: np.ndarray, B: np.ndarray, C: np.ndarray, entraxe: float, lg_ab: float, n_iter: int = 6
) -> None:
    """Localise A : intersection du cercle (C, entraxe) et du cercle (B, LgAB). Modifie ``A`` en place."""
    x = np.array([A[0], A[2]])
    for _ in range(n_iter):
        f = np.array(
            [
                entraxe ** 2 - (C[0] - x[0]) ** 2 - (C[2] - x[1]) ** 2,
                lg_ab ** 2 - (B[0] - x[0]) ** 2 - (B[2] - x[1]) ** 2,
            ]
        )
        jac = np.array(
            [
                [2 * C[0] - 2 * x[0], 2 * C[2] - 2 * x[1]],
                [2 * B[0] - 2 * x[0], 2 * B[2] - 2 * x[1]],
            ]
        )
        x = x - np.linalg.solve(jac, f)
    A[0], A[2] = x[0], x[1]


def deter_pos_bal_r(
    R: np.ndarray, A: np.ndarray, B: np.ndarray, lg_ra: float, lg_rb: float, n_iter: int = 6
) -> None:
    """Localise R : intersection du cercle (A, LgRA) et du cercle (B, LgRB). Modifie ``R`` en place."""
    x = np.array([R[0], R[2]])
    for _ in range(n_iter):
        f = np.array(
            [
                lg_ra ** 2 - (A[0] - x[0]) ** 2 - (A[2] - x[1]) ** 2,
                lg_rb ** 2 - (B[0] - x[0]) ** 2 - (B[2] - x[1]) ** 2,
            ]
        )
        jac = np.array(
            [
                [2 * A[0] - 2 * x[0], 2 * A[2] - 2 * x[1]],
                [2 * B[0] - 2 * x[0], 2 * B[2] - 2 * x[1]],
            ]
        )
        x = x - np.linalg.solve(jac, f)
    R[0], R[2] = x[0], x[1]


__all__ = ["chgt_rep", "deter_pos_bal_a", "deter_pos_bal_r"]
