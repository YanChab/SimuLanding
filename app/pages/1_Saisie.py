"""Page **Saisie** : formulaire des données du train à balancier (MLG).

Toutes les valeurs sont saisies dans les unités d'affichage de l'Excel d'origine.
À la validation, les erreurs sont détectées à trois niveaux (saisie, pré-calcul,
exécution) et **localisées** : le champ fautif est surligné et accompagné d'un
message clair et d'un conseil de correction.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dropsim import MLGInputs, SimError, default_mlg_inputs, run_simulation  # noqa: E402
from dropsim.inputs import Point3, Rainure  # noqa: E402
from dropsim.metering import build_section_table  # noqa: E402

if "inputs" not in st.session_state:
    st.session_state.inputs = default_mlg_inputs()

# Erreurs localisées issues de la dernière validation : {champ: message}.
field_errors: dict[str, str] = st.session_state.get("field_errors", {})

st.title("📝 Saisie des données du train d'atterrissage")
st.caption("Architecture à balancier (MLG) — unités : mm · bar · cc · cSt · MPa · ° · °C")


# --------------------------------------------------------------------------- #
#  Helper de champ numérique avec surlignage d'erreur localisée
# --------------------------------------------------------------------------- #
def num(label: str, field: str, default: float, *, step: float = 1.0,
        fmt: str | None = None, help: str | None = None, min_value=None) -> None:
    """Affiche un ``number_input`` lié à ``field`` et surligne l'erreur éventuelle."""
    err = field_errors.get(field)
    shown = f"⚠️ {label}" if err else label
    st.number_input(
        shown,
        value=float(default),
        step=step,
        format=fmt,
        help=help,
        min_value=min_value,
        key=f"f_{field}",
    )
    if err:
        st.markdown(
            f"<span style='color:#d33;font-size:0.8em'>↳ {err}</span>",
            unsafe_allow_html=True,
        )


def num_grid(specs: list[tuple], ncols: int) -> None:
    """Dispose une liste de champs ``(label, field, default, kwargs)`` sur ``ncols`` colonnes."""
    cols = st.columns(ncols)
    for i, spec in enumerate(specs):
        label, field, default = spec[0], spec[1], spec[2]
        kw = spec[3] if len(spec) > 3 else {}
        with cols[i % ncols]:
            num(label, field, default, **kw)


# --------------------------------------------------------------------------- #
#  Mini-graphe « papier millimétré » associé à un tableau
# --------------------------------------------------------------------------- #
_PAPER_BG = "#fbfbf2"
_GRID_MAJOR = "#e08e7b"
_GRID_MINOR = "#f3c9bf"


def _mini_axis(title: str) -> dict:
    return dict(
        title=title, showgrid=True, gridcolor=_GRID_MAJOR, gridwidth=1,
        zeroline=True, zerolinecolor=_GRID_MAJOR, showline=True, linecolor=_GRID_MAJOR,
        mirror=True, ticks="outside",
        minor=dict(showgrid=True, gridcolor=_GRID_MINOR, gridwidth=0.5),
    )


def mini_chart(x, y, xlab: str, ylab: str, *, mode: str = "lines+markers",
               equal: bool = False, color: str = "#1f77b4") -> go.Figure:
    """Petit graphe stylé papier millimétré pour accompagner un tableau de saisie."""
    fig = go.Figure(go.Scatter(x=x, y=y, mode=mode, line=dict(color=color, width=2),
                               marker=dict(size=5, color=color)))
    yaxis = _mini_axis(ylab)
    if equal:
        yaxis.update(scaleanchor="x", scaleratio=1.0)
    fig.update_layout(
        height=210, margin=dict(l=8, r=8, t=8, b=8),
        plot_bgcolor=_PAPER_BG, paper_bgcolor="white",
        xaxis=_mini_axis(xlab), yaxis=yaxis, showlegend=False,
    )
    return fig


def _safe_xy(df_table: pd.DataFrame):
    """Extrait deux colonnes numériques d'un éditeur en ignorant les lignes vides."""
    d = df_table.dropna()
    if d.empty:
        return [], []
    return d.iloc[:, 0].to_numpy(), d.iloc[:, 1].to_numpy()


inp: MLGInputs = st.session_state.inputs

# --------------------------------------------------------------------------- #
#  Conditions de chute
# --------------------------------------------------------------------------- #
st.header("Conditions de chute")
num_grid([
    ("Masse supportée (kg)", "masse", inp.masse, dict(step=10.0, min_value=0.0)),
    ("Vitesse verticale Vz (m/s)", "vz", inp.vz, dict(step=0.1, min_value=0.0)),
    ("Vitesse horizontale Vx (m/s)", "vx", inp.vx, dict(step=1.0, min_value=0.0)),
    ("Coefficient de portance (0..1)", "lift", inp.lift, dict(step=0.01)),
    ("Assiette / pitch (°)", "pitch", inp.pitch, dict(step=0.5)),
    ("Gîte / roll (°)", "roll", inp.roll, dict(step=0.5)),
    ("Durée simulée (s)", "temps_simu", inp.temps_simu, dict(step=0.05, fmt="%.4f")),
    ("Pas de temps It (s)", "it", inp.it, dict(step=0.0001, fmt="%.5f")),
    ("Température (°C)", "temperature", inp.temperature, dict(step=1.0)),
], 5)

# --------------------------------------------------------------------------- #
#  Amortisseur
# --------------------------------------------------------------------------- #
st.header("Amortisseur (géométrie)")
num_grid([
    ("Ø piston Dpis (mm)", "Dpis", inp.Dpis, dict(step=0.5)),
    ("Ø bague hydraulique Dbh (mm)", "Dbh", inp.Dbh, dict(step=0.5)),
    ("Ø tige Dt (mm)", "Dt", inp.Dt, dict(step=0.5)),
    ("Ø intérieur tige Dp (mm)", "Dp", inp.Dp, dict(step=0.5)),
    ("Ø intérieur BH (mm)", "DInsideBh", inp.DInsideBh, dict(step=0.5)),
    ("Longueur trou BH (mm)", "Lbh", inp.Lbh, dict(step=1.0)),
    ("Course totale SAT (mm)", "course", inp.course, dict(step=1.0)),
    ("Ø trou piston détente (mm)", "DTrouPis", inp.DTrouPis, dict(step=0.1, fmt="%.2f")),
    ("Nb trous piston", "NbTrouPis", inp.NbTrouPis, dict(step=1.0)),
    ("Hauteur piston BH (mm)", "HauteurPisBh", inp.HauteurPisBh, dict(step=0.5)),
    ("Ø trou clapet (mm)", "DTrouDiap", inp.DTrouDiap, dict(step=0.1, fmt="%.2f")),
    ("Nb trous clapet", "NbTrouDiap", inp.NbTrouDiap, dict(step=1.0)),
], 6)

# --------------------------------------------------------------------------- #
#  Ressort gazeux
# --------------------------------------------------------------------------- #
st.header("Ressort gazeux (double chambre)")
num_grid([
    ("Pression init. BP (bar)", "Pinitbp", inp.Pinitbp, dict(step=1.0)),
    ("Volume gaz init. BP (cc)", "Vgbp", inp.Vgbp, dict(step=1.0, fmt="%.4f")),
    ("Volume d'huile (cc)", "Vh", inp.Vh, dict(step=1.0, fmt="%.4f")),
    ("Pression init. HP (bar)", "Pinithp", inp.Pinithp, dict(step=1.0)),
    ("Volume gaz init. HP (cc)", "Vghp", inp.Vghp, dict(step=1.0, fmt="%.4f")),
    ("Coefficient polytropique γ", "gamma", inp.gamma, dict(step=0.01, fmt="%.2f")),
], 6)

# --------------------------------------------------------------------------- #
#  Huile
# --------------------------------------------------------------------------- #
st.header("Huile")
num_grid([
    ("Viscosité cinématique (cSt)", "visc", inp.visc, dict(step=0.1, fmt="%.4f")),
    ("Module de compressibilité (MPa)", "bulk", inp.bulk, dict(step=1.0, fmt="%.2f")),
    ("Masse volumique ρ (kg/m³)", "rho", inp.rho, dict(step=1.0)),
], 6)

# --------------------------------------------------------------------------- #
#  Pneu
# --------------------------------------------------------------------------- #
st.header("Pneu et spring-back")
num_grid([
    ("Masse non suspendue (kg)", "unsprung_mass", inp.unsprung_mass, dict(step=0.5)),
    ("Inertie polaire roue (kg·m²)", "wheel_inertia", inp.wheel_inertia, dict(step=0.01, fmt="%.5f")),
    ("Rayon libre (mm)", "unload_radius", inp.unload_radius, dict(step=1.0, fmt="%.2f")),
    ("Raideur spring-back Kx (N/m)", "kx", inp.kx, dict(step=10000.0)),
    ("Amortissement spring-back Cx (N·s/m)", "cx", inp.cx, dict(step=10.0, fmt="%.4f")),
    ("Masse roue spring-back (kg)", "wheelmass", inp.wheelmass, dict(step=0.5)),
], 6)


tyre_col, mu_col = st.columns(2)
with tyre_col:
    st.markdown("**Courbe pneu** — déflexion (mm) → charge (kN)")
    te, tg = st.columns([1, 1])
    with te:
        tyre_df = st.data_editor(
            pd.DataFrame(inp.tyre_curve, columns=["Déflexion (mm)", "Charge (kN)"]),
            num_rows="dynamic",
            use_container_width=True,
            height=210,
            key="tyre_curve_editor",
        )
    with tg:
        tx, ty = _safe_xy(tyre_df)
        st.plotly_chart(
            mini_chart(tx, ty, "Déflexion (mm)", "Charge (kN)", color="#1f77b4"),
            use_container_width=True,
        )

with mu_col:
    st.markdown("**Courbe d'adhérence** — taux de glissement → μ")
    me, mg = st.columns([1, 1])
    with me:
        mu_df = st.data_editor(
            pd.DataFrame(inp.mu_curve, columns=["Slip", "μ"]),
            num_rows="dynamic",
            use_container_width=True,
            height=210,
            key="mu_curve_editor",
        )
    with mg:
        mx, my = _safe_xy(mu_df)
        st.plotly_chart(
            mini_chart(mx, my, "Slip", "μ", color="#2ca02c"),
            use_container_width=True,
        )

# --------------------------------------------------------------------------- #
#  Balancier et géométrie
# --------------------------------------------------------------------------- #
st.header("Balancier et géométrie")
num("Inertie balancier Jyy (kg·m²)", "jyy", inp.jyy, step=0.1, fmt="%.4f")

st.markdown("**Points (mm, repère avion)**")
pe, pg_col, pg_yz = st.columns([1, 1, 1])
with pe:
    points_df = st.data_editor(
        pd.DataFrame(
            {
                "Point": ["B", "A", "C", "R", "S"],
                "X": [inp.B.x, inp.A.x, inp.C.x, inp.R.x, inp.S.x],
                "Y": [inp.B.y, inp.A.y, inp.C.y, inp.R.y, inp.S.y],
                "Z": [inp.B.z, inp.A.z, inp.C.z, inp.R.z, inp.S.z],
            }
        ),
        use_container_width=True,
        hide_index=True,
        disabled=["Point"],
        height=210,
        key="points_editor",
    )
with pg_col:
    try:
        pdict = {r["Point"]: (float(r["X"]), float(r["Z"])) for _, r in points_df.iterrows()}
        # Amortisseur C-A, bras balancier A-B-R, liaison roue R-S.
        seg_x = [pdict["C"][0], pdict["A"][0], None, pdict["A"][0], pdict["B"][0],
                 pdict["R"][0], None, pdict["R"][0], pdict["S"][0]]
        seg_z = [pdict["C"][1], pdict["A"][1], None, pdict["A"][1], pdict["B"][1],
                 pdict["R"][1], None, pdict["R"][1], pdict["S"][1]]
        fig_pts = go.Figure()
        fig_pts.add_trace(go.Scatter(x=seg_x, y=seg_z, mode="lines",
                                     line=dict(color="#2c3e50", width=3), name="Liaisons"))
        fig_pts.add_trace(go.Scatter(
            x=[v[0] for v in pdict.values()], y=[v[1] for v in pdict.values()],
            mode="markers+text", text=list(pdict.keys()), textposition="top center",
            marker=dict(size=9, color="#e74c3c"), name="Points"))
        fig_pts.update_layout(
            height=210, margin=dict(l=8, r=8, t=26, b=8),
            plot_bgcolor=_PAPER_BG, paper_bgcolor="white", showlegend=False,
            title=dict(text="Vue X-Z (profil)", x=0.5, font=dict(size=12)),
            xaxis=_mini_axis("X (mm)"),
            yaxis=_mini_axis("Z (mm)") | dict(scaleanchor="x", scaleratio=1.0),
        )
        st.plotly_chart(fig_pts, use_container_width=True)
    except (KeyError, ValueError, TypeError):
        st.caption("Géométrie incomplète — graphe indisponible.")
with pg_yz:
    try:
        pyz = {r["Point"]: (float(r["Y"]), float(r["Z"])) for _, r in points_df.iterrows()}
        # Amortisseur C-A, bras balancier A-B-R, liaison roue R-S (plan Y-Z).
        seg_y = [pyz["C"][0], pyz["A"][0], None, pyz["A"][0], pyz["B"][0],
                 pyz["R"][0], None, pyz["R"][0], pyz["S"][0]]
        seg_z2 = [pyz["C"][1], pyz["A"][1], None, pyz["A"][1], pyz["B"][1],
                  pyz["R"][1], None, pyz["R"][1], pyz["S"][1]]
        fig_yz = go.Figure()
        fig_yz.add_trace(go.Scatter(x=seg_y, y=seg_z2, mode="lines",
                                    line=dict(color="#2c3e50", width=3), name="Liaisons"))
        fig_yz.add_trace(go.Scatter(
            x=[v[0] for v in pyz.values()], y=[v[1] for v in pyz.values()],
            mode="markers+text", text=list(pyz.keys()), textposition="top center",
            marker=dict(size=9, color="#e74c3c"), name="Points"))
        fig_yz.update_layout(
            title=dict(text="Vue Y-Z (face)", x=0.5, font=dict(size=12)),
            height=210, margin=dict(l=8, r=8, t=26, b=8),
            plot_bgcolor=_PAPER_BG, paper_bgcolor="white", showlegend=False,
            xaxis=_mini_axis("Y (mm)"),
            yaxis=_mini_axis("Z (mm)") | dict(scaleanchor="x", scaleratio=1.0),
        )
        st.plotly_chart(fig_yz, use_container_width=True)
    except (KeyError, ValueError, TypeError):
        st.caption("Géométrie incomplète — graphe indisponible.")

# --------------------------------------------------------------------------- #
#  Rainures de la bague hydraulique
# --------------------------------------------------------------------------- #
st.header("Rainures de la bague hydraulique")
num("Ø rainure (mm)", "diametre_rainure", inp.diametre_rainure, step=1.0)
st.markdown("**Cotes des rainures** — début / fin / profondeur (mm)")
re_col, rg_col, rs_col = st.columns([1, 1, 1])
with re_col:
    rainures_df = st.data_editor(
        pd.DataFrame(
            [(r.debut, r.fin, r.profondeur) for r in inp.rainures],
            columns=["Début (mm)", "Fin (mm)", "Profondeur (mm)"],
        ),
        num_rows="dynamic",
        use_container_width=True,
        height=210,
        key="rainures_editor",
    )
with rg_col:
    try:
        rfig = go.Figure()
        for k, row in enumerate(rainures_df.dropna().itertuples(index=False), start=1):
            debut, fin, prof = float(row[0]), float(row[1]), float(row[2])
            rfig.add_trace(go.Scatter(
                x=[debut, fin], y=[prof, prof], mode="lines+markers",
                line=dict(width=3), marker=dict(size=5), name=f"Rainure {k}"))
        rfig.update_layout(
            title=dict(text="Profil des rainures", x=0.5, font=dict(size=12)),
            height=210, margin=dict(l=8, r=8, t=26, b=8),
            plot_bgcolor=_PAPER_BG, paper_bgcolor="white", showlegend=False,
            xaxis=_mini_axis("Course (mm)"), yaxis=_mini_axis("Profondeur (mm)"),
        )
        st.plotly_chart(rfig, use_container_width=True)
    except (ValueError, TypeError):
        st.caption("Cotes incomplètes — graphe indisponible.")
with rs_col:
    # Section cumulée de la butée hydraulique (somme des aires ouvertes par les rainures)
    try:
        _rd = rainures_df.dropna()
        shim = types.SimpleNamespace(
            Dbh=float(st.session_state["f_Dbh"]) / 1000.0,
            diametre_rainure=float(st.session_state["f_diametre_rainure"]),
            course=float(st.session_state["f_course"]) / 1000.0,
            rainures_debut=np.array([float(r[0]) for r in _rd.itertuples(index=False)]),
            rainures_fin=np.array([float(r[1]) for r in _rd.itertuples(index=False)]),
            rainures_profondeur=np.array([float(r[2]) for r in _rd.itertuples(index=False)]),
        )
        tab_pos, tab_sec = build_section_table(shim)
        course_mm = np.arange(len(tab_sec), dtype=float)
        sec_mm2 = tab_sec * 1.0e6
        sfig = go.Figure()
        sfig.add_trace(go.Scatter(
            x=course_mm, y=sec_mm2, mode="lines",
            line=dict(width=2.5, color="#9467bd"), name="Section cumulée"))
        sfig.update_layout(
            title=dict(text="Section cumulée butée hydraulique", x=0.5,
                       font=dict(size=12)),
            height=210, margin=dict(l=8, r=8, t=26, b=8),
            plot_bgcolor=_PAPER_BG, paper_bgcolor="white", showlegend=False,
            xaxis=_mini_axis("Course (mm)"), yaxis=_mini_axis("Section (mm²)"),
        )
        st.plotly_chart(sfig, use_container_width=True)
    except (ValueError, TypeError, KeyError, ZeroDivisionError):
        st.caption("Section cumulée indisponible — vérifier les cotes et Dbh.")



# --------------------------------------------------------------------------- #
#  Construction d'un MLGInputs depuis les widgets
# --------------------------------------------------------------------------- #
def _build_inputs() -> MLGInputs:
    def g(field: str) -> float:
        return float(st.session_state[f"f_{field}"])

    def pt(row) -> Point3:
        return Point3(float(row["X"]), float(row["Y"]), float(row["Z"]))

    pts = {r["Point"]: pt(r) for _, r in points_df.iterrows()}

    return MLGInputs(
        masse=g("masse"), vz=g("vz"), vx=g("vx"), lift=g("lift"),
        pitch=g("pitch"), roll=g("roll"), temps_simu=g("temps_simu"),
        it=g("it"), temperature=g("temperature"),
        Dpis=g("Dpis"), Dbh=g("Dbh"), Dt=g("Dt"), Dp=g("Dp"),
        DInsideBh=g("DInsideBh"), Lbh=g("Lbh"), course=g("course"),
        DTrouPis=g("DTrouPis"), NbTrouPis=g("NbTrouPis"),
        HauteurPisBh=g("HauteurPisBh"), DTrouDiap=g("DTrouDiap"),
        NbTrouDiap=g("NbTrouDiap"),
        Pinitbp=g("Pinitbp"), Vgbp=g("Vgbp"), Vh=g("Vh"),
        Pinithp=g("Pinithp"), Vghp=g("Vghp"), gamma=g("gamma"),
        visc=g("visc"), bulk=g("bulk"), rho=g("rho"),
        unsprung_mass=g("unsprung_mass"), wheel_inertia=g("wheel_inertia"),
        unload_radius=g("unload_radius"), kx=g("kx"), cx=g("cx"),
        wheelmass=g("wheelmass"), jyy=g("jyy"),
        B=pts["B"], A=pts["A"], C=pts["C"], R=pts["R"], S=pts["S"],
        tyre_curve=[(float(a), float(b)) for a, b in tyre_df.itertuples(index=False)],
        mu_curve=[(float(a), float(b)) for a, b in mu_df.itertuples(index=False)],
        diametre_rainure=g("diametre_rainure"),
        rainures=[
            Rainure(float(a), float(b), float(c))
            for a, b, c in rainures_df.itertuples(index=False)
        ],
    )


# --------------------------------------------------------------------------- #
#  Actions
# --------------------------------------------------------------------------- #
st.divider()
col_run, col_reset, _ = st.columns([1, 1, 4])
launch = col_run.button("▶️ Lancer le calcul", type="primary", use_container_width=True)
reset = col_reset.button("↺ Réinitialiser", use_container_width=True)

if reset:
    for key in list(st.session_state.keys()):
        if key.startswith("f_") or key.endswith("_editor"):
            del st.session_state[key]
    st.session_state.inputs = default_mlg_inputs()
    st.session_state.pop("field_errors", None)
    st.session_state.pop("result", None)
    st.rerun()

if launch:
    new_inputs = _build_inputs()
    st.session_state.inputs = new_inputs

    # Niveau SAISIE : on remonte TOUTES les erreurs d'un coup.
    collector = new_inputs.validate()
    if collector.has_errors:
        st.session_state.field_errors = {
            e.field or "_global": str(e.message) + (f" — {e.hint}" if e.hint else "")
            for e in collector.errors
        }
        st.session_state.pop("result", None)
        st.rerun()
    else:
        st.session_state.field_errors = {}
        try:
            with st.spinner("Calcul en cours…"):
                result = run_simulation(new_inputs)
            st.session_state.result = result
            st.success(
                "Calcul terminé. Consultez la page **Résultats**.", icon="✅"
            )
            if result.warnings:
                with st.expander(f"⚠️ {len(result.warnings)} avertissement(s)"):
                    for w in result.warnings:
                        st.warning(str(w))
        except SimError as exc:
            # Erreur de pré-calcul ou d'exécution : on la localise.
            st.session_state.pop("result", None)
            if exc.field:
                st.session_state.field_errors = {
                    exc.field: str(exc.message) + (f" — {exc.hint}" if exc.hint else "")
                }
            st.error(
                f"**[{exc.level.value}] {exc.code}** "
                f"{'(champ : ' + exc.field + ') ' if exc.field else ''}: "
                f"{exc.message}"
                + (f"\n\n💡 {exc.hint}" if exc.hint else ""),
                icon="🛑",
            )
            st.rerun()

# --------------------------------------------------------------------------- #
#  Panneau de synthèse des erreurs localisées
# --------------------------------------------------------------------------- #
if field_errors:
    st.divider()
    st.subheader("🛑 Erreurs détectées")
    st.caption("Les champs concernés sont surlignés ci-dessus avec un ⚠️.")
    for field, msg in field_errors.items():
        label = "Général" if field == "_global" else f"Champ « {field} »"
        st.error(f"**{label}** : {msg}")
