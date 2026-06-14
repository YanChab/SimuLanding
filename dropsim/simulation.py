"""Point d'entrée haut niveau de la simulation MLG.

Enchaîne : validation des entrées (niveau SAISIE) → conversion SI → contrôles de
cohérence (niveau PRÉ-CALCUL) → intégration temporelle (niveau EXÉCUTION) →
synthèse des résultats. Toute erreur détectée est localisée précisément via
:class:`~dropsim.errors.SimError`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .engine import OUTPUT_COLUMNS, run_mlg
from .errors import ErrorCollector, ErrorLevel, SimError
from .inputs import MLGInputs


@dataclass
class SimulationResult:
    """Résultats de simulation prêts pour l'affichage."""

    df: pd.DataFrame                      # séries temporelles (libellés avec unités)
    summary: dict[str, float]            # grandeurs synthétiques
    n_steps: int
    warnings: list[SimError] = field(default_factory=list)
    geometry: pd.DataFrame | None = None  # positions des points (mm) pour l'animation


def _subsample(data: dict[str, np.ndarray], max_points: int = 1000) -> dict[str, np.ndarray]:
    """Sous-échantillonne les séries à ``max_points`` points (comme l'affichage Excel)."""
    n = len(next(iter(data.values())))
    if n <= max_points:
        return data
    step = max(1, n // max_points)
    return {k: v[::step] for k, v in data.items()}


def run_simulation(inputs: MLGInputs, max_points: int = 1000) -> SimulationResult:
    """Valide, exécute et synthétise une simulation de drop test MLG.

    Raises
    ------
    SimError
        Au premier problème bloquant (saisie invalide, incohérence, divergence).
    """
    # Niveau SAISIE : validation complète du formulaire.
    collector = ErrorCollector()
    inputs.validate(collector)
    if collector.has_errors:
        collector.raise_if_any()

    # Conversion SI.
    params = inputs.to_si()

    # Niveau PRÉ-CALCUL : cohérence des sections dérivées.
    pre = ErrorCollector()
    pre.check(
        params.Sc <= 0,
        code="SECTION_COMPRESSION_INVALIDE",
        message="La section de compression est nulle ou négative.",
        level=ErrorLevel.PRECALCUL,
        field="Dpis",
        hint="Vérifier Dpis et Dbh (Dpis doit être > Dbh).",
    )
    pre.check(
        params.Sd <= 0,
        code="SECTION_DETENTE_INVALIDE",
        message="La section de détente est nulle ou négative.",
        level=ErrorLevel.PRECALCUL,
        field="Dpis",
        hint="Vérifier Dpis et Dt (Dpis doit être > Dt).",
    )
    if pre.has_errors:
        pre.raise_if_any()

    # Niveau EXÉCUTION.
    engine_out = run_mlg(params)

    data = _subsample(engine_out.data, max_points=max_points)
    df = pd.DataFrame({OUTPUT_COLUMNS[k]: v for k, v in data.items()})
    geom = _subsample(engine_out.geometry, max_points=max_points) if engine_out.geometry else {}
    geom_df = pd.DataFrame(geom) if geom else None
    if geom_df is not None:
        geom_df.insert(0, "temps", data["temps"])
    full = engine_out.data
    summary = {
        "Course max (mm)": float(np.max(full["mlg_d"]) * 1000.0),
        "Effort vertical max Fz (N)": float(np.max(full["tyre_ftyre"])),
        "Effort horizontal max Fx (N)": float(np.max(np.abs(full["tr_x"]))),
        "Effort amortisseur max (N)": float(np.max(np.abs(full["mlg_ftot"]))),
        "Pression gaz max (bar)": float(np.max(full["pg"])),
        "Pression compression max (bar)": float(np.max(full["pc"])),
        "Accélération max (g)": float(np.max(np.abs(full["accms"])) / 9.81),
        "Nombre de pas": int(engine_out.n_steps),
    }

    return SimulationResult(
        df=df,
        summary=summary,
        n_steps=engine_out.n_steps,
        warnings=engine_out.warnings,
        geometry=geom_df,
    )


__all__ = ["run_simulation", "SimulationResult"]
