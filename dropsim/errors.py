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


__all__ = ["ErrorLevel", "SimError", "ErrorCollector"]
