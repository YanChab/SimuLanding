"""Page **Comparaison** : compare deux simulations enregistrées (ou la courante).

Permet de sélectionner deux simulations (A et B) parmi les sauvegardes — ou la
simulation courante en mémoire — et d'afficher :

* un tableau comparatif des grandeurs de synthèse (valeurs A, B, écart Δ et Δ %) ;
* des courbes superposées d'une grandeur au choix en fonction d'une abscisse.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_APP = Path(__file__).resolve().parent.parent
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

from dropsim import list_saved, load_simulation  # noqa: E402
from theme import apply_theme  # noqa: E402

apply_theme()

st.title("⚖️ Comparaison de deux simulations")

GRAPH_HEIGHT = 560

# --------------------------------------------------------------------------- #
#  Sources disponibles : simulation courante + sauvegardes
# --------------------------------------------------------------------------- #
sources: dict[str, dict] = {}

current = st.session_state.get("result")
if current is not None:
    cur_name = st.session_state.get("result_name", "Simulation courante")
    sources[f"🟢 {cur_name} (en mémoire)"] = {"kind": "current"}

for e in list_saved():
    label = f"{e['name']}  ·  {e['saved_at'][:16].replace('T', ' ')}"
    sources[label] = {"kind": "file", "path": e["path"]}

if len(sources) < 2:
    st.info(
        "Il faut au moins **deux** simulations disponibles pour comparer. "
        "Lancez un calcul puis sauvegardez-le (page **Résultats**), ou enregistrez "
        "plusieurs simulations.",
        icon="ℹ️",
    )
    st.stop()


def _load(source: dict):
    """Renvoie (inputs|None, result) pour une source (courante ou fichier)."""
    if source["kind"] == "current":
        return None, st.session_state.get("result")
    inputs, result, _meta = load_simulation(source["path"])
    return inputs, result


labels = list(sources.keys())
col_a, col_b = st.columns(2)
with col_a:
    sel_a = st.selectbox("Simulation A", labels, index=0, key="cmp_a")
with col_b:
    default_b = 1 if len(labels) > 1 else 0
    sel_b = st.selectbox("Simulation B", labels, index=default_b, key="cmp_b")

_, res_a = _load(sources[sel_a])
_, res_b = _load(sources[sel_b])

name_a = sel_a.lstrip("🟢 ").split("  ·  ")[0]
name_b = sel_b.lstrip("🟢 ").split("  ·  ")[0]
if name_a == name_b:
    name_a, name_b = f"{name_a} (A)", f"{name_b} (B)"

# --------------------------------------------------------------------------- #
#  Tableau comparatif des grandeurs de synthèse
# --------------------------------------------------------------------------- #
st.subheader("Synthèse comparée")

rows_a = {lbl: (val, unit) for lbl, val, unit in getattr(res_a, "summary_rows", [])}
rows_b = {lbl: (val, unit) for lbl, val, unit in getattr(res_b, "summary_rows", [])}

if rows_a and rows_b:
    records = []
    for lbl in rows_a:
        if lbl not in rows_b:
            continue
        va, unit = rows_a[lbl]
        vb, _ = rows_b[lbl]
        delta = vb - va
        pct = (delta / va * 100.0) if va else float("nan")
        param = f"{lbl} ({unit})" if unit and unit != "-" else lbl
        records.append(
            {"Paramètre": param, name_a: va, name_b: vb, "Δ (B−A)": delta, "Δ %": pct}
        )
    cmp_df = pd.DataFrame(records)
    st.dataframe(
        cmp_df,
        column_config={
            "Paramètre": st.column_config.TextColumn("Paramètre"),
            name_a: st.column_config.NumberColumn(name_a, format="%.4g"),
            name_b: st.column_config.NumberColumn(name_b, format="%.4g"),
            "Δ (B−A)": st.column_config.NumberColumn("Δ (B−A)", format="%.4g"),
            "Δ %": st.column_config.NumberColumn("Δ %", format="%.2f"),
        },
        hide_index=True,
        width="stretch",
        height=38 + 35 * len(records),
    )
else:
    st.caption("Synthèse indisponible pour l'une des simulations.")

# --------------------------------------------------------------------------- #
#  Courbes superposées
# --------------------------------------------------------------------------- #
st.subheader("Courbes superposées")

common_cols = [c for c in res_a.df.columns if c in res_b.df.columns]
if not common_cols:
    st.caption("Aucune grandeur commune à comparer.")
    st.stop()

col_x, col_y = st.columns(2)
with col_x:
    x_col = st.selectbox(
        "Abscisse (X)",
        common_cols,
        index=common_cols.index("Temps (s)") if "Temps (s)" in common_cols else 0,
        key="cmp_x",
    )
with col_y:
    y_default = "Tyre.FTyre (N)" if "Tyre.FTyre (N)" in common_cols else common_cols[min(1, len(common_cols) - 1)]
    y_col = st.selectbox(
        "Ordonnée (Y)", common_cols, index=common_cols.index(y_default), key="cmp_y"
    )

fig = go.Figure()
fig.add_trace(go.Scatter(x=res_a.df[x_col], y=res_a.df[y_col], mode="lines", name=name_a))
fig.add_trace(go.Scatter(x=res_b.df[x_col], y=res_b.df[y_col], mode="lines", name=name_b))
fig.update_layout(
    title=dict(text=f"{y_col} en fonction de {x_col}", y=0.98, yanchor="top"),
    margin=dict(l=10, r=10, t=80, b=55),
    legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0),
    height=GRAPH_HEIGHT,
    xaxis_title=x_col,
    yaxis_title=y_col,
)
st.plotly_chart(fig, use_container_width=True, config={"responsive": True})
