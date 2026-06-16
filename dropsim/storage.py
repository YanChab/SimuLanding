"""Sauvegarde et rechargement des simulations (entrées + résultats).

Sérialise une simulation complète (les entrées :class:`~dropsim.inputs.MLGInputs`
et le résultat :class:`~dropsim.simulation.SimulationResult`) dans un fichier
**JSON** autonome, puis permet de la recharger à l'identique. Le format JSON est
volontairement choisi (plutôt que ``pickle``) pour être **sûr** (aucune exécution
de code à la lecture), lisible et stable d'une version à l'autre.

Fonctions principales :

* :func:`save_simulation` — écrit une simulation dans un fichier ;
* :func:`load_simulation` — relit un fichier et reconstruit (inputs, result) ;
* :func:`list_saved` — liste les simulations sauvegardées d'un dossier ;
* :func:`delete_saved` — supprime un fichier de sauvegarde.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, fields
from datetime import datetime
from pathlib import Path

import pandas as pd

from .inputs import MLGInputs, Point3, Rainure
from .simulation import SimulationResult

# Version du schéma de fichier (incrémentée si le format évolue de façon incompatible).
SCHEMA = "simuland/1"

# Dossier de sauvegarde par défaut (à la racine du dépôt).
DEFAULT_SAVE_DIR = Path(__file__).resolve().parent.parent / "saved_simulations"


# --------------------------------------------------------------------------- #
#  Sérialisation des entrées
# --------------------------------------------------------------------------- #
def inputs_to_dict(inputs: MLGInputs) -> dict:
    """Convertit ``MLGInputs`` en dictionnaire JSON-compatible."""
    return asdict(inputs)


def inputs_from_dict(d: dict) -> MLGInputs:
    """Reconstruit ``MLGInputs`` depuis un dictionnaire (robuste aux clés en trop)."""
    known = {f.name for f in fields(MLGInputs)}
    data = {k: v for k, v in d.items() if k in known}

    for key in ("B", "A", "C", "R", "S"):
        if key in data and isinstance(data[key], dict):
            data[key] = Point3(**data[key])

    if "rainures" in data:
        data["rainures"] = [
            Rainure(**r) if isinstance(r, dict) else Rainure(*r)
            for r in data["rainures"]
        ]
    if "tyre_curve" in data:
        data["tyre_curve"] = [tuple(t) for t in data["tyre_curve"]]
    if "mu_curve" in data:
        data["mu_curve"] = [tuple(t) for t in data["mu_curve"]]

    return MLGInputs(**data)


# --------------------------------------------------------------------------- #
#  Sérialisation des résultats
# --------------------------------------------------------------------------- #
def result_to_dict(result: SimulationResult) -> dict:
    """Convertit ``SimulationResult`` en dictionnaire JSON-compatible."""
    return {
        "df": result.df.to_dict(orient="list"),
        "summary": result.summary,
        "n_steps": int(result.n_steps),
        "summary_rows": [[str(lbl), float(val), str(unit)] for lbl, val, unit in result.summary_rows],
        "geometry": (
            result.geometry.to_dict(orient="list") if result.geometry is not None else None
        ),
        "warnings": [str(w) for w in result.warnings],
    }


def result_from_dict(d: dict) -> SimulationResult:
    """Reconstruit ``SimulationResult`` depuis un dictionnaire."""
    geom = d.get("geometry")
    return SimulationResult(
        df=pd.DataFrame(d["df"]),
        summary=dict(d.get("summary", {})),
        n_steps=int(d.get("n_steps", 0)),
        warnings=list(d.get("warnings", [])),
        geometry=pd.DataFrame(geom) if geom else None,
        summary_rows=[(str(lbl), float(val), str(unit)) for lbl, val, unit in d.get("summary_rows", [])],
    )


# --------------------------------------------------------------------------- #
#  Fichiers de sauvegarde
# --------------------------------------------------------------------------- #
def _slugify(name: str) -> str:
    """Transforme un nom en identifiant de fichier sûr."""
    slug = re.sub(r"[^\w\-]+", "_", name.strip(), flags=re.UNICODE).strip("_")
    return slug or "simulation"


def bundle(inputs: MLGInputs, result: SimulationResult, *, name: str) -> dict:
    """Construit le dictionnaire complet (schéma + métadonnées + données)."""
    return {
        "schema": SCHEMA,
        "name": name,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "inputs": inputs_to_dict(inputs),
        "result": result_to_dict(result),
    }


def save_simulation(
    inputs: MLGInputs,
    result: SimulationResult,
    *,
    name: str,
    directory: Path | str = DEFAULT_SAVE_DIR,
) -> Path:
    """Sauvegarde une simulation dans ``directory`` ; renvoie le chemin du fichier."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{_slugify(name)}.json"
    data = bundle(inputs, result, name=name)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_simulation(path: Path | str) -> tuple[MLGInputs, SimulationResult, dict]:
    """Recharge une simulation ; renvoie ``(inputs, result, meta)``.

    ``meta`` contient ``name`` et ``saved_at``. Lève ``ValueError`` si le schéma
    du fichier est inconnu.
    """
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = data.get("schema")
    if schema != SCHEMA:
        raise ValueError(
            f"Schéma de fichier non reconnu : {schema!r} (attendu : {SCHEMA!r})."
        )
    inputs = inputs_from_dict(data["inputs"])
    result = result_from_dict(data["result"])
    meta = {"name": data.get("name", path.stem), "saved_at": data.get("saved_at", "")}
    return inputs, result, meta


def list_saved(directory: Path | str = DEFAULT_SAVE_DIR) -> list[dict]:
    """Liste les simulations sauvegardées (les plus récentes d'abord).

    Chaque entrée : ``{"name", "saved_at", "path"}``. Les fichiers illisibles
    sont ignorés silencieusement.
    """
    directory = Path(directory)
    if not directory.exists():
        return []
    entries: list[dict] = []
    for p in directory.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if data.get("schema") != SCHEMA:
                continue
            entries.append(
                {
                    "name": data.get("name", p.stem),
                    "saved_at": data.get("saved_at", ""),
                    "path": str(p),
                }
            )
        except (json.JSONDecodeError, OSError):
            continue
    entries.sort(key=lambda e: e["saved_at"], reverse=True)
    return entries


def delete_saved(path: Path | str) -> None:
    """Supprime un fichier de sauvegarde (ignore l'absence du fichier)."""
    Path(path).unlink(missing_ok=True)


__all__ = [
    "SCHEMA",
    "DEFAULT_SAVE_DIR",
    "inputs_to_dict",
    "inputs_from_dict",
    "result_to_dict",
    "result_from_dict",
    "bundle",
    "save_simulation",
    "load_simulation",
    "list_saved",
    "delete_saved",
]
