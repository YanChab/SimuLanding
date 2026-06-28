"""Sauvegarde et rechargement des simulations (entrées + résultats).

Sérialise une simulation complète (les entrées :class:`~dropsim.inputs.TrailingArmInputs`
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

from .inputs import (
    AircraftBodyInputs,
    AircraftDropConfig,
    AircraftGearDropOverride,
    AircraftGearLayoutInputs,
    AircraftInputs,
    AircraftSimulationInputs,
    Point3,
    Rainure,
    StraitStrutInputs,
    StraitStrutDragBraceInputs,
    TrailingArmInputs,
    TrailingArmDragBraceInputs,
)
from .simulation import SimulationResult

# Version du schéma de fichier (incrémentée si le format évolue de façon incompatible).
SCHEMA = "simuland/1"

# Dossier de sauvegarde par défaut (à la racine du dépôt).
DEFAULT_SAVE_DIR = Path(__file__).resolve().parent.parent / "saved_simulations"

# Projet par défaut (classe les sauvegardes sans projet explicite).
DEFAULT_PROJECT = "Général"


# --------------------------------------------------------------------------- #
#  Sérialisation des entrées
# --------------------------------------------------------------------------- #
def inputs_to_dict(inputs: AircraftInputs | TrailingArmInputs | StraitStrutInputs) -> dict:
    """Convertit ``TrailingArmInputs`` en dictionnaire JSON-compatible."""
    return asdict(inputs)


def _coerce_trailing_like_inputs(data: dict, cls: type[TrailingArmInputs] | type[StraitStrutInputs]) -> dict:
    out = dict(data)
    if out.get("damper_core_solver") in {"legacy", "implicit_adaptive", "auto"}:
        out["damper_core_solver"] = "auto_precise"
    for key in ("B", "A", "C", "R", "S", "Gt", "Gb", "B1", "B2", "Cdb", "Ddb",
                "F1", "F2", "Dbr", "Ebr"):
        if key in out and isinstance(out[key], dict):
            out[key] = Point3(**out[key])
    if "rainures" in out:
        out["rainures"] = [
            Rainure(**r) if isinstance(r, dict) else Rainure(*r)
            for r in out["rainures"]
        ]
    if "tyre_curve" in out:
        out["tyre_curve"] = [tuple(t) for t in out["tyre_curve"]]
    if "mu_curve" in out:
        out["mu_curve"] = [tuple(t) for t in out["mu_curve"]]
    known = {f.name for f in fields(cls)}
    return {k: v for k, v in out.items() if k in known}


def inputs_from_dict(d: dict) -> AircraftInputs | TrailingArmInputs | StraitStrutInputs:
    """Reconstruit des entrées depuis un dictionnaire (robuste aux clés en trop)."""
    model_kind = d.get("model_kind", "trailing_arm")
    if model_kind == "aircraft":
        body = d.get("body", {})
        simulation = d.get("simulation", {})
        drop = d.get("drop", {})
        layout = d.get("layout", {})
        nlg = d.get("nlg", {})
        mlg = d.get("mlg", {})

        if "cg" in body and isinstance(body["cg"], dict):
            body = dict(body)
            body["cg"] = Point3(**body["cg"])
        for key in ("nlg_station", "mlg_left_station", "mlg_right_station"):
            if key in layout and isinstance(layout[key], dict):
                layout = dict(layout)
                layout[key] = Point3(**layout[key])

        # Type de train par position : on lit le model_kind du sous-dict, avec
        # repli sur la convention historique (NLG StraitStrut, MLG TrailingArm)
        # pour les sauvegardes antérieures au choix de type par position.
        def _gear_cls(sub: dict, default_kind: str) -> type:
            kind = sub.get("model_kind", default_kind)
            if kind == "strait_strut_drag_brace":
                return StraitStrutDragBraceInputs
            if kind == "trailing_arm_drag_brace":
                return TrailingArmDragBraceInputs
            return StraitStrutInputs if kind == "strait_strut" else TrailingArmInputs

        def _override(sub: dict) -> AircraftGearDropOverride:
            known = {f.name for f in fields(AircraftGearDropOverride)}
            return AircraftGearDropOverride(**{k: v for k, v in sub.items() if k in known})

        nlg_cls = _gear_cls(nlg, "strait_strut")
        mlg_cls = _gear_cls(mlg, "trailing_arm")

        return AircraftInputs(
            model_kind="aircraft",
            body=AircraftBodyInputs(**{k: v for k, v in body.items() if k in {f.name for f in fields(AircraftBodyInputs)}}),
            simulation=AircraftSimulationInputs(
                **{k: v for k, v in simulation.items() if k in {f.name for f in fields(AircraftSimulationInputs)}}
            ),
            drop=AircraftDropConfig(**{k: v for k, v in drop.items() if k in {f.name for f in fields(AircraftDropConfig)}}),
            layout=AircraftGearLayoutInputs(
                **{k: v for k, v in layout.items() if k in {f.name for f in fields(AircraftGearLayoutInputs)}}
            ),
            nlg=nlg_cls(**_coerce_trailing_like_inputs(nlg, nlg_cls)),
            mlg=mlg_cls(**_coerce_trailing_like_inputs(mlg, mlg_cls)),
            nlg_drop=_override(d.get("nlg_drop", {})),
            mlg_drop=_override(d.get("mlg_drop", {})),
        )

    if model_kind == "strait_strut_drag_brace":
        cls = StraitStrutDragBraceInputs
    elif model_kind == "strait_strut":
        cls = StraitStrutInputs
    elif model_kind == "trailing_arm_drag_brace":
        cls = TrailingArmDragBraceInputs
    else:
        cls = TrailingArmInputs
    data = _coerce_trailing_like_inputs(d, cls)
    return cls(**data)


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


def _project_dir(directory: Path | str, project: str | None) -> Path:
    """Sous-dossier physique d'un projet (un slug par projet)."""
    return Path(directory) / _slugify(project or DEFAULT_PROJECT)


def bundle(
    inputs: AircraftInputs | TrailingArmInputs | StraitStrutInputs,
    result: SimulationResult,
    *,
    name: str,
    project: str = DEFAULT_PROJECT,
) -> dict:
    """Construit le dictionnaire complet (schéma + métadonnées + données)."""
    return {
        "schema": SCHEMA,
        "name": name,
        "project": project or DEFAULT_PROJECT,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "inputs": inputs_to_dict(inputs),
        "result": result_to_dict(result),
    }


def save_simulation(
    inputs: AircraftInputs | TrailingArmInputs | StraitStrutInputs,
    result: SimulationResult,
    *,
    name: str,
    project: str = DEFAULT_PROJECT,
    directory: Path | str = DEFAULT_SAVE_DIR,
) -> Path:
    """Sauvegarde une simulation (classée par ``project``) ; renvoie le chemin.

    Les simulations sont rangées dans un sous-dossier par projet
    (``directory/<projet>/<nom>.json``) et le nom du projet est aussi inscrit
    dans les métadonnées du fichier.
    """
    pdir = _project_dir(directory, project)
    pdir.mkdir(parents=True, exist_ok=True)
    path = pdir / f"{_slugify(name)}.json"
    data = bundle(inputs, result, name=name, project=project)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_simulation(path: Path | str) -> tuple[AircraftInputs | TrailingArmInputs | StraitStrutInputs, SimulationResult, dict]:
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
    meta = {
        "name": data.get("name", path.stem),
        "saved_at": data.get("saved_at", ""),
        "project": data.get("project") or DEFAULT_PROJECT,
    }
    return inputs, result, meta


def _read_meta(path: Path) -> dict | None:
    """Lit les métadonnées d'un fichier de sauvegarde (ou ``None`` si invalide)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        return None
    if data.get("kind") == "bundle":
        contents = list((data.get("items") or {}).keys())
        return {
            "name": data.get("name", path.stem),
            "saved_at": data.get("saved_at", ""),
            "project": data.get("project") or DEFAULT_PROJECT,
            "model_kind": "bundle",
            "contents": contents,
            "path": str(path),
        }
    return {
        "name": data.get("name", path.stem),
        "saved_at": data.get("saved_at", ""),
        "project": data.get("project") or DEFAULT_PROJECT,
        "model_kind": (data.get("inputs") or {}).get("model_kind", "trailing_arm"),
        "contents": [],
        "path": str(path),
    }


def list_projects(directory: Path | str = DEFAULT_SAVE_DIR) -> list[str]:
    """Liste les noms de projets contenant au moins une sauvegarde (triés)."""
    directory = Path(directory)
    if not directory.exists():
        return []
    names: set[str] = set()
    for p in directory.rglob("*.json"):
        try:
            meta = _read_meta(p)
        except (json.JSONDecodeError, OSError):
            continue
        if meta:
            names.add(meta["project"])
    return sorted(names, key=str.casefold)


def list_saved(
    directory: Path | str = DEFAULT_SAVE_DIR,
    project: str | None = None,
) -> list[dict]:
    """Liste les simulations sauvegardées (les plus récentes d'abord).

    Si ``project`` est fourni, seules les sauvegardes de ce projet sont
    renvoyées. Chaque entrée : ``{"name", "saved_at", "project", "path"}``.
    Les fichiers illisibles sont ignorés silencieusement.
    """
    directory = Path(directory)
    if not directory.exists():
        return []
    entries: list[dict] = []
    for p in directory.rglob("*.json"):
        try:
            meta = _read_meta(p)
        except (json.JSONDecodeError, OSError):
            continue
        if not meta:
            continue
        if project is not None and meta["project"] != project:
            continue
        entries.append(meta)
    entries.sort(key=lambda e: e["saved_at"], reverse=True)
    return entries


def delete_saved(path: Path | str) -> None:
    """Supprime un fichier de sauvegarde + ses compagnons lisibles (.md, CSV résultats)."""
    p = Path(path)
    p.unlink(missing_ok=True)
    p.with_suffix(".md").unlink(missing_ok=True)
    p.with_suffix(".csv").unlink(missing_ok=True)  # ancien format (CSV unique)
    stem = p.with_suffix("")
    for csv in p.parent.glob(f"{stem.name}__*.csv"):
        csv.unlink(missing_ok=True)


# --------------------------------------------------------------------------- #
#  Sauvegarde groupée (bundle) + export lisible (CSV)
# --------------------------------------------------------------------------- #
from dataclasses import is_dataclass  # noqa: E402

_BUNDLE_LABELS = {"aircraft": "Avion complet", "nlg": "NLG seul", "mlg": "MLG seul"}


def _flatten_params(obj, prefix: str = "") -> list[tuple[str, object]]:
    """Aplatissement récursif des paramètres d'un objet d'entrées en lignes
    (paramètre, valeur) lisibles. Les Point3 sont éclatés en .x/.y/.z ; les listes
    de dataclasses (rainures) sont indexées ; les grandes courbes (pneu, mu) sont
    résumées par leur nombre de points."""
    rows: list[tuple[str, object]] = []
    if is_dataclass(obj):
        for f in fields(obj):
            rows += _flatten_params(getattr(obj, f.name), f"{prefix}{f.name}.")
    elif isinstance(obj, (list, tuple)):
        if obj and is_dataclass(obj[0]):
            for k, item in enumerate(obj):
                rows += _flatten_params(item, f"{prefix[:-1]}[{k}].")
        else:
            rows.append((prefix.rstrip("."), f"[{len(obj)} points]"))
    elif isinstance(obj, dict):
        rows.append((prefix.rstrip("."), "[…]"))
    else:
        rows.append((prefix.rstrip("."), obj))
    return rows


def _fmt_val(value) -> str:
    if isinstance(value, bool):
        return "oui" if value else "non"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _md_table(rows: list[tuple[str, object]]) -> str:
    """Table Markdown (Paramètre | Valeur)."""
    out = ["| Paramètre | Valeur |", "|---|---|"]
    for param, value in rows:
        out.append(f"| {param} | {_fmt_val(value)} |")
    return "\n".join(out) + "\n"


def config_markdown(items: dict, *, name: str = "") -> str:
    """Document **Markdown** lisible : paramètres de simulation + configuration
    complète de l'avion et des trains. ``items`` : dict ``{clé: inputs}``."""
    md: list[str] = [f"# Configuration de simulation — {name}".rstrip(" —"), ""]
    for key in ("aircraft", "nlg", "mlg"):
        inp = items.get(key)
        if inp is None:
            continue
        md.append(f"## {_BUNDLE_LABELS[key]}")
        md.append("")
        if getattr(inp, "model_kind", "") == "aircraft":
            # Sous-sections par bloc (corps, simulation, chute, implantation, trains).
            _sub = {"body": "Corps", "simulation": "Simulation", "drop": "Chute",
                    "layout": "Implantation des trains", "nlg": "Train avant (NLG)",
                    "mlg": "Train principal (MLG)", "nlg_drop": "Surcharge chute NLG",
                    "mlg_drop": "Surcharge chute MLG"}
            for f in fields(inp):
                v = getattr(inp, f.name)
                if not is_dataclass(v):
                    continue
                title = _sub.get(f.name, f.name)
                if f.name in ("nlg", "mlg"):
                    title += f" — type : {getattr(v, 'model_kind', '')}"
                md.append(f"### {title}")
                md.append("")
                md.append(_md_table(_flatten_params(v)))
        else:
            md.append(f"*Type de train : {getattr(inp, 'model_kind', '')}*")
            md.append("")
            md.append(_md_table(_flatten_params(inp)))
    return "\n".join(md) + "\n"


def result_csv_text(result: SimulationResult) -> str:
    """CSV des **résultats** (séries temporelles) d'une simulation. Utilise les
    colonnes complètes si disponibles (mode avion). Directive ``sep=;`` pour qu'Excel
    ouvre directement en colonnes."""
    df = result.full_df if getattr(result, "full_df", None) is not None else result.df
    return "sep=;\n" + df.to_csv(index=False, sep=";")


def save_bundle(
    items: dict,
    *,
    name: str,
    project: str = DEFAULT_PROJECT,
    directory: Path | str = DEFAULT_SAVE_DIR,
) -> Path:
    """Sauvegarde groupée : un fichier JSON (rechargeable) contenant le sous-ensemble
    fourni parmi {aircraft, nlg, mlg}, **plus** un CSV compagnon lisible des
    paramètres. ``items`` : dict ``{clé: (inputs, result)}``. Renvoie le chemin JSON."""
    present = {k: v for k, v in items.items() if v is not None}
    if not present:
        raise ValueError("Rien à sauvegarder (aucun résultat sélectionné).")
    pdir = _project_dir(directory, project)
    pdir.mkdir(parents=True, exist_ok=True)
    path = pdir / f"{_slugify(name)}.json"
    data = {
        "schema": SCHEMA,
        "kind": "bundle",
        "name": name,
        "project": project or DEFAULT_PROJECT,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "items": {
            k: {"inputs": inputs_to_dict(inp), "result": result_to_dict(res)}
            for k, (inp, res) in present.items()
        },
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    # Compagnons lisibles : Markdown (config/paramètres) + CSV (résultats par élément).
    md_text = config_markdown({k: inp for k, (inp, res) in present.items()}, name=name)
    path.with_suffix(".md").write_text(md_text, encoding="utf-8")
    stem = path.with_suffix("")
    for k, (inp, res) in present.items():
        stem.with_name(f"{stem.name}__{k}.csv").write_text(
            result_csv_text(res), encoding="utf-8-sig")
    return path


def load_bundle(path: Path | str) -> dict:
    """Charge un fichier de sauvegarde (bundle OU simple, rétro-compatible).

    Renvoie ``{"kind", "name", "project", "saved_at", "items": {clé: (inputs, result)}}``
    où, pour un fichier simple, ``items`` contient une seule entrée déduite du
    ``model_kind`` (aircraft → 'aircraft', sinon le train isolé)."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError(f"Schéma non reconnu : {data.get('schema')!r}.")
    meta = {
        "name": data.get("name", path.stem),
        "project": data.get("project") or DEFAULT_PROJECT,
        "saved_at": data.get("saved_at", ""),
    }
    if data.get("kind") == "bundle":
        items = {
            k: (inputs_from_dict(v["inputs"]), result_from_dict(v["result"]))
            for k, v in data.get("items", {}).items()
        }
        return {"kind": "bundle", **meta, "items": items}
    # Fichier simple (format historique).
    inp = inputs_from_dict(data["inputs"])
    res = result_from_dict(data["result"])
    key = "aircraft" if getattr(inp, "model_kind", "") == "aircraft" else "gear"
    return {"kind": "single", **meta, "items": {key: (inp, res)}}


__all__ = [
    "SCHEMA",
    "DEFAULT_SAVE_DIR",
    "DEFAULT_PROJECT",
    "inputs_to_dict",
    "inputs_from_dict",
    "result_to_dict",
    "result_from_dict",
    "bundle",
    "save_simulation",
    "load_simulation",
    "save_bundle",
    "load_bundle",
    "config_markdown",
    "result_csv_text",
    "list_projects",
    "list_saved",
    "delete_saved",
]
