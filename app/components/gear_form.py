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
            st.markdown("**Géométrie jambe StraitStrut**")
            _num_table(_STRUT_FIELDS, prefix, base_inputs, key=f"{prefix}_strut_tbl")
            points_df = None
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

    if kind == "strait_strut":
        strut = {f: g(f) for _, f in _STRUT_FIELDS}
        return replace(base if isinstance(base, StraitStrutInputs) else default_strait_strut_inputs(),
                       **common, **strut)

    pts = {r["Point"]: Point3(float(r["X"]), float(r["Y"]), float(r["Z"])) for _, r in points_df.iterrows()}
    return replace(base if isinstance(base, TrailingArmInputs) and base.model_kind == "trailing_arm"
                   else default_trailing_arm_inputs(),
                   **common, jyy=g("jyy"),
                   B=pts["B"], A=pts["A"], C=pts["C"], R=pts["R"], S=pts["S"])


def render_single_gear_result(result, label: str) -> None:
    """Affiche un résumé compact + courbes clés d'un résultat train isolé."""
    df = result.df
    cols = list(df.columns)
    t = df[cols[0]]
    # Heuristique : repérer une colonne d'effort total et de course.
    ftot_col = next((c for c in cols if "Ftot" in c), None)
    stroke_col = next((c for c in cols if ".d (" in c or "Course" in c or "stroke" in c.lower()), None)
    m1, m2, m3 = st.columns(3)
    m1.metric("Pas de temps", f"{len(df)}")
    if ftot_col is not None:
        m2.metric("Effort total max", f"{float(np.max(np.abs(df[ftot_col]))):.0f} N")
    if stroke_col is not None:
        m3.metric("Course max", f"{float(np.max(df[stroke_col])) * 1000.0:.1f} mm")
    plot_cols = [c for c in (ftot_col, stroke_col) if c is not None]
    if plot_cols:
        st.line_chart(df.set_index(cols[0])[plot_cols])

    # --- Bilan énergétique (si les colonnes Énergie.* sont présentes) ---------
    e_cols = [c for c in cols if c.startswith("Énergie.")]
    if e_cols:
        import plotly.graph_objects as go

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

        def _energy_layout(fig, title, b=90):
            fig.update_layout(
                height=420,
                title=dict(text=title, y=0.98, yanchor="top"),
                margin=dict(l=10, r=10, t=56, b=b),
                xaxis_title="Temps (s)", yaxis_title="Énergie (J)",
                legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="left", x=0),
            )
            return fig

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

    if getattr(result, "warnings", None):
        with st.expander(f"⚠️ {len(result.warnings)} avertissement(s) — {label}"):
            for w in result.warnings:
                st.warning(str(w))
