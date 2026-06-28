"""Page unique de saisie et de lancement du mode avion complet.

Toutes les données se saisissent ici. Trois boutons permettent de lancer :
- la simulation avion complet (1 NLG + 2 MLG couplés) ;
- la simulation du train avant (NLG) seul ;
- la simulation du train principal (MLG) seul.

Pour chaque position (NLG, MLG), un sélecteur choisit le type de train
(StraitStrut ou TrailingArm) et le jeu complet de paramètres est éditable, de
sorte qu'un run train isolé dispose de toutes les informations nécessaires.
"""
from __future__ import annotations

import importlib
import json
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_APP = Path(__file__).resolve().parent.parent
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

from dropsim import errors as ds_errors  # noqa: E402
from dropsim import inputs as ds_inputs  # noqa: E402
from dropsim import storage as ds_storage  # noqa: E402
from dropsim.engine_aircraft import OUTPUT_COLUMNS_AC, run_aircraft  # noqa: E402
from dropsim.simulation import run_simulation  # noqa: E402
from components.gear_form import render_gear_form  # noqa: E402
from theme import apply_theme  # noqa: E402

apply_theme()

st.title("Avion complet — Saisie et lancement")
st.caption("Page unique : saisir les données, choisir le type de chaque train, lancer avion complet / NLG seul / MLG seul.")


def _resolve_inputs_api():
    required = (
        "AircraftInputs",
        "AircraftBodyInputs",
        "AircraftSimulationInputs",
        "AircraftDropConfig",
        "AircraftGearLayoutInputs",
        "default_aircraft_inputs",
        "default_strait_strut_inputs",
        "default_trailing_arm_inputs",
    )
    if all(hasattr(ds_inputs, name) for name in required):
        return ds_inputs
    try:
        reloaded = importlib.reload(ds_inputs)
        if all(hasattr(reloaded, name) for name in required):
            return reloaded
    except Exception:
        reloaded = ds_inputs
    pkg = importlib.import_module("dropsim")
    if hasattr(reloaded, "Point3") and all(hasattr(pkg, name) for name in required[:-3]):
        return SimpleNamespace(
            Point3=reloaded.Point3,
            AircraftInputs=pkg.AircraftInputs,
            AircraftBodyInputs=pkg.AircraftBodyInputs,
            AircraftSimulationInputs=pkg.AircraftSimulationInputs,
            AircraftDropConfig=pkg.AircraftDropConfig,
            AircraftGearLayoutInputs=pkg.AircraftGearLayoutInputs,
            default_aircraft_inputs=getattr(pkg, "default_aircraft_inputs", None),
            default_strait_strut_inputs=pkg.default_strait_strut_inputs,
            default_trailing_arm_inputs=pkg.default_trailing_arm_inputs,
        )
    raise AttributeError("dropsim.inputs ne fournit pas les symboles avion requis")


_INPUTS = _resolve_inputs_api()


# --------------------------------------------------------------------------- #
#  Construction du résultat avion complet (pour la page Résultats avion)
# --------------------------------------------------------------------------- #
class _AircraftPageResult:
    def __init__(self, *, df, summary, n_steps, warnings=None, geometry=None, summary_rows=None):
        self.df = df
        self.summary = summary
        self.n_steps = n_steps
        self.warnings = list(warnings or [])
        self.geometry = geometry
        self.summary_rows = list(summary_rows or [])


def _subsample(data: dict[str, np.ndarray], max_points: int = 1000) -> dict[str, np.ndarray]:
    if not data:
        return {}
    n = len(next(iter(data.values())))
    if n <= max_points:
        return data
    step = max(1, n // max_points)
    return {k: v[::step] for k, v in data.items()}


def _negative_pressure_warnings(full: dict[str, np.ndarray]) -> list[ds_errors.SimError]:
    warnings: list[ds_errors.SimError] = []
    temps = full.get("temps")
    keys = [("nlg_pg", "pression gaz NLG"), ("nlg_pc", "pression compression NLG"), ("nlg_pd", "pression détente NLG")]
    for side in ("mlg_left", "mlg_right"):
        for suffix, lbl in (("pg", "pression gaz"), ("pc", "pression compression"), ("pd", "pression détente")):
            keys.append((f"{side}_{suffix}", f"{lbl} {side.replace('_', ' ')}"))
    for key, label in keys:
        series = full.get(key)
        if series is None or len(series) == 0:
            continue
        idx_min = int(np.argmin(series))
        min_val = float(series[idx_min])
        if min_val >= 0.0:
            continue
        t_s = float(temps[idx_min]) if temps is not None and idx_min < len(temps) else float("nan")
        warnings.append(
            ds_errors.SimError(
                code="PRESSION_NEGATIVE",
                message=f"La {label} devient négative: {min_val:.3f} bar (t = {t_s*1000.0:.2f} ms).",
                level=ds_errors.ErrorLevel.RUNTIME,
                field=key,
                hint="Vérifier les conditions d'entrée et les paramètres hydrauliques du train.",
                context={"key": key, "min_bar": min_val, "index": idx_min, "time_s": t_s},
            )
        )
    return warnings


def _build_aircraft_result_locally(engine_out, *, max_points: int = 1000):
    col_map = OUTPUT_COLUMNS_AC
    data = _subsample(engine_out.data, max_points=max_points)
    df = pd.DataFrame({col_map[k]: v for k, v in data.items() if k in col_map})
    geom = _subsample(engine_out.geometry, max_points=max_points) if engine_out.geometry else {}
    geom_df = pd.DataFrame(geom) if geom else None
    if geom_df is not None:
        geom_df.insert(0, "temps", data["temps"])
    full = engine_out.data
    summary = {
        "Course max NLG (mm)": float(np.max(full["nlg_stroke"]) * 1000.0),
        "Course max MLG gauche (mm)": float(np.max(full["mlg_left_stroke"]) * 1000.0),
        "Course max MLG droite (mm)": float(np.max(full["mlg_right_stroke"]) * 1000.0),
        "Effort vertical total max Fz (N)": float(np.max(full["aircraft_fz_total"])),
        "Moment de tangage max (N.m)": float(np.max(np.abs(full["aircraft_mx_total"]))),
        "Couple max en B NLG (N.m)": float(np.max(np.abs(full["nlg_torsb_my"]))),
        "Couple max en B MLG gauche (N.m)": float(np.max(np.abs(full["mlg_left_torsb_my"]))),
        "Couple max en B MLG droite (N.m)": float(np.max(np.abs(full["mlg_right_torsb_my"]))),
        "Accélération CG max (g)": float(np.max(np.abs(full["aircraft_cg_az"])) / 9.81),
        "Nombre de pas": int(engine_out.n_steps),
    }
    warnings = list(engine_out.warnings)
    warnings.extend(_negative_pressure_warnings(full))
    return _AircraftPageResult(df=df, summary=summary, n_steps=engine_out.n_steps, warnings=warnings, geometry=geom_df)


def _run_aircraft_simulation(inputs, *, progress_callback=None):
    params = inputs.to_si()
    engine_out = run_aircraft(params, progress_callback=progress_callback)
    return _build_aircraft_result_locally(engine_out)


def _load_golden_defaults() -> dict | None:
    golden_path = _ROOT / "tests" / "reference" / "golden_default_params.json"
    if golden_path.exists():
        try:
            with open(golden_path) as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _make_default_aircraft_inputs():
    factory = getattr(_INPUTS, "default_aircraft_inputs", None)
    inputs = factory() if callable(factory) else _INPUTS.AircraftInputs()
    golden = _load_golden_defaults()
    if golden:
        body = golden.get("body", {})
        if body:
            inputs.body.masse = float(body.get("masse", inputs.body.masse))
            inputs.body.jyy = float(body.get("jyy", inputs.body.jyy))
            inputs.body.lift = float(body.get("lift", inputs.body.lift))
            cg = body.get("cg", {})
            if cg:
                inputs.body.cg = _INPUTS.Point3(
                    float(cg.get("x", inputs.body.cg.x)),
                    float(cg.get("y", inputs.body.cg.y)),
                    float(cg.get("z", inputs.body.cg.z)),
                )
        drop = golden.get("drop", {})
        if drop:
            inputs.drop.vz = float(drop.get("vz", inputs.drop.vz))
            inputs.drop.vx = float(drop.get("vx", inputs.drop.vx))
            inputs.drop.pitch = float(drop.get("pitch", inputs.drop.pitch))
            inputs.drop.pitch_rate_deg_s = float(drop.get("pitch_rate_deg_s", inputs.drop.pitch_rate_deg_s))
        layout = golden.get("layout", {})
        for key in ("nlg_station", "mlg_left_station", "mlg_right_station"):
            cfg = layout.get(key, {})
            if cfg:
                cur = getattr(inputs.layout, key)
                setattr(inputs.layout, key, _INPUTS.Point3(
                    float(cfg.get("x", cur.x)), float(cfg.get("y", cur.y)), float(cfg.get("z", cur.z))))
        sim = golden.get("simulation", {})
        if sim:
            inputs.simulation.temps_simu = float(sim.get("temps_simu", inputs.simulation.temps_simu))
            inputs.simulation.it = float(sim.get("it", inputs.simulation.it))
            inputs.simulation.integrator = str(sim.get("integrator", inputs.simulation.integrator))
            inputs.simulation.temperature = float(sim.get("temperature", inputs.simulation.temperature))
    return inputs


def _is_aircraft_inputs_like(obj: Any) -> bool:
    return (
        getattr(obj, "model_kind", "") == "aircraft"
        and all(hasattr(obj, a) for a in ("body", "simulation", "drop", "layout", "nlg", "mlg"))
    )


def _ensure_state() -> None:
    if "aircraft_inputs" not in st.session_state or not _is_aircraft_inputs_like(st.session_state.aircraft_inputs):
        st.session_state.aircraft_inputs = _make_default_aircraft_inputs()
    st.session_state.setdefault("aircraft_result", None)
    st.session_state.setdefault("aircraft_result_name", "Simulation avion complet")
    st.session_state.setdefault("aircraft_nlg_result", None)
    st.session_state.setdefault("aircraft_mlg_result", None)
    st.session_state.setdefault("aircraft_current_project", ds_storage.DEFAULT_PROJECT)


_ensure_state()
inp: Any = st.session_state.aircraft_inputs


# --------------------------------------------------------------------------- #
#  Barre de lancement — toujours visible (sticky en haut de page)
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <style>
    /* Barre de lancement collée SOUS l'en-tête de navigation Streamlit
       (header [data-testid="stHeader"] : ~3.75rem de haut, z-index très élevé). */
    div[data-testid="stVerticalBlock"] > div:has(div.ac-launch-anchor) {
        position: sticky;
        top: 3.75rem;
        z-index: 99;
        background-color: var(--background-color, #ffffff);
        padding: 0.5rem 0;
        border-bottom: 1px solid rgba(128, 128, 128, 0.25);
        box-shadow: 0 4px 8px -6px rgba(0, 0, 0, 0.35);
    }
    </style>
    """,
    unsafe_allow_html=True,
)
_launch_bar = st.container()
with _launch_bar:
    st.markdown('<div class="ac-launch-anchor"></div>', unsafe_allow_html=True)
    _lb1, _lb2, _lb3 = st.columns(3)
    launch_ac = _lb1.button("▶️ Avion complet", type="primary", use_container_width=True)
    launch_nlg = _lb2.button("Lancer NLG seul", use_container_width=True)
    launch_mlg = _lb3.button("Lancer MLG seul", use_container_width=True)
    # Conteneur de statut (progression / messages) DANS la barre sticky : reste
    # visible avec les boutons même quand on a fait défiler la page.
    _launch_msg = st.container()


def _num(label: str, key: str, value: float, *, step: float = 1.0, min_value=None) -> float:
    if key not in st.session_state:
        st.session_state[key] = float(value)
    return float(st.number_input(label, key=key, step=step, min_value=min_value))


def _decimal_places(*values: float) -> int:
    decimals = 0
    for value in values:
        exponent = Decimal(format(float(value), ".16g")).as_tuple().exponent
        decimals = max(decimals, -exponent if exponent < 0 else 0)
    return decimals


def _num_precise(label: str, key: str, value: float, *, step: float, min_value=None) -> float:
    if key not in st.session_state:
        st.session_state[key] = float(value)
    decimals = _decimal_places(value, step)
    return float(st.number_input(label, key=key, step=step, min_value=min_value, format=f"%.{decimals}f"))


# --------------------------------------------------------------------------- #
#  Sauvegarde / chargement
# --------------------------------------------------------------------------- #
def _set_loaded_aircraft_state(inputs: Any, result, *, name: str, project: str) -> None:
    st.session_state.aircraft_inputs = inputs
    st.session_state.aircraft_result = result
    st.session_state.aircraft_result_name = name
    st.session_state.aircraft_current_project = project
    # Purge des états de formulaire pour réamorcer depuis les inputs chargés.
    for k in list(st.session_state.keys()):
        if k.startswith("ac_nlg") or k.startswith("ac_mlg") or k.startswith("ac_body") \
                or k.startswith("ac_sim") or k.startswith("ac_drop") or k.startswith("ac_cg") \
                or k.startswith("ac_lay"):
            del st.session_state[k]


with st.expander("Sauvegarder / charger une simulation avion complet", expanded=False):
    projects = ds_storage.list_projects()
    new_project_label = "+ Nouveau projet"
    col_save, col_load = st.columns(2)
    with col_save:
        st.markdown("**Sauvegarder la simulation courante**")
        if st.session_state.aircraft_result is None:
            st.caption("Aucun résultat avion complet à sauvegarder.")
        else:
            current_project = st.session_state.get("aircraft_current_project", ds_storage.DEFAULT_PROJECT)
            save_options = projects + [new_project_label]
            save_index = projects.index(current_project) if current_project in projects else len(save_options) - 1
            project_choice = st.selectbox("Projet", save_options, index=save_index, key="ac_save_project_choice")
            if project_choice == new_project_label:
                project_name = st.text_input(
                    "Nom du nouveau projet", value="" if current_project in projects else current_project,
                    key="ac_save_project_new", placeholder=ds_storage.DEFAULT_PROJECT,
                ).strip() or ds_storage.DEFAULT_PROJECT
            else:
                project_name = project_choice
            save_name = st.text_input("Nom de la sauvegarde",
                                      value=st.session_state.get("aircraft_result_name", "Simulation avion complet"),
                                      key="ac_save_name")
            if st.button("Enregistrer", key="ac_save_btn", use_container_width=True):
                path = ds_storage.save_simulation(
                    st.session_state.aircraft_inputs, st.session_state.aircraft_result,
                    name=save_name, project=project_name)
                st.session_state.aircraft_result_name = save_name
                st.session_state.aircraft_current_project = project_name
                st.success(f"Sauvegarde enregistrée: {path.name}", icon="✅")
    with col_load:
        st.markdown("**Charger une simulation avion complet**")
        if not projects:
            st.caption("Aucune sauvegarde disponible.")
        else:
            current_project = st.session_state.get("aircraft_current_project", ds_storage.DEFAULT_PROJECT)
            load_index = projects.index(current_project) if current_project in projects else 0
            project_name = st.selectbox("Projet", projects, index=load_index, key="ac_load_project")
            entries = [e for e in ds_storage.list_saved(project=project_name) if e.get("project") == project_name]
            if not entries:
                st.caption("Aucune sauvegarde dans ce projet.")
            else:
                labels = {f"{e['name']} · {e['saved_at'][:16].replace('T', ' ')}": e["path"] for e in entries}
                selected = st.selectbox("Sauvegardes disponibles", list(labels.keys()), key="ac_load_choice")
                load_col, del_col = st.columns(2)
                if load_col.button("Charger", key="ac_load_btn", use_container_width=True):
                    loaded_inputs, loaded_result, meta = ds_storage.load_simulation(labels[selected])
                    if getattr(loaded_inputs, "model_kind", "") != "aircraft":
                        st.error("La sauvegarde sélectionnée n'est pas une simulation avion complet.", icon="🛑")
                    else:
                        _set_loaded_aircraft_state(loaded_inputs, loaded_result,
                                                   name=meta.get("name", "Simulation avion complet"),
                                                   project=meta.get("project", ds_storage.DEFAULT_PROJECT))
                        st.rerun()
                if del_col.button("Supprimer", key="ac_delete_btn", use_container_width=True):
                    ds_storage.delete_saved(labels[selected])
                    st.rerun()


# --------------------------------------------------------------------------- #
#  Blocs globaux avion
# --------------------------------------------------------------------------- #
st.subheader("Paramètres avion (corps)")
a, b, c = st.columns(3)
with a:
    _num("Masse avion (kg)", "ac_body_masse", inp.body.masse, step=10.0, min_value=0.0)
    _num("Inertie Jyy (kg.m²)", "ac_body_jyy", inp.body.jyy, step=100.0, min_value=0.0)
    _num("Lift (0..1)", "ac_body_lift", inp.body.lift, step=0.01, min_value=0.0)
with b:
    _num("CG X (mm)", "ac_cg_x", inp.body.cg.x, step=10.0)
    _num("CG Y (mm)", "ac_cg_y", inp.body.cg.y, step=10.0)
    _num("CG Z (mm)", "ac_cg_z", inp.body.cg.z, step=10.0)
with c:
    _num("Pitch avion initial (°)", "ac_drop_pitch", inp.drop.pitch, step=0.1)
    st.caption("Repère avion : X longitudinal, Y latéral, Z vertical.")

st.subheader("Simulation et chute")
a, b = st.columns(2)
with a:
    _num("Durée simulation (s)", "ac_sim_t", inp.simulation.temps_simu, step=0.1, min_value=0.0)
    _num_precise("Pas de temps (s)", "ac_sim_dt", inp.simulation.it, step=1e-6, min_value=1e-8)
    _num_precise("Tol. hydraulique", "ac_sim_hyd_tol", inp.simulation.hydraulic_error_tol, step=1e-6, min_value=1e-8)
    _num("Iter max hydraulique", "ac_sim_hyd_iter", float(inp.simulation.hydraulic_max_iter), step=1.0, min_value=4.0)
with b:
    st.selectbox("Solveur noyau", ["auto_fast", "auto_precise"], key="ac_sim_solver",
                 index=0 if inp.simulation.damper_core_solver == "auto_fast" else 1)
    _num("Température (°C)", "ac_sim_temp", inp.simulation.temperature, step=1.0)
    _num("Vz initiale (m/s)", "ac_drop_vz", inp.drop.vz, step=0.1)
    _num("Vx initiale (m/s)", "ac_drop_vx", inp.drop.vx, step=0.5)
    _num("Pitch rate initial (°/s)", "ac_drop_pitch_rate", inp.drop.pitch_rate_deg_s, step=0.1)

st.subheader("Géométrie d'implantation des trains (stations, mm)")
nlg_col, mlg_l_col, mlg_r_col = st.columns(3)
with nlg_col:
    st.markdown("**Station NLG**")
    _num("NLG X", "ac_nlg_x", inp.layout.nlg_station.x, step=10.0)
    _num("NLG Y", "ac_nlg_y", inp.layout.nlg_station.y, step=10.0)
    _num("NLG Z", "ac_nlg_z", inp.layout.nlg_station.z, step=10.0)
with mlg_l_col:
    st.markdown("**Station MLG gauche**")
    _num("MLGg X", "ac_mlg_l_x", inp.layout.mlg_left_station.x, step=10.0)
    _num("MLGg Y", "ac_mlg_l_y", inp.layout.mlg_left_station.y, step=10.0)
    _num("MLGg Z", "ac_mlg_l_z", inp.layout.mlg_left_station.z, step=10.0)
with mlg_r_col:
    st.markdown("**Station MLG droite**")
    _num("MLGd X", "ac_mlg_r_x", inp.layout.mlg_right_station.x, step=10.0)
    _num("MLGd Y", "ac_mlg_r_y", inp.layout.mlg_right_station.y, step=10.0)
    _num("MLGd Z", "ac_mlg_r_z", inp.layout.mlg_right_station.z, step=10.0)


# --------------------------------------------------------------------------- #
#  Formulaires de train (type + jeu complet de paramètres)
# --------------------------------------------------------------------------- #
st.divider()
st.subheader("Train avant (NLG)")
nlg_inputs = render_gear_form("NLG", "ac_nlg", inp.nlg)

st.divider()
st.subheader("Train principal (MLG)")
mlg_inputs = render_gear_form("MLG", "ac_mlg", inp.mlg)


def _build_aircraft_inputs():
    return _INPUTS.AircraftInputs(
        model_kind="aircraft",
        body=_INPUTS.AircraftBodyInputs(
            masse=float(st.session_state.ac_body_masse),
            jyy=float(st.session_state.ac_body_jyy),
            lift=float(st.session_state.ac_body_lift),
            cg=_INPUTS.Point3(float(st.session_state.ac_cg_x), float(st.session_state.ac_cg_y), float(st.session_state.ac_cg_z)),
        ),
        simulation=_INPUTS.AircraftSimulationInputs(
            temps_simu=float(st.session_state.ac_sim_t),
            it=float(st.session_state.ac_sim_dt),
            integrator=str(inp.simulation.integrator),
            damper_core_solver=str(st.session_state.ac_sim_solver),
            hydraulic_error_tol=float(st.session_state.ac_sim_hyd_tol),
            hydraulic_max_iter=int(st.session_state.ac_sim_hyd_iter),
            temperature=float(st.session_state.ac_sim_temp),
        ),
        drop=_INPUTS.AircraftDropConfig(
            vz=float(st.session_state.ac_drop_vz),
            vx=float(st.session_state.ac_drop_vx),
            pitch=float(st.session_state.ac_drop_pitch),
            pitch_rate_deg_s=float(st.session_state.ac_drop_pitch_rate),
        ),
        layout=_INPUTS.AircraftGearLayoutInputs(
            nlg_station=_INPUTS.Point3(float(st.session_state.ac_nlg_x), float(st.session_state.ac_nlg_y), float(st.session_state.ac_nlg_z)),
            mlg_left_station=_INPUTS.Point3(float(st.session_state.ac_mlg_l_x), float(st.session_state.ac_mlg_l_y), float(st.session_state.ac_mlg_l_z)),
            mlg_right_station=_INPUTS.Point3(float(st.session_state.ac_mlg_r_x), float(st.session_state.ac_mlg_r_y), float(st.session_state.ac_mlg_r_z)),
        ),
        nlg=nlg_inputs,
        mlg=mlg_inputs,
    )


# --------------------------------------------------------------------------- #
#  Traitement des lancements (boutons créés dans la barre sticky en haut)
# --------------------------------------------------------------------------- #
def _run_single_gear(position: str, store_key: str):
    inputs = _build_aircraft_inputs()
    st.session_state.aircraft_inputs = inputs
    gear = inputs.gear_inputs_for(position)
    collector = gear.validate()
    if collector.has_errors:
        _launch_msg.error(f"Validation {position.upper()} invalide.", icon="🛑")
        for err in collector.errors:
            _launch_msg.error(f"{err.field or 'général'}: {err.message}")
        return
    try:
        progress = _launch_msg.progress(0.0)

        def _cb(cur, total):
            if total > 0:
                progress.progress(min(1.0, cur / total))

        result = run_simulation(gear, progress_callback=_cb)
        progress.empty()
        st.session_state[store_key] = result
        _launch_msg.success(
            f"Calcul {position.upper()} seul terminé. "
            f"Voir l'onglet « {position.upper()} seul » dans la page Résultats avion.",
            icon="✅",
        )
    except ds_errors.SimError as exc:
        st.session_state[store_key] = None
        _launch_msg.error(f"{exc.code}: {exc.message}", icon="🛑")


if launch_ac:
    aircraft_inputs = _build_aircraft_inputs()
    st.session_state.aircraft_inputs = aircraft_inputs
    collector = aircraft_inputs.validate()
    if collector.has_errors:
        _launch_msg.error("Validation invalide. Corriger les champs et relancer.", icon="🛑")
        for err in collector.errors:
            _launch_msg.error(f"{err.field or 'général'}: {err.message}")
    else:
        try:
            progress = _launch_msg.progress(0.0)

            def _cb(cur, total):
                if total > 0:
                    progress.progress(min(1.0, cur / total))

            result = _run_aircraft_simulation(aircraft_inputs, progress_callback=_cb)
            progress.empty()
            st.session_state.aircraft_result = result
            st.session_state.aircraft_result_name = "Simulation avion complet"
            _launch_msg.success("Calcul avion terminé. Voir la page Résultats avion.", icon="✅")
        except ds_errors.SimError as exc:
            _launch_msg.error(f"{exc.code}: {exc.message}", icon="🛑")

if launch_nlg:
    _run_single_gear("nlg", "aircraft_nlg_result")
if launch_mlg:
    _run_single_gear("mlg", "aircraft_mlg_result")


# --------------------------------------------------------------------------- #
#  Résultats
# --------------------------------------------------------------------------- #
res = st.session_state.aircraft_result
if res is not None:
    st.divider()
    st.subheader("Résumé avion complet")
    m1, m2, m3 = st.columns(3)
    m1.metric("Pas", f"{res.n_steps}")
    m2.metric("Fz total max", f"{res.summary.get('Effort vertical total max Fz (N)', 0.0):.0f} N")
    m3.metric("Acc CG max", f"{res.summary.get('Accélération CG max (g)', 0.0):.3f} g")
    n1, n2, n3 = st.columns(3)
    n1.metric("Moment tangage max", f"{res.summary.get('Moment de tangage max (N.m)', 0.0):.0f} N·m")
    n2.metric("Couple max en B — NLG", f"{res.summary.get('Couple max en B NLG (N.m)', 0.0):.0f} N·m",
              help="Couple de flexion transmis au fuselage à l'encastrement B du train avant (axe de tangage).")
    _mlg_couple = max(res.summary.get('Couple max en B MLG gauche (N.m)', 0.0),
                      res.summary.get('Couple max en B MLG droite (N.m)', 0.0))
    n3.metric("Couple max en B — MLG", f"{_mlg_couple:.0f} N·m",
              help="Non nul seulement si un MLG est de type StraitStrut (encastrement). 0 pour un TrailingArm (pivot).")
    # Avertissements du résultat affichés dans la zone des boutons (barre sticky).
    for w in getattr(res, "warnings", []) or []:
        if getattr(w, "code", "") == "SUR_ENFONCEMENT":
            _launch_msg.warning(f"⚠️ {w.message}\n\n💡 {w.hint}")
        else:
            _launch_msg.warning(str(w))

if st.session_state.get("aircraft_nlg_result") is not None or \
        st.session_state.get("aircraft_mlg_result") is not None:
    st.divider()
    st.info(
        "Les résultats des simulations train isolé (NLG seul / MLG seul) sont "
        "affichés dans la page **Résultats avion**, onglets « NLG seul » / « MLG seul » "
        "(avec toutes les courbes et le bilan énergétique).",
        icon="➡️",
    )
