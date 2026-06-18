"""Page Loi hydraulique : tableau course x vitesse de l'effort total amortisseur.

Abscisse : vitesse de -1.00 a +3.00 m/s par pas de 0.25 m/s.
Ordonnee : course amortisseur de 0 a course max, par pas de 1 mm.
Cellule : effort total amortisseur Ftot (N).
"""
from __future__ import annotations

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

from dropsim import default_mlg_inputs  # noqa: E402
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
    st.session_state.inputs = default_mlg_inputs()

inputs = st.session_state.inputs


try:
    inputs.validate().raise_if_any()
    p = inputs.to_si()
    tab_pos, tab_sec = build_section_table(p)

    course_mm_max = int(round(inputs.course))
    course_mm = np.arange(0, course_mm_max + 1, 1, dtype=float)
    d_values = course_mm / 1000.0

    v_values = np.arange(-1.0, 3.0001, 0.25)
    col_labels = [f"{v:+.2f} m/s" for v in v_values]

    matrix = np.full((len(d_values), len(v_values)), np.nan, dtype=float)

    # Meme loi que le moteur : calcul stateful avec memoire gaz/hydraulique.
    for j, v in enumerate(v_values):
        gas = GasSpring(p)
        pg_prev = p.Pinitbp
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
                    p,
                    gas,
                    tab_pos,
                    tab_sec,
                    d,
                    float(v),
                    delta_pc,
                    delta_pd,
                    pg_prev,
                )
                matrix[i, j] = damp["ftot"]
                delta_pc = damp["delta_pc"]
                delta_pd = damp["delta_pd"]
                pg_prev = damp["pg"]
            except SimError:
                matrix[i, j] = np.nan

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

    fig = go.Figure()
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
                name=label,
            )
        )

    if len(fig.data) == 0:
        st.info("Selectionne au moins une vitesse avec des points calculables.")

    title_suffix = ", ".join(selected_labels) if selected_labels else "aucune vitesse"
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

    st.caption("Modele identique au moteur de simulation (gaz + hydraulique + friction + butees).")
    n_nan = int(np.isnan(matrix).sum())
    if n_nan:
        st.warning(
            f"{n_nan} points n'ont pas pu etre evalues numeriquement et sont affiches vides (NaN)."
        )
except SimError as err:
    st.error(f"Impossible de calculer la loi hydraulique : {err.message}")
    if err.hint:
        st.caption(f"Conseil : {err.hint}")
except Exception as err:  # pragma: no cover - garde-fou UI
    st.error(f"Erreur inattendue pendant le calcul de la loi hydraulique : {err}")
