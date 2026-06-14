"""Page **Résultats** : courbes et synthèse de la simulation.

Affiche les grandeurs caractéristiques (efforts, course, pressions, accélération…)
sous forme de courbes interactives Plotly, ainsi qu'un tableau de synthèse et un
export CSV des séries temporelles.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dropsim.engine import OUTPUT_COLUMNS  # noqa: E402

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


# Style « papier millimétré » : fond crème, quadrillage principal + sous-quadrillage fin.
GRAPH_PAPER_BG = "#fbfbf2"
GRID_MAJOR = "#e08e7b"   # rouge-orangé estompé (lignes principales)
GRID_MINOR = "#f3c9bf"   # rose pâle (sous-graduations)


def _grid_axis(title: str) -> dict:
    """Configuration d'axe imitant le papier millimétré (quadrillage + sous-quadrillage)."""
    return dict(
        title=title,
        showgrid=True,
        gridcolor=GRID_MAJOR,
        gridwidth=1,
        griddash="solid",
        zeroline=True,
        zerolinecolor=GRID_MAJOR,
        zerolinewidth=1.4,
        showline=True,
        linecolor=GRID_MAJOR,
        mirror=True,
        ticks="outside",
        minor=dict(
            showgrid=True,
            gridcolor=GRID_MINOR,
            gridwidth=0.5,
            ticks="outside",
        ),
    )


def _apply_graph_paper(fig: go.Figure, xlab: str, ylab: str, *, equal: bool = False) -> None:
    """Applique le fond et le quadrillage millimétré à une figure Plotly."""
    yaxis = _grid_axis(ylab)
    if equal:
        yaxis.update(scaleanchor="x", scaleratio=1.0)
    fig.update_layout(
        plot_bgcolor=GRAPH_PAPER_BG,
        paper_bgcolor="white",
        xaxis=_grid_axis(xlab),
        yaxis=yaxis,
    )


def line(x, ys: list[tuple[str, "object"]], title: str, xlab: str, ylab: str):
    """Construit un graphe linéaire Plotly multi-séries, style papier millimétré."""
    fig = go.Figure()
    for name, y in ys:
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=name))
    fig.update_layout(
        title=title,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        height=380,
    )
    _apply_graph_paper(fig, xlab, ylab)
    return fig


t = df[COL["temps"]]

# --------------------------------------------------------------------------- #
#  Courbes
# --------------------------------------------------------------------------- #
tab1, tab2, tab3, tab4 = st.tabs(["Efforts", "Pressions", "Cinématique", "Animation"])

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

with tab4:
    geom = getattr(st.session_state.result, "geometry", None)
    if geom is None or geom.empty:
        st.info(
            "Aucune donnée géométrique disponible. Relancez le calcul depuis la "
            "page **Saisie** pour générer l'animation.",
            icon="ℹ️",
        )
    else:
        st.caption(
            "Vue de côté (plan X-Z, en mm) du train à balancier pendant la chute. "
            "Utilisez ▶ pour lancer l'animation ou le curseur pour parcourir le temps."
        )

        # Positions en mm (le moteur les stocke en m).
        gx = {k: geom[k].to_numpy() * 1000.0 for k in
              ("ax", "az", "bx", "bz", "cx", "cz", "rx", "rz", "ground_z", "wheel_radius")}
        gt = geom["temps"].to_numpy()
        n = len(gt)

        # Le rayon dessiné du pneu ne peut pas dépasser le rayon libre (sinon
        # aspect non physique au rebond, quand la roue décolle du sol).
        free_radius = float(st.session_state.inputs.unload_radius)  # mm
        gx["wheel_radius"] = np.minimum(gx["wheel_radius"], free_radius)

        # Limiter à ~70 images pour une animation fluide.
        stride = max(1, n // 70)
        idx = list(range(0, n, stride))
        if idx[-1] != n - 1:
            idx.append(n - 1)

        theta = np.linspace(0.0, 2.0 * np.pi, 48)

        def frame_traces(i: int) -> list[go.Scatter]:
            ax, az = gx["ax"][i], gx["az"][i]
            bx, bz = gx["bx"][i], gx["bz"][i]
            cx, cz = gx["cx"][i], gx["cz"][i]
            rx, rz = gx["rx"][i], gx["rz"][i]
            rad = gx["wheel_radius"][i]
            # Amortisseur (C-A), bras de balancier (B-A et B-R), bâti avion (C-B).
            shock = go.Scatter(x=[cx, ax], y=[cz, az], mode="lines",
                               line=dict(color="#1f77b4", width=6), name="Amortisseur")
            arm = go.Scatter(x=[ax, bx, rx], y=[az, bz, rz], mode="lines",
                             line=dict(color="#2c3e50", width=4), name="Balancier")
            frame_air = go.Scatter(x=[cx, bx], y=[cz, bz], mode="lines",
                                   line=dict(color="#95a5a6", width=3, dash="dot"),
                                   name="Bâti avion")
            wheel = go.Scatter(x=rx + rad * np.sin(theta), y=rz + rad * np.cos(theta),
                               mode="lines", line=dict(color="#34495e", width=3),
                               fill="toself", fillcolor="rgba(52,73,94,0.12)", name="Pneu")
            pts = go.Scatter(
                x=[bx, ax, cx, rx], y=[bz, az, cz, rz], mode="markers+text",
                text=["B", "A", "C", "R"], textposition="top center",
                marker=dict(size=9, color="#e74c3c"), name="Points",
            )
            return [frame_air, shock, arm, wheel, pts]

        # Sol et bornes fixes du graphe.
        ground = float(gx["ground_z"][0])
        all_x = np.concatenate([gx["ax"], gx["bx"], gx["cx"], gx["rx"]])
        all_z = np.concatenate([gx["az"], gx["bz"], gx["cz"], gx["rz"]])
        rad_max = float(np.max(gx["wheel_radius"]))
        xmin, xmax = float(all_x.min()) - rad_max - 30, float(all_x.max()) + rad_max + 30
        zmin = ground - 30
        zmax = float(all_z.max()) + 30
        ground_line = go.Scatter(
            x=[xmin, xmax], y=[ground, ground], mode="lines",
            line=dict(color="#7f8c8d", width=2), name="Sol",
        )

        fig = go.Figure(
            data=[ground_line] + frame_traces(0),
            frames=[
                go.Frame(data=[ground_line] + frame_traces(i), name=f"{gt[i]*1000:.0f}")
                for i in idx
            ],
        )
        anim_xaxis = _grid_axis("X (mm)")
        anim_xaxis.update(range=[xmin, xmax], constrain="domain")
        anim_yaxis = _grid_axis("Z (mm)")
        anim_yaxis.update(range=[zmin, zmax], scaleanchor="x", scaleratio=1.0)
        fig.update_layout(
            height=560,
            plot_bgcolor=GRAPH_PAPER_BG,
            paper_bgcolor="white",
            xaxis=anim_xaxis,
            yaxis=anim_yaxis,
            margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            updatemenus=[dict(
                type="buttons", showactive=False, x=0.0, y=-0.08, xanchor="left",
                direction="left",
                buttons=[
                    dict(label="▶ Lecture", method="animate",
                         args=[None, dict(frame=dict(duration=40, redraw=True),
                                          fromcurrent=True, transition=dict(duration=0))]),
                    dict(label="⏸ Pause", method="animate",
                         args=[[None], dict(frame=dict(duration=0, redraw=False),
                                            mode="immediate")]),
                ],
            )],
            sliders=[dict(
                active=0, x=0.0, len=1.0, y=-0.02,
                currentvalue=dict(prefix="t = ", suffix=" ms"),
                steps=[dict(method="animate", label=f"{gt[i]*1000:.0f}",
                            args=[[f"{gt[i]*1000:.0f}"],
                                  dict(mode="immediate",
                                       frame=dict(duration=0, redraw=True),
                                       transition=dict(duration=0))])
                       for i in idx],
            )],
        )
        st.plotly_chart(fig, use_container_width=True)

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
