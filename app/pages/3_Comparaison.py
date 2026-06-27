"""Page **Comparaison** : compare deux simulations **avion complet**.

Permet de sélectionner deux simulations avion complet (A et B) — la simulation
courante en mémoire et/ou des sauvegardes — et d'afficher :

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

st.title("⚖️ Comparaison de simulations avion complet")

GRAPH_HEIGHT = 560

# --------------------------------------------------------------------------- #
#  Sources : simulation avion en mémoire + sauvegardes avion complet
# --------------------------------------------------------------------------- #
sources: dict[str, dict] = {}

current = st.session_state.get("aircraft_result")
if current is not None:
    cur_name = st.session_state.get("aircraft_result_name", "Simulation avion complet")
    sources[f"🟢 {cur_name} (en mémoire)"] = {"kind": "current"}

for e in list_saved():
    if e.get("model_kind") != "aircraft":
        continue
    label = f"[{e.get('project', '—')}] {e['name']}  ·  {e['saved_at'][:16].replace('T', ' ')}"
    sources[label] = {"kind": "file", "path": e["path"]}

if len(sources) < 2:
    st.info(
        "Il faut au moins **deux** simulations avion complet disponibles pour comparer. "
        "Lancez des simulations depuis la page **Avion complet** et sauvegardez-les "
        "(bloc « Sauvegarder / charger »).",
        icon="ℹ️",
    )
    st.stop()


def _load(source: dict):
    """Renvoie le résultat (avion complet) d'une source (courante ou fichier)."""
    if source["kind"] == "current":
        return st.session_state.get("aircraft_result")
    _inputs, result, _meta = load_simulation(source["path"])
    return result


labels = list(sources.keys())
col_a, col_b = st.columns(2)
with col_a:
    sel_a = st.selectbox("Simulation A", labels, index=0, key="cmp_a")
with col_b:
    default_b = 1 if len(labels) > 1 else 0
    sel_b = st.selectbox("Simulation B", labels, index=default_b, key="cmp_b")

res_a = _load(sources[sel_a])
res_b = _load(sources[sel_b])


def _short_name(label: str) -> str:
    """Extrait le nom de simulation d'un libellé de source."""
    s = label.lstrip("🟢 ").split("  ·  ")[0]
    if s.startswith("[") and "] " in s:  # retire le préfixe « [projet] »
        s = s.split("] ", 1)[1]
    return s


name_a = _short_name(sel_a)
name_b = _short_name(sel_b)
if name_a == name_b:
    name_a, name_b = f"{name_a} (A)", f"{name_b} (B)"

# --------------------------------------------------------------------------- #
#  Tableau comparatif des grandeurs de synthèse (depuis le résumé avion)
# --------------------------------------------------------------------------- #
st.subheader("Synthèse comparée")

sum_a = dict(getattr(res_a, "summary", {}) or {})
sum_b = dict(getattr(res_b, "summary", {}) or {})

records = []
for lbl in sum_a:
    if lbl not in sum_b:
        continue
    try:
        va = float(sum_a[lbl])
        vb = float(sum_b[lbl])
    except (TypeError, ValueError):
        continue
    delta = vb - va
    pct = (delta / va * 100.0) if va else float("nan")
    records.append({"Paramètre": lbl, name_a: va, name_b: vb, "Δ (B−A)": delta, "Δ %": pct})

if records:
    cmp_df = pd.DataFrame(records)
    st.dataframe(
        cmp_df,
        column_config={
            "Paramètre": st.column_config.TextColumn("Paramètre"),
            name_a: st.column_config.NumberColumn(name_a, format="%.12g"),
            name_b: st.column_config.NumberColumn(name_b, format="%.12g"),
            "Δ (B−A)": st.column_config.NumberColumn("Δ (B−A)", format="%.12g"),
            "Δ %": st.column_config.NumberColumn("Δ %", format="%.12g"),
        },
        hide_index=True,
        width="stretch",
        height=38 + 35 * len(records),
    )
else:
    st.caption("Synthèse comparable indisponible pour ces deux simulations.")

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
    _y_default = "Aircraft.Fz total (N)" if "Aircraft.Fz total (N)" in common_cols else common_cols[min(1, len(common_cols) - 1)]
    y_col = st.selectbox(
        "Ordonnée (Y)", common_cols, index=common_cols.index(_y_default), key="cmp_y"
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
st.plotly_chart(fig, width="stretch", config={"responsive": True})
