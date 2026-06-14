"""Page **Résultats** : courbes et synthèse de la simulation.

Affiche les grandeurs caractéristiques (efforts, course, pressions, accélération…)
sous forme de courbes interactives Plotly, ainsi qu'un tableau de synthèse et un
export CSV des séries temporelles.
"""
from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dropsim.engine import OUTPUT_COLUMNS  # noqa: E402

st.set_page_config(page_title="Résultats — SimuLanding", page_icon="📈", layout="wide")

st.title("📈 Résultats de la simulation")

result = st.session_state.get("result")
if result is None:
    st.info(
        "Aucun résultat disponible. Renseignez les données dans la page **Saisie** "
        "puis lancez le calcul.",
        icon="ℹ️",
    )
    st.stop()

df = result.df
COL = OUTPUT_COLUMNS  # clé interne -> libellé de colonne

# Colonne « course » exprimée en mm pour l'affichage.
course_mm = df[COL["mlg_d"]] * 1000.0


# --------------------------------------------------------------------------- #
#  Synthèse
# --------------------------------------------------------------------------- #
st.subheader("Synthèse")
s = result.summary
m = st.columns(4)
m[0].metric("Course max", f"{s['Course max (mm)']:.2f} mm")
m[1].metric("Effort vertical max Fz", f"{s['Effort vertical max Fz (N)']:.0f} N")
m[2].metric("Effort horizontal max Fx", f"{s['Effort horizontal max Fx (N)']:.0f} N")
m[3].metric("Effort amortisseur max", f"{s['Effort amortisseur max (N)']:.0f} N")
m = st.columns(4)
m[0].metric("Pression gaz max", f"{s['Pression gaz max (bar)']:.1f} bar")
m[1].metric("Pression compression max", f"{s['Pression compression max (bar)']:.1f} bar")
m[2].metric("Accélération max", f"{s['Accélération max (g)']:.2f} g")
m[3].metric("Nombre de pas", f"{s['Nombre de pas']:,}".replace(",", " "))


def line(x, ys: list[tuple[str, "object"]], title: str, xlab: str, ylab: str):
    """Construit un graphe linéaire Plotly multi-séries."""
    fig = go.Figure()
    for name, y in ys:
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=name))
    fig.update_layout(
        title=title,
        xaxis_title=xlab,
        yaxis_title=ylab,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        height=380,
    )
    return fig


t = df[COL["temps"]]

# --------------------------------------------------------------------------- #
#  Courbes
# --------------------------------------------------------------------------- #
tab1, tab2, tab3 = st.tabs(["Efforts", "Pressions", "Cinématique"])

with tab1:
    c = st.columns(2)
    c[0].plotly_chart(
        line(
            t,
            [
                ("Fz (pneu/sol)", df[COL["tyre_ftyre"]]),
                ("Fx (horizontal)", df[COL["tr_x"]]),
                ("Effort amortisseur", df[COL["mlg_ftot"]]),
            ],
            "Efforts en fonction du temps",
            "Temps (s)",
            "Effort (N)",
        ),
        use_container_width=True,
    )
    c[1].plotly_chart(
        line(
            course_mm,
            [("Fz (pneu/sol)", df[COL["tyre_ftyre"]])],
            "Effort vertical en fonction de la course",
            "Course amortisseur (mm)",
            "Fz (N)",
        ),
        use_container_width=True,
    )

with tab2:
    st.plotly_chart(
        line(
            t,
            [
                ("Pc (compression)", df[COL["pc"]]),
                ("Pg (gaz)", df[COL["pg"]]),
                ("Pd (détente)", df[COL["pd"]]),
            ],
            "Pressions en fonction du temps",
            "Temps (s)",
            "Pression (bar)",
        ),
        use_container_width=True,
    )

with tab3:
    c = st.columns(2)
    c[0].plotly_chart(
        line(
            t,
            [
                ("Course amortisseur (mm)", course_mm),
                ("Déflexion pneu (mm)", df[COL["tyre_defl"]] * 1000.0),
            ],
            "Course et déflexion en fonction du temps",
            "Temps (s)",
            "Déplacement (mm)",
        ),
        use_container_width=True,
    )
    c[1].plotly_chart(
        line(
            t,
            [
                ("Accélération masse susp. (g)", df[COL["accms"]] / 9.81),
                ("Vitesse amortisseur (m/s)", df[COL["mlg_v"]]),
            ],
            "Accélération et vitesse en fonction du temps",
            "Temps (s)",
            "g  /  m·s⁻¹",
        ),
        use_container_width=True,
    )

# --------------------------------------------------------------------------- #
#  Données et export
# --------------------------------------------------------------------------- #
st.divider()
with st.expander("Séries temporelles (tableau)"):
    st.dataframe(df, use_container_width=True, height=320)

st.download_button(
    "⬇️ Exporter les résultats (CSV)",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="resultats_mlg.csv",
    mime="text/csv",
)
