"""Système de détection et de localisation des erreurs.

Objectif : pour chaque problème détecté, indiquer **précisément** à l'utilisateur
d'où vient l'erreur (quel champ), à quel niveau elle survient et comment la corriger.

Trois niveaux sont distingués :

* ``SAISIE``    : valeur d'entrée invalide (type, signe, plage). Détecté avant tout calcul.
* ``PRECALCUL`` : incohérence physique/géométrique détectée à la préparation du modèle
                  (sections nulles, géométrie impossible, volumes incompatibles...).
* ``RUNTIME``   : anomalie pendant l'intégration temporelle (divergence, NaN, déterminant nul,
                  dépassement de butée, non convergence d'un solveur de Newton...).
"""
from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field
from enum import Enum
from typing import Optional


class ErrorLevel(str, Enum):
    SAISIE = "Saisie"
    PRECALCUL = "Pré-calcul"
    RUNTIME = "Exécution"


@dataclass
class SimError(Exception):
    """Erreur localisée et explicite.

    Parameters
    ----------
    field:
        Identifiant du champ d'entrée concerné (ex. ``"Dpis"``). ``None`` si l'erreur
        n'est pas rattachable à un champ unique.
    code:
        Code court et stable, utilisable par l'UI (ex. ``"SECTION_NEGATIVE"``).
    message:
        Message clair en français destiné à l'utilisateur.
    level:
        Niveau auquel l'erreur est survenue.
    hint:
        Conseil concret de correction.
    context:
        Informations complémentaires (valeurs, indices d'itération...).
    """

    code: str
    message: str
    level: ErrorLevel = ErrorLevel.SAISIE
    field: Optional[str] = None
    hint: Optional[str] = None
    context: dict = dc_field(default_factory=dict)

    def __str__(self) -> str:  # pragma: no cover - confort d'affichage
        loc = f" [champ : {self.field}]" if self.field else ""
        hint = f"\n  → {self.hint}" if self.hint else ""
        return f"[{self.level.value}] {self.code}{loc} : {self.message}{hint}"

    def as_dict(self) -> dict:
        return {
            "niveau": self.level.value,
            "code": self.code,
            "champ": self.field,
            "message": self.message,
            "conseil": self.hint,
            "contexte": self.context,
        }


class ErrorCollector:
    """Accumule des erreurs/avertissements non bloquants pour les présenter en bloc.

    Permet de valider l'intégralité d'un formulaire et de remonter **toutes** les
    erreurs d'un coup plutôt que de s'arrêter à la première.
    """

    def __init__(self) -> None:
        self.errors: list[SimError] = []
        self.warnings: list[SimError] = []

    def add(self, error: SimError) -> None:
        self.errors.append(error)

    def warn(self, error: SimError) -> None:
        self.warnings.append(error)

    def check(
        self,
        condition: bool,
        *,
        code: str,
        message: str,
        level: ErrorLevel = ErrorLevel.SAISIE,
        field: Optional[str] = None,
        hint: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> bool:
        """Ajoute une erreur si ``condition`` est vraie. Retourne ``condition``."""
        if condition:
            self.add(
                SimError(
                    code=code,
                    message=message,
                    level=level,
                    field=field,
                    hint=hint,
                    context=context or {},
                )
            )
        return condition

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    def raise_if_any(self) -> None:
        """Lève la première erreur si au moins une a été collectée."""
        if self.errors:
            raise self.errors[0]

    def as_dicts(self) -> list[dict]:
        return [e.as_dict() for e in self.errors]


# Codes d'erreur runtime traduisant un sur-enfoncement de l'amortisseur (chambre
# de gaz totalement comprimée). On les intercepte pour arrêter proprement la
# simulation au lieu de la faire échouer.
OVERSTROKE_CODES = frozenset({"GAZ_VOLUME_NEGATIF", "GAZ_JACOBIEN_SINGULIER"})


def make_overstroke_warning(
    gear_label: str,
    time_s: float,
    stroke_m: float,
    course_m: float,
    cause: "SimError | None" = None,
) -> "SimError":
    """Construit un avertissement non bloquant de sur-enfoncement (butée atteinte).

    Utilisé par les moteurs pour signaler qu'un amortisseur a atteint sa butée de
    compression : la simulation s'arrête à cet instant et conserve les données
    jusque-là.
    """
    stroke_txt = f"{stroke_m * 1000.0:.1f} mm" if stroke_m == stroke_m else "n/d"
    return SimError(
        code="SUR_ENFONCEMENT",
        message=(
            f"Sur-enfoncement {gear_label} à t = {time_s * 1000.0:.1f} ms "
            f"(course ≈ {stroke_txt}, course mécanique {course_m * 1000.0:.1f} mm) : "
            "l'amortisseur atteint sa butée de compression. La simulation s'arrête "
            "à cet instant ; les données précédentes restent exploitables."
        ),
        level=ErrorLevel.RUNTIME,
        field="course",
        hint=(
            "Revoir le dimensionnement (augmenter le volume/la pression de gaz ou "
            "l'amortissement), ou réduire la sévérité de la chute (Vz, masse, assiette)."
        ),
        context={
            "time_s": time_s,
            "stroke_m": stroke_m,
            "course_m": course_m,
            "cause": getattr(cause, "code", None),
        },
    )


__all__ = [
    "ErrorLevel",
    "SimError",
    "ErrorCollector",
    "OVERSTROKE_CODES",
    "make_overstroke_warning",
]
