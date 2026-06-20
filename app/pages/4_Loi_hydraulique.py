"""Page Loi hydraulique : tableau course x vitesse de l'effort total amortisseur.

Abscisse : vitesse de -1.00 a +3.00 m/s par pas de 0.25 m/s.
Ordonnee : course amortisseur de 0 a course max, par pas de 1 mm.
Cellule : effort total amortisseur Ftot (N).
"""
from __future__ import annotations

from dataclasses import replace
import importlib
import math
import sys
from pathlib import Path

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

from dropsim import default_trailing_arm_inputs  # noqa: E402
from dropsim.errors import SimError  # noqa: E402
from dropsim.gas import GasSpring  # noqa: E402
from dropsim.metering import build_section_table  # noqa: E402
from theme import apply_theme  # noqa: E402

import dropsim.engine as _engine_mod  # noqa: E402

_engine_mod = importlib.reload(_engine_mod)
damper_force_step = _engine_mod.damper_force_step

apply_theme()

st.title("🧮 Loi hydraulique")
st.caption(
    "Tableau de l'effort total amortisseur en fonction de la vitesse et de la course "
    "(calcul base sur les parametres saisis)."
)

if "inputs" not in st.session_state:
    st.session_state.inputs = default_trailing_arm_inputs()

inputs = st.session_state.inputs


def _compute_matrix_for_params(p_case, d_values: np.ndarray, v_values: np.ndarray) -> np.ndarray:
    """Calcule la matrice effort/course/vitesse pour un jeu de paramètres SI."""
    tab_pos, tab_sec = build_section_table(p_case)
    matrix_case = np.full((len(d_values), len(v_values)), np.nan, dtype=float)

    # Meme loi que le moteur : calcul stateful avec memoire gaz/hydraulique.
    for j, v in enumerate(v_values):
        gas = GasSpring(p_case)
        pg_prev = p_case.Pinitbp
        delta_pc = 0.0
        delta_pd = 0.0

        if v < 0.0:
            # Branche detente : on initialise l'etat gaz en fin de compression.
            for d_init in d_values:
                try:
                    pg_prev = gas.pressure(float(d_init), float(pg_prev))
                except SimError:
                    break
            indices = range(len(d_values) - 1, -1, -1)
        else:
            indices = range(len(d_values))

        for i in indices:
            d = float(d_values[i])
            try:
                damp = damper_force_step(
                    p_case,
                    gas,
                    tab_pos,
                    tab_sec,
                    d,
                    float(v),
                    delta_pc,
                    delta_pd,
                    pg_prev,
                )
                matrix_case[i, j] = damp["ftot"]
                delta_pc = damp["delta_pc"]
                delta_pd = damp["delta_pd"]
                pg_prev = damp["pg"]
            except SimError:
                matrix_case[i, j] = np.nan

    return matrix_case


def _build_tolerance_cases(p_nominal):
    """Construit les 3 cas (nominal / tol mini / tol maxi) en fonction des tolérances UI."""
    st.subheader("Tolérances de fabrication")
    c1, c2, c3 = st.columns(3)
    tol_palier_mm = c1.number_input(
        "Tol. Ø intérieur palier BH (± mm)",
        min_value=0.0,
        value=0.0,
        step=0.01,
        format="%.3f",
        key="hydrau_tol_dinsidepalier_mm",
    )
    tol_dbh_mm = c2.number_input(
        "Tol. Ø extérieur BH (± mm)",
        min_value=0.0,
        value=0.0,
        step=0.01,
        format="%.3f",
        key="hydrau_tol_dbh_mm",
    )
    tol_rainure_mm = c3.number_input(
        "Tol. profondeur rainures (± mm)",
        min_value=0.0,
        value=0.0,
        step=0.01,
        format="%.3f",
        key="hydrau_tol_rainure_mm",
    )

    tol_palier_m = float(tol_palier_mm) / 1000.0
    tol_dbh_m = float(tol_dbh_mm) / 1000.0
    tol_rainure = float(tol_rainure_mm)

    cases = {
        "Nominal": p_nominal,
        # Cas mini demandé : Dpalier max, DBH min, rainures min
        "Tolérance mini": replace(
            p_nominal,
            DInsidePalierBh=p_nominal.DInsidePalierBh + tol_palier_m,
            Dbh=p_nominal.Dbh - tol_dbh_m,
            rainures_profondeur=np.maximum(p_nominal.rainures_profondeur - tol_rainure, 0.0),
        ),
        # Cas maxi demandé : Dpalier min, DBH max, rainures max
        "Tolérance maxi": replace(
            p_nominal,
            DInsidePalierBh=p_nominal.DInsidePalierBh - tol_palier_m,
            Dbh=p_nominal.Dbh + tol_dbh_m,
            rainures_profondeur=p_nominal.rainures_profondeur + tol_rainure,
        ),
    }
    return cases


def _case_is_valid(case_p) -> tuple[bool, str]:
    """Vérifications minimales des paramètres géométriques d'un cas de tolérance."""
    if case_p.Dbh <= 0.0:
        return False, "Dbh devient nul ou négatif."
    if case_p.DInsidePalierBh <= 0.0:
        return False, "DInsidePalierBh devient nul ou négatif."
    if np.any(case_p.rainures_profondeur < 0.0):
        return False, "Une profondeur de rainure devient négative."
    return True, ""


try:
    inputs.validate().raise_if_any()
    p = inputs.to_si()

    course_mm_max = int(round(inputs.course))
    course_mm = np.arange(0, course_mm_max + 1, 1, dtype=float)
    d_values = course_mm / 1000.0

    v_values = np.arange(-1.0, 3.0001, 0.25)
    col_labels = [f"{v:+.2f} m/s" for v in v_values]

    cases = _build_tolerance_cases(p)
    case_matrices: dict[str, np.ndarray] = {}

    for case_name, case_p in cases.items():
        valid, reason = _case_is_valid(case_p)
        if not valid:
            st.warning(f"{case_name} ignoré : {reason}")
            case_matrices[case_name] = np.full((len(d_values), len(v_values)), np.nan, dtype=float)
            continue
        case_matrices[case_name] = _compute_matrix_for_params(case_p, d_values, v_values)

    st.subheader("Courbe effort/course")
    speed_labels = [f"{v:+.2f} m/s" for v in v_values]
    default_label = "+0.00 m/s" if "+0.00 m/s" in speed_labels else speed_labels[0]
    selected_labels = st.multiselect(
        "Vitesses a afficher (max 6)",
        speed_labels,
        default=[default_label],
        max_selections=6,
        key="hydrau_curve_speeds",
    )

    case_labels = list(case_matrices.keys())
    selected_cases = st.multiselect(
        "Cas a afficher",
        case_labels,
        default=["Nominal"],
        key="hydrau_curve_cases",
    )

    fig = go.Figure()
    for case_name in selected_cases:
        matrix = case_matrices[case_name]
        for label in selected_labels:
            sel_idx = speed_labels.index(label)
            y = matrix[:, sel_idx]
            valid = np.isfinite(y)
            if not np.any(valid):
                continue
            fig.add_trace(
                go.Scatter(
                    x=course_mm[valid],
                    y=y[valid],
                    mode="lines",
                    line=dict(width=2),
                    name=f"{case_name} | {label}",
                )
            )

    if len(fig.data) == 0:
        st.info("Selectionne au moins une vitesse et un cas avec des points calculables.")

    title_parts = []
    if selected_cases:
        title_parts.append(" / ".join(selected_cases))
    if selected_labels:
        title_parts.append(", ".join(selected_labels))
    title_suffix = " | ".join(title_parts) if title_parts else "aucune selection"
    fig.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=70, b=90),
        xaxis_title="Course amortisseur (mm)",
        yaxis_title="Effort total amortisseur (N)",
        title=dict(text=f"Ftot en fonction de la course ({title_suffix})", y=0.98, yanchor="top"),
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="left", x=0),
    )
    st.plotly_chart(fig, width="stretch", config={"responsive": True})

    st.subheader("Tableau effort/course/vitesse")

    tabs = st.tabs(list(case_matrices.keys()))
    for tab, case_name in zip(tabs, case_matrices.keys()):
        with tab:
            matrix = case_matrices[case_name]
            df = pd.DataFrame(matrix, columns=col_labels)
            df.insert(0, "Course (mm)", course_mm.astype(int))
            st.dataframe(
                df,
                hide_index=True,
                width="stretch",
                height=700,
                column_config={
                    "Course (mm)": st.column_config.NumberColumn("Course (mm)", format="%d"),
                    **{c: st.column_config.NumberColumn(c, format="%.0f") for c in col_labels},
                },
            )

    c_nom, c_min, c_max = st.columns(3)
    c_nom.caption(
        f"Nominal: Dpalier={p.DInsidePalierBh*1000:.3f} mm, "
        f"DBH={p.Dbh*1000:.3f} mm"
    )
    p_min = cases["Tolérance mini"]
    p_max = cases["Tolérance maxi"]
    c_min.caption(
        f"Tol mini: Dpalier={p_min.DInsidePalierBh*1000:.3f} mm, "
        f"DBH={p_min.Dbh*1000:.3f} mm"
    )
    c_max.caption(
        f"Tol maxi: Dpalier={p_max.DInsidePalierBh*1000:.3f} mm, "
        f"DBH={p_max.Dbh*1000:.3f} mm"
    )

    st.caption("Modele identique au moteur de simulation (gaz + hydraulique + friction + butees).")
    for case_name, matrix in case_matrices.items():
        n_nan = int(np.isnan(matrix).sum())
        if n_nan:
            st.warning(
                f"{case_name}: {n_nan} points n'ont pas pu etre evalues numeriquement et sont affiches vides (NaN)."
            )
except SimError as err:
    st.error(f"Impossible de calculer la loi hydraulique : {err.message}")
    if err.hint:
        st.caption(f"Conseil : {err.hint}")
except Exception as err:  # pragma: no cover - garde-fou UI
    st.error(f"Erreur inattendue pendant le calcul de la loi hydraulique : {err}")
