"""Page de saisie dédiée au mode avion complet (lot 4).

Cette page gère un état Streamlit séparé pour le mode aircraft :
- `aircraft_inputs` : dernière saisie validée ou en cours ;
- `aircraft_result` : dernier résultat calculé ;
- `aircraft_result_name` : nom logique du résultat ;
- `aircraft_ui_state` : préférences d'affichage de la page.
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
from theme import apply_theme  # noqa: E402

apply_theme()

st.title("Avion complet - Saisie")
st.caption("V1 2 DDL: translation verticale CG + tangage, avec 1 NLG + 2 MLG.")


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

    for key, label in (("nlg_pg", "pression gaz NLG"), ("nlg_pc", "pression compression NLG"), ("nlg_pd", "pression détente NLG")):
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

    for side in ("mlg_left", "mlg_right"):
        for suffix, label in (("pg", "pression gaz"), ("pc", "pression compression"), ("pd", "pression détente")):
            key = f"{side}_{suffix}"
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
                    message=(
                        f"La {label} {side.replace('_', ' ')} devient négative: "
                        f"{min_val:.3f} bar (t = {t_s*1000.0:.2f} ms)."
                    ),
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
        "Accélération CG max (g)": float(np.max(np.abs(full["aircraft_cg_az"])) / 9.81),
        "Nombre de pas": int(engine_out.n_steps),
    }
    warnings = list(engine_out.warnings)
    warnings.extend(_negative_pressure_warnings(full))
    return _AircraftPageResult(
        df=df,
        summary=summary,
        n_steps=engine_out.n_steps,
        warnings=warnings,
        geometry=geom_df,
        summary_rows=[],
    )


def _run_aircraft_simulation(inputs, *, progress_callback=None):
    params = inputs.to_si()
    engine_out = run_aircraft(params, progress_callback=progress_callback)
    return _build_aircraft_result_locally(engine_out)


def _load_golden_defaults() -> dict | None:
    """Load default aircraft parameters from the golden reference file if available."""
    golden_path = Path(__file__).resolve().parent.parent.parent / "tests" / "reference" / "golden_default_params.json"
    if golden_path.exists():
        try:
            with open(golden_path) as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _make_default_aircraft_inputs():
    factory = getattr(_INPUTS, "default_aircraft_inputs", None)
    golden_defaults = _load_golden_defaults()
    
    if callable(factory):
        inputs = factory()
    else:
        inputs = _INPUTS.AircraftInputs(
            model_kind="aircraft",
            body=_INPUTS.AircraftBodyInputs(),
            simulation=_INPUTS.AircraftSimulationInputs(),
            drop=_INPUTS.AircraftDropConfig(),
            layout=_INPUTS.AircraftGearLayoutInputs(),
            nlg=_INPUTS.default_strait_strut_inputs(),
            mlg=_INPUTS.default_trailing_arm_inputs(),
        )
    
    # Apply golden defaults if available
    if golden_defaults:
        body_cfg = golden_defaults.get("body", {})
        if body_cfg:
            inputs.body.masse = float(body_cfg.get("masse", inputs.body.masse))
            inputs.body.jyy = float(body_cfg.get("jyy", inputs.body.jyy))
            inputs.body.lift = float(body_cfg.get("lift", inputs.body.lift))
            cg_cfg = body_cfg.get("cg", {})
            if cg_cfg:
                inputs.body.cg = _INPUTS.Point3(
                    x=float(cg_cfg.get("x", inputs.body.cg.x)),
                    y=float(cg_cfg.get("y", inputs.body.cg.y)),
                    z=float(cg_cfg.get("z", inputs.body.cg.z)),
                )
        
        drop_cfg = golden_defaults.get("drop", {})
        if drop_cfg:
            inputs.drop.vz = float(drop_cfg.get("vz", inputs.drop.vz))
            inputs.drop.vx = float(drop_cfg.get("vx", inputs.drop.vx))
            inputs.drop.pitch = float(drop_cfg.get("pitch", inputs.drop.pitch))
            inputs.drop.pitch_rate_deg_s = float(drop_cfg.get("pitch_rate_deg_s", inputs.drop.pitch_rate_deg_s))
        
        layout_cfg = golden_defaults.get("layout", {})
        if layout_cfg:
            nlg_st = layout_cfg.get("nlg_station", {})
            if nlg_st:
                inputs.layout.nlg_station = _INPUTS.Point3(
                    x=float(nlg_st.get("x", inputs.layout.nlg_station.x)),
                    y=float(nlg_st.get("y", inputs.layout.nlg_station.y)),
                    z=float(nlg_st.get("z", inputs.layout.nlg_station.z)),
                )
            mlg_l_st = layout_cfg.get("mlg_left_station", {})
            if mlg_l_st:
                inputs.layout.mlg_left_station = _INPUTS.Point3(
                    x=float(mlg_l_st.get("x", inputs.layout.mlg_left_station.x)),
                    y=float(mlg_l_st.get("y", inputs.layout.mlg_left_station.y)),
                    z=float(mlg_l_st.get("z", inputs.layout.mlg_left_station.z)),
                )
            mlg_r_st = layout_cfg.get("mlg_right_station", {})
            if mlg_r_st:
                inputs.layout.mlg_right_station = _INPUTS.Point3(
                    x=float(mlg_r_st.get("x", inputs.layout.mlg_right_station.x)),
                    y=float(mlg_r_st.get("y", inputs.layout.mlg_right_station.y)),
                    z=float(mlg_r_st.get("z", inputs.layout.mlg_right_station.z)),
                )
        
        sim_cfg = golden_defaults.get("simulation", {})
        if sim_cfg:
            inputs.simulation.temps_simu = float(sim_cfg.get("temps_simu", inputs.simulation.temps_simu))
            inputs.simulation.it = float(sim_cfg.get("it", inputs.simulation.it))
            inputs.simulation.integrator = str(sim_cfg.get("integrator", inputs.simulation.integrator))
            inputs.simulation.temperature = float(sim_cfg.get("temperature", inputs.simulation.temperature))
    
    return inputs


def _is_aircraft_inputs_like(obj: Any) -> bool:
    return (
        getattr(obj, "model_kind", "") == "aircraft"
        and hasattr(obj, "body")
        and hasattr(obj, "simulation")
        and hasattr(obj, "drop")
        and hasattr(obj, "layout")
        and hasattr(obj, "nlg")
        and hasattr(obj, "mlg")
    )


def _ensure_state() -> None:
    if "aircraft_inputs" not in st.session_state or not _is_aircraft_inputs_like(st.session_state.aircraft_inputs):
        st.session_state.aircraft_inputs = _make_default_aircraft_inputs()
    if "aircraft_result" not in st.session_state:
        st.session_state.aircraft_result = None
    if "aircraft_result_name" not in st.session_state:
        st.session_state.aircraft_result_name = "Simulation avion complet"
    if "aircraft_ui_state" not in st.session_state:
        st.session_state.aircraft_ui_state = {}
    if "aircraft_current_project" not in st.session_state:
        st.session_state.aircraft_current_project = ds_storage.DEFAULT_PROJECT


_ensure_state()
inp: Any = st.session_state.aircraft_inputs


def _num(label: str, key: str, value: float, *, step: float = 1.0, min_value=None) -> float:
    if key not in st.session_state:
        st.session_state[key] = float(value)
    return float(st.number_input(label, key=key, step=step, min_value=min_value))


def _decimal_places(*values: float) -> int:
    decimals = 0
    for value in values:
        text = format(float(value), ".16g")
        exponent = Decimal(text).as_tuple().exponent
        decimals = max(decimals, -exponent if exponent < 0 else 0)
    return decimals


def _num_precise(label: str, key: str, value: float, *, step: float, min_value=None) -> float:
    if key not in st.session_state:
        st.session_state[key] = float(value)
    decimals = _decimal_places(value, step)
    return float(
        st.number_input(
            label,
            key=key,
            step=step,
            min_value=min_value,
            format=f"%.{decimals}f",
        )
    )


def _sync_widgets_from_inputs(inp: Any) -> None:
    st.session_state.ac_body_masse = float(inp.body.masse)
    st.session_state.ac_body_jyy = float(inp.body.jyy)
    st.session_state.ac_body_lift = float(inp.body.lift)
    st.session_state.ac_cg_x = float(inp.body.cg.x)
    st.session_state.ac_cg_y = float(inp.body.cg.y)
    st.session_state.ac_cg_z = float(inp.body.cg.z)

    st.session_state.ac_sim_t = float(inp.simulation.temps_simu)
    st.session_state.ac_sim_dt = float(inp.simulation.it)
    st.session_state.ac_sim_hyd_tol = float(inp.simulation.hydraulic_error_tol)
    st.session_state.ac_sim_hyd_iter = int(inp.simulation.hydraulic_max_iter)
    st.session_state.ac_sim_integrator = str(inp.simulation.integrator)
    st.session_state.ac_sim_solver = str(inp.simulation.damper_core_solver)
    st.session_state.ac_sim_temp = float(inp.simulation.temperature)

    st.session_state.ac_drop_vz = float(inp.drop.vz)
    st.session_state.ac_drop_vx = float(inp.drop.vx)
    st.session_state.ac_drop_pitch = float(inp.drop.pitch)
    st.session_state.ac_drop_pitch_rate = float(inp.drop.pitch_rate_deg_s)

    st.session_state.ac_nlg_x = float(inp.layout.nlg_station.x)
    st.session_state.ac_nlg_y = float(inp.layout.nlg_station.y)
    st.session_state.ac_nlg_z = float(inp.layout.nlg_station.z)
    st.session_state.ac_mlg_l_x = float(inp.layout.mlg_left_station.x)
    st.session_state.ac_mlg_l_y = float(inp.layout.mlg_left_station.y)
    st.session_state.ac_mlg_l_z = float(inp.layout.mlg_left_station.z)
    st.session_state.ac_mlg_r_x = float(inp.layout.mlg_right_station.x)
    st.session_state.ac_mlg_r_y = float(inp.layout.mlg_right_station.y)
    st.session_state.ac_mlg_r_z = float(inp.layout.mlg_right_station.z)

    st.session_state.ac_nlg_strut_pitch = float(inp.nlg.strut_pitch)
    st.session_state.ac_nlg_strut_roll = float(inp.nlg.strut_roll)
    st.session_state.ac_nlg_h_pivot = float(inp.nlg.h_pivot_z)
    st.session_state.ac_nlg_h_gt = float(inp.nlg.h_guide_top_z)
    st.session_state.ac_nlg_h_gb = float(inp.nlg.h_guide_bot_z)
    st.session_state.ac_nlg_bg = float(inp.nlg.bague_guide)
    st.session_state.ac_nlg_bp = float(inp.nlg.bague_piston)
    st.session_state.ac_nlg_seal = float(inp.nlg.seal_precomp_pa)

    st.session_state.ac_mlg_dpis = float(inp.mlg.Dpis)
    st.session_state.ac_mlg_dbh = float(inp.mlg.Dbh)
    st.session_state.ac_mlg_dt = float(inp.mlg.Dt)
    st.session_state.ac_mlg_course = float(inp.mlg.course)
    st.session_state.ac_mlg_pinitbp = float(inp.mlg.Pinitbp)
    st.session_state.ac_mlg_vgbp = float(inp.mlg.Vgbp)
    st.session_state.ac_mlg_pinithp = float(inp.mlg.Pinithp)
    st.session_state.ac_mlg_vghp = float(inp.mlg.Vghp)
    st.session_state.ac_mlg_unsprung = float(inp.mlg.unsprung_mass)
    st.session_state.ac_mlg_unload = float(inp.mlg.unload_radius)
    st.session_state.ac_mlg_kx = float(inp.mlg.kx)
    st.session_state.ac_mlg_cx = float(inp.mlg.cx)


def _set_loaded_aircraft_state(inputs: Any, result, *, name: str, project: str) -> None:
    st.session_state.aircraft_inputs = inputs
    st.session_state.aircraft_result = result
    st.session_state.aircraft_result_name = name
    st.session_state.aircraft_current_project = project
    _sync_widgets_from_inputs(inputs)


def _update_ui_state() -> None:
    keys = [
        "ac_show_body",
        "ac_show_sim",
        "ac_show_drop",
        "ac_show_layout",
        "ac_show_nlg",
        "ac_show_mlg",
    ]
    st.session_state.aircraft_ui_state = {k: st.session_state.get(k) for k in keys}


def _seed_ui_state() -> None:
    ui = st.session_state.aircraft_ui_state
    defaults = {
        "ac_show_body": True,
        "ac_show_sim": True,
        "ac_show_drop": True,
        "ac_show_layout": True,
        "ac_show_nlg": True,
        "ac_show_mlg": True,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = bool(ui.get(k, v))


_seed_ui_state()

with st.expander("Sauvegarder / charger une simulation avion complet", expanded=False):
    projects = ds_storage.list_projects()
    new_project_label = "+ Nouveau projet"
    col_save, col_load = st.columns(2)

    with col_save:
        st.markdown("**Sauvegarder la simulation courante**")
        if st.session_state.aircraft_result is None:
            st.caption("Aucun resultat avion complet a sauvegarder.")
        else:
            current_project = st.session_state.get("aircraft_current_project", ds_storage.DEFAULT_PROJECT)
            save_options = projects + [new_project_label]
            save_index = projects.index(current_project) if current_project in projects else len(save_options) - 1
            project_choice = st.selectbox("Projet", save_options, index=save_index, key="ac_save_project_choice")
            if project_choice == new_project_label:
                project_name = st.text_input(
                    "Nom du nouveau projet",
                    value="" if current_project in projects else current_project,
                    key="ac_save_project_new",
                    placeholder=ds_storage.DEFAULT_PROJECT,
                ).strip() or ds_storage.DEFAULT_PROJECT
            else:
                project_name = project_choice

            default_name = st.session_state.get("aircraft_result_name", "Simulation avion complet")
            save_name = st.text_input("Nom de la sauvegarde", value=default_name, key="ac_save_name")
            if st.button("Enregistrer", key="ac_save_btn", use_container_width=True):
                path = ds_storage.save_simulation(
                    
                    st.session_state.aircraft_inputs,
                    st.session_state.aircraft_result,
                    name=save_name,
                    project=project_name,
                )
                st.session_state.aircraft_result_name = save_name
                st.session_state.aircraft_current_project = project_name
                st.success(f"Sauvegarde avion enregistree: {path.name}", icon="✅")

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
                labels = {
                    f"{entry['name']} · {entry['saved_at'][:16].replace('T', ' ')}": entry["path"]
                    for entry in entries
                }
                selected = st.selectbox("Sauvegardes disponibles", list(labels.keys()), key="ac_load_choice")
                load_col, del_col = st.columns(2)
                if load_col.button("Charger", key="ac_load_btn", use_container_width=True):
                    loaded_inputs, loaded_result, meta = ds_storage.load_simulation(labels[selected])
                    if getattr(loaded_inputs, "model_kind", "") != "aircraft":
                        st.error("La sauvegarde selectionnee n'est pas une simulation avion complet.", icon="🛑")
                    else:
                        _set_loaded_aircraft_state(
                            loaded_inputs,
                            loaded_result,
                            name=meta.get("name", "Simulation avion complet"),
                            project=meta.get("project", ds_storage.DEFAULT_PROJECT),
                        )
                        st.rerun()
                if del_col.button("Supprimer", key="ac_delete_btn", use_container_width=True):
                    ds_storage.delete_saved(labels[selected])
                    st.rerun()

c1, c2, c3 = st.columns(3)
with c1:
    st.checkbox("Afficher parametres avion", key="ac_show_body")
with c2:
    st.checkbox("Afficher simulation/chute", key="ac_show_sim")
with c3:
    st.checkbox("Afficher geometrie/trains", key="ac_show_layout")

s1, s2 = st.columns(2)
with s1:
    st.checkbox("Afficher bloc NLG", key="ac_show_nlg")
with s2:
    st.checkbox("Afficher bloc MLG", key="ac_show_mlg")

if st.session_state.ac_show_body:
    st.subheader("Parametres avion")
    a, b, c = st.columns(3)
    with a:
        body_masse = _num("Masse avion (kg)", "ac_body_masse", inp.body.masse, step=10.0, min_value=0.0)
        body_jyy = _num("Inertie Jyy (kg.m2)", "ac_body_jyy", inp.body.jyy, step=100.0, min_value=0.0)
        body_lift = _num("Lift (0..1)", "ac_body_lift", inp.body.lift, step=0.01, min_value=0.0)
    with b:
        cg_x = _num("CG X (mm)", "ac_cg_x", inp.body.cg.x, step=10.0)
        cg_y = _num("CG Y (mm)", "ac_cg_y", inp.body.cg.y, step=10.0)
        cg_z = _num("CG Z (mm)", "ac_cg_z", inp.body.cg.z, step=10.0)
    with c:
        drop_pitch = _num("Pitch avion initial (deg)", "ac_drop_pitch", inp.drop.pitch, step=0.1)
        st.caption("Repere avion: X longitudinal, Y lateral, Z vertical.")

if st.session_state.ac_show_sim:
    st.subheader("Simulation et chute")
    a, b = st.columns(2)
    with a:
        sim_t = _num("Duree simulation (s)", "ac_sim_t", inp.simulation.temps_simu, step=0.1, min_value=0.0)
        sim_dt = _num_precise("Pas de temps (s)", "ac_sim_dt", inp.simulation.it, step=1e-6, min_value=1e-8)
        sim_hyd_tol = _num_precise(
            "Tol. hydraulique", "ac_sim_hyd_tol", inp.simulation.hydraulic_error_tol, step=1e-6, min_value=1e-8
        )
        sim_hyd_iter = int(_num("Iter max hydraulique", "ac_sim_hyd_iter", float(inp.simulation.hydraulic_max_iter), step=1.0, min_value=4.0))
    with b:
        sim_int = st.selectbox("Integrateur", options=["rk4", "euler"], key="ac_sim_integrator", index=0 if inp.simulation.integrator == "rk4" else 1)
        sim_solver = st.selectbox(
            "Solveur noyau", options=["auto_fast", "auto_precise"], key="ac_sim_solver",
            index=0 if inp.simulation.damper_core_solver == "auto_fast" else 1,
        )
        sim_temp = _num("Temperature (C)", "ac_sim_temp", inp.simulation.temperature, step=1.0)
        drop_vz = _num("Vz initiale (m/s)", "ac_drop_vz", inp.drop.vz, step=0.1)
        drop_vx = _num("Vx initiale (m/s)", "ac_drop_vx", inp.drop.vx, step=0.5)
        drop_pitch_rate = _num("Pitch rate initial (deg/s)", "ac_drop_pitch_rate", inp.drop.pitch_rate_deg_s, step=0.1)

if st.session_state.ac_show_layout:
    st.subheader("Geometrie d'implantation des trains")
    nlg_col, mlg_l_col, mlg_r_col = st.columns(3)
    with nlg_col:
        st.markdown("**Station NLG (mm)**")
        nlg_x = _num("NLG X", "ac_nlg_x", inp.layout.nlg_station.x, step=10.0)
        nlg_y = _num("NLG Y", "ac_nlg_y", inp.layout.nlg_station.y, step=10.0)
        nlg_z = _num("NLG Z", "ac_nlg_z", inp.layout.nlg_station.z, step=10.0)
    with mlg_l_col:
        st.markdown("**Station MLG gauche (mm)**")
        mlg_l_x = _num("MLGg X", "ac_mlg_l_x", inp.layout.mlg_left_station.x, step=10.0)
        mlg_l_y = _num("MLGg Y", "ac_mlg_l_y", inp.layout.mlg_left_station.y, step=10.0)
        mlg_l_z = _num("MLGg Z", "ac_mlg_l_z", inp.layout.mlg_left_station.z, step=10.0)
    with mlg_r_col:
        st.markdown("**Station MLG droite (mm)**")
        mlg_r_x = _num("MLGd X", "ac_mlg_r_x", inp.layout.mlg_right_station.x, step=10.0)
        mlg_r_y = _num("MLGd Y", "ac_mlg_r_y", inp.layout.mlg_right_station.y, step=10.0)
        mlg_r_z = _num("MLGd Z", "ac_mlg_r_z", inp.layout.mlg_right_station.z, step=10.0)

if st.session_state.ac_show_nlg:
    st.subheader("Parametres NLG (specifiques StraitStrut)")
    a, b = st.columns(2)
    with a:
        nlg_strut_pitch = _num("NLG strut pitch (deg)", "ac_nlg_strut_pitch", inp.nlg.strut_pitch, step=0.1)
        nlg_strut_roll = _num("NLG strut roll (deg)", "ac_nlg_strut_roll", inp.nlg.strut_roll, step=0.1)
        nlg_h_pivot = _num("NLG h pivot Z (mm)", "ac_nlg_h_pivot", inp.nlg.h_pivot_z, step=1.0)
        nlg_h_gt = _num("NLG h guide top (mm)", "ac_nlg_h_gt", inp.nlg.h_guide_top_z, step=1.0)
    with b:
        nlg_h_gb = _num("NLG h guide bot (mm)", "ac_nlg_h_gb", inp.nlg.h_guide_bot_z, step=1.0)
        nlg_bg = _num("NLG bague guide (mm)", "ac_nlg_bg", inp.nlg.bague_guide, step=1.0)
        nlg_bp = _num("NLG bague piston (mm)", "ac_nlg_bp", inp.nlg.bague_piston, step=1.0)
        nlg_seal = _num("NLG seal precomp (Pa)", "ac_nlg_seal", inp.nlg.seal_precomp_pa, step=100.0)

if st.session_state.ac_show_mlg:
    st.subheader("Parametres MLG (principaux)")
    a, b, c = st.columns(3)
    with a:
        mlg_dpis = _num("MLG Dpis (mm)", "ac_mlg_dpis", inp.mlg.Dpis, step=0.5)
        mlg_dbh = _num("MLG Dbh (mm)", "ac_mlg_dbh", inp.mlg.Dbh, step=0.5)
        mlg_dt = _num("MLG Dt (mm)", "ac_mlg_dt", inp.mlg.Dt, step=0.5)
        mlg_course = _num("MLG course (mm)", "ac_mlg_course", inp.mlg.course, step=1.0)
    with b:
        mlg_pinitbp = _num("MLG Pinit BP (bar)", "ac_mlg_pinitbp", inp.mlg.Pinitbp, step=0.1)
        mlg_vgbp = _num("MLG Vg BP (cc)", "ac_mlg_vgbp", inp.mlg.Vgbp, step=1.0)
        mlg_pinithp = _num("MLG Pinit HP (bar)", "ac_mlg_pinithp", inp.mlg.Pinithp, step=0.5)
        mlg_vghp = _num("MLG Vg HP (cc)", "ac_mlg_vghp", inp.mlg.Vghp, step=1.0)
    with c:
        mlg_unsprung = _num("MLG unsprung mass (kg)", "ac_mlg_unsprung", inp.mlg.unsprung_mass, step=0.5)
        mlg_unload = _num("MLG rayon libre (mm)", "ac_mlg_unload", inp.mlg.unload_radius, step=1.0)
        mlg_kx = _num("MLG Kx (N/m)", "ac_mlg_kx", inp.mlg.kx, step=1000.0)
        mlg_cx = _num("MLG Cx (N.s/m)", "ac_mlg_cx", inp.mlg.cx, step=10.0)


def _build_aircraft_inputs():
    base = st.session_state.aircraft_inputs
    if not _is_aircraft_inputs_like(base):
        base = _make_default_aircraft_inputs()
        st.session_state.aircraft_inputs = base
    out = _INPUTS.AircraftInputs(
        model_kind="aircraft",
        body=base.body,
        simulation=base.simulation,
        drop=base.drop,
        layout=base.layout,
        nlg=base.nlg,
        mlg=base.mlg,
    )
    out.body.masse = float(st.session_state.ac_body_masse)
    out.body.jyy = float(st.session_state.ac_body_jyy)
    out.body.lift = float(st.session_state.ac_body_lift)
    out.body.cg = _INPUTS.Point3(float(st.session_state.ac_cg_x), float(st.session_state.ac_cg_y), float(st.session_state.ac_cg_z))

    out.simulation.temps_simu = float(st.session_state.ac_sim_t)
    out.simulation.it = float(st.session_state.ac_sim_dt)
    out.simulation.integrator = str(st.session_state.ac_sim_integrator)
    out.simulation.damper_core_solver = str(st.session_state.ac_sim_solver)
    out.simulation.hydraulic_error_tol = float(st.session_state.ac_sim_hyd_tol)
    out.simulation.hydraulic_max_iter = int(st.session_state.ac_sim_hyd_iter)
    out.simulation.temperature = float(st.session_state.ac_sim_temp)

    out.drop.vz = float(st.session_state.ac_drop_vz)
    out.drop.vx = float(st.session_state.ac_drop_vx)
    out.drop.pitch = float(st.session_state.ac_drop_pitch)
    out.drop.pitch_rate_deg_s = float(st.session_state.ac_drop_pitch_rate)

    out.layout.nlg_station = _INPUTS.Point3(float(st.session_state.ac_nlg_x), float(st.session_state.ac_nlg_y), float(st.session_state.ac_nlg_z))
    out.layout.mlg_left_station = _INPUTS.Point3(float(st.session_state.ac_mlg_l_x), float(st.session_state.ac_mlg_l_y), float(st.session_state.ac_mlg_l_z))
    out.layout.mlg_right_station = _INPUTS.Point3(float(st.session_state.ac_mlg_r_x), float(st.session_state.ac_mlg_r_y), float(st.session_state.ac_mlg_r_z))

    out.nlg.strut_pitch = float(st.session_state.ac_nlg_strut_pitch)
    out.nlg.strut_roll = float(st.session_state.ac_nlg_strut_roll)
    out.nlg.h_pivot_z = float(st.session_state.ac_nlg_h_pivot)
    out.nlg.h_guide_top_z = float(st.session_state.ac_nlg_h_gt)
    out.nlg.h_guide_bot_z = float(st.session_state.ac_nlg_h_gb)
    out.nlg.bague_guide = float(st.session_state.ac_nlg_bg)
    out.nlg.bague_piston = float(st.session_state.ac_nlg_bp)
    out.nlg.seal_precomp_pa = float(st.session_state.ac_nlg_seal)

    out.mlg.Dpis = float(st.session_state.ac_mlg_dpis)
    out.mlg.Dbh = float(st.session_state.ac_mlg_dbh)
    out.mlg.Dt = float(st.session_state.ac_mlg_dt)
    out.mlg.course = float(st.session_state.ac_mlg_course)
    out.mlg.Pinitbp = float(st.session_state.ac_mlg_pinitbp)
    out.mlg.Vgbp = float(st.session_state.ac_mlg_vgbp)
    out.mlg.Pinithp = float(st.session_state.ac_mlg_pinithp)
    out.mlg.Vghp = float(st.session_state.ac_mlg_vghp)
    out.mlg.unsprung_mass = float(st.session_state.ac_mlg_unsprung)
    out.mlg.unload_radius = float(st.session_state.ac_mlg_unload)
    out.mlg.kx = float(st.session_state.ac_mlg_kx)
    out.mlg.cx = float(st.session_state.ac_mlg_cx)

    return out


st.divider()
a, b, c = st.columns([1, 1, 4])
launch = a.button("Lancer calcul avion", type="primary", use_container_width=True)
reset = b.button("Reinitialiser", use_container_width=True)

if reset:
    for key in list(st.session_state.keys()):
        if key.startswith("ac_"):
            del st.session_state[key]
    st.session_state.aircraft_inputs = _make_default_aircraft_inputs()
    st.session_state.aircraft_result = None
    st.session_state.aircraft_result_name = "Simulation avion complet"
    st.session_state.aircraft_ui_state = {}
    st.rerun()

if launch:
    aircraft_inputs = _build_aircraft_inputs()
    aircraft_inputs.model_kind = "aircraft"
    if hasattr(aircraft_inputs, "nlg"):
        aircraft_inputs.nlg.model_kind = "strait_strut"
    if hasattr(aircraft_inputs, "mlg"):
        aircraft_inputs.mlg.model_kind = "trailing_arm"
    st.session_state.aircraft_inputs = aircraft_inputs
    collector = aircraft_inputs.validate()
    if collector.has_errors:
        c.error("Validation invalide. Corriger les champs et relancer.", icon="🛑")
        for err in collector.errors:
            c.error(f"{err.field or 'general'}: {err.message}")
    else:
        try:
            progress = st.progress(0.0)

            def _cb(cur: int, total: int) -> None:
                if total > 0:
                    progress.progress(min(1.0, cur / total))

            result = _run_aircraft_simulation(aircraft_inputs, progress_callback=_cb)
            progress.empty()
            st.session_state.aircraft_result = result
            st.session_state.aircraft_result_name = "Simulation avion complet"
            c.success("Calcul avion termine. Le resultat est conserve dans la session.", icon="✅")
            c.caption("Consultez la page Resultats avion pour les graphes dedies lot 5.")
        except ds_errors.SimError as exc:
            c.error(f"{exc.code}: {exc.message}", icon="🛑")

res = st.session_state.aircraft_result
if res is not None:
    st.divider()
    st.subheader("Resume rapide")
    m1, m2, m3 = st.columns(3)
    m1.metric("Pas", f"{res.n_steps}")
    m2.metric("Fz total max", f"{res.summary.get('Effort vertical total max Fz (N)', 0.0):.0f} N")
    m3.metric("Acc CG max", f"{res.summary.get('Accélération CG max (g)', res.summary.get('Acceleration CG max (g)', 0.0)):.3f} g")

_update_ui_state()
