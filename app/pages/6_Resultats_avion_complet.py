"""Page resultats dediee au mode avion complet (lot 5).

Sections principales:
- Avion complet (global CG + pitch + charges)
- MLG (gauche/droite)
- NLG
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from dropsim import storage as ds_storage
from dropsim.tyre import r_eff

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_APP = Path(__file__).resolve().parent.parent
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

from theme import apply_theme  # noqa: E402

apply_theme()

st.title("Avion complet - Resultats")


def _set_loaded_aircraft_state(inputs, result, *, name: str, project: str) -> None:
    """Réinjecte une simulation avion complet chargée dans la session.

    Mêmes clés que la page Avion complet, afin que la navigation entre les deux
    pages reste cohérente. Les états de formulaire ``ac_*`` sont purgés pour que
    la page de saisie se réamorce depuis les entrées chargées.
    """
    st.session_state.aircraft_inputs = inputs
    st.session_state.aircraft_result = result
    st.session_state.aircraft_result_name = name
    st.session_state.aircraft_current_project = project
    for k in list(st.session_state.keys()):
        if k.startswith(("ac_nlg", "ac_mlg", "ac_body", "ac_sim", "ac_drop", "ac_cg", "ac_lay")):
            del st.session_state[k]


with st.expander("Charger une simulation avion complet sauvegardée", expanded=False):
    projects = ds_storage.list_projects()
    if not projects:
        st.caption("Aucune sauvegarde disponible.")
    else:
        current_project = st.session_state.get("aircraft_current_project", ds_storage.DEFAULT_PROJECT)
        load_index = projects.index(current_project) if current_project in projects else 0
        project_name = st.selectbox("Projet", projects, index=load_index, key="ac_res_load_project")
        entries = [e for e in ds_storage.list_saved(project=project_name) if e.get("project") == project_name]
        if not entries:
            st.caption("Aucune sauvegarde dans ce projet.")
        else:
            labels = {f"{e['name']} · {e['saved_at'][:16].replace('T', ' ')}": e["path"] for e in entries}
            selected = st.selectbox("Sauvegardes disponibles", list(labels.keys()), key="ac_res_load_choice")
            if st.button("Charger", key="ac_res_load_btn", use_container_width=True):
                loaded_inputs, loaded_result, meta = ds_storage.load_simulation(labels[selected])
                if getattr(loaded_inputs, "model_kind", "") != "aircraft":
                    st.error("La sauvegarde sélectionnée n'est pas une simulation avion complet.", icon="🛑")
                else:
                    _set_loaded_aircraft_state(
                        loaded_inputs, loaded_result,
                        name=meta.get("name", "Simulation avion complet"),
                        project=meta.get("project", ds_storage.DEFAULT_PROJECT),
                    )
                    st.rerun()


result = st.session_state.get("aircraft_result")
if result is None:
    st.info(
        "Aucun resultat avion complet en session. Lancez une simulation depuis la page "
        "Avion complet, ou chargez une simulation sauvegardée ci-dessus.",
        icon="ℹ️",
    )
    st.stop()

loaded_name = st.session_state.get("aircraft_result_name")
if loaded_name:
    st.caption(f"Résultat affiché : **{loaded_name}**")

df = result.df
df_energy = result.full_df if getattr(result, "full_df", None) is not None else df
aircraft_inputs = st.session_state.get("aircraft_inputs")


def _require_columns(cols: list[str], title: str) -> bool:
    missing = [c for c in cols if c not in df.columns]
    if not missing:
        return True
    st.info(
        f"{title}: colonnes indisponibles dans ce resultat ({', '.join(missing)}). "
        "Relancez une simulation avion complet.",
        icon="ℹ️",
    )
    return False


def _line(x, ys: list[tuple[str, object]], title: str, xlab: str, ylab: str) -> go.Figure:
    fig = go.Figure()
    for name, y in ys:
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=name))
    fig.update_layout(
        title=dict(text=title, y=0.98, yanchor="top"),
        xaxis_title=xlab,
        yaxis_title=ylab,
        height=560,
        margin=dict(l=8, r=8, t=56, b=110),
        legend=dict(orientation="h", yanchor="top", y=-0.14, xanchor="left", x=0),
    )
    return fig


def _line_dual(
    x,
    left: list[tuple[str, object]],
    right: list[tuple[str, object]],
    title: str,
    xlab: str,
    left_lab: str,
    right_lab: str,
) -> go.Figure:
    """Courbes avec efforts sur l'axe gauche et moments sur l'axe vertical
    secondaire (droite). Les moments sont tracés en pointillés."""
    fig = go.Figure()
    for name, y in left:
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=name))
    for name, y in right:
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=name, yaxis="y2", line=dict(dash="dot")))
    fig.update_layout(
        title=dict(text=title, y=0.98, yanchor="top"),
        xaxis_title=xlab,
        yaxis=dict(title=left_lab),
        yaxis2=dict(title=right_lab, overlaying="y", side="right", showgrid=False),
        height=560,
        margin=dict(l=8, r=8, t=56, b=110),
        legend=dict(orientation="h", yanchor="top", y=-0.14, xanchor="left", x=0),
    )
    return fig


def _cumtrapz(time_s: np.ndarray, signal: np.ndarray) -> np.ndarray:
    if len(time_s) == 0:
        return np.array([], dtype=float)
    out = np.zeros_like(signal, dtype=float)
    if len(time_s) < 2:
        return out
    dt = np.diff(time_s)
    out[1:] = np.cumsum(0.5 * (signal[:-1] + signal[1:]) * dt)
    return out


def _compute_absorbed_energy_by_train(
    df_src,
    *,
    train: str,
    vx: float,
    wheel_radius_m: float,
) -> dict[str, np.ndarray] | None:
    if "Temps (s)" not in df_src.columns:
        return None
    t_s = df_src["Temps (s)"].to_numpy(dtype=float)

    specs = {
        "nlg": {
            "v": "NLG.v (m/s)",
            "fhyd": "NLG.Fhyd (N)",
            "ffric": ["NLG.FFriJoi (N)", "NLG.FFriBag (N)"],
            "fgas": "NLG.FGas (N)",
            "mu": "NLG.Tyre.Mu (-)",
            "fz": "NLG.Tyre.FTyre (N)",
            "omega": "NLG.Tyre.Omega (rad/s)",
            "defl": "NLG.TyreDefl (m)",
        },
        "mlg_left": {
            "v": "MLG left.v (m/s)",
            "fhyd": "MLG left.Fhyd (N)",
            "ffric": ["MLG left.FFriJoi (N)"],
            "fgas": "MLG left.FGas (N)",
            "mu": "MLG left.Tyre.Mu (-)",
            "fz": "MLG left.Tyre.FTyre (N)",
            "omega": "MLG left.Tyre.Omega (rad/s)",
            "defl": "MLG left.TyreDefl (m)",
        },
        "mlg_right": {
            "v": "MLG right.v (m/s)",
            "fhyd": "MLG right.Fhyd (N)",
            "ffric": ["MLG right.FFriJoi (N)"],
            "fgas": "MLG right.FGas (N)",
            "mu": "MLG right.Tyre.Mu (-)",
            "fz": "MLG right.Tyre.FTyre (N)",
            "omega": "MLG right.Tyre.Omega (rad/s)",
            "defl": "MLG right.TyreDefl (m)",
        },
    }
    if train not in specs:
        return None
    s = specs[train]
    needed = [s["v"], s["fhyd"], s["fgas"], s["mu"], s["fz"], s["omega"], s["defl"], *s["ffric"]]
    if any(c not in df_src.columns for c in needed):
        return None

    v = df_src[s["v"]].to_numpy(dtype=float)
    fhyd = df_src[s["fhyd"]].to_numpy(dtype=float)
    fgas = df_src[s["fgas"]].to_numpy(dtype=float)
    ffric = np.zeros_like(v)
    for c in s["ffric"]:
        ffric += df_src[c].to_numpy(dtype=float)

    mu_t = np.abs(df_src[s["mu"]].to_numpy(dtype=float))
    fz_t = np.abs(df_src[s["fz"]].to_numpy(dtype=float))
    omega = df_src[s["omega"]].to_numpy(dtype=float)
    defl = df_src[s["defl"]].to_numpy(dtype=float)

    p_hyd = np.maximum(0.0, -(fhyd * v))
    p_fric = np.maximum(0.0, -(ffric * v))
    reff = r_eff(wheel_radius_m, defl)
    p_slip = mu_t * fz_t * np.abs(vx - omega * reff)
    p_store_gas = -(fgas * v)
    p_store_tyre = fz_t * np.gradient(defl, t_s)

    e_total = _cumtrapz(t_s, p_hyd + p_fric + p_slip + p_store_gas + p_store_tyre)
    return {
        "temps": t_s,
        "e_total": e_total,
    }


def _rotate_xz(x_local: np.ndarray, z_local: np.ndarray, pitch_rad: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    cos_t = np.cos(pitch_rad)
    sin_t = np.sin(pitch_rad)
    return x_local * cos_t - z_local * sin_t, x_local * sin_t + z_local * cos_t


def _render_aircraft_animation() -> None:
    if aircraft_inputs is None:
        st.info(
            "Les entrées avion ne sont pas disponibles dans la session. Relancez la simulation depuis la page Avion complet.",
            icon="ℹ️",
        )
        return

    required_cols = [
        "Temps (s)",
        "Aircraft.CG.z (m)",
        "Aircraft.Pitch (rad)",
        "NLG.TyreDefl (m)",
        "MLG left.TyreDefl (m)",
        "MLG right.TyreDefl (m)",
    ]
    if not _require_columns(required_cols, "Animation avion complet"):
        return

    geom = getattr(result, "geometry", None)
    geom_required = [
        "temps",
        "cg_x",
        "cg_z",
        "ground_z",
        "nlg_bx",
        "nlg_bz",
        "nlg_gtx",
        "nlg_gtz",
        "nlg_gbx",
        "nlg_gbz",
        "nlg_rx",
        "nlg_rz",
        "nlg_wheel_radius",
        "mlg_left_ax",
        "mlg_left_az",
        "mlg_left_bx",
        "mlg_left_bz",
        "mlg_left_cx",
        "mlg_left_cz",
        "mlg_left_rx",
        "mlg_left_rz",
        "mlg_left_wheel_radius",
        "mlg_right_ax",
        "mlg_right_az",
        "mlg_right_bx",
        "mlg_right_bz",
        "mlg_right_cx",
        "mlg_right_cz",
        "mlg_right_rx",
        "mlg_right_rz",
        "mlg_right_wheel_radius",
    ]
    use_geom = geom is not None and not geom.empty and all(col in geom.columns for col in geom_required)

    st.caption(
        "Vue de côté du fuselage, du centre de gravité et des trains. "
        "Les points caractéristiques NLG/MLG sont animés à partir du modèle avion quand ils sont disponibles."
    )

    time_s = df["Temps (s)"].to_numpy(dtype=float)
    cg_z_mm = df["Aircraft.CG.z (m)"].to_numpy(dtype=float) * 1000.0 + float(aircraft_inputs.body.cg.z)
    pitch = df["Aircraft.Pitch (rad)"].to_numpy(dtype=float)
    n = len(time_s)

    stride = max(1, n // 70)
    idx = list(range(0, n, stride))
    if idx[-1] != n - 1:
        idx.append(n - 1)

    # Géométrie locale dans le repère avion, centrée au CG, en mm.
    cg_x0 = float(aircraft_inputs.body.cg.x)
    cg_z0 = float(aircraft_inputs.body.cg.z)
    nlg_x_local = float(aircraft_inputs.layout.nlg_station.x) - cg_x0
    nlg_z_local = float(aircraft_inputs.layout.nlg_station.z) - cg_z0
    mlg_l_x_local = float(aircraft_inputs.layout.mlg_left_station.x) - cg_x0
    mlg_l_z_local = float(aircraft_inputs.layout.mlg_left_station.z) - cg_z0
    mlg_r_x_local = float(aircraft_inputs.layout.mlg_right_station.x) - cg_x0
    mlg_r_z_local = float(aircraft_inputs.layout.mlg_right_station.z) - cg_z0

    x_min_local = min(nlg_x_local, mlg_l_x_local, mlg_r_x_local)
    x_max_local = max(nlg_x_local, mlg_l_x_local, mlg_r_x_local)
    body_x_local = np.array([
        x_min_local - 1100.0,
        x_min_local - 350.0,
        x_max_local + 1500.0,
    ])
    body_z_local = np.array([80.0, 0.0, -40.0])

    cg_z_plot = cg_z_mm.copy()

    body_x_world, body_z_world = _rotate_xz(body_x_local[:, None], body_z_local[:, None], pitch[None, :])
    body_x_world = body_x_world + cg_x0
    body_z_world = body_z_world + cg_z_plot

    nlg_mount_x, nlg_mount_z = _rotate_xz(np.full(n, nlg_x_local), np.full(n, nlg_z_local), pitch)
    mlg_l_mount_x, mlg_l_mount_z = _rotate_xz(np.full(n, mlg_l_x_local), np.full(n, mlg_l_z_local), pitch)
    mlg_r_mount_x, mlg_r_mount_z = _rotate_xz(np.full(n, mlg_r_x_local), np.full(n, mlg_r_z_local), pitch)

    nlg_mount_x += cg_x0
    mlg_l_mount_x += cg_x0
    mlg_r_mount_x += cg_x0
    nlg_mount_z += cg_z_plot
    mlg_l_mount_z += cg_z_plot
    mlg_r_mount_z += cg_z_plot

    nlg_radius = float(aircraft_inputs.nlg.unload_radius)
    mlg_radius = float(aircraft_inputs.mlg.unload_radius)
    nlg_defl = df["NLG.TyreDefl (m)"].to_numpy(dtype=float) * 1000.0
    mlg_l_defl = df["MLG left.TyreDefl (m)"].to_numpy(dtype=float) * 1000.0
    mlg_r_defl = df["MLG right.TyreDefl (m)"].to_numpy(dtype=float) * 1000.0

    ground_mm = 0.0
    nlg_wheel_x = nlg_mount_x
    mlg_l_wheel_x = mlg_l_mount_x
    mlg_r_wheel_x = mlg_r_mount_x
    nlg_wheel_z = ground_mm + nlg_radius - nlg_defl
    mlg_l_wheel_z = ground_mm + mlg_radius - mlg_l_defl
    mlg_r_wheel_z = ground_mm + mlg_radius - mlg_r_defl

    if use_geom:
        geom_time = geom["temps"].to_numpy(dtype=float)
        if len(geom_time) == len(time_s) and np.allclose(geom_time, time_s):
            cg_x_anim = geom["cg_x"].to_numpy(dtype=float) * 1000.0
            cg_z_anim = geom["cg_z"].to_numpy(dtype=float) * 1000.0
            ground_anim = geom["ground_z"].to_numpy(dtype=float) * 1000.0
            nlg_bx = geom["nlg_bx"].to_numpy(dtype=float) * 1000.0
            nlg_bz = geom["nlg_bz"].to_numpy(dtype=float) * 1000.0
            nlg_gtx = geom["nlg_gtx"].to_numpy(dtype=float) * 1000.0
            nlg_gtz = geom["nlg_gtz"].to_numpy(dtype=float) * 1000.0
            nlg_gbx = geom["nlg_gbx"].to_numpy(dtype=float) * 1000.0
            nlg_gbz = geom["nlg_gbz"].to_numpy(dtype=float) * 1000.0
            nlg_rx = geom["nlg_rx"].to_numpy(dtype=float) * 1000.0
            nlg_rz = geom["nlg_rz"].to_numpy(dtype=float) * 1000.0
            nlg_radius_anim = geom["nlg_wheel_radius"].to_numpy(dtype=float) * 1000.0

            mlg_l_ax = geom["mlg_left_ax"].to_numpy(dtype=float) * 1000.0
            mlg_l_az = geom["mlg_left_az"].to_numpy(dtype=float) * 1000.0
            mlg_l_bx = geom["mlg_left_bx"].to_numpy(dtype=float) * 1000.0
            mlg_l_bz = geom["mlg_left_bz"].to_numpy(dtype=float) * 1000.0
            mlg_l_cx = geom["mlg_left_cx"].to_numpy(dtype=float) * 1000.0
            mlg_l_cz = geom["mlg_left_cz"].to_numpy(dtype=float) * 1000.0
            mlg_l_rx = geom["mlg_left_rx"].to_numpy(dtype=float) * 1000.0
            mlg_l_rz = geom["mlg_left_rz"].to_numpy(dtype=float) * 1000.0
            mlg_l_radius_anim = geom["mlg_left_wheel_radius"].to_numpy(dtype=float) * 1000.0

            mlg_r_ax = geom["mlg_right_ax"].to_numpy(dtype=float) * 1000.0
            mlg_r_az = geom["mlg_right_az"].to_numpy(dtype=float) * 1000.0
            mlg_r_bx = geom["mlg_right_bx"].to_numpy(dtype=float) * 1000.0
            mlg_r_bz = geom["mlg_right_bz"].to_numpy(dtype=float) * 1000.0
            mlg_r_cx = geom["mlg_right_cx"].to_numpy(dtype=float) * 1000.0
            mlg_r_cz = geom["mlg_right_cz"].to_numpy(dtype=float) * 1000.0
            mlg_r_rx = geom["mlg_right_rx"].to_numpy(dtype=float) * 1000.0
            mlg_r_rz = geom["mlg_right_rz"].to_numpy(dtype=float) * 1000.0
            mlg_r_radius_anim = geom["mlg_right_wheel_radius"].to_numpy(dtype=float) * 1000.0
            cg_z_plot = cg_z_anim

            body_x_world, body_z_world = _rotate_xz(body_x_local[:, None], body_z_local[:, None], pitch[None, :])
            body_x_world = body_x_world + cg_x0
            body_z_world = body_z_world + cg_z_plot

            nlg_mount_x, nlg_mount_z = _rotate_xz(np.full(n, nlg_x_local), np.full(n, nlg_z_local), pitch)
            mlg_l_mount_x, mlg_l_mount_z = _rotate_xz(np.full(n, mlg_l_x_local), np.full(n, mlg_l_z_local), pitch)
            mlg_r_mount_x, mlg_r_mount_z = _rotate_xz(np.full(n, mlg_r_x_local), np.full(n, mlg_r_z_local), pitch)
            nlg_mount_x += cg_x0
            mlg_l_mount_x += cg_x0
            mlg_r_mount_x += cg_x0
            nlg_mount_z += cg_z_plot
            mlg_l_mount_z += cg_z_plot
            mlg_r_mount_z += cg_z_plot
        else:
            use_geom = False

    theta = np.linspace(0.0, 2.0 * np.pi, 48)

    def _wheel_trace(cx: float, cz: float, radius: float, name: str, color: str) -> go.Scatter:
        return go.Scatter(
            x=cx + radius * np.sin(theta),
            y=cz + radius * np.cos(theta),
            mode="lines",
            line=dict(color=color, width=3),
            fill="toself",
            fillcolor="rgba(138,26,29,0.08)" if color == "#8A1A1D" else "rgba(74,73,73,0.08)",
            name=name,
        )

    def _frame_traces(i: int) -> list[go.Scatter]:
        fuselage = go.Scatter(
            x=body_x_world[:, i],
            y=body_z_world[:, i],
            mode="lines",
            line=dict(color="#8A1A1D", width=8, shape="spline", smoothing=0.7),
            name="Fuselage",
        )
        cg_marker = go.Scatter(
            x=[cg_x0],
            y=[cg_z_plot[i]],
            mode="markers+text",
            marker=dict(size=12, color="#B97677"),
            text=["CG"],
            textposition="top center",
            name="Centre de gravité",
        )
        if not use_geom:
            nlg_leg = go.Scatter(
                x=[nlg_mount_x[i], nlg_wheel_x[i]],
                y=[nlg_mount_z[i], nlg_wheel_z[i]],
                mode="lines",
                line=dict(color="#4A4949", width=4),
                name="NLG",
            )
            mlg_l_leg = go.Scatter(
                x=[mlg_l_mount_x[i], mlg_l_wheel_x[i]],
                y=[mlg_l_mount_z[i], mlg_l_wheel_z[i]],
                mode="lines",
                line=dict(color="#878786", width=4),
                name="MLG gauche",
            )
            mlg_r_leg = go.Scatter(
                x=[mlg_r_mount_x[i], mlg_r_wheel_x[i]],
                y=[mlg_r_mount_z[i], mlg_r_wheel_z[i]],
                mode="lines",
                line=dict(color="#B7B7B6", width=4),
                name="MLG droite",
            )
            mount_points = go.Scatter(
                x=[nlg_mount_x[i], mlg_l_mount_x[i], mlg_r_mount_x[i]],
                y=[nlg_mount_z[i], mlg_l_mount_z[i], mlg_r_mount_z[i]],
                mode="markers",
                marker=dict(size=7, color="#4A4949"),
                name="Attaches trains",
            )
            return [
                fuselage,
                cg_marker,
                nlg_leg,
                mlg_l_leg,
                mlg_r_leg,
                _wheel_trace(nlg_wheel_x[i], nlg_wheel_z[i], nlg_radius, "Roue NLG", "#8A1A1D"),
                _wheel_trace(mlg_l_wheel_x[i], mlg_l_wheel_z[i], mlg_radius, "Roue MLG gauche", "#4A4949"),
                _wheel_trace(mlg_r_wheel_x[i], mlg_r_wheel_z[i], mlg_radius, "Roue MLG droite", "#878786"),
                mount_points,
            ]

        nlg_leg = go.Scatter(
            x=[nlg_bx[i], nlg_rx[i]],
            y=[nlg_bz[i], nlg_rz[i]],
            mode="lines",
            line=dict(color="#4A4949", width=4),
            name="NLG",
        )
        nlg_guides = go.Scatter(
            x=[nlg_gtx[i], nlg_gbx[i]],
            y=[nlg_gtz[i], nlg_gbz[i]],
            mode="lines",
            line=dict(color="#B97677", width=3, dash="dot"),
            name="Guidage NLG",
        )
        nlg_points = go.Scatter(
            x=[nlg_bx[i], nlg_gtx[i], nlg_gbx[i], nlg_rx[i]],
            y=[nlg_bz[i], nlg_gtz[i], nlg_gbz[i], nlg_rz[i]],
            mode="markers+text",
            text=["B", "Gt", "Gb", "R"],
            textposition="top center",
            marker=dict(size=8, color="#8A1A1D"),
            name="Points NLG",
        )
        mlg_l_leg = go.Scatter(
            x=[mlg_l_ax[i], mlg_l_bx[i], mlg_l_rx[i]],
            y=[mlg_l_az[i], mlg_l_bz[i], mlg_l_rz[i]],
            mode="lines",
            line=dict(color="#878786", width=4),
            name="MLG gauche",
        )
        mlg_l_shock = go.Scatter(
            x=[mlg_l_cx[i], mlg_l_ax[i]],
            y=[mlg_l_cz[i], mlg_l_az[i]],
            mode="lines",
            line=dict(color="#4A4949", width=4),
            name="Amortisseur MLG gauche",
        )
        mlg_l_points = go.Scatter(
            x=[mlg_l_ax[i], mlg_l_bx[i], mlg_l_cx[i], mlg_l_rx[i]],
            y=[mlg_l_az[i], mlg_l_bz[i], mlg_l_cz[i], mlg_l_rz[i]],
            mode="markers+text",
            text=["A", "B", "C", "R"],
            textposition="top center",
            marker=dict(size=8, color="#4A4949"),
            name="Points MLG gauche",
        )
        mlg_r_leg = go.Scatter(
            x=[mlg_r_ax[i], mlg_r_bx[i], mlg_r_rx[i]],
            y=[mlg_r_az[i], mlg_r_bz[i], mlg_r_rz[i]],
            mode="lines",
            line=dict(color="#B7B7B6", width=4, dash="dash"),
            name="MLG droite",
        )
        mlg_r_shock = go.Scatter(
            x=[mlg_r_cx[i], mlg_r_ax[i]],
            y=[mlg_r_cz[i], mlg_r_az[i]],
            mode="lines",
            line=dict(color="#878786", width=4, dash="dash"),
            name="Amortisseur MLG droite",
        )
        return [
            fuselage,
            cg_marker,
            nlg_leg,
            nlg_guides,
            nlg_points,
            mlg_l_leg,
            mlg_l_shock,
            mlg_l_points,
            mlg_r_leg,
            mlg_r_shock,
            _wheel_trace(nlg_rx[i], nlg_rz[i], nlg_radius_anim[i], "Roue NLG", "#8A1A1D"),
            _wheel_trace(mlg_l_rx[i], mlg_l_rz[i], mlg_l_radius_anim[i], "Roue MLG gauche", "#4A4949"),
            _wheel_trace(mlg_r_rx[i], mlg_r_rz[i], mlg_r_radius_anim[i], "Roue MLG droite", "#878786"),
        ]

    if use_geom:
        xmin = float(min(body_x_world.min(), nlg_bx.min(), nlg_gtx.min(), nlg_gbx.min(), nlg_rx.min() - nlg_radius_anim.max(), mlg_l_ax.min(), mlg_l_bx.min(), mlg_l_cx.min(), mlg_l_rx.min() - mlg_l_radius_anim.max(), mlg_r_ax.min(), mlg_r_bx.min(), mlg_r_cx.min(), mlg_r_rx.min() - mlg_r_radius_anim.max()) - 120.0)
        xmax = float(max(body_x_world.max(), nlg_bx.max(), nlg_gtx.max(), nlg_gbx.max(), nlg_rx.max() + nlg_radius_anim.max(), mlg_l_ax.max(), mlg_l_bx.max(), mlg_l_cx.max(), mlg_l_rx.max() + mlg_l_radius_anim.max(), mlg_r_ax.max(), mlg_r_bx.max(), mlg_r_cx.max(), mlg_r_rx.max() + mlg_r_radius_anim.max()) + 120.0)
        zmax = float(max(body_z_world.max(), cg_z_anim.max(), nlg_bz.max(), nlg_gtz.max(), nlg_gbz.max(), nlg_rz.max() + nlg_radius_anim.max(), mlg_l_az.max(), mlg_l_bz.max(), mlg_l_cz.max(), mlg_l_rz.max() + mlg_l_radius_anim.max(), mlg_r_az.max(), mlg_r_bz.max(), mlg_r_cz.max(), mlg_r_rz.max() + mlg_r_radius_anim.max()) + 180.0)
        zmin = float(min(ground_anim.min() - 60.0, nlg_rz.min() - nlg_radius_anim.max() - 60.0, mlg_l_rz.min() - mlg_l_radius_anim.max() - 60.0, mlg_r_rz.min() - mlg_r_radius_anim.max() - 60.0))
    else:
        xmin = float(min(body_x_world.min(), nlg_wheel_x.min() - nlg_radius, mlg_l_wheel_x.min() - mlg_radius, mlg_r_wheel_x.min() - mlg_radius) - 120.0)
        xmax = float(max(body_x_world.max(), nlg_wheel_x.max() + nlg_radius, mlg_l_wheel_x.max() + mlg_radius, mlg_r_wheel_x.max() + mlg_radius) + 120.0)
        zmax = float(max(body_z_world.max(), cg_z_mm.max()) + 180.0)
        zmin = float(min(ground_mm - 60.0, nlg_wheel_z.min() - nlg_radius - 60.0, mlg_l_wheel_z.min() - mlg_radius - 60.0, mlg_r_wheel_z.min() - mlg_radius - 60.0))

    ground_line = go.Scatter(
        x=[xmin, xmax],
        y=[float(ground_anim[0]) if use_geom else ground_mm, float(ground_anim[0]) if use_geom else ground_mm],
        mode="lines",
        line=dict(color="#929292", width=2),
        name="Sol",
    )

    if len(idx) > 1:
        sampled_dt_ms = float(np.mean(np.diff(time_s[idx])) * 1000.0)
    else:
        sampled_dt_ms = 40.0
    real_time_frame_ms = max(1, int(round(sampled_dt_ms)))

    def _anim_args(speed_factor: float) -> list[object]:
        duration = max(1, int(round(real_time_frame_ms / speed_factor)))
        return [None, dict(frame=dict(duration=duration, redraw=True), fromcurrent=True, transition=dict(duration=0))]

    fig = go.Figure(
        data=[ground_line] + _frame_traces(0),
        frames=[go.Frame(data=[ground_line] + _frame_traces(i), name=f"{time_s[i]*1000:.0f}") for i in idx],
    )
    fig.update_layout(
        height=580,
        xaxis=dict(title="X avion (mm)", range=[xmin, xmax], constrain="domain", showgrid=True, gridcolor="#E6E6E6"),
        yaxis=dict(title="Z avion (mm)", range=[zmin, zmax], scaleanchor="x", scaleratio=1.0, showgrid=True, gridcolor="#E6E6E6"),
        margin=dict(l=8, r=8, t=30, b=140),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            x=0.0,
            y=0.02,
            xanchor="left",
            direction="left",
            buttons=[
                dict(label="▶ 1x", method="animate", args=_anim_args(1.0)),
                dict(label="▶ 0.5x", method="animate", args=_anim_args(0.5)),
                dict(label="▶ 0.25x", method="animate", args=_anim_args(0.25)),
                dict(label="⏸ Pause", method="animate", args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")]),
            ],
        )],
        sliders=[dict(
            active=0,
            x=0.0,
            len=1.0,
            y=-0.08,
            currentvalue=dict(prefix="t = ", suffix=" ms"),
            steps=[
                dict(
                    method="animate",
                    label=f"{time_s[i]*1000:.0f}",
                    args=[[f"{time_s[i]*1000:.0f}"], dict(mode="immediate", frame=dict(duration=0, redraw=True), transition=dict(duration=0))],
                )
                for i in idx
            ],
        )],
    )
    st.plotly_chart(fig, use_container_width=True)


st.subheader("Synthese")
s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("Pas", f"{result.n_steps}")
s2.metric("Fz total max", f"{result.summary.get('Effort vertical total max Fz (N)', 0.0):.0f} N")
s3.metric("Moment tangage max", f"{result.summary.get('Moment de tangage max (N.m)', 0.0):.0f} N.m")
s4.metric("Acc CG max", f"{result.summary.get('Accélération CG max (g)', result.summary.get('Acceleration CG max (g)', 0.0)):.3f} g")

contact_metric = "N/A"
contact_label = "Contact initial roue basse"
geom0 = getattr(result, "geometry", None)
contact_cols = [
    "nlg_rz", "nlg_wheel_radius",
    "mlg_left_rz", "mlg_left_wheel_radius",
    "mlg_right_rz", "mlg_right_wheel_radius",
]
if geom0 is not None and not geom0.empty and all(c in geom0.columns for c in contact_cols):
    gaps = {
        "NLG": float(geom0["nlg_rz"].iloc[0] - geom0["nlg_wheel_radius"].iloc[0]),
        "MLG gauche": float(geom0["mlg_left_rz"].iloc[0] - geom0["mlg_left_wheel_radius"].iloc[0]),
        "MLG droite": float(geom0["mlg_right_rz"].iloc[0] - geom0["mlg_right_wheel_radius"].iloc[0]),
    }
    lowest_name = min(gaps, key=gaps.get)
    lowest_gap_mm = gaps[lowest_name] * 1000.0
    contact_metric = f"{lowest_gap_mm:.3f} mm"
    contact_label = f"Contact initial roue basse ({lowest_name})"

s5.metric(contact_label, contact_metric)

t = df["Temps (s)"]


def _liaison_charts(label: str, base: str, *, has_c: bool, b_kind: str) -> None:
    """Trace, pour chaque liaison du train avec la structure, les efforts (axe
    gauche) et les moments (axe vertical secondaire). ``base`` est le préfixe de
    colonne ("NLG", "MLG left", "MLG right"). ``b_kind`` qualifie la liaison B
    ("encastrement" pour un StraitStrut, "pivot" pour un TrailingArm)."""
    fx, fz = f"{base}.Torseur@B.Fx (N)", f"{base}.Torseur@B.Fz (N)"
    mx, mz = f"{base}.Torseur@B.Mx (N.m)", f"{base}.Torseur@B.Mz (N.m)"
    my = f"{base}.Torseur@B.My tangage (N.m)"
    if _require_columns([fx, fz, mx, mz], f"{label} - Liaison B"):
        moments = [("Moment Mx", df[mx]), ("Moment Mz", df[mz])]
        if my in df.columns:
            moments.insert(1, ("Moment My (tangage)", df[my]))
        st.plotly_chart(
            _line_dual(
                t,
                [("Effort Fx", df[fx]), ("Effort Fz", df[fz])],
                moments,
                f"{label} — Liaison {b_kind} B : efforts (gauche) + moments (axe secondaire)",
                "Temps (s)", "Effort (N)", "Moment (N.m)",
            ),
            use_container_width=True,
        )
    if has_c:
        cfx, cfz = f"{base}.Torseur@C.Fx (N)", f"{base}.Torseur@C.Fz (N)"
        if _require_columns([cfx, cfz], f"{label} - Liaison C"):
            st.plotly_chart(
                _line(
                    t,
                    [("Effort Fx", df[cfx]), ("Effort Fz", df[cfz])],
                    f"{label} — Liaison rotule C : efforts (pas de moment transmis)",
                    "Temps (s)", "Effort (N)",
                ),
                use_container_width=True,
            )


tab_aircraft, tab_mlg, tab_nlg = st.tabs(["Avion complet", "Section MLG", "Section NLG"])

with tab_aircraft:
    st.markdown("### Animation")
    _render_aircraft_animation()

    if _require_columns([
        "Aircraft.CG.z (m)",
        "Aircraft.CG.vz (m/s)",
        "Aircraft.CG.az (m/s²)",
    ], "Section avion - dynamique CG"):
        st.plotly_chart(
            _line(
                t,
                [
                    ("CG z", df["Aircraft.CG.z (m)"]),
                    ("CG vz", df["Aircraft.CG.vz (m/s)"]),
                    ("CG az", df["Aircraft.CG.az (m/s²)"]),
                ],
                "Dynamique verticale du centre de gravite",
                "Temps (s)",
                "m / m/s / m/s2",
            ),
            use_container_width=True,
        )

    if _require_columns([
        "Aircraft.Pitch (rad)",
        "Aircraft.PitchRate (rad/s)",
        "Aircraft.PitchAcc (rad/s²)",
    ], "Section avion - tangage"):
        st.plotly_chart(
            _line(
                t,
                [
                    ("Pitch", df["Aircraft.Pitch (rad)"]),
                    ("Pitch rate", df["Aircraft.PitchRate (rad/s)"]),
                    ("Pitch acc", df["Aircraft.PitchAcc (rad/s²)"]),
                ],
                "Dynamique de tangage",
                "Temps (s)",
                "rad / rad/s / rad/s2",
            ),
            use_container_width=True,
        )

    if _require_columns([
        "Aircraft.Fz total (N)",
        "Aircraft.Fz NLG (N)",
        "Aircraft.Fz MLG left (N)",
        "Aircraft.Fz MLG right (N)",
        "Aircraft.Mpitch total (N.m)",
    ], "Section avion - charges"):
        st.plotly_chart(
            _line(
                t,
                [
                    ("Fz total", df["Aircraft.Fz total (N)"]),
                    ("Fz NLG", df["Aircraft.Fz NLG (N)"]),
                    ("Fz MLG left", df["Aircraft.Fz MLG left (N)"]),
                    ("Fz MLG right", df["Aircraft.Fz MLG right (N)"]),
                    ("Mpitch", df["Aircraft.Mpitch total (N.m)"]),
                ],
                "Charges globales avion",
                "Temps (s)",
                "N / N.m",
            ),
            use_container_width=True,
        )

    st.markdown("### Bilan energetique")
    energy_required = [
        "Aircraft.CG.z (m)",
        "Aircraft.CG.vz (m/s)",
        "Aircraft.PitchRate (rad/s)",
        "NLG.v (m/s)",
        "MLG left.v (m/s)",
        "MLG right.v (m/s)",
        "NLG.Fhyd (N)",
        "MLG left.Fhyd (N)",
        "MLG right.Fhyd (N)",
        "NLG.FFriJoi (N)",
        "NLG.FFriBag (N)",
        "MLG left.FFriJoi (N)",
        "MLG right.FFriJoi (N)",
        "NLG.FGas (N)",
        "MLG left.FGas (N)",
        "MLG right.FGas (N)",
        "NLG.Tyre.FTyre (N)",
        "MLG left.Tyre.FTyre (N)",
        "MLG right.Tyre.FTyre (N)",
        "NLG.Tyre.Mu (-)",
        "MLG left.Tyre.Mu (-)",
        "MLG right.Tyre.Mu (-)",
        "NLG.Tyre.Omega (rad/s)",
        "MLG left.Tyre.Omega (rad/s)",
        "MLG right.Tyre.Omega (rad/s)",
        "NLG.TyreDefl (m)",
        "MLG left.TyreDefl (m)",
        "MLG right.TyreDefl (m)",
    ]
    if aircraft_inputs is None:
        st.info(
            "Bilan energetique indisponible: entrées avion absentes de la session.",
            icon="ℹ️",
        )
    elif not [c for c in energy_required if c not in df_energy.columns]:
        t_s = t.to_numpy(dtype=float)
        z = df_energy["Aircraft.CG.z (m)"].to_numpy(dtype=float)
        vz = df_energy["Aircraft.CG.vz (m/s)"].to_numpy(dtype=float)
        q = df_energy["Aircraft.PitchRate (rad/s)"].to_numpy(dtype=float)

        mass = float(aircraft_inputs.body.masse)
        jyy = float(aircraft_inputs.body.jyy)
        lift = float(aircraft_inputs.body.lift)
        vx = float(aircraft_inputs.drop.vx)
        g_eff = 9.81 * (1.0 - lift)

        e_kin_trans = 0.5 * mass * vz * vz
        e_kin_rot = 0.5 * jyy * q * q
        e_kin_total = e_kin_trans + e_kin_rot
        e_gravity = mass * g_eff * (z[0] - z)
        e_input = float(e_kin_total[0]) + e_gravity

        v_nlg = df_energy["NLG.v (m/s)"].to_numpy(dtype=float)
        v_mlg_l = df_energy["MLG left.v (m/s)"].to_numpy(dtype=float)
        v_mlg_r = df_energy["MLG right.v (m/s)"].to_numpy(dtype=float)

        fhyd_nlg = df_energy["NLG.Fhyd (N)"].to_numpy(dtype=float)
        fhyd_mlg_l = df_energy["MLG left.Fhyd (N)"].to_numpy(dtype=float)
        fhyd_mlg_r = df_energy["MLG right.Fhyd (N)"].to_numpy(dtype=float)

        ffr_nlg = df_energy["NLG.FFriJoi (N)"].to_numpy(dtype=float)
        ffrbag_nlg = df_energy["NLG.FFriBag (N)"].to_numpy(dtype=float)
        ffr_mlg_l = df_energy["MLG left.FFriJoi (N)"].to_numpy(dtype=float)
        ffr_mlg_r = df_energy["MLG right.FFriJoi (N)"].to_numpy(dtype=float)

        p_hyd = np.maximum(0.0, -(fhyd_nlg * v_nlg + fhyd_mlg_l * v_mlg_l + fhyd_mlg_r * v_mlg_r))
        p_fric = np.maximum(0.0, -(ffr_nlg * v_nlg + ffrbag_nlg * v_nlg + ffr_mlg_l * v_mlg_l + ffr_mlg_r * v_mlg_r))

        fgas_nlg = df_energy["NLG.FGas (N)"].to_numpy(dtype=float)
        fgas_mlg_l = df_energy["MLG left.FGas (N)"].to_numpy(dtype=float)
        fgas_mlg_r = df_energy["MLG right.FGas (N)"].to_numpy(dtype=float)
        p_store_gas_signed = -(fgas_nlg * v_nlg + fgas_mlg_l * v_mlg_l + fgas_mlg_r * v_mlg_r)
        p_store_gas = p_store_gas_signed

        nlg_mu = np.abs(df_energy["NLG.Tyre.Mu (-)"].to_numpy(dtype=float))
        nlg_fz = np.abs(df_energy["NLG.Tyre.FTyre (N)"].to_numpy(dtype=float))
        nlg_omega = df_energy["NLG.Tyre.Omega (rad/s)"].to_numpy(dtype=float)
        nlg_defl = df_energy["NLG.TyreDefl (m)"].to_numpy(dtype=float)
        mlg_l_mu = np.abs(df_energy["MLG left.Tyre.Mu (-)"].to_numpy(dtype=float))
        mlg_l_fz = np.abs(df_energy["MLG left.Tyre.FTyre (N)"].to_numpy(dtype=float))
        mlg_l_omega = df_energy["MLG left.Tyre.Omega (rad/s)"].to_numpy(dtype=float)
        mlg_l_defl = df_energy["MLG left.TyreDefl (m)"].to_numpy(dtype=float)
        mlg_r_mu = np.abs(df_energy["MLG right.Tyre.Mu (-)"].to_numpy(dtype=float))
        mlg_r_fz = np.abs(df_energy["MLG right.Tyre.FTyre (N)"].to_numpy(dtype=float))
        mlg_r_omega = df_energy["MLG right.Tyre.Omega (rad/s)"].to_numpy(dtype=float)
        mlg_r_defl = df_energy["MLG right.TyreDefl (m)"].to_numpy(dtype=float)

        rnlg = r_eff(float(aircraft_inputs.nlg.unload_radius) / 1000.0, nlg_defl)
        rmlg_l = r_eff(float(aircraft_inputs.mlg.unload_radius) / 1000.0, mlg_l_defl)
        rmlg_r = r_eff(float(aircraft_inputs.mlg.unload_radius) / 1000.0, mlg_r_defl)
        vslip_nlg = np.abs(vx - nlg_omega * rnlg)
        vslip_mlg_l = np.abs(vx - mlg_l_omega * rmlg_l)
        vslip_mlg_r = np.abs(vx - mlg_r_omega * rmlg_r)
        p_slip = nlg_mu * nlg_fz * vslip_nlg + mlg_l_mu * mlg_l_fz * vslip_mlg_l + mlg_r_mu * mlg_r_fz * vslip_mlg_r

        dnlg = np.gradient(nlg_defl, t_s)
        dmlg_l = np.gradient(mlg_l_defl, t_s)
        dmlg_r = np.gradient(mlg_r_defl, t_s)
        # Stockage pneu net (signé): charge en compression, restitution en détente.
        p_store_tyre_signed = nlg_fz * dnlg + mlg_l_fz * dmlg_l + mlg_r_fz * dmlg_r
        p_store_tyre = p_store_tyre_signed

        e_hyd = _cumtrapz(t_s, p_hyd)
        e_fric = _cumtrapz(t_s, p_fric)
        e_slip = _cumtrapz(t_s, p_slip)
        e_diss_total = e_hyd + e_fric + e_slip
        e_store_gas = _cumtrapz(t_s, p_store_gas)
        e_store_tyre = _cumtrapz(t_s, p_store_tyre)
        e_store_total = e_store_gas + e_store_tyre

        e_residual = e_input - (e_kin_total + e_diss_total)
        e_gap_quasi = e_input - (e_kin_total + e_diss_total + e_store_total)
        ref = abs(float(e_input[0])) if abs(float(e_input[0])) > 1.0e-9 else 1.0
        e_res_max = float(np.max(np.abs(e_residual)))
        e_gap_max = float(np.max(np.abs(e_gap_quasi)))

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Apport initial", f"{float(e_input[0]):.0f} J")
        c2.metric("Dissipation hydraulique", f"{float(e_hyd[-1]):.0f} J")
        c3.metric("Stockage gaz+pneu", f"{float(e_store_total[-1]):.0f} J")
        c4.metric(
            "|Écart quasi fermé| max",
            f"{e_gap_max:.0f} J",
            f"{100.0 * e_gap_max / ref:.2f} % de l'apport",
            delta_color="off",
        )
        st.caption(
            "Le bilan quasi fermé ajoute un stockage explicite gaz+pneu."
            " L'écart restant correspond aux termes internes encore non modélisés"
            " (couplages locaux, approximations de puissance, discrétisation)."
        )

        st.plotly_chart(
            _line(
                t,
                [
                    ("Apport cumulé (cinétique init + gravité)", e_input),
                    ("Cinétique translation + tangage", e_kin_total),
                    ("Dissipation hydraulique", e_hyd),
                    ("Dissipation friction", e_fric),
                    ("Dissipation glissement", e_slip),
                    ("Dissipation totale", e_diss_total),
                    ("Stockage gaz", e_store_gas),
                    ("Stockage pneu net", e_store_tyre),
                    ("Stockage total", e_store_total),
                    ("Écart quasi fermé", e_gap_quasi),
                    ("Énergie non comptée (ancien)", e_residual),
                ],
                "Bilan énergétique avion complet",
                "Temps (s)",
                "Énergie (J)",
            ),
            use_container_width=True,
        )
        st.plotly_chart(
            _line(
                t,
                [
                    ("Écart quasi fermé", e_gap_quasi),
                    ("Énergie non comptée (ancien)", e_residual),
                ],
                "Comparaison des écarts de bilan",
                "Temps (s)",
                "Énergie (J)",
            ),
            use_container_width=True,
        )
    else:
        missing = [c for c in energy_required if c not in df_energy.columns]
        st.info(
            "Bilan énergétique indisponible: colonnes manquantes dans ce résultat "
            f"({', '.join(missing[:8])}{'…' if len(missing) > 8 else ''}).",
            icon="ℹ️",
        )

with tab_mlg:
    e_mlg_l = None
    e_mlg_r = None
    if aircraft_inputs is not None:
        vx_abs = abs(float(aircraft_inputs.drop.vx))
        e_mlg_l = _compute_absorbed_energy_by_train(
            df_energy,
            train="mlg_left",
            vx=vx_abs,
            wheel_radius_m=float(aircraft_inputs.mlg.unload_radius) / 1000.0,
        )
        e_mlg_r = _compute_absorbed_energy_by_train(
            df_energy,
            train="mlg_right",
            vx=vx_abs,
            wheel_radius_m=float(aircraft_inputs.mlg.unload_radius) / 1000.0,
        )

    st.markdown("### MLG gauche")
    if e_mlg_l is not None:
        st.metric("Énergie absorbée MLG gauche", f"{float(e_mlg_l['e_total'][-1]) / 1000.0:.2f} kJ")
    mlg_l_tabs = st.tabs([
        "Efforts (temps)",
        "Effort / course",
        "Pressions",
        "Conv. hydraulique",
        "Course & déflexion",
        "Accél. & vitesse",
        "Torseur B & C",
    ])

    with mlg_l_tabs[0]:
        if _require_columns([
            "MLG left.Tyre.FTyre (N)", "MLG left.Reaction H (N)", "MLG left.Ftot (N)"
        ], "MLG gauche - Efforts"):
            st.plotly_chart(_line(t, [
                ("Fz (pneu/sol)", df["MLG left.Tyre.FTyre (N)"]),
                ("Fx (horizontal)", df["MLG left.Reaction H (N)"]),
                ("Effort amortisseur", df["MLG left.Ftot (N)"]),
            ], "MLG gauche - Efforts en fonction du temps", "Temps (s)", "Effort (N)"), use_container_width=True)

    with mlg_l_tabs[1]:
        if _require_columns([
            "MLG left.d (m)", "MLG left.Tyre.FTyre (N)", "MLG left.Reaction H (N)"
        ], "MLG gauche - Effort/course"):
            st.plotly_chart(_line(df["MLG left.d (m)"] * 1000.0, [
                ("Fz (pneu/sol)", df["MLG left.Tyre.FTyre (N)"]),
                ("Fx (horizontal)", df["MLG left.Reaction H (N)"]),
            ], "MLG gauche - Effort en fonction de la course", "Course amortisseur (mm)", "Effort (N)"), use_container_width=True)

    with mlg_l_tabs[2]:
        if _require_columns([
            "MLG left.Pc (bar)", "MLG left.Pg (bar)", "MLG left.Pd (bar)", "MLG left.DeltaPc (bar)", "MLG left.DeltaPd (bar)"
        ], "MLG gauche - Pressions"):
            st.plotly_chart(_line(t, [
                ("Pc", df["MLG left.Pc (bar)"]),
                ("Pg", df["MLG left.Pg (bar)"]),
                ("Pd", df["MLG left.Pd (bar)"]),
                ("DeltaPc", df["MLG left.DeltaPc (bar)"]),
                ("DeltaPd", df["MLG left.DeltaPd (bar)"]),
            ], "MLG gauche - Pressions en fonction du temps", "Temps (s)", "Pression (bar)"), use_container_width=True)

    with mlg_l_tabs[3]:
        if _require_columns([
            "MLG left.Hyd.Erreur conv (-)", "MLG left.Hyd.Iter conv (-)", "MLG left.Hyd.Qc total (m³/s)", "MLG left.Hyd.Part fuite (-)"
        ], "MLG gauche - Convergence hydraulique"):
            st.plotly_chart(_line(t, [
                ("Erreur convergence", df["MLG left.Hyd.Erreur conv (-)"]),
                ("Itérations", df["MLG left.Hyd.Iter conv (-)"]),
                ("Qc total", df["MLG left.Hyd.Qc total (m³/s)"]),
                ("Part fuite", df["MLG left.Hyd.Part fuite (-)"]),
            ], "MLG gauche - Convergence hydraulique", "Temps (s)", "- / m³.s⁻¹"), use_container_width=True)

    with mlg_l_tabs[4]:
        if _require_columns([
            "MLG left.d (m)", "MLG left.TyreDefl (m)"
        ], "MLG gauche - Course/déflexion"):
            st.plotly_chart(_line(t, [
                ("Course amortisseur (mm)", df["MLG left.d (m)"] * 1000.0),
                ("Déflexion pneu (mm)", df["MLG left.TyreDefl (m)"] * 1000.0),
            ], "MLG gauche - Course et déflexion", "Temps (s)", "Déplacement (mm)"), use_container_width=True)

    with mlg_l_tabs[5]:
        if _require_columns([
            "MLG left.AccMs (m/s²)", "MLG left.v (m/s)"
        ], "MLG gauche - Accélération/vitesse"):
            st.plotly_chart(_line(t, [
                ("Accélération masse susp. (g)", df["MLG left.AccMs (m/s²)"] / 9.81),
                ("Vitesse amortisseur (m/s)", df["MLG left.v (m/s)"]),
            ], "MLG gauche - Accélération et vitesse", "Temps (s)", "g / m.s⁻¹"), use_container_width=True)

    with mlg_l_tabs[6]:
        _liaison_charts("MLG gauche", "MLG left", has_c=True, b_kind="pivot")

    st.markdown("### MLG droite")
    if e_mlg_r is not None:
        st.metric("Énergie absorbée MLG droite", f"{float(e_mlg_r['e_total'][-1]) / 1000.0:.2f} kJ")
    mlg_r_tabs = st.tabs([
        "Efforts (temps)",
        "Effort / course",
        "Pressions",
        "Conv. hydraulique",
        "Course & déflexion",
        "Accél. & vitesse",
        "Torseur B & C",
    ])

    with mlg_r_tabs[0]:
        if _require_columns([
            "MLG right.Tyre.FTyre (N)", "MLG right.Reaction H (N)", "MLG right.Ftot (N)"
        ], "MLG droite - Efforts"):
            st.plotly_chart(_line(t, [
                ("Fz (pneu/sol)", df["MLG right.Tyre.FTyre (N)"]),
                ("Fx (horizontal)", df["MLG right.Reaction H (N)"]),
                ("Effort amortisseur", df["MLG right.Ftot (N)"]),
            ], "MLG droite - Efforts en fonction du temps", "Temps (s)", "Effort (N)"), use_container_width=True)

    with mlg_r_tabs[1]:
        if _require_columns([
            "MLG right.d (m)", "MLG right.Tyre.FTyre (N)", "MLG right.Reaction H (N)"
        ], "MLG droite - Effort/course"):
            st.plotly_chart(_line(df["MLG right.d (m)"] * 1000.0, [
                ("Fz (pneu/sol)", df["MLG right.Tyre.FTyre (N)"]),
                ("Fx (horizontal)", df["MLG right.Reaction H (N)"]),
            ], "MLG droite - Effort en fonction de la course", "Course amortisseur (mm)", "Effort (N)"), use_container_width=True)

    with mlg_r_tabs[2]:
        if _require_columns([
            "MLG right.Pc (bar)", "MLG right.Pg (bar)", "MLG right.Pd (bar)", "MLG right.DeltaPc (bar)", "MLG right.DeltaPd (bar)"
        ], "MLG droite - Pressions"):
            st.plotly_chart(_line(t, [
                ("Pc", df["MLG right.Pc (bar)"]),
                ("Pg", df["MLG right.Pg (bar)"]),
                ("Pd", df["MLG right.Pd (bar)"]),
                ("DeltaPc", df["MLG right.DeltaPc (bar)"]),
                ("DeltaPd", df["MLG right.DeltaPd (bar)"]),
            ], "MLG droite - Pressions en fonction du temps", "Temps (s)", "Pression (bar)"), use_container_width=True)

    with mlg_r_tabs[3]:
        if _require_columns([
            "MLG right.Hyd.Erreur conv (-)", "MLG right.Hyd.Iter conv (-)", "MLG right.Hyd.Qc total (m³/s)", "MLG right.Hyd.Part fuite (-)"
        ], "MLG droite - Convergence hydraulique"):
            st.plotly_chart(_line(t, [
                ("Erreur convergence", df["MLG right.Hyd.Erreur conv (-)"]),
                ("Itérations", df["MLG right.Hyd.Iter conv (-)"]),
                ("Qc total", df["MLG right.Hyd.Qc total (m³/s)"]),
                ("Part fuite", df["MLG right.Hyd.Part fuite (-)"]),
            ], "MLG droite - Convergence hydraulique", "Temps (s)", "- / m³.s⁻¹"), use_container_width=True)

    with mlg_r_tabs[4]:
        if _require_columns([
            "MLG right.d (m)", "MLG right.TyreDefl (m)"
        ], "MLG droite - Course/déflexion"):
            st.plotly_chart(_line(t, [
                ("Course amortisseur (mm)", df["MLG right.d (m)"] * 1000.0),
                ("Déflexion pneu (mm)", df["MLG right.TyreDefl (m)"] * 1000.0),
            ], "MLG droite - Course et déflexion", "Temps (s)", "Déplacement (mm)"), use_container_width=True)

    with mlg_r_tabs[5]:
        if _require_columns([
            "MLG right.AccMs (m/s²)", "MLG right.v (m/s)"
        ], "MLG droite - Accélération/vitesse"):
            st.plotly_chart(_line(t, [
                ("Accélération masse susp. (g)", df["MLG right.AccMs (m/s²)"] / 9.81),
                ("Vitesse amortisseur (m/s)", df["MLG right.v (m/s)"]),
            ], "MLG droite - Accélération et vitesse", "Temps (s)", "g / m.s⁻¹"), use_container_width=True)

    with mlg_r_tabs[6]:
        _liaison_charts("MLG droite", "MLG right", has_c=True, b_kind="pivot")

with tab_nlg:
    e_nlg = None
    if aircraft_inputs is not None:
        e_nlg = _compute_absorbed_energy_by_train(
            df_energy,
            train="nlg",
            vx=abs(float(aircraft_inputs.drop.vx)),
            wheel_radius_m=float(aircraft_inputs.nlg.unload_radius) / 1000.0,
        )
    if e_nlg is not None:
        st.metric("Énergie absorbée NLG", f"{float(e_nlg['e_total'][-1]) / 1000.0:.2f} kJ")
    nlg_tabs = st.tabs([
        "Efforts (temps)",
        "Effort / course",
        "Pressions",
        "Conv. hydraulique",
        "Course & déflexion",
        "Accél. & vitesse",
        "Torseur B",
    ])

    with nlg_tabs[0]:
        if _require_columns([
            "NLG.Tyre.FTyre (N)", "NLG.Reaction H (N)", "NLG.Ftot (N)"
        ], "NLG - Efforts"):
            st.plotly_chart(_line(t, [
                ("Fz (pneu/sol)", df["NLG.Tyre.FTyre (N)"]),
                ("Fx (horizontal)", df["NLG.Reaction H (N)"]),
                ("Effort amortisseur", df["NLG.Ftot (N)"]),
            ], "NLG - Efforts en fonction du temps", "Temps (s)", "Effort (N)"), use_container_width=True)

    with nlg_tabs[1]:
        if _require_columns([
            "NLG.d (m)", "NLG.Tyre.FTyre (N)", "NLG.Reaction H (N)"
        ], "NLG - Effort/course"):
            st.plotly_chart(_line(df["NLG.d (m)"] * 1000.0, [
                ("Fz (pneu/sol)", df["NLG.Tyre.FTyre (N)"]),
                ("Fx (horizontal)", df["NLG.Reaction H (N)"]),
            ], "NLG - Effort en fonction de la course", "Course amortisseur (mm)", "Effort (N)"), use_container_width=True)

    with nlg_tabs[2]:
        if _require_columns([
            "NLG.Pc (bar)", "NLG.Pg (bar)", "NLG.Pd (bar)", "NLG.DeltaPc (bar)", "NLG.DeltaPd (bar)"
        ], "NLG - Pressions"):
            st.plotly_chart(_line(t, [
                ("Pc", df["NLG.Pc (bar)"]),
                ("Pg", df["NLG.Pg (bar)"]),
                ("Pd", df["NLG.Pd (bar)"]),
                ("DeltaPc", df["NLG.DeltaPc (bar)"]),
                ("DeltaPd", df["NLG.DeltaPd (bar)"]),
            ], "NLG - Pressions en fonction du temps", "Temps (s)", "Pression (bar)"), use_container_width=True)

    with nlg_tabs[3]:
        if _require_columns([
            "NLG.Hyd.Erreur conv (-)", "NLG.Hyd.Iter conv (-)", "NLG.Hyd.Qc total (m³/s)", "NLG.Hyd.Part fuite (-)"
        ], "NLG - Convergence hydraulique"):
            st.plotly_chart(_line(t, [
                ("Erreur convergence", df["NLG.Hyd.Erreur conv (-)"]),
                ("Itérations", df["NLG.Hyd.Iter conv (-)"]),
                ("Qc total", df["NLG.Hyd.Qc total (m³/s)"]),
                ("Part fuite", df["NLG.Hyd.Part fuite (-)"]),
            ], "NLG - Convergence hydraulique", "Temps (s)", "- / m³.s⁻¹"), use_container_width=True)

    with nlg_tabs[4]:
        if _require_columns([
            "NLG.d (m)", "NLG.TyreDefl (m)"
        ], "NLG - Course/déflexion"):
            st.plotly_chart(_line(t, [
                ("Course amortisseur (mm)", df["NLG.d (m)"] * 1000.0),
                ("Déflexion pneu (mm)", df["NLG.TyreDefl (m)"] * 1000.0),
            ], "NLG - Course et déflexion", "Temps (s)", "Déplacement (mm)"), use_container_width=True)

    with nlg_tabs[5]:
        if _require_columns([
            "NLG.AccMs (m/s²)", "NLG.v (m/s)"
        ], "NLG - Accélération/vitesse"):
            st.plotly_chart(_line(t, [
                ("Accélération masse susp. (g)", df["NLG.AccMs (m/s²)"] / 9.81),
                ("Vitesse amortisseur (m/s)", df["NLG.v (m/s)"]),
            ], "NLG - Accélération et vitesse", "Temps (s)", "g / m.s⁻¹"), use_container_width=True)

    with nlg_tabs[6]:
        _liaison_charts("NLG", "NLG", has_c=False, b_kind="encastrement")

csv = df.to_csv(index=False).encode("utf-8")
st.download_button(
    "Exporter CSV avion complet",
    data=csv,
    file_name="aircraft_results.csv",
    mime="text/csv",
    use_container_width=True,
)
