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
_APP = Path(__file__).resolve().parent.parent
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

from dropsim import MLGInputs, SimError, default_mlg_inputs, run_simulation  # noqa: E402
from dropsim.inputs import (  # noqa: E402
    Point3,
    Rainure,
    compute_gas_oil_at_temperature,
    compute_bulk_modulus_at_temperature,
    compute_bulk_modulus_from_aeration,
    TEMP_REF_C,
)
from dropsim.metering import build_section_table  # noqa: E402
from theme import apply_theme  # noqa: E402

apply_theme()

if "inputs" not in st.session_state:
    st.session_state.inputs = default_mlg_inputs()

_LEGACY_OIL_DEFAULTS = {
    "k_huile": 10000.0,
    "k_huile_temp_coeff": -0.003,
    "bulk": 196.08,
}


def _is_close(a: float, b: float, *, tol: float = 1.0e-9) -> bool:
    return abs(a - b) <= tol * max(1.0, abs(b))


def _migrate_legacy_oil_defaults() -> None:
    """Migre une session héritée (anciens défauts Excel) vers les défauts
    MIL-PRF-87257, sans écraser des valeurs déjà personnalisées."""
    if st.session_state.get("_oil_defaults_migrated_v1", False):
        return

    new_defaults = default_mlg_inputs()

    inp = st.session_state.get("inputs")
    if isinstance(inp, MLGInputs):
        if (
            _is_close(float(inp.k_huile), _LEGACY_OIL_DEFAULTS["k_huile"])
            and _is_close(
                float(inp.k_huile_temp_coeff),
                _LEGACY_OIL_DEFAULTS["k_huile_temp_coeff"],
            )
            and _is_close(float(inp.bulk), _LEGACY_OIL_DEFAULTS["bulk"])
        ):
            inp.k_huile = float(new_defaults.k_huile)
            inp.k_huile_temp_coeff = float(new_defaults.k_huile_temp_coeff)
            inp.bulk = float(new_defaults.bulk)

    if _is_close(
        float(st.session_state.get("f_k_huile", _LEGACY_OIL_DEFAULTS["k_huile"])),
        _LEGACY_OIL_DEFAULTS["k_huile"],
    ):
        st.session_state["f_k_huile"] = float(new_defaults.k_huile)

    if _is_close(
        float(
            st.session_state.get(
                "f_k_huile_temp_coeff",
                _LEGACY_OIL_DEFAULTS["k_huile_temp_coeff"],
            )
        ),
        _LEGACY_OIL_DEFAULTS["k_huile_temp_coeff"],
    ):
        st.session_state["f_k_huile_temp_coeff"] = float(new_defaults.k_huile_temp_coeff)

    if _is_close(
        float(st.session_state.get("f_bulk", _LEGACY_OIL_DEFAULTS["bulk"])),
        _LEGACY_OIL_DEFAULTS["bulk"],
    ):
        st.session_state["f_bulk"] = float(new_defaults.bulk)

    st.session_state["_oil_defaults_migrated_v1"] = True


_migrate_legacy_oil_defaults()

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
    skey = f"f_{field}"
    # Semer la valeur une seule fois puis laisser le widget gérer son état via
    # ``key`` : passer simultanément ``value`` et ``key`` désynchronise le widget
    # de ``st.session_state`` (la valeur saisie n'est pas répercutée).
    if skey not in st.session_state:
        st.session_state[skey] = float(default)
    st.number_input(
        shown,
        step=step,
        format=fmt,
        help=help,
        min_value=min_value,
        key=skey,
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


def num_table(specs: list[tuple], key: str, *, height: int | None = None,
              stretch: bool = False) -> None:
    """Affiche une liste de champs ``(label, field, default, …)`` sous forme de
    tableau éditable compact (colonnes Paramètre / Valeur) et écrit chaque valeur
    dans ``st.session_state[f"f_{field}"]`` pour rester compatible avec ``_build_inputs``.

    Si ``stretch`` est vrai, le tableau occupe toute la largeur de sa colonne ;
    sinon il s'ajuste à son contenu (``width="content"``).

    Les champs en erreur sont préfixés d'un ⚠️ dans la colonne « Paramètre » ; le
    détail reste affiché dans le panneau de synthèse en bas de page.
    """
    rows = []
    for spec in specs:
        label, field, default = spec[0], spec[1], spec[2]
        cur = st.session_state.get(f"f_{field}", float(default))
        marker = "⚠️ " if field_errors.get(field) else ""
        rows.append({
            "Paramètre": f"{marker}{label}",
            "Valeur": float(cur),
        })
    df = pd.DataFrame(rows)
    if height is None:
        height = 38 + 35 * len(rows)
    edited = st.data_editor(
        df,
        column_config={
            "Paramètre": st.column_config.TextColumn("Paramètre", alignment="right"),
            "Valeur": st.column_config.NumberColumn("Valeur", width="small", alignment="center"),
        },
        disabled=["Paramètre"],
        hide_index=True,
        width="stretch" if stretch else "content",
        height=height,
        key=key,
    )
    for spec, (_, row) in zip(specs, edited.iterrows()):
        field = spec[1]
        try:
            st.session_state[f"f_{field}"] = float(row["Valeur"])
        except (TypeError, ValueError):
            st.session_state[f"f_{field}"] = float(spec[2])


def value_table(rows: list[tuple[str, float]], *, height: int | None = None) -> None:
    """Affiche un tableau en lecture seule (Paramètre / Valeur), même style que
    ``num_table``. Utilisé pour montrer des valeurs *calculées* (non éditables)."""
    df = pd.DataFrame([{"Paramètre": lbl, "Valeur": float(val)} for lbl, val in rows])
    if height is None:
        height = 38 + 35 * len(rows)
    st.dataframe(
        df,
        column_config={
            "Paramètre": st.column_config.TextColumn("Paramètre", alignment="right"),
            "Valeur": st.column_config.NumberColumn(
                "Valeur", width="small", alignment="center", format="%.4g"
            ),
        },
        hide_index=True,
        width="content",
        height=height,
    )


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
#  1) Conditions de chute  +  2) Balancier et géométrie (côte à côte)
# --------------------------------------------------------------------------- #
col_chute, col_balancier = st.columns([2, 5])

with col_chute:
    st.header("Conditions de chute")
    num_table([
        ("Masse supportée (kg)", "masse", inp.masse),
        ("Vitesse verticale Vz (m/s)", "vz", inp.vz),
        ("Vitesse horizontale Vx (m/s)", "vx", inp.vx),
        ("Coefficient de portance (0..1)", "lift", inp.lift),
        ("Assiette / pitch (°)", "pitch", inp.pitch),
        ("Gîte / roll (°)", "roll", inp.roll),
        ("Durée simulée (s)", "temps_simu", inp.temps_simu),
        ("Pas de temps It (s)", "it", inp.it),
    ], "chute_editor")
    # Champ dédié pour la température : un number_input accepte nativement les
    # valeurs négatives (température froide), contrairement à l'éditeur tabulaire.
    num(
        "Température (°C)", "temperature", inp.temperature,
        step=1.0,
        help="Température de l'huile et du gaz. Les valeurs négatives "
             "(conditions froides) sont autorisées.",
    )

with col_balancier:
    st.header("Balancier et géométrie")
    num_table([
        ("Inertie balancier Jyy (kg·m²)", "jyy", inp.jyy),
    ], "jyy_editor")

    st.markdown("**Points (mm, repère avion)**")
    points_df = st.data_editor(
        pd.DataFrame(
            {
                "Point": ["B", "A", "C", "R", "S"],
                "X": [inp.B.x, inp.A.x, inp.C.x, inp.R.x, inp.S.x],
                "Y": [inp.B.y, inp.A.y, inp.C.y, inp.R.y, inp.S.y],
                "Z": [inp.B.z, inp.A.z, inp.C.z, inp.R.z, inp.S.z],
            }
        ),
        column_config={
            "X": st.column_config.NumberColumn("X", alignment="center"),
            "Y": st.column_config.NumberColumn("Y", alignment="center"),
            "Z": st.column_config.NumberColumn("Z", alignment="center"),
        },
        width="stretch",
        hide_index=True,
        disabled=["Point"],
        height=222,
        key="points_editor",
    )
    pg_col, pg_yz = st.columns([1, 1])
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
            st.plotly_chart(fig_pts, width="stretch")
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
            st.plotly_chart(fig_yz, width="stretch")
        except (KeyError, ValueError, TypeError):
            st.caption("Géométrie incomplète — graphe indisponible.")

# --------------------------------------------------------------------------- #
#  3) Pneu et spring-back
# --------------------------------------------------------------------------- #
st.header("Pneu et spring-back")

# Tableau de paramètres pneu (gauche) + tableau/courbe d'effort du pneu (droite).
pneu_param_col, tyre_chart_col = st.columns([2, 5])
with pneu_param_col:
    num_table([
        ("Masse non suspendue (kg)", "unsprung_mass", inp.unsprung_mass),
        ("Inertie polaire roue (kg·m²)", "wheel_inertia", inp.wheel_inertia),
        ("Rayon libre (mm)", "unload_radius", inp.unload_radius),
        ("Raideur spring-back Kx (N/m)", "kx", inp.kx),
        ("Amortissement spring-back Cx (N·s/m)", "cx", inp.cx),
        ("Masse roue spring-back (kg)", "wheelmass", inp.wheelmass),
    ], "pneu_editor")

with tyre_chart_col:
    # Courbe pneu : tableau en lignes (points en colonnes) + graphe juste en dessous.
    st.markdown("**Courbe pneu** — déflexion (mm) → charge (kN)")
    _tyre_t = pd.DataFrame(inp.tyre_curve, columns=["Déflexion (mm)", "Charge (kN)"]).T
    _tyre_t.columns = [f"P{i + 1}" for i in range(_tyre_t.shape[1])]
    tyre_t_edit = st.data_editor(
        _tyre_t,
        width="stretch",
        key="tyre_curve_editor",
    )
    tyre_df = tyre_t_edit.T.reset_index(drop=True)
    tyre_df.columns = ["Déflexion (mm)", "Charge (kN)"]
    tx, ty = _safe_xy(tyre_df)
    st.plotly_chart(
        mini_chart(tx, ty, "Déflexion (mm)", "Charge (kN)", color="#1f77b4"),
        width="stretch",
    )

# Courbe d'adhérence : tableau en lignes (points en colonnes) + graphe juste en dessous.
st.markdown("**Courbe d'adhérence** — taux de glissement → μ")
_mu_t = pd.DataFrame(inp.mu_curve, columns=["Slip", "μ"]).T
_mu_t.columns = [f"P{i + 1}" for i in range(_mu_t.shape[1])]
mu_t_edit = st.data_editor(
    _mu_t,
    width="stretch",
    key="mu_curve_editor",
)
mu_df = mu_t_edit.T.reset_index(drop=True)
mu_df.columns = ["Slip", "μ"]
mx, my = _safe_xy(mu_df)
st.plotly_chart(
    mini_chart(mx, my, "Slip", "μ", color="#2ca02c"),
    width="stretch",
)

# --------------------------------------------------------------------------- #
#  4) Amortisseur, ressort gazeux, huile et rainures de la butée hydraulique
# --------------------------------------------------------------------------- #
st.header("Amortisseur, ressort gazeux, huile et rainures de la butée hydraulique")

col_amort, col_gaz, col_huile = st.columns([1, 1, 1])
with col_amort:
    st.subheader("Amortisseur (géométrie)")
    num_table([
        ("Ø piston Dpis (mm)", "Dpis", inp.Dpis),
        ("Ø bague hydraulique Dbh (mm)", "Dbh", inp.Dbh),
        ("Ø tige Dt (mm)", "Dt", inp.Dt),
        ("Ø intérieur tige Dp (mm)", "Dp", inp.Dp),
        ("Ø intérieur butée BH (mm)", "DInsideBh", inp.DInsideBh),
        ("Ø intérieur palier BH (mm)", "DInsidePalierBh", inp.DInsidePalierBh),
        ("Longueur trou BH (mm)", "Lbh", inp.Lbh),
        ("Longueur palier BH (mm)", "LPalierBh", inp.LPalierBh),
        ("Désaxage BH/palier (mm)", "excentricite_palier_bh", inp.excentricite_palier_bh),
        ("Course totale SAT (mm)", "course", inp.course),
        ("Ø trou piston détente (mm)", "DTrouPis", inp.DTrouPis),
        ("Nb trous piston", "NbTrouPis", inp.NbTrouPis),
        ("Hauteur piston BH (mm)", "HauteurPisBh", inp.HauteurPisBh),
        ("Ø trou clapet (mm)", "DTrouDiap", inp.DTrouDiap),
        ("Nb trous clapet", "NbTrouDiap", inp.NbTrouDiap),
        ("Section tore joint (mm)", "tore", inp.tore),
        ("Friction sèche joint fc (N/mm)", "fc", inp.fc),
        ("Coeff. friction pression fh", "fh", inp.fh),
    ], "amort_editor")
with col_gaz:
    st.subheader("Ressort gazeux")
    num_table([
        ("Pression init. BP (bar)", "Pinitbp", inp.Pinitbp),
        ("Volume gaz init. BP (cc)", "Vgbp", inp.Vgbp),
        ("Volume d'huile (cc)", "Vh", inp.Vh),
        ("Pression init. HP (bar)", "Pinithp", inp.Pinithp),
        ("Volume gaz init. HP (cc)", "Vghp", inp.Vghp),
        ("Coefficient polytropique γ", "gamma", inp.gamma),
    ], "gaz_editor")
    _temp = float(st.session_state.get("f_temperature", inp.temperature))
    _adj = compute_gas_oil_at_temperature(
        Pinitbp=float(st.session_state.get("f_Pinitbp", inp.Pinitbp)),
        Vgbp=float(st.session_state.get("f_Vgbp", inp.Vgbp)),
        Vh=float(st.session_state.get("f_Vh", inp.Vh)),
        Pinithp=float(st.session_state.get("f_Pinithp", inp.Pinithp)),
        Vghp=float(st.session_state.get("f_Vghp", inp.Vghp)),
        visc=float(st.session_state.get("f_visc", inp.visc)),
        temperature=_temp,
    )
    st.markdown(f"**Calculé à {_temp:g} °C** (référence {TEMP_REF_C:g} °C)")
    value_table([
        ("Pression init. BP (bar)", _adj["Pinitbp"]),
        ("Volume gaz init. BP (cc)", _adj["Vgbp"]),
        ("Volume d'huile (cc)", _adj["Vh"]),
        ("Pression init. HP (bar)", _adj["Pinithp"]),
        ("Volume gaz init. HP (cc)", _adj["Vghp"]),
    ])
with col_huile:
    st.subheader("Huile")
    num_table([
        ("Viscosité cinématique (cSt)", "visc", inp.visc),
        ("Masse volumique ρ (kg/m³)", "rho", inp.rho),
        ("Aération volumique à 25°C (%)", "aeration_pct", inp.aeration_pct),
        ("Module compressibilité azote Kair à 25°C (MPa)", "k_air", inp.k_air),
        ("Module compressibilité huile Khuile à 25°C (MPa)", "k_huile", inp.k_huile),
        ("Sensibilité thermique Khuile (1/°C)", "k_huile_temp_coeff", inp.k_huile_temp_coeff),
    ], "huile_editor")
    st.caption(
        "Valeurs par défaut de compressibilité calibrées sur des données "
        "MIL-PRF-87257 (point de référence 40 °C / 27,6 MPa)."
    )
    try:
        _bulk_25 = compute_bulk_modulus_from_aeration(
            aeration_pct=float(st.session_state.get("f_aeration_pct", inp.aeration_pct)),
            k_air=float(st.session_state.get("f_k_air", inp.k_air)),
            k_huile=float(st.session_state.get("f_k_huile", inp.k_huile)),
        )
        _bulk_adj = compute_bulk_modulus_at_temperature(
            aeration_pct=float(st.session_state.get("f_aeration_pct", inp.aeration_pct)),
            k_air_ref=float(st.session_state.get("f_k_air", inp.k_air)),
            k_huile_ref=float(st.session_state.get("f_k_huile", inp.k_huile)),
            temperature=float(st.session_state.get("f_temperature", inp.temperature)),
            k_huile_temp_coeff=float(
                st.session_state.get("f_k_huile_temp_coeff", inp.k_huile_temp_coeff)
            ),
        )
        _bulk_mpa = float(_bulk_adj["bulk"])
    except (TypeError, ValueError):
        _bulk_mpa = float(inp.bulk)
        _bulk_25 = float(inp.bulk)
        _bulk_adj = {
            "k_air": float(inp.k_air),
            "k_huile": float(inp.k_huile),
            "bulk_ref": float(inp.bulk),
            "bulk": float(inp.bulk),
        }
        st.caption("Bulk calculé indisponible tant que les paramètres d'aération sont invalides.")
    # Le module utilisé par la simulation est synchronisé avec la formule MLG/NLG
    # et corrigé à la température courante.
    st.session_state["f_bulk"] = float(_bulk_mpa)
    _t_cur = float(st.session_state.get("f_temperature", inp.temperature))
    st.markdown(
        f"**Compressibilité calculée** (référence {TEMP_REF_C:g} °C, appliquée à {_t_cur:g} °C)"
    )
    value_table([
        ("Bulk effectif à 25°C (MPa)", _bulk_25),
        ("Kair corrigé en T (MPa)", float(_bulk_adj["k_air"])),
        ("Khuile corrigé en T (MPa)", float(_bulk_adj["k_huile"])),
        ("Bulk effectif à la température courante (MPa)", _bulk_mpa),
    ])
    _visc_temp = float(st.session_state.get("f_temperature", inp.temperature))
    _visc_adj = compute_gas_oil_at_temperature(
        Pinitbp=float(st.session_state.get("f_Pinitbp", inp.Pinitbp)),
        Vgbp=float(st.session_state.get("f_Vgbp", inp.Vgbp)),
        Vh=float(st.session_state.get("f_Vh", inp.Vh)),
        Pinithp=float(st.session_state.get("f_Pinithp", inp.Pinithp)),
        Vghp=float(st.session_state.get("f_Vghp", inp.Vghp)),
        visc=float(st.session_state.get("f_visc", inp.visc)),
        temperature=_visc_temp,
    )
    st.markdown(f"**Calculé à {_visc_temp:g} °C** (référence {TEMP_REF_C:g} °C)")
    value_table([
        ("Viscosité cinématique (cSt)", _visc_adj["visc"]),
    ])

st.subheader("Rainures de la butée hydraulique")
diam_col, _diam_pad = st.columns([2, 5])
with diam_col:
    num_table([
        ("Ø rainure (mm)", "diametre_rainure", inp.diametre_rainure),
    ], "diametre_rainure_editor")

st.markdown("**Cotes des rainures** — début / fin / profondeur (mm)")
re_col, rs_col = st.columns([1, 1])
with re_col:
    # Tableau horizontal : cotes en lignes, rainures en colonnes (R1, R2, …).
    _rain_t = pd.DataFrame(
        [(r.debut, r.fin, r.profondeur) for r in inp.rainures],
        columns=["Début (mm)", "Fin (mm)", "Profondeur (mm)"],
    ).T
    _rain_t.columns = [f"R{i + 1}" for i in range(_rain_t.shape[1])]
    _rain_cfg = {
        c: st.column_config.NumberColumn(c, alignment="center")
        for c in _rain_t.columns
    }
    rain_t_edit = st.data_editor(
        _rain_t,
        column_config=_rain_cfg,
        width="stretch",
        height=150,
        key="rainures_editor",
    )
    rainures_df = rain_t_edit.T.reset_index(drop=True)
    rainures_df.columns = ["Début (mm)", "Fin (mm)", "Profondeur (mm)"]
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
        st.plotly_chart(sfig, width="stretch")
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
        DInsideBh=g("DInsideBh"),
        DInsidePalierBh=g("DInsidePalierBh"),
        Lbh=g("Lbh"),
        LPalierBh=g("LPalierBh"),
        excentricite_palier_bh=g("excentricite_palier_bh"),
        course=g("course"),
        DTrouPis=g("DTrouPis"), NbTrouPis=g("NbTrouPis"),
        HauteurPisBh=g("HauteurPisBh"), DTrouDiap=g("DTrouDiap"),
        NbTrouDiap=g("NbTrouDiap"),
        tore=g("tore"), fc=g("fc"), fh=g("fh"),
        Pinitbp=g("Pinitbp"), Vgbp=g("Vgbp"), Vh=g("Vh"),
        Pinithp=g("Pinithp"), Vghp=g("Vghp"), gamma=g("gamma"),
        visc=g("visc"),
        aeration_pct=g("aeration_pct"),
        k_air=g("k_air"),
        k_huile=g("k_huile"),
        k_huile_temp_coeff=g("k_huile_temp_coeff"),
        bulk=g("bulk"),
        rho=g("rho"),
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
col_run, col_reset, col_msg = st.columns([1, 1, 4])
launch = col_run.button("▶️ Lancer le calcul", type="primary", width="stretch")
reset = col_reset.button("↺ Réinitialiser", width="stretch")

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
            col_msg.success(
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
            col_msg.error(
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
