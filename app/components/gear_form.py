"""Composant de formulaire de train réutilisable pour la page Avion complet.

Expose, pour une position donnée (NLG ou MLG), un sélecteur de type
(StraitStrut / TrailingArm) et le **jeu complet** de paramètres d'un train,
afin de pouvoir lancer une simulation train isolé depuis la page unique.

Toutes les clés de widgets sont préfixées par ``prefix`` (``ac_nlg`` / ``ac_mlg``)
pour éviter toute collision d'état entre les deux positions.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
import streamlit as st

from dropsim import (
    StraitStrutInputs,
    TrailingArmInputs,
    default_strait_strut_inputs,
    default_trailing_arm_inputs,
)
from dropsim.inputs import Point3, Rainure

GEAR_TYPE_LABELS = {
    "strait_strut": "StraitStrut (jambe droite)",
    "trailing_arm": "TrailingArm (balancier)",
}
_GEAR_TYPE_OPTIONS = ["strait_strut", "trailing_arm"]

# Groupes de paramètres scalaires (label, attribut). Les réglages numériques
# globaux (intégrateur, solveur, tolérance, température) sont gérés au niveau
# avion et synchronisés par gear_inputs_for ; ils ne figurent pas ici.
_DROP_FIELDS = [
    ("Masse supportée (kg)", "masse"),
    ("Vitesse verticale Vz (m/s)", "vz"),
    ("Vitesse horizontale Vx (m/s)", "vx"),
    ("Portance lift (0..1)", "lift"),
    ("Assiette pitch (°)", "pitch"),
    ("Gîte roll (°)", "roll"),
    ("Durée simulée (s)", "temps_simu"),
    ("Pas de temps It (s)", "it"),
]
_DAMPER_FIELDS = [
    ("Ø piston Dpis (mm)", "Dpis"),
    ("Ø ext. butée Dbh (mm)", "Dbh"),
    ("Ø tige Dt (mm)", "Dt"),
    ("Ø int. tige Dp (mm)", "Dp"),
    ("Ø int. butée (mm)", "DInsideBh"),
    ("Ø int. palier butée (mm)", "DInsidePalierBh"),
    ("Longueur trou BH (mm)", "Lbh"),
    ("Longueur palier BH (mm)", "LPalierBh"),
    ("Excentricité palier e (mm)", "excentricite_palier_bh"),
    ("Course totale (mm)", "course"),
    ("Ø trou piston détente (mm)", "DTrouPis"),
    ("Nb trous piston", "NbTrouPis"),
    ("Hauteur piston BH (mm)", "HauteurPisBh"),
    ("Ø trou clapet (mm)", "DTrouDiap"),
    ("Nb trous clapet", "NbTrouDiap"),
    ("Lissage butée (mm)", "endstop_smooth_mm"),
    ("Section tore joint (mm)", "tore"),
    ("Friction sèche fc (N/mm)", "fc"),
    ("Coeff friction pression fh", "fh"),
]
_GAS_FIELDS = [
    ("Pression init. BP (bar)", "Pinitbp"),
    ("Volume gaz BP (cc)", "Vgbp"),
    ("Volume huile (cc)", "Vh"),
    ("Pression init. HP (bar)", "Pinithp"),
    ("Volume gaz HP (cc)", "Vghp"),
    ("Polytropique γ", "gamma"),
]
_OIL_FIELDS = [
    ("Viscosité (cSt)", "visc"),
    ("Masse volumique ρ (kg/m³)", "rho"),
    ("Aération à 25°C (%)", "aeration_pct"),
    ("Kair à 25°C (MPa)", "k_air"),
    ("Khuile à 25°C (MPa)", "k_huile"),
    ("Sensib. thermique Khuile (1/°C)", "k_huile_temp_coeff"),
    ("Compressibilité bulk (MPa)", "bulk"),
]
_TYRE_FIELDS = [
    ("Masse non suspendue (kg)", "unsprung_mass"),
    ("Inertie roue (kg·m²)", "wheel_inertia"),
    ("Rayon libre (mm)", "unload_radius"),
    ("Raideur spring-back Kx (N/m)", "kx"),
    ("Amortissement Cx (N·s/m)", "cx"),
    ("Masse roue spring-back (kg)", "wheelmass"),
]
# Géométrie de jambe scalaire conservée à la SAISIE (le rake, le roll et les
# hauteurs sont désormais DÉRIVÉS des points B/Gt/Gb/R). _STRUT_FIELDS reste
# référencé pour la purge d'état au changement de type.
_STRUT_FIELDS = [
    ("Rake / strut pitch (°)", "strut_pitch"),
    ("Roll jambe (°)", "strut_roll"),
    ("Hauteur pivot B (mm)", "h_pivot_z"),
    ("Hauteur bague haute Gt (mm)", "h_guide_top_z"),
    ("Hauteur bague basse Gb (mm)", "h_guide_bot_z"),
    ("Longueur bague guidage (mm)", "bague_guide"),
    ("Longueur bague piston (mm)", "bague_piston"),
    ("Précontrainte joint (Pa)", "seal_precomp_pa"),
]
_STRUT_SCALAR_FIELDS = [
    ("Longueur bague guidage (mm)", "bague_guide"),
    ("Longueur bague piston (mm)", "bague_piston"),
    ("Précontrainte joint (Pa)", "seal_precomp_pa"),
]


def _default_for(kind: str):
    return default_strait_strut_inputs() if kind == "strait_strut" else default_trailing_arm_inputs()


def _num_table(specs, prefix, base, *, key):
    """Tableau Paramètre/Valeur éditable, écrit dans st.session_state[f'{prefix}_{field}']."""
    rows = []
    for label, field in specs:
        skey = f"{prefix}_{field}"
        cur = st.session_state.get(skey, float(getattr(base, field)))
        rows.append({"Paramètre": label, "Valeur": float(cur)})
    edited = st.data_editor(
        pd.DataFrame(rows),
        column_config={
            "Paramètre": st.column_config.TextColumn("Paramètre", alignment="right"),
            "Valeur": st.column_config.NumberColumn("Valeur", width="small", alignment="center", format="%.12g"),
        },
        disabled=["Paramètre"],
        hide_index=True,
        width="stretch",
        height=38 + 35 * len(rows),
        key=key,
    )
    for (label, field), (_, row) in zip(specs, edited.iterrows()):
        try:
            st.session_state[f"{prefix}_{field}"] = float(row["Valeur"])
        except (TypeError, ValueError):
            st.session_state[f"{prefix}_{field}"] = float(getattr(base, field))


def gear_type_selectbox(position_label: str, prefix: str, current_kind: str) -> str:
    """Sélecteur de type de train. Réinitialise l'objet stocké au défaut du
    nouveau type lors d'un changement."""
    key = f"{prefix}_type"
    if key not in st.session_state:
        st.session_state[key] = current_kind
    selected = st.selectbox(
        f"Type de train — {position_label}",
        options=_GEAR_TYPE_OPTIONS,
        key=key,
        format_func=lambda k: GEAR_TYPE_LABELS[k],
    )
    return selected


def render_gear_form(position_label: str, prefix: str, base_inputs):
    """Affiche le sélecteur de type + le formulaire complet et renvoie un objet
    d'entrées train (StraitStrutInputs|TrailingArmInputs) du type sélectionné."""
    kind = gear_type_selectbox(position_label, prefix, getattr(base_inputs, "model_kind", "trailing_arm"))

    # Si le type a changé (ou ne correspond pas), repartir du défaut du type voulu.
    if getattr(base_inputs, "model_kind", "") != kind:
        # Purge des clés scalaires pour réamorcer depuis le défaut du nouveau type.
        for _, field in (_DROP_FIELDS + _DAMPER_FIELDS + _GAS_FIELDS + _OIL_FIELDS
                         + _TYRE_FIELDS + _STRUT_FIELDS + [("", "jyy"), ("", "diametre_rainure")]):
            st.session_state.pop(f"{prefix}_{field}", None)
        st.session_state.pop(f"{prefix}_points", None)
        st.session_state.pop(f"{prefix}_rainures", None)
        st.session_state.pop(f"{prefix}_tyre", None)
        st.session_state.pop(f"{prefix}_mu", None)
        base_inputs = _default_for(kind)

    with st.expander(f"Conditions de chute (run isolé) — {position_label}", expanded=False):
        st.caption(
            "Utilisées pour le run train isolé. En run avion complet, masse/lift/"
            "chute sont imposés par les blocs globaux."
        )
        _num_table(_DROP_FIELDS, prefix, base_inputs, key=f"{prefix}_drop_tbl")

    geo_col, dmp_col = st.columns(2)
    with geo_col:
        if kind == "strait_strut":
            st.markdown("**Points jambe (mm, repère avion, pitch 0°)**")
            pkey = f"{prefix}_points"
            if pkey not in st.session_state:
                st.session_state[pkey] = pd.DataFrame({
                    "Point": ["B", "Gt", "Gb", "R"],
                    "X": [base_inputs.B.x, base_inputs.Gt.x, base_inputs.Gb.x, base_inputs.R.x],
                    "Y": [base_inputs.B.y, base_inputs.Gt.y, base_inputs.Gb.y, base_inputs.R.y],
                    "Z": [base_inputs.B.z, base_inputs.Gt.z, base_inputs.Gb.z, base_inputs.R.z],
                })
            points_df = st.data_editor(
                st.session_state[pkey], hide_index=True, disabled=["Point"],
                width="stretch", key=f"{prefix}_points_ed",
            )
            st.caption(
                "B = attache fuselage, Gt/Gb = bagues haute/basse (axe de coulisse), "
                "R = centre roue. B et R peuvent être décalés de l'axe Gt-Gb ; le rake, "
                "le roll et les hauteurs sont dérivés de ces points."
            )
            st.markdown("**Bagues / joint**")
            _num_table(_STRUT_SCALAR_FIELDS, prefix, base_inputs, key=f"{prefix}_strut_tbl")
        else:
            st.markdown("**Balancier**")
            _num_table([("Inertie balancier Jyy (kg·m²)", "jyy")], prefix, base_inputs, key=f"{prefix}_jyy_tbl")
            st.markdown("**Points (mm, repère avion)**")
            pkey = f"{prefix}_points"
            if pkey not in st.session_state:
                st.session_state[pkey] = pd.DataFrame({
                    "Point": ["B", "A", "C", "R", "S"],
                    "X": [base_inputs.B.x, base_inputs.A.x, base_inputs.C.x, base_inputs.R.x, base_inputs.S.x],
                    "Y": [base_inputs.B.y, base_inputs.A.y, base_inputs.C.y, base_inputs.R.y, base_inputs.S.y],
                    "Z": [base_inputs.B.z, base_inputs.A.z, base_inputs.C.z, base_inputs.R.z, base_inputs.S.z],
                })
            points_df = st.data_editor(
                st.session_state[pkey], hide_index=True, disabled=["Point"],
                width="stretch", key=f"{prefix}_points_ed",
            )
    with dmp_col:
        st.markdown("**Amortisseur (géométrie)**")
        _num_table(_DAMPER_FIELDS, prefix, base_inputs, key=f"{prefix}_dmp_tbl")

    g1, g2, g3 = st.columns(3)
    with g1:
        st.markdown("**Ressort gazeux**")
        _num_table(_GAS_FIELDS, prefix, base_inputs, key=f"{prefix}_gas_tbl")
    with g2:
        st.markdown("**Huile**")
        _num_table(_OIL_FIELDS, prefix, base_inputs, key=f"{prefix}_oil_tbl")
    with g3:
        st.markdown("**Pneu / spring-back**")
        _num_table(_TYRE_FIELDS, prefix, base_inputs, key=f"{prefix}_tyre_tbl")

    rc1, rc2 = st.columns(2)
    with rc1:
        st.markdown("**Rainures butée hydraulique**")
        _num_table([("Ø rainure (mm)", "diametre_rainure")], prefix, base_inputs, key=f"{prefix}_drain_tbl")
        rkey = f"{prefix}_rainures"
        if rkey not in st.session_state:
            st.session_state[rkey] = pd.DataFrame(
                [(r.debut, r.fin, r.profondeur) for r in base_inputs.rainures],
                columns=["Début (mm)", "Fin (mm)", "Profondeur (mm)"],
            )
        rainures_df = st.data_editor(
            st.session_state[rkey], hide_index=True, width="stretch",
            num_rows="dynamic", key=f"{prefix}_rainures_ed",
        )
    with rc2:
        st.markdown("**Courbe pneu** (déflexion mm → charge kN)")
        tkey = f"{prefix}_tyre"
        if tkey not in st.session_state:
            st.session_state[tkey] = pd.DataFrame(base_inputs.tyre_curve, columns=["Déflexion (mm)", "Charge (kN)"])
        tyre_df = st.data_editor(
            st.session_state[tkey], hide_index=True, width="stretch",
            num_rows="dynamic", key=f"{prefix}_tyre_ed",
        )
        st.markdown("**Courbe adhérence** (slip → μ)")
        mkey = f"{prefix}_mu"
        if mkey not in st.session_state:
            st.session_state[mkey] = pd.DataFrame(base_inputs.mu_curve, columns=["Slip", "μ"])
        mu_df = st.data_editor(
            st.session_state[mkey], hide_index=True, width="stretch",
            num_rows="dynamic", key=f"{prefix}_mu_ed",
        )

    return _build_gear_inputs(prefix, kind, base_inputs, points_df, rainures_df, tyre_df, mu_df)


def _build_gear_inputs(prefix, kind, base, points_df, rainures_df, tyre_df, mu_df):
    """Construit l'objet d'entrées train depuis l'état des widgets."""
    def g(field):
        return float(st.session_state.get(f"{prefix}_{field}", float(getattr(base, field))))

    def gi(field):
        return int(round(g(field)))

    scalars = {}
    for _, field in (_DROP_FIELDS + _DAMPER_FIELDS + _GAS_FIELDS + _OIL_FIELDS + _TYRE_FIELDS):
        scalars[field] = g(field)
    for intfield in ("NbTrouPis", "NbTrouDiap"):
        scalars[intfield] = gi(intfield)
    scalars["diametre_rainure"] = g("diametre_rainure")

    rainures = [
        Rainure(float(a), float(b), float(c))
        for a, b, c in rainures_df.dropna().itertuples(index=False)
    ]
    tyre_curve = [(float(a), float(b)) for a, b in tyre_df.dropna().itertuples(index=False)]
    mu_curve = [(float(a), float(b)) for a, b in mu_df.dropna().itertuples(index=False)]

    common = dict(
        model_kind=kind,
        rainures=rainures,
        tyre_curve=tyre_curve,
        mu_curve=mu_curve,
        **scalars,
    )

    pts = {r["Point"]: Point3(float(r["X"]), float(r["Y"]), float(r["Z"])) for _, r in points_df.iterrows()}

    if kind == "strait_strut":
        strut_scalars = {f: g(f) for _, f in _STRUT_SCALAR_FIELDS}
        return replace(base if isinstance(base, StraitStrutInputs) else default_strait_strut_inputs(),
                       **common, **strut_scalars,
                       B=pts["B"], Gt=pts["Gt"], Gb=pts["Gb"], R=pts["R"])

    return replace(base if isinstance(base, TrailingArmInputs) and base.model_kind == "trailing_arm"
                   else default_trailing_arm_inputs(),
                   **common, jyy=g("jyy"),
                   B=pts["B"], A=pts["A"], C=pts["C"], R=pts["R"], S=pts["S"])


# --------------------------------------------------------------------------- #
#  Rendu complet d'un train isolé (mêmes onglets que les sections NLG/MLG de la
#  page Résultats avion + bilan énergétique). Utilisé par les onglets
#  « NLG seul » / « MLG seul » de la page Résultats avion.
# --------------------------------------------------------------------------- #
def _energy_layout(fig, title, b=90):
    fig.update_layout(
        height=420,
        title=dict(text=title, y=0.98, yanchor="top"),
        margin=dict(l=10, r=10, t=56, b=b),
        xaxis_title="Temps (s)", yaxis_title="Énergie (J)",
        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="left", x=0),
    )
    return fig


def _render_energy_balance(df, label: str) -> None:
    """Trace le bilan énergétique (synthèse + détail) si les colonnes
    ``Énergie.*`` sont présentes. Partagé par tous les affichages train isolé."""
    import plotly.graph_objects as go

    cols = list(df.columns)
    e_cols = [c for c in cols if c.startswith("Énergie.")]
    if not e_cols:
        return
    t = df[cols[0]]
    apport = next((c for c in e_cols if "Apport" in c), None)
    residual = next((c for c in e_cols if "Résidu" in c), None)
    kin = [c for c in e_cols if "Cinétique" in c]
    stock = [c for c in e_cols if "Stockée" in c or "Emmagasinée" in c]
    diss = [c for c in e_cols if "Dissipée" in c]
    zero = t * 0.0
    e_kin_tot = df[kin].sum(axis=1) if kin else zero
    e_stock_tot = df[stock].sum(axis=1) if stock else zero
    e_diss_tot = df[diss].sum(axis=1) if diss else zero
    somme = e_kin_tot + e_stock_tot + e_diss_tot

    st.markdown(f"#### Bilan énergétique — {label}")
    if apport is not None and residual is not None:
        ref = max(1.0, float(np.max(np.abs(df[apport]))))
        res_max = float(np.max(np.abs(df[residual])))
        st.caption(
            f"Résidu max = {res_max:.1f} J ({100.0 * res_max / ref:.3f} % de l'apport) "
            "— doit rester au niveau de l'erreur d'intégration."
        )

    fig = go.Figure()
    if apport is not None:
        fig.add_trace(go.Scatter(x=t, y=df[apport], mode="lines", name="Apport (à absorber)"))
    fig.add_trace(go.Scatter(x=t, y=e_diss_tot, mode="lines", name="Dissipée (absorbée déf.)"))
    fig.add_trace(go.Scatter(x=t, y=e_stock_tot, mode="lines", name="Stockée (ressorts)"))
    fig.add_trace(go.Scatter(x=t, y=e_kin_tot, mode="lines", name="Cinétique (pièces en mvt)"))
    fig.add_trace(go.Scatter(x=t, y=somme, mode="lines", name="Somme cin+stock+diss", line=dict(dash="dot")))
    if residual is not None:
        fig.add_trace(go.Scatter(x=t, y=df[residual], mode="lines", name="Résidu"))
    st.plotly_chart(_energy_layout(fig, f"Bilan énergétique — {label}"), use_container_width=True)

    with st.expander(f"Détail des réservoirs / dissipations — {label}"):
        fig2 = go.Figure()
        for c in e_cols:
            if c not in (apport, residual):
                fig2.add_trace(go.Scatter(
                    x=t, y=df[c], mode="lines",
                    name=c.replace("Énergie.", "").replace(" (J)", ""),
                ))
        st.plotly_chart(_energy_layout(fig2, f"Détail énergétique — {label}", b=130),
                        use_container_width=True)


def _gline(x, ys, title, xlab, ylab):
    import plotly.graph_objects as go

    fig = go.Figure()
    for name, y in ys:
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=name))
    fig.update_layout(
        title=dict(text=title, y=0.98, yanchor="top"),
        xaxis_title=xlab, yaxis_title=ylab, height=520,
        margin=dict(l=8, r=8, t=56, b=110),
        legend=dict(orientation="h", yanchor="top", y=-0.14, xanchor="left", x=0),
    )
    return fig


def _gline_dual(x, left, right, title, xlab, left_lab, right_lab):
    import plotly.graph_objects as go

    fig = go.Figure()
    for name, y in left:
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=name))
    for name, y in right:
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=name, yaxis="y2", line=dict(dash="dot")))
    fig.update_layout(
        title=dict(text=title, y=0.98, yanchor="top"),
        xaxis_title=xlab, yaxis=dict(title=left_lab),
        yaxis2=dict(title=right_lab, overlaying="y", side="right", showgrid=False),
        height=520, margin=dict(l=8, r=8, t=56, b=110),
        legend=dict(orientation="h", yanchor="top", y=-0.14, xanchor="left", x=0),
    )
    return fig


def _req(df, needed, title) -> bool:
    missing = [c for c in needed if c not in df.columns]
    if missing:
        st.info(f"{title} : colonnes indisponibles ({', '.join(missing)}).", icon="ℹ️")
        return False
    return True


def render_full_gear_result(result, label: str) -> None:
    """Affiche le jeu complet de courbes d'un train isolé — mêmes onglets que les
    sections NLG/MLG de la page Résultats avion (efforts, pressions, hydraulique,
    course/déflexion, accél./vitesse, liaisons) **plus** le bilan énergétique.

    Auto-détecte le type de train (StraitStrut / TrailingArm) d'après les colonnes.
    """
    df = result.df
    cols = list(df.columns)
    t = df["Temps (s)"] if "Temps (s)" in cols else df[cols[0]]
    p = "StraitStrut" if any(c.startswith("StraitStrut.") for c in cols) else "TrailingArm"
    is_ta = p == "TrailingArm"

    m1, m2, m3 = st.columns(3)
    m1.metric("Pas de temps", f"{len(df)}")
    if f"{p}.Ftot (N)" in cols:
        m2.metric("Effort amortisseur max", f"{float(np.max(np.abs(df[f'{p}.Ftot (N)']))):.0f} N")
    if "Tyre.FTyre (N)" in cols:
        m3.metric("Fz pneu max", f"{float(np.max(np.abs(df['Tyre.FTyre (N)']))):.0f} N")

    tabs = st.tabs([
        "Efforts (temps)", "Effort / course", "Pressions", "Conv. hydraulique",
        "Course & déflexion", "Accél. & vitesse", "Liaisons", "Bilan énergétique",
    ])

    with tabs[0]:
        if _req(df, ["Tyre.FTyre (N)", "Reaction sol horizontale (N)", f"{p}.Ftot (N)"], f"{label} - Efforts"):
            st.plotly_chart(_gline(t, [
                ("Fz (pneu/sol)", df["Tyre.FTyre (N)"]),
                ("Fx (horizontal)", df["Reaction sol horizontale (N)"]),
                ("Effort amortisseur", df[f"{p}.Ftot (N)"]),
            ], f"{label} - Efforts en fonction du temps", "Temps (s)", "Effort (N)"), use_container_width=True)

    with tabs[1]:
        if _req(df, [f"{p}.d (m)", "Tyre.FTyre (N)", "Reaction sol horizontale (N)"], f"{label} - Effort/course"):
            st.plotly_chart(_gline(df[f"{p}.d (m)"] * 1000.0, [
                ("Fz (pneu/sol)", df["Tyre.FTyre (N)"]),
                ("Fx (horizontal)", df["Reaction sol horizontale (N)"]),
            ], f"{label} - Effort en fonction de la course", "Course amortisseur (mm)", "Effort (N)"), use_container_width=True)

    with tabs[2]:
        pcols = [f"{p}.Pc (bar)", f"{p}.Pg (bar)", f"{p}.Pd (bar)", f"{p}.DeltaPc (bar)", f"{p}.DeltaPd (bar)"]
        if _req(df, pcols, f"{label} - Pressions"):
            st.plotly_chart(_gline(t, [
                ("Pc", df[f"{p}.Pc (bar)"]), ("Pg", df[f"{p}.Pg (bar)"]), ("Pd", df[f"{p}.Pd (bar)"]),
                ("DeltaPc", df[f"{p}.DeltaPc (bar)"]), ("DeltaPd", df[f"{p}.DeltaPd (bar)"]),
            ], f"{label} - Pressions en fonction du temps", "Temps (s)", "Pression (bar)"), use_container_width=True)

    with tabs[3]:
        if _req(df, ["Hydrau.Erreur convergence (-)", "Hydrau.Itérations convergence (-)"], f"{label} - Conv. hydraulique"):
            st.plotly_chart(_gline_dual(
                t,
                [("Erreur convergence", df["Hydrau.Erreur convergence (-)"])],
                [("Itérations", df["Hydrau.Itérations convergence (-)"])],
                f"{label} - Convergence hydraulique",
                "Temps (s)", "Erreur convergence (-)", "Itérations (-)",
            ), use_container_width=True)

    with tabs[4]:
        if _req(df, [f"{p}.d (m)", "Tyre.Defl (m)"], f"{label} - Course/déflexion"):
            st.plotly_chart(_gline(t, [
                ("Course amortisseur (mm)", df[f"{p}.d (m)"] * 1000.0),
                ("Déflexion pneu (mm)", df["Tyre.Defl (m)"] * 1000.0),
            ], f"{label} - Course et déflexion", "Temps (s)", "Déplacement (mm)"), use_container_width=True)

    with tabs[5]:
        ys = []
        if "AccMs.RsolZ (m/s²)" in cols:
            ys.append(("Accélération masse susp. (g)", df["AccMs.RsolZ (m/s²)"] / 9.81))
        if f"{p}.v (m/s)" in cols:
            ys.append(("Vitesse amortisseur (m/s)", df[f"{p}.v (m/s)"]))
        if is_ta and "OmY (rad/s)" in cols:
            ys.append(("Vitesse rotation balancier (rad/s)", df["OmY (rad/s)"]))
        if ys:
            st.plotly_chart(_gline(t, ys, f"{label} - Accélération et vitesse",
                                   "Temps (s)", "g / m.s⁻¹ / rad.s⁻¹"), use_container_width=True)
        else:
            st.info(f"{label} - Accél./vitesse : colonnes indisponibles.", icon="ℹ️")

    with tabs[6]:
        bx, bz = "Torseur@B (pivot).Effort X (N)", "Torseur@B (pivot).Effort Z (N)"
        mx, mz = "Torseur@B (pivot).Moment X (N·m)", "Torseur@B (pivot).Moment Z (N·m)"
        b_kind = "pivot" if is_ta else "encastrement"
        if _req(df, [bx, bz, mx, mz], f"{label} - Liaison B"):
            st.plotly_chart(_gline_dual(
                t,
                [("Effort Fx", df[bx]), ("Effort Fz", df[bz])],
                [("Moment Mx", df[mx]), ("Moment Mz", df[mz])],
                f"{label} — Liaison {b_kind} B : efforts (gauche) + moments (axe secondaire)",
                "Temps (s)", "Effort (N)", "Moment (N.m)",
            ), use_container_width=True)
        if is_ta:
            cfx, cfz = "Torseur@C (rotule).Effort X (N)", "Torseur@C (rotule).Effort Z (N)"
            if _req(df, [cfx, cfz], f"{label} - Liaison C"):
                st.plotly_chart(_gline(
                    t, [("Effort Fx", df[cfx]), ("Effort Fz", df[cfz])],
                    f"{label} — Liaison rotule C : efforts (pas de moment transmis)",
                    "Temps (s)", "Effort (N)",
                ), use_container_width=True)

    with tabs[7]:
        _render_energy_balance(df, label)

    if getattr(result, "warnings", None):
        with st.expander(f"⚠️ {len(result.warnings)} avertissement(s) — {label}"):
            for w in result.warnings:
                st.warning(str(w))
