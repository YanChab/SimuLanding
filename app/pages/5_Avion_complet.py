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
import plotly.graph_objects as go
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
from dropsim.inputs import (  # noqa: E402
    TEMP_REF_C,
    compute_bulk_modulus_at_temperature,
    compute_bulk_modulus_from_aeration,
    compute_gas_oil_at_temperature,
)
from dropsim.metering import build_section_table  # noqa: E402
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
    return float(st.number_input(label, key=key, step=step, min_value=min_value, format="%.12g"))


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
            format=f"%.{max(decimals, 12)}g",
        )
    )


_PAPER_BG = "#fbfbf2"
_GRID_MAJOR = "#e08e7b"
_GRID_MINOR = "#f3c9bf"


def _mini_axis(title: str) -> dict:
    return dict(
        title=title,
        showgrid=True,
        gridcolor=_GRID_MAJOR,
        gridwidth=1,
        zeroline=True,
        zerolinecolor=_GRID_MAJOR,
        showline=True,
        linecolor=_GRID_MAJOR,
        mirror=True,
        ticks="outside",
        minor=dict(showgrid=True, gridcolor=_GRID_MINOR, gridwidth=0.5),
    )


def _safe_xy(df_table: pd.DataFrame):
    d = df_table.dropna()
    if d.empty:
        return [], []
    return d.iloc[:, 0].to_numpy(), d.iloc[:, 1].to_numpy()


def _mini_chart(x, y, xlab: str, ylab: str, *, color: str) -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=x,
            y=y,
            mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=5, color=color),
        )
    )
    fig.update_layout(
        height=210,
        margin=dict(l=8, r=8, t=8, b=8),
        plot_bgcolor=_PAPER_BG,
        paper_bgcolor="white",
        xaxis=_mini_axis(xlab),
        yaxis=_mini_axis(ylab),
        showlegend=False,
    )
    return fig


def _curve_to_editor_df(curve, col_a: str, col_b: str) -> pd.DataFrame:
    table = pd.DataFrame(curve, columns=[col_a, col_b]).T
    table.columns = [f"P{i + 1}" for i in range(table.shape[1])]
    return table


def _rainures_to_editor_df(rainures) -> pd.DataFrame:
    table = pd.DataFrame(
        [(r.debut, r.fin, r.profondeur) for r in rainures],
        columns=["Début (mm)", "Fin (mm)", "Profondeur (mm)"],
    ).T
    table.columns = [f"R{i + 1}" for i in range(table.shape[1])]
    return table


def _read_curve_editor(key: str, fallback, col_a: str, col_b: str):
    edited = st.session_state.get(key)
    if edited is None:
        return [(float(x), float(y)) for x, y in fallback]
    try:
        df = pd.DataFrame(edited).T.reset_index(drop=True)
        if df.shape[1] < 2:
            return [(float(x), float(y)) for x, y in fallback]
        df = df.iloc[:, :2]
        df.columns = [col_a, col_b]
        df = df.apply(pd.to_numeric, errors="coerce").dropna()
        if len(df) < 2:
            return [(float(x), float(y)) for x, y in fallback]
        return [(float(r[0]), float(r[1])) for r in df.itertuples(index=False)]
    except Exception:
        return [(float(x), float(y)) for x, y in fallback]


def _read_rainures_editor(key: str, fallback):
    edited = st.session_state.get(key)
    if edited is None:
        return [ds_inputs.Rainure(float(r.debut), float(r.fin), float(r.profondeur)) for r in fallback]
    try:
        df = pd.DataFrame(edited).T.reset_index(drop=True)
        if df.shape[1] < 3:
            return [ds_inputs.Rainure(float(r.debut), float(r.fin), float(r.profondeur)) for r in fallback]
        df = df.iloc[:, :3]
        df.columns = ["Début (mm)", "Fin (mm)", "Profondeur (mm)"]
        df = df.apply(pd.to_numeric, errors="coerce").dropna()
        if df.empty:
            return [ds_inputs.Rainure(float(r.debut), float(r.fin), float(r.profondeur)) for r in fallback]
        return [
            ds_inputs.Rainure(float(a), float(b), float(c))
            for a, b, c in df.itertuples(index=False)
        ]
    except Exception:
        return [ds_inputs.Rainure(float(r.debut), float(r.fin), float(r.profondeur)) for r in fallback]


def _sync_gear_widgets(prefix: str, gear: Any, *, include_strut: bool) -> None:
    p = f"ac_{prefix}_"
    if include_strut:
        st.session_state[f"{p}strut_pitch"] = float(gear.strut_pitch)
        st.session_state[f"{p}strut_roll"] = float(gear.strut_roll)
        st.session_state[f"{p}h_pivot"] = float(gear.h_pivot_z)
        st.session_state[f"{p}h_gt"] = float(gear.h_guide_top_z)
        st.session_state[f"{p}h_gb"] = float(gear.h_guide_bot_z)
        st.session_state[f"{p}bg"] = float(gear.bague_guide)
        st.session_state[f"{p}bp"] = float(gear.bague_piston)
        st.session_state[f"{p}seal"] = float(gear.seal_precomp_pa)

    st.session_state[f"{p}unsprung_mass"] = float(gear.unsprung_mass)
    st.session_state[f"{p}wheel_inertia"] = float(gear.wheel_inertia)
    st.session_state[f"{p}unload_radius"] = float(gear.unload_radius)
    st.session_state[f"{p}kx"] = float(gear.kx)
    st.session_state[f"{p}cx"] = float(gear.cx)
    st.session_state[f"{p}wheelmass"] = float(gear.wheelmass)

    st.session_state[f"{p}Dpis"] = float(gear.Dpis)
    st.session_state[f"{p}Dbh"] = float(gear.Dbh)
    st.session_state[f"{p}Dt"] = float(gear.Dt)
    st.session_state[f"{p}Dp"] = float(gear.Dp)
    st.session_state[f"{p}DInsideBh"] = float(gear.DInsideBh)
    st.session_state[f"{p}DInsidePalierBh"] = float(gear.DInsidePalierBh)
    st.session_state[f"{p}Lbh"] = float(gear.Lbh)
    st.session_state[f"{p}LPalierBh"] = float(gear.LPalierBh)
    st.session_state[f"{p}excentricite_palier_bh"] = float(gear.excentricite_palier_bh)
    st.session_state[f"{p}course"] = float(gear.course)
    st.session_state[f"{p}DTrouPis"] = float(gear.DTrouPis)
    st.session_state[f"{p}NbTrouPis"] = float(gear.NbTrouPis)
    st.session_state[f"{p}HauteurPisBh"] = float(gear.HauteurPisBh)
    st.session_state[f"{p}DTrouDiap"] = float(gear.DTrouDiap)
    st.session_state[f"{p}NbTrouDiap"] = float(gear.NbTrouDiap)
    st.session_state[f"{p}tore"] = float(gear.tore)
    st.session_state[f"{p}fc"] = float(gear.fc)
    st.session_state[f"{p}fh"] = float(gear.fh)
    st.session_state[f"{p}endstop_smooth_mm"] = float(gear.endstop_smooth_mm)

    st.session_state[f"{p}Pinitbp"] = float(gear.Pinitbp)
    st.session_state[f"{p}Vgbp"] = float(gear.Vgbp)
    st.session_state[f"{p}Vh"] = float(gear.Vh)
    st.session_state[f"{p}Pinithp"] = float(gear.Pinithp)
    st.session_state[f"{p}Vghp"] = float(gear.Vghp)
    st.session_state[f"{p}gamma"] = float(gear.gamma)

    st.session_state[f"{p}visc"] = float(gear.visc)
    st.session_state[f"{p}rho"] = float(gear.rho)
    st.session_state[f"{p}aeration_pct"] = float(gear.aeration_pct)
    st.session_state[f"{p}k_air"] = float(gear.k_air)
    st.session_state[f"{p}k_huile"] = float(gear.k_huile)
    st.session_state[f"{p}k_huile_temp_coeff"] = float(gear.k_huile_temp_coeff)
    st.session_state[f"{p}bulk"] = float(gear.bulk)

    st.session_state[f"{p}diametre_rainure"] = float(gear.diametre_rainure)
    st.session_state[f"{p}tyre_curve_editor"] = _curve_to_editor_df(
        gear.tyre_curve,
        "Déflexion (mm)",
        "Charge (kN)",
    )
    st.session_state[f"{p}mu_curve_editor"] = _curve_to_editor_df(
        gear.mu_curve,
        "Slip",
        "μ",
    )
    st.session_state[f"{p}rainures_editor"] = _rainures_to_editor_df(gear.rainures)


def _render_gear_full_sections(prefix: str, gear: Any, *, include_strut: bool, title: str) -> None:
    p = f"ac_{prefix}_"
    st.subheader(title)

    if include_strut:
        st.markdown("**Géométrie jambe NLG (StraitStrut)**")
        a, b = st.columns(2)
        with a:
            _num("Strut pitch (deg)", f"{p}strut_pitch", gear.strut_pitch, step=0.1)
            _num("Strut roll (deg)", f"{p}strut_roll", gear.strut_roll, step=0.1)
            _num("h pivot Z (mm)", f"{p}h_pivot", gear.h_pivot_z, step=1.0)
            _num("h guide top (mm)", f"{p}h_gt", gear.h_guide_top_z, step=1.0)
        with b:
            _num("h guide bot (mm)", f"{p}h_gb", gear.h_guide_bot_z, step=1.0)
            _num("Bague guide (mm)", f"{p}bg", gear.bague_guide, step=1.0)
            _num("Bague piston (mm)", f"{p}bp", gear.bague_piston, step=1.0)
            _num("Précharge joint (Pa)", f"{p}seal", gear.seal_precomp_pa, step=100.0)

    st.markdown("### Pneu et spring-back")
    pneu_param_col, tyre_chart_col = st.columns([2, 5])
    with pneu_param_col:
        _num("Masse non suspendue (kg)", f"{p}unsprung_mass", gear.unsprung_mass, step=0.5, min_value=0.0)
        _num("Inertie polaire roue (kg.m²)", f"{p}wheel_inertia", gear.wheel_inertia, step=0.01, min_value=0.0)
        _num("Rayon libre (mm)", f"{p}unload_radius", gear.unload_radius, step=1.0)
        _num("Raideur spring-back Kx (N/m)", f"{p}kx", gear.kx, step=1000.0, min_value=0.0)
        _num("Amortissement spring-back Cx (N.s/m)", f"{p}cx", gear.cx, step=10.0, min_value=0.0)
        _num("Masse roue spring-back (kg)", f"{p}wheelmass", gear.wheelmass, step=0.5, min_value=0.0)

    with tyre_chart_col:
        st.markdown("**Courbe pneu** - déflexion (mm) -> charge (kN)")
        tyre_t_edit = st.data_editor(
            _curve_to_editor_df(gear.tyre_curve, "Déflexion (mm)", "Charge (kN)"),
            column_config={
                "Déflexion (mm)": st.column_config.NumberColumn("Déflexion (mm)", alignment="center", format="%.12g"),
                "Charge (kN)": st.column_config.NumberColumn("Charge (kN)", alignment="center", format="%.12g"),
            },
            width="stretch",
            key=f"{p}tyre_curve_editor",
        )
        tyre_df = tyre_t_edit.T.reset_index(drop=True)
        tyre_df.columns = ["Déflexion (mm)", "Charge (kN)"]
        tx, ty = _safe_xy(tyre_df)
        st.plotly_chart(
            _mini_chart(tx, ty, "Déflexion (mm)", "Charge (kN)", color="#1f77b4"),
            width="stretch",
            key=f"ac_{prefix}_tyre_chart",
        )

    st.markdown("**Courbe d'adhérence** - taux de glissement -> μ")
    mu_t_edit = st.data_editor(
        _curve_to_editor_df(gear.mu_curve, "Slip", "μ"),
        column_config={
            "Slip": st.column_config.NumberColumn("Slip", alignment="center", format="%.12g"),
            "μ": st.column_config.NumberColumn("μ", alignment="center", format="%.12g"),
        },
        width="stretch",
        key=f"{p}mu_curve_editor",
    )
    mu_df = mu_t_edit.T.reset_index(drop=True)
    mu_df.columns = ["Slip", "μ"]
    mx, my = _safe_xy(mu_df)
    st.plotly_chart(
        _mini_chart(mx, my, "Slip", "μ", color="#2ca02c"),
        width="stretch",
        key=f"ac_{prefix}_mu_chart",
    )

    st.markdown("### Amortisseur, ressort gazeux, huile et rainures de la butée hydraulique")
    col_amort, col_gaz, col_huile = st.columns([1, 1, 1])
    with col_amort:
        st.markdown("**Amortisseur (géométrie)**")
        _num("Ø piston Dpis (mm)", f"{p}Dpis", gear.Dpis, step=0.5)
        _num("Ø ext. butée hydraulique Dbh (mm)", f"{p}Dbh", gear.Dbh, step=0.5)
        _num("Ø tige Dt (mm)", f"{p}Dt", gear.Dt, step=0.5)
        _num("Ø intérieur tige Dp (mm)", f"{p}Dp", gear.Dp, step=0.5)
        _num("Ø intérieur butée DInsideBh (mm)", f"{p}DInsideBh", gear.DInsideBh, step=0.5)
        _num("Ø intérieur palier DInsidePalierBh (mm)", f"{p}DInsidePalierBh", gear.DInsidePalierBh, step=0.5)
        _num("Longueur trou BH (mm)", f"{p}Lbh", gear.Lbh, step=0.5)
        _num("Longueur palier BH (mm)", f"{p}LPalierBh", gear.LPalierBh, step=0.5)
        _num("Excentricité BH/palier (mm)", f"{p}excentricite_palier_bh", gear.excentricite_palier_bh, step=0.05)
        _num("Course totale SAT (mm)", f"{p}course", gear.course, step=1.0)
        _num("Ø trou piston détente (mm)", f"{p}DTrouPis", gear.DTrouPis, step=0.1)
        _num("Nb trous piston", f"{p}NbTrouPis", gear.NbTrouPis, step=1.0, min_value=0.0)
        _num("Hauteur piston BH (mm)", f"{p}HauteurPisBh", gear.HauteurPisBh, step=0.5)
        _num("Ø trou clapet (mm)", f"{p}DTrouDiap", gear.DTrouDiap, step=0.1)
        _num("Nb trous clapet", f"{p}NbTrouDiap", gear.NbTrouDiap, step=1.0, min_value=0.0)
        _num("Section tore joint (mm)", f"{p}tore", gear.tore, step=0.1)
        _num("Friction sèche joint fc (N/mm)", f"{p}fc", gear.fc, step=1.0)
        _num("Coeff. friction pression fh", f"{p}fh", gear.fh, step=0.01)
        _num("Longueur lissage butée (mm)", f"{p}endstop_smooth_mm", gear.endstop_smooth_mm, step=0.1, min_value=1.0e-6)

    with col_gaz:
        st.markdown("**Ressort gazeux**")
        _num("Pression init. BP (bar)", f"{p}Pinitbp", gear.Pinitbp, step=0.1)
        _num("Volume gaz init. BP (cc)", f"{p}Vgbp", gear.Vgbp, step=1.0)
        _num("Volume d'huile (cc)", f"{p}Vh", gear.Vh, step=1.0)
        _num("Pression init. HP (bar)", f"{p}Pinithp", gear.Pinithp, step=0.1)
        _num("Volume gaz init. HP (cc)", f"{p}Vghp", gear.Vghp, step=1.0)
        _num("Coefficient polytropique γ", f"{p}gamma", gear.gamma, step=0.01)
        temp = float(st.session_state.get("ac_sim_temp", gear.temperature))
        adj = compute_gas_oil_at_temperature(
            Pinitbp=float(st.session_state[f"{p}Pinitbp"]),
            Vgbp=float(st.session_state[f"{p}Vgbp"]),
            Vh=float(st.session_state[f"{p}Vh"]),
            Pinithp=float(st.session_state[f"{p}Pinithp"]),
            Vghp=float(st.session_state[f"{p}Vghp"]),
            visc=float(st.session_state.get(f"{p}visc", gear.visc)),
            temperature=temp,
        )
        st.caption(f"Calculé à {temp:g} °C (référence {TEMP_REF_C:g} °C)")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Paramètre": "Pression init. BP (bar)", "Valeur": adj["Pinitbp"]},
                    {"Paramètre": "Volume gaz init. BP (cc)", "Valeur": adj["Vgbp"]},
                    {"Paramètre": "Volume d'huile (cc)", "Valeur": adj["Vh"]},
                    {"Paramètre": "Pression init. HP (bar)", "Valeur": adj["Pinithp"]},
                    {"Paramètre": "Volume gaz init. HP (cc)", "Valeur": adj["Vghp"]},
                ]
            ),
            column_config={
                "Paramètre": st.column_config.TextColumn("Paramètre", alignment="right"),
                "Valeur": st.column_config.NumberColumn("Valeur", alignment="center", format="%.12g"),
            },
            hide_index=True,
            width="stretch",
        )

    with col_huile:
        st.markdown("**Huile**")
        _num("Viscosité cinématique (cSt)", f"{p}visc", gear.visc, step=1.0)
        _num("Masse volumique ρ (kg/m³)", f"{p}rho", gear.rho, step=1.0)
        _num("Aération volumique à 25°C (%)", f"{p}aeration_pct", gear.aeration_pct, step=0.1, min_value=0.0)
        _num("Kair à 25°C (MPa)", f"{p}k_air", gear.k_air, step=0.1)
        _num("Khuile à 25°C (MPa)", f"{p}k_huile", gear.k_huile, step=1.0)
        _num("Sensibilité thermique Khuile (1/°C)", f"{p}k_huile_temp_coeff", gear.k_huile_temp_coeff, step=0.001)
        try:
            bulk_25 = compute_bulk_modulus_from_aeration(
                aeration_pct=float(st.session_state[f"{p}aeration_pct"]),
                k_air=float(st.session_state[f"{p}k_air"]),
                k_huile=float(st.session_state[f"{p}k_huile"]),
            )
            bulk_adj = compute_bulk_modulus_at_temperature(
                aeration_pct=float(st.session_state[f"{p}aeration_pct"]),
                k_air_ref=float(st.session_state[f"{p}k_air"]),
                k_huile_ref=float(st.session_state[f"{p}k_huile"]),
                temperature=float(st.session_state.get("ac_sim_temp", gear.temperature)),
                k_huile_temp_coeff=float(st.session_state[f"{p}k_huile_temp_coeff"]),
            )
            bulk_mpa = float(bulk_adj["bulk"])
        except (TypeError, ValueError):
            bulk_25 = float(gear.bulk)
            bulk_adj = {"k_air": float(gear.k_air), "k_huile": float(gear.k_huile)}
            bulk_mpa = float(gear.bulk)
        st.session_state[f"{p}bulk"] = float(bulk_mpa)
        st.dataframe(
            pd.DataFrame(
                [
                    {"Paramètre": "Bulk effectif à 25°C (MPa)", "Valeur": bulk_25},
                    {"Paramètre": "Kair corrigé en T (MPa)", "Valeur": float(bulk_adj["k_air"])},
                    {"Paramètre": "Khuile corrigé en T (MPa)", "Valeur": float(bulk_adj["k_huile"])},
                    {"Paramètre": "Bulk effectif courant (MPa)", "Valeur": bulk_mpa},
                ]
            ),
            column_config={
                "Paramètre": st.column_config.TextColumn("Paramètre", alignment="right"),
                "Valeur": st.column_config.NumberColumn("Valeur", alignment="center", format="%.12g"),
            },
            hide_index=True,
            width="stretch",
        )

    st.markdown("**Rainures de la butée hydraulique**")
    _num("Ø rainure (mm)", f"{p}diametre_rainure", gear.diametre_rainure, step=0.1, min_value=0.0)
    re_col, rs_col = st.columns([1, 1])
    with re_col:
        rain_t_edit = st.data_editor(
            _rainures_to_editor_df(gear.rainures),
            column_config={
                "Début (mm)": st.column_config.NumberColumn("Début (mm)", alignment="center", format="%.12g"),
                "Fin (mm)": st.column_config.NumberColumn("Fin (mm)", alignment="center", format="%.12g"),
                "Profondeur (mm)": st.column_config.NumberColumn("Profondeur (mm)", alignment="center", format="%.12g"),
            },
            width="stretch",
            height=150,
            key=f"{p}rainures_editor",
        )
        rainures_df = rain_t_edit.T.reset_index(drop=True)
        rainures_df.columns = ["Début (mm)", "Fin (mm)", "Profondeur (mm)"]
    with rs_col:
        try:
            rd = rainures_df.apply(pd.to_numeric, errors="coerce").dropna()
            shim = SimpleNamespace(
                Dbh=float(st.session_state[f"{p}Dbh"]) / 1000.0,
                diametre_rainure=float(st.session_state[f"{p}diametre_rainure"]),
                course=float(st.session_state[f"{p}course"]) / 1000.0,
                rainures_debut=np.array([float(r[0]) for r in rd.itertuples(index=False)]),
                rainures_fin=np.array([float(r[1]) for r in rd.itertuples(index=False)]),
                rainures_profondeur=np.array([float(r[2]) for r in rd.itertuples(index=False)]),
            )
            _, tab_sec = build_section_table(shim)
            course_mm = np.arange(len(tab_sec), dtype=float)
            sec_mm2 = tab_sec * 1.0e6
            sfig = go.Figure()
            sfig.add_trace(
                go.Scatter(
                    x=course_mm,
                    y=sec_mm2,
                    mode="lines",
                    line=dict(width=2.5, color="#9467bd"),
                    name="Section cumulée",
                )
            )
            sfig.update_layout(
                title=dict(text="Section cumulée butée hydraulique", x=0.5, font=dict(size=12)),
                height=210,
                margin=dict(l=8, r=8, t=26, b=8),
                plot_bgcolor=_PAPER_BG,
                paper_bgcolor="white",
                showlegend=False,
                xaxis=_mini_axis("Course (mm)"),
                yaxis=_mini_axis("Section (mm²)"),
            )
            st.plotly_chart(sfig, width="stretch", key=f"ac_{prefix}_rainure_chart")
        except (ValueError, TypeError, KeyError, ZeroDivisionError):
            st.caption("Section cumulée indisponible — vérifier les cotes et Dbh.")


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

    _sync_gear_widgets("nlg", inp.nlg, include_strut=True)
    _sync_gear_widgets("mlg", inp.mlg, include_strut=False)


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
    _render_gear_full_sections(
        "nlg",
        inp.nlg,
        include_strut=True,
        title="Paramètres NLG",
    )

if st.session_state.ac_show_mlg:
    _render_gear_full_sections(
        "mlg",
        inp.mlg,
        include_strut=False,
        title="Paramètres MLG",
    )


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

    def _apply_gear(prefix: str, gear_out: Any, gear_in: Any, *, include_strut: bool) -> None:
        p = f"ac_{prefix}_"
        if include_strut:
            gear_out.strut_pitch = float(st.session_state[f"{p}strut_pitch"])
            gear_out.strut_roll = float(st.session_state[f"{p}strut_roll"])
            gear_out.h_pivot_z = float(st.session_state[f"{p}h_pivot"])
            gear_out.h_guide_top_z = float(st.session_state[f"{p}h_gt"])
            gear_out.h_guide_bot_z = float(st.session_state[f"{p}h_gb"])
            gear_out.bague_guide = float(st.session_state[f"{p}bg"])
            gear_out.bague_piston = float(st.session_state[f"{p}bp"])
            gear_out.seal_precomp_pa = float(st.session_state[f"{p}seal"])

        gear_out.unsprung_mass = float(st.session_state[f"{p}unsprung_mass"])
        gear_out.wheel_inertia = float(st.session_state[f"{p}wheel_inertia"])
        gear_out.unload_radius = float(st.session_state[f"{p}unload_radius"])
        gear_out.kx = float(st.session_state[f"{p}kx"])
        gear_out.cx = float(st.session_state[f"{p}cx"])
        gear_out.wheelmass = float(st.session_state[f"{p}wheelmass"])

        gear_out.tyre_curve = _read_curve_editor(
            f"{p}tyre_curve_editor",
            gear_in.tyre_curve,
            "Déflexion (mm)",
            "Charge (kN)",
        )
        gear_out.mu_curve = _read_curve_editor(
            f"{p}mu_curve_editor",
            gear_in.mu_curve,
            "Slip",
            "μ",
        )

        gear_out.Dpis = float(st.session_state[f"{p}Dpis"])
        gear_out.Dbh = float(st.session_state[f"{p}Dbh"])
        gear_out.Dt = float(st.session_state[f"{p}Dt"])
        gear_out.Dp = float(st.session_state[f"{p}Dp"])
        gear_out.DInsideBh = float(st.session_state[f"{p}DInsideBh"])
        gear_out.DInsidePalierBh = float(st.session_state[f"{p}DInsidePalierBh"])
        gear_out.Lbh = float(st.session_state[f"{p}Lbh"])
        gear_out.LPalierBh = float(st.session_state[f"{p}LPalierBh"])
        gear_out.excentricite_palier_bh = float(st.session_state[f"{p}excentricite_palier_bh"])
        gear_out.course = float(st.session_state[f"{p}course"])
        gear_out.DTrouPis = float(st.session_state[f"{p}DTrouPis"])
        gear_out.NbTrouPis = int(round(float(st.session_state[f"{p}NbTrouPis"])))
        gear_out.HauteurPisBh = float(st.session_state[f"{p}HauteurPisBh"])
        gear_out.DTrouDiap = float(st.session_state[f"{p}DTrouDiap"])
        gear_out.NbTrouDiap = int(round(float(st.session_state[f"{p}NbTrouDiap"])))
        gear_out.tore = float(st.session_state[f"{p}tore"])
        gear_out.fc = float(st.session_state[f"{p}fc"])
        gear_out.fh = float(st.session_state[f"{p}fh"])
        gear_out.endstop_smooth_mm = float(st.session_state[f"{p}endstop_smooth_mm"])

        gear_out.Pinitbp = float(st.session_state[f"{p}Pinitbp"])
        gear_out.Vgbp = float(st.session_state[f"{p}Vgbp"])
        gear_out.Vh = float(st.session_state[f"{p}Vh"])
        gear_out.Pinithp = float(st.session_state[f"{p}Pinithp"])
        gear_out.Vghp = float(st.session_state[f"{p}Vghp"])
        gear_out.gamma = float(st.session_state[f"{p}gamma"])

        gear_out.visc = float(st.session_state[f"{p}visc"])
        gear_out.rho = float(st.session_state[f"{p}rho"])
        gear_out.aeration_pct = float(st.session_state[f"{p}aeration_pct"])
        gear_out.k_air = float(st.session_state[f"{p}k_air"])
        gear_out.k_huile = float(st.session_state[f"{p}k_huile"])
        gear_out.k_huile_temp_coeff = float(st.session_state[f"{p}k_huile_temp_coeff"])
        gear_out.bulk = float(st.session_state.get(f"{p}bulk", gear_in.bulk))

        gear_out.diametre_rainure = float(st.session_state[f"{p}diametre_rainure"])
        gear_out.rainures = _read_rainures_editor(f"{p}rainures_editor", gear_in.rainures)

    _apply_gear("nlg", out.nlg, base.nlg, include_strut=True)
    _apply_gear("mlg", out.mlg, base.mlg, include_strut=False)

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
