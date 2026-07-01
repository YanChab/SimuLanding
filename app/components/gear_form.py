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
    StraitStrutDragBraceInputs,
    LeafSpringInputs,
    TrailingArmInputs,
    TrailingArmDragBraceInputs,
    default_strait_strut_inputs,
    default_strait_strut_drag_brace_inputs,
    default_leaf_spring_inputs,
    default_trailing_arm_inputs,
    default_trailing_arm_drag_brace_inputs,
)
from dropsim.inputs import Point3, Rainure
from dropsim.metering import build_section_table
from theme import graph_paper

GEAR_TYPE_LABELS = {
    "strait_strut": "StraitStrut (jambe droite)",
    "strait_strut_drag_brace": "StraitStrut + drag brace",
    "trailing_arm": "TrailingArm (balancier)",
    "trailing_arm_drag_brace": "TrailingArm + jambe/bielle",
    "leaf_spring": "Train à lame (leaf spring)",
}
_GEAR_TYPE_OPTIONS = ["strait_strut", "strait_strut_drag_brace",
                      "trailing_arm", "trailing_arm_drag_brace", "leaf_spring"]

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

# Amortisseur découpé en sous-groupes (4 petites tables au lieu d'une de 19 lignes).
_DF_BY_ATTR = {a: (lbl, a) for lbl, a in _DAMPER_FIELDS}
_DAMPER_SUB = [
    ("Vérin / sections", ["Dpis", "Dbh", "Dt", "Dp", "course"]),
    ("Butée hydraulique (BH)", ["DInsideBh", "DInsidePalierBh", "Lbh", "LPalierBh",
                                "excentricite_palier_bh", "HauteurPisBh"]),
    ("Orifices (piston / clapet)", ["DTrouPis", "NbTrouPis", "DTrouDiap", "NbTrouDiap"]),
    ("Friction / butée", ["fc", "fh", "tore", "endstop_smooth_mm"]),
]
_DAMPER_SUB = [(title, [_DF_BY_ATTR[a] for a in attrs]) for title, attrs in _DAMPER_SUB]
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
# Coefficients du modèle DP4 de friction de bague (NLG StraitStrut). μ = ½[μ_p(p) + μ_v(v)],
# μ_p exp-décroissant en pression, μ_v asymptotique en vitesse. Défauts GGB DP4 lubrifié.
_BAG_DP4_FIELDS = [
    ("μ_p0 — μ à pression nulle (-)", "bag_mu_p0"),
    ("μ_p∞ — μ haute pression (-)", "bag_mu_pinf"),
    ("p_ref — pression caractéristique (MPa)", "bag_p_ref"),
    ("μ_v,min — μ à vitesse nulle (-)", "bag_mu_vmin"),
    ("μ_v,max — μ haute vitesse (-)", "bag_mu_vmax"),
    ("α — raideur montée vitesse (s/m)", "bag_alpha"),
]
# Paramètres propres au Train à lame (leaf spring).
_LEAF_FIELDS = [
    ("Raideur lame (N/mm)", "lame_raideur"),
    ("Amortissement lame (N/(m/s))", "lame_amortissement"),
]


def _default_for(kind: str):
    if kind == "strait_strut_drag_brace":
        return default_strait_strut_drag_brace_inputs()
    if kind == "strait_strut":
        return default_strait_strut_inputs()
    if kind == "trailing_arm_drag_brace":
        return default_trailing_arm_drag_brace_inputs()
    if kind == "leaf_spring":
        return default_leaf_spring_inputs()
    return default_trailing_arm_inputs()


def _apply_editor_state(df: pd.DataFrame, state: dict) -> pd.DataFrame:
    """Replie l'état d'édition d'un ``st.data_editor`` (dict ``edited_rows`` /
    ``added_rows`` / ``deleted_rows``, indices **positionnels**) dans ``df`` et
    renvoie la DataFrame résultante (index réinitialisé).

    Fonction **pure** (sans Streamlit) pour être testable unitairement ; c'est le
    cœur du correctif du bug « saisie prise en compte une fois sur deux »
    (streamlit#7749) : on applique les éditions à la source *avant* le re-rendu
    de l'éditeur, au lieu de réinjecter sa sortie au cycle suivant.
    """
    out = df.reset_index(drop=True).copy()
    # 1) Éditions de cellules (positions valides dans la source courante).
    for ridx, changes in (state.get("edited_rows") or {}).items():
        pos = int(ridx)
        if 0 <= pos < len(out):
            for col, val in changes.items():
                if col in out.columns:
                    out.iat[pos, out.columns.get_loc(col)] = val
    # 2) Suppressions (positions décroissantes pour rester valides).
    deleted = sorted({int(i) for i in (state.get("deleted_rows") or [])}, reverse=True)
    if deleted:
        out = out.drop(index=[p for p in deleted if 0 <= p < len(out)]).reset_index(drop=True)
    # 3) Ajouts de lignes (colonnes manquantes → NaN, filtrées en aval par dropna).
    for row in (state.get("added_rows") or []):
        out.loc[len(out)] = {c: row.get(c) for c in out.columns}
    return out.reset_index(drop=True)


def _fold_editor_edits(skey: str, wkey: str) -> None:
    """Callback ``on_change`` d'un ``st.data_editor`` : replie les éditions
    (état sous ``wkey``) dans la DataFrame source (``skey``). Exécuté *avant* le
    re-rendu, ce qui évite le décalage d'un cycle de streamlit#7749."""
    state = st.session_state.get(wkey)
    if not state:
        return
    st.session_state[skey] = _apply_editor_state(st.session_state[skey], state)


def _editable_df(skey: str, wkey: str, initial_df: pd.DataFrame, **editor_kwargs) -> pd.DataFrame:
    """``st.data_editor`` robuste dont la **source de vérité** est
    ``st.session_state[skey]`` (jamais écrasée par la sortie de l'éditeur dans le
    corps du script). Les éditions sont repliées dans la source par le callback
    :func:`_fold_editor_edits`. Renvoie la DataFrame courante (= la source)."""
    if skey not in st.session_state:
        st.session_state[skey] = initial_df.copy()
    st.data_editor(
        st.session_state[skey], key=wkey,
        on_change=_fold_editor_edits, args=(skey, wkey),
        **editor_kwargs,
    )
    return st.session_state[skey]


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
            "Paramètre": st.column_config.TextColumn("Paramètre"),
            "Valeur": st.column_config.NumberColumn("Valeur", width="small", format="%.12g"),
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


@st.cache_data(show_spinner=False)
def _cached_section_table(dbh_mm: float, diametre_rainure: float, course_mm: float,
                          rainures: tuple) -> np.ndarray:
    """Table de section BH (mm²) mise en cache sur ses **entrées primitives**
    (hashables), pour ne pas recalculer :func:`build_section_table` à chaque
    rerun tant que la géométrie ne change pas."""
    import types

    arr = np.array(rainures, dtype=float).reshape(-1, 3) if rainures else np.empty((0, 3))
    shim = types.SimpleNamespace(
        Dbh=dbh_mm / 1000.0,                  # m
        diametre_rainure=diametre_rainure,    # mm (convention metering)
        course=course_mm / 1000.0,            # m
        rainures_debut=arr[:, 0],
        rainures_fin=arr[:, 1],
        rainures_profondeur=arr[:, 2],
    )
    _, tab_sec = build_section_table(shim)
    return tab_sec * 1.0e6                     # m² → mm²


def _render_bh_section_curve(prefix, base_inputs, rainures_df) -> None:
    """Trace la **section cumulée de la butée hydraulique** en fonction de la
    course, recalculée en direct (mêmes formules que le moteur,
    :func:`build_section_table`, mise en cache) à partir des valeurs courantes
    des widgets et du tableau des rainures."""
    def _live(field):
        return float(st.session_state.get(f"{prefix}_{field}", getattr(base_inputs, field)))

    try:
        cols = ["Début (mm)", "Fin (mm)", "Profondeur (mm)"]
        rdf = rainures_df[cols].apply(pd.to_numeric, errors="coerce").dropna()
        section_mm2 = _cached_section_table(
            _live("Dbh"), _live("diametre_rainure"), _live("course"),
            tuple(map(tuple, rdf.to_numpy(dtype=float).tolist())),
        )
        course_axis_mm = np.arange(len(section_mm2), dtype=float)
    except Exception as exc:  # géométrie incohérente (Ø rainure nul, etc.)
        st.info(f"Section BH non calculable avec ces valeurs ({exc}).", icon="ℹ️")
        return

    st.plotly_chart(
        _gline(
            course_axis_mm,
            [("Section cumulée BH", section_mm2)],
            "Section cumulée de la butée hydraulique en fonction de la course",
            "Course (mm)", "Section (mm²)",
        ),
        use_container_width=True,
        key=f"{prefix}_bh_section_chart",
    )


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


@st.fragment
def render_gear_form(position_label: str, prefix: str, base_inputs):
    """Affiche le sélecteur de type + le formulaire complet et renvoie un objet
    d'entrées train (StraitStrutInputs|TrailingArmInputs) du type sélectionné.

    Isolé dans un ``st.fragment`` : éditer un champ ne re-exécute que **ce**
    formulaire (pas toute la page ni l'autre train). L'objet d'entrées construit
    est aussi publié dans ``st.session_state[f'{prefix}_built']`` afin que le
    code de lancement (hors fragment) puisse le lire quel que soit le type de
    rerun (fragment isolé ou rerun complet)."""
    kind = gear_type_selectbox(position_label, prefix, getattr(base_inputs, "model_kind", "trailing_arm"))

    # Si le type a changé (ou ne correspond pas), repartir du défaut du type voulu.
    if getattr(base_inputs, "model_kind", "") != kind:
        # Purge des clés scalaires pour réamorcer depuis le défaut du nouveau type.
        for _, field in (_DROP_FIELDS + _DAMPER_FIELDS + _GAS_FIELDS + _OIL_FIELDS
                         + _TYRE_FIELDS + _STRUT_FIELDS + _LEAF_FIELDS
                         + [("", "jyy"), ("", "diametre_rainure")]):
            st.session_state.pop(f"{prefix}_{field}", None)
        st.session_state.pop(f"{prefix}_points", None)
        st.session_state.pop(f"{prefix}_rainures", None)
        st.session_state.pop(f"{prefix}_tyre", None)
        st.session_state.pop(f"{prefix}_mu", None)
        base_inputs = _default_for(kind)

    _is_leaf = kind == "leaf_spring"
    st.caption(f"Type : **{GEAR_TYPE_LABELS.get(kind, kind)}**")

    # Le Train à lame n'a ni oléo, ni gaz, ni rainures : on ne montre pas ces
    # sections et on réamorce rainures/tyre/mu depuis les valeurs par défaut.
    rainures_df = pd.DataFrame(
        [(r.debut, r.fin, r.profondeur) for r in base_inputs.rainures],
        columns=["Début (mm)", "Fin (mm)", "Profondeur (mm)"],
    )

    geo_col, dmp_col = st.columns(2)
    with geo_col:
        st.markdown("**Géométrie**")
        if _is_leaf:
            st.markdown("**Points lame (mm, repère avion, pitch 0°)**")
            _ls_spec = [("B", "B"), ("R", "R")]
            _ls_df = pd.DataFrame({
                "Point": [lbl for lbl, _ in _ls_spec],
                "X": [getattr(base_inputs, a).x for _, a in _ls_spec],
                "Y": [getattr(base_inputs, a).y for _, a in _ls_spec],
                "Z": [getattr(base_inputs, a).z for _, a in _ls_spec],
            })
            points_df = _editable_df(
                f"{prefix}_points", f"{prefix}_points_ed", _ls_df,
                hide_index=True, disabled=["Point"], width="stretch",
            )
            st.caption(
                "B = encastrement structure, R = centre roue. La lame agit comme un "
                "ressort vertical (k) + amortisseur (c) entre B et R. Cf. PFD §6c."
            )
        elif kind in ("strait_strut", "strait_strut_drag_brace"):
            st.markdown("**Points jambe (mm, repère avion, pitch 0°)**")
            # Points de l'axe de coulisse + ancrage. Variante drag brace : l'attache
            # B (encastrement) est remplacée par B1/B2 (rotule + linéaire annulaire)
            # et la bielle C–D. Libellés UI → attributs : C→Cdb, D→Ddb.
            if kind == "strait_strut_drag_brace":
                _pt_spec = [
                    ("B1", "B1"), ("B2", "B2"), ("Gt", "Gt"), ("Gb", "Gb"),
                    ("R", "R"), ("C", "Cdb"), ("D", "Ddb"),
                ]
            else:
                _pt_spec = [("B", "B"), ("Gt", "Gt"), ("Gb", "Gb"), ("R", "R")]
            _pt_df = pd.DataFrame({
                "Point": [lbl for lbl, _ in _pt_spec],
                "X": [getattr(base_inputs, a).x for _, a in _pt_spec],
                "Y": [getattr(base_inputs, a).y for _, a in _pt_spec],
                "Z": [getattr(base_inputs, a).z for _, a in _pt_spec],
            })
            points_df = _editable_df(
                f"{prefix}_points", f"{prefix}_points_ed", _pt_df,
                hide_index=True, disabled=["Point"], width="stretch",
            )
            if kind == "strait_strut_drag_brace":
                st.caption(
                    "Gt/Gb = bagues (axe de coulisse), R = centre roue. Ancrage du corps : "
                    "B1 (rotule) + B2 (linéaire annulaire d'axe B1-B2) + drag brace C–D "
                    "(C sur le corps, D sur la structure). Cf. PFD §5b."
                )
            else:
                st.caption(
                    "B = attache fuselage, Gt/Gb = bagues haute/basse (axe de coulisse), "
                    "R = centre roue. B et R peuvent être décalés de l'axe Gt-Gb ; le rake, "
                    "le roll et les hauteurs sont dérivés de ces points."
                )
            st.markdown("**Bagues / joint**")
            _num_table(_STRUT_SCALAR_FIELDS, prefix, base_inputs, key=f"{prefix}_strut_tbl")
            st.markdown("**Friction de bague (DP4)**")
            _num_table(_BAG_DP4_FIELDS, prefix, base_inputs, key=f"{prefix}_bagdp4_tbl")
        else:
            st.markdown("**Balancier**")
            _num_table([("Inertie balancier Jyy (kg·m²)", "jyy")], prefix, base_inputs, key=f"{prefix}_jyy_tbl")
            st.markdown("**Points (mm, repère avion)**")
            # Variante jambe/bielle : on ajoute l'ancrage F1/F2 + bielle D–E.
            # Libellés UI → attributs : D→Dbr, E→Ebr.
            if kind == "trailing_arm_drag_brace":
                _ta_spec = [
                    ("B", "B"), ("A", "A"), ("C", "C"), ("R", "R"), ("S", "S"),
                    ("F1", "F1"), ("F2", "F2"), ("D", "Dbr"), ("E", "Ebr"),
                ]
            else:
                _ta_spec = [("B", "B"), ("A", "A"), ("C", "C"), ("R", "R"), ("S", "S")]
            _ta_df = pd.DataFrame({
                "Point": [lbl for lbl, _ in _ta_spec],
                "X": [getattr(base_inputs, a).x for _, a in _ta_spec],
                "Y": [getattr(base_inputs, a).y for _, a in _ta_spec],
                "Z": [getattr(base_inputs, a).z for _, a in _ta_spec],
            })
            points_df = _editable_df(
                f"{prefix}_points", f"{prefix}_points_ed", _ta_df,
                hide_index=True, disabled=["Point"], width="stretch",
            )
            if kind == "trailing_arm_drag_brace":
                st.caption(
                    "B/A/C/R/S = balancier+amortisseur (inchangé). Ancrage de la jambe : "
                    "F1 (rotule) + F2 (linéaire annulaire d'axe F1-F2) + bielle D–E "
                    "(D sur la jambe, E sur la structure). Cf. PFD §6b."
                )
    with dmp_col:
        if _is_leaf:
            st.markdown("**Lame (ressort + amortisseur)**")
            _num_table(_LEAF_FIELDS, prefix, base_inputs, key=f"{prefix}_leaf_tbl")
            st.caption(
                "F_lame = k·δ + c·δ̇ (vertical). Réduit en B par le PFD de la lame → "
                "torseur d'encastrement. La masse non suspendue est dans « Pneu »."
            )
        else:
            st.markdown("**Amortisseur (géométrie)**")
            _d1, _d2 = st.columns(2)
            _dcols = [_d1, _d2, _d1, _d2]
            for _i, (_title, _sub) in enumerate(_DAMPER_SUB):
                with _dcols[_i]:
                    st.caption(_title)
                    _num_table(_sub, prefix, base_inputs, key=f"{prefix}_dmp{_i}_tbl")

    # --- Sections secondaires (repliées par défaut pour alléger la page) ---
    # Le Train à lame n'a ni ressort gaz, ni huile, ni rainures hydrauliques.
    if not _is_leaf:
        with st.expander("Ressort gazeux", expanded=False):
            _num_table(_GAS_FIELDS, prefix, base_inputs, key=f"{prefix}_gas_tbl")
        with st.expander("Huile", expanded=False):
            _num_table(_OIL_FIELDS, prefix, base_inputs, key=f"{prefix}_oil_tbl")
    with st.expander("Pneu / spring-back", expanded=False):
        _num_table(_TYRE_FIELDS, prefix, base_inputs, key=f"{prefix}_tyre_tbl")

    if not _is_leaf:
        with st.expander("Rainures butée hydraulique", expanded=False):
            _num_table([("Ø rainure (mm)", "diametre_rainure")], prefix, base_inputs, key=f"{prefix}_drain_tbl")
            _rain_df = pd.DataFrame(
                [(r.debut, r.fin, r.profondeur) for r in base_inputs.rainures],
                columns=["Début (mm)", "Fin (mm)", "Profondeur (mm)"],
            )
            rainures_df = _editable_df(
                f"{prefix}_rainures", f"{prefix}_rainures_ed", _rain_df,
                hide_index=True, width="stretch", num_rows="dynamic",
            )
            _render_bh_section_curve(prefix, base_inputs, rainures_df)

    with st.expander("Courbes pneu & adhérence", expanded=False):
        _c1, _c2 = st.columns(2)
        with _c1:
            st.markdown("**Courbe pneu** (déflexion mm → charge kN)")
            tyre_df = _editable_df(
                f"{prefix}_tyre", f"{prefix}_tyre_ed",
                pd.DataFrame(base_inputs.tyre_curve, columns=["Déflexion (mm)", "Charge (kN)"]),
                hide_index=True, width="stretch", num_rows="dynamic",
            )
        with _c2:
            st.markdown("**Courbe adhérence** (slip → μ)")
            mu_df = _editable_df(
                f"{prefix}_mu", f"{prefix}_mu_ed",
                pd.DataFrame(base_inputs.mu_curve, columns=["Slip", "μ"]),
                hide_index=True, width="stretch", num_rows="dynamic",
            )

    with st.expander(f"Conditions de chute (run isolé) — {position_label}", expanded=False):
        st.caption(
            "Utilisées pour le run train isolé. En run avion complet, masse/lift/"
            "chute sont imposés par les blocs globaux."
        )
        _num_table(_DROP_FIELDS, prefix, base_inputs, key=f"{prefix}_drop_tbl")

    built = _build_gear_inputs(prefix, kind, base_inputs, points_df, rainures_df, tyre_df, mu_df)
    st.session_state[f"{prefix}_built"] = built
    return built


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

    if kind == "leaf_spring":
        base_ls = base if isinstance(base, LeafSpringInputs) else default_leaf_spring_inputs()
        return replace(base_ls, **common,
                       lame_raideur=g("lame_raideur"),
                       lame_amortissement=g("lame_amortissement"),
                       B=pts["B"], R=pts["R"])

    if kind == "strait_strut_drag_brace":
        strut_scalars = {f: g(f) for _, f in _STRUT_SCALAR_FIELDS + _BAG_DP4_FIELDS}
        base_db = base if isinstance(base, StraitStrutDragBraceInputs) else default_strait_strut_drag_brace_inputs()
        return replace(base_db, **common, **strut_scalars,
                       Gt=pts["Gt"], Gb=pts["Gb"], R=pts["R"],
                       B1=pts["B1"], B2=pts["B2"], Cdb=pts["C"], Ddb=pts["D"])

    if kind == "strait_strut":
        strut_scalars = {f: g(f) for _, f in _STRUT_SCALAR_FIELDS + _BAG_DP4_FIELDS}
        # base StraitStrut "pur" (pas la sous-classe drag brace, gérée ci-dessus)
        base_ss = base if (isinstance(base, StraitStrutInputs)
                           and not isinstance(base, StraitStrutDragBraceInputs)) else default_strait_strut_inputs()
        return replace(base_ss, **common, **strut_scalars,
                       B=pts["B"], Gt=pts["Gt"], Gb=pts["Gb"], R=pts["R"])

    if kind == "trailing_arm_drag_brace":
        base_jb = base if isinstance(base, TrailingArmDragBraceInputs) else default_trailing_arm_drag_brace_inputs()
        return replace(base_jb, **common, jyy=g("jyy"),
                       B=pts["B"], A=pts["A"], C=pts["C"], R=pts["R"], S=pts["S"],
                       F1=pts["F1"], F2=pts["F2"], Dbr=pts["D"], Ebr=pts["E"])

    return replace(base if (isinstance(base, TrailingArmInputs)
                            and not isinstance(base, (StraitStrutInputs, TrailingArmDragBraceInputs))
                            and base.model_kind == "trailing_arm")
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
    return graph_paper(fig)


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
        fig.add_trace(go.Scattergl(x=t, y=df[apport], mode="lines", name="Apport (à absorber)"))
    fig.add_trace(go.Scattergl(x=t, y=e_diss_tot, mode="lines", name="Dissipée (absorbée déf.)"))
    fig.add_trace(go.Scattergl(x=t, y=e_stock_tot, mode="lines", name="Stockée (ressorts)"))
    fig.add_trace(go.Scattergl(x=t, y=e_kin_tot, mode="lines", name="Cinétique (pièces en mvt)"))
    fig.add_trace(go.Scattergl(x=t, y=somme, mode="lines", name="Somme cin+stock+diss", line=dict(dash="dot")))
    if residual is not None:
        fig.add_trace(go.Scattergl(x=t, y=df[residual], mode="lines", name="Résidu"))
    st.plotly_chart(_energy_layout(fig, f"Bilan énergétique — {label}"), use_container_width=True)

    with st.expander(f"Détail des réservoirs / dissipations — {label}"):
        fig2 = go.Figure()
        for c in e_cols:
            if c not in (apport, residual):
                fig2.add_trace(go.Scattergl(
                    x=t, y=df[c], mode="lines",
                    name=c.replace("Énergie.", "").replace(" (J)", ""),
                ))
        st.plotly_chart(_energy_layout(fig2, f"Détail énergétique — {label}", b=130),
                        use_container_width=True)


def _gline(x, ys, title, xlab, ylab, dashes=None):
    import plotly.graph_objects as go

    fig = go.Figure()
    for i, (name, y) in enumerate(ys):
        # ``dashes`` (optionnel) rend distinguables des courbes qui se superposent
        # (ex. composantes proportionnelles selon la géométrie de la bielle).
        line = dict(dash=dashes[i], width=2.4) if dashes else None
        # Scattergl (WebGL) : rendu bien plus rapide côté navigateur pour ces
        # tracés à nombreux points / nombreuses courbes.
        fig.add_trace(go.Scattergl(x=x, y=y, mode="lines", name=name, line=line))
    fig.update_layout(
        title=dict(text=title, y=0.98, yanchor="top"),
        xaxis_title=xlab, yaxis_title=ylab, height=520,
        margin=dict(l=8, r=8, t=56, b=110),
        legend=dict(orientation="h", yanchor="top", y=-0.14, xanchor="left", x=0),
    )
    return graph_paper(fig)


def _gline_dual(x, left, right, title, xlab, left_lab, right_lab):
    import plotly.graph_objects as go

    fig = go.Figure()
    for name, y in left:
        fig.add_trace(go.Scattergl(x=x, y=y, mode="lines", name=name))
    for name, y in right:
        fig.add_trace(go.Scattergl(x=x, y=y, mode="lines", name=name, yaxis="y2", line=dict(dash="dot")))
    fig.update_layout(
        title=dict(text=title, y=0.98, yanchor="top"),
        xaxis_title=xlab, yaxis=dict(title=left_lab),
        yaxis2=dict(title=right_lab, overlaying="y", side="right", showgrid=False),
        height=520, margin=dict(l=8, r=8, t=56, b=110),
        legend=dict(orientation="h", yanchor="top", y=-0.14, xanchor="left", x=0),
    )
    return graph_paper(fig)


def _req(df, needed, title) -> bool:
    missing = [c for c in needed if c not in df.columns]
    if missing:
        st.info(f"{title} : colonnes indisponibles ({', '.join(missing)}).", icon="ℹ️")
        return False
    return True


# Les 4 configurations de train et leurs interfaces avec la structure :
#  - strait_strut            : encastrement B (3 efforts + moments)
#  - trailing_arm            : pivot B (efforts + moments) + rotule C (efforts)
#  - strait_strut_drag_brace : rotule B1 + linéaire annulaire B2 + bielle C–D
#  - trailing_arm_drag_brace : rotule F1 + linéaire annulaire F2 + bielle D–E
INTERFACE_KINDS = (
    "strait_strut", "trailing_arm",
    "strait_strut_drag_brace", "trailing_arm_drag_brace",
)


def _interface_cols(naming: str, base: str, a1: str, a2: str) -> dict:
    """Renvoie le dico logique→colonne selon le schéma de nommage.

    ``naming`` vaut ``"isolated"`` (train isolé, colonnes sans préfixe) ou
    ``"aircraft"`` (avion complet, colonnes préfixées ``base`` = "NLG",
    "MLG left", "MLG right"). ``a1``/``a2`` = noms des ancrages du drag brace
    (B1/B2 ou F1/F2)."""
    if naming == "isolated":
        return {
            "B.Fx": "Torseur@B (pivot).Effort X (N)", "B.Fz": "Torseur@B (pivot).Effort Z (N)",
            "B.Mx": "Torseur@B (pivot).Moment X (N·m)", "B.Mz": "Torseur@B (pivot).Moment Z (N·m)",
            "B.My": "Torseur@B (pivot).Moment Y (N·m)",
            "C.Fx": "Torseur@C (rotule).Effort X (N)", "C.Fz": "Torseur@C (rotule).Effort Z (N)",
            "bielle": "DragBrace.Effort bielle (N)",
            "a1.Fx": f"DragBrace.{a1} Fx (N)", "a1.Fy": f"DragBrace.{a1} Fy (N)", "a1.Fz": f"DragBrace.{a1} Fz (N)",
            "a2.Fx": f"DragBrace.{a2} Fx (N)", "a2.Fy": f"DragBrace.{a2} Fy (N)", "a2.Fz": f"DragBrace.{a2} Fz (N)",
        }
    return {
        "B.Fx": f"{base}.Torseur@B.Fx (N)", "B.Fz": f"{base}.Torseur@B.Fz (N)",
        "B.Mx": f"{base}.Torseur@B.Mx (N.m)", "B.Mz": f"{base}.Torseur@B.Mz (N.m)",
        "B.My": f"{base}.Torseur@B.My tangage (N.m)",
        "C.Fx": f"{base}.Torseur@C.Fx (N)", "C.Fz": f"{base}.Torseur@C.Fz (N)",
        "bielle": f"{base}.DragBrace.Effort bielle (N)",
        "a1.Fx": f"{base}.DragBrace.{a1} Fx (N)", "a1.Fy": f"{base}.DragBrace.{a1} Fy (N)", "a1.Fz": f"{base}.DragBrace.{a1} Fz (N)",
        "a2.Fx": f"{base}.DragBrace.{a2} Fx (N)", "a2.Fy": f"{base}.DragBrace.{a2} Fy (N)", "a2.Fz": f"{base}.DragBrace.{a2} Fz (N)",
    }


def render_interface_efforts(df, t, label, model_kind, *, naming="isolated", base="", key_prefix="") -> None:
    """Affiche, dans un seul bloc, les **efforts aux interfaces** train↔structure
    en **adaptant les points** à la configuration ``model_kind`` (cf.
    :data:`INTERFACE_KINDS`). Partagé par les trains isolés et l'avion complet."""
    is_ta = model_kind.startswith("trailing_arm")
    is_db = model_kind.endswith("drag_brace")
    a1, a2 = ("B1", "B2") if model_kind == "strait_strut_drag_brace" else ("F1", "F2")
    c = _interface_cols(naming, base, a1, a2)
    kp = key_prefix or label

    if not is_db:
        # Liaison(s) classiques : encastrement B (StraitStrut) ou pivot B (+ rotule C, TrailingArm).
        b_kind = "pivot" if is_ta else "encastrement"
        if _req(df, [c["B.Fx"], c["B.Fz"], c["B.Mx"], c["B.Mz"]], f"{label} - Liaison B"):
            moments = [("Moment Mx", df[c["B.Mx"]]), ("Moment Mz", df[c["B.Mz"]])]
            if c["B.My"] in df.columns:
                moments.insert(1, ("Moment My (tangage)", df[c["B.My"]]))
            st.plotly_chart(_gline_dual(
                t, [("Effort Fx", df[c["B.Fx"]]), ("Effort Fz", df[c["B.Fz"]])], moments,
                f"{label} — Liaison {b_kind} B : efforts (gauche) + moments (axe secondaire)",
                "Temps (s)", "Effort (N)", "Moment (N.m)",
            ), use_container_width=True, key=f"{kp}_iface_b")
        if is_ta and _req(df, [c["C.Fx"], c["C.Fz"]], f"{label} - Liaison C"):
            st.plotly_chart(_gline(
                t, [("Effort Fx", df[c["C.Fx"]]), ("Effort Fz", df[c["C.Fz"]])],
                f"{label} — Liaison rotule C : efforts (pas de moment transmis)",
                "Temps (s)", "Effort (N)",
            ), use_container_width=True, key=f"{kp}_iface_c")
        return

    # Configurations drag brace : ancrage isostatique (rotule + linéaire annulaire + bielle).
    need = [c["bielle"], c["a1.Fx"], c["a1.Fy"], c["a1.Fz"], c["a2.Fx"], c["a2.Fy"], c["a2.Fz"]]
    if not _req(df, need, f"{label} - Efforts aux interfaces"):
        return
    r1 = np.sqrt(df[c["a1.Fx"]] ** 2 + df[c["a1.Fy"]] ** 2 + df[c["a1.Fz"]] ** 2)
    r2 = np.sqrt(df[c["a2.Fx"]] ** 2 + df[c["a2.Fy"]] ** 2 + df[c["a2.Fz"]] ** 2)
    st.plotly_chart(_gline(t, [
        ("Effort bielle", df[c["bielle"]]),
        (f"|R| rotule {a1}", r1),
        (f"|R| linéaire annulaire {a2}", r2),
    ], f"{label} — Efforts aux interfaces (structure↔corps)", "Temps (s)", "Effort (N)"),
        use_container_width=True, key=f"{kp}_iface_anchor")

    # Composantes de l'effort de la bielle à son point de fixation sur la structure
    # (D pour un StraitStrut+DB, E pour un TrailingArm+DB).
    struct_pt = "D" if model_kind == "strait_strut_drag_brace" else "E"
    if naming == "isolated":
        bcx, bcy, bcz = (f"DragBrace.Bielle@{struct_pt} F{a} (N)" for a in "xyz")
    else:
        bcx, bcy, bcz = (f"{base}.DragBrace.Bielle F{a} (N)" for a in "xyz")
    if all(col in df.columns for col in (bcx, bcy, bcz)):
        st.plotly_chart(_gline(t, [
            ("Fx", df[bcx]), ("Fy", df[bcy]), ("Fz", df[bcz]),
        ], f"{label} — Bielle : composantes au point de fixation structure {struct_pt}",
           "Temps (s)", "Effort (N)", dashes=["solid", "dash", "dot"]),
           use_container_width=True, key=f"{kp}_iface_brace")

    with st.expander(f"Composantes {a1} / {a2} (repère corps) — {label}"):
        st.plotly_chart(_gline(t, [
            (f"{a1} Fx", df[c["a1.Fx"]]), (f"{a1} Fy", df[c["a1.Fy"]]), (f"{a1} Fz", df[c["a1.Fz"]]),
            (f"{a2} Fx", df[c["a2.Fx"]]), (f"{a2} Fy", df[c["a2.Fy"]]), (f"{a2} Fz", df[c["a2.Fz"]]),
        ], f"{label} — Composantes d'ancrage", "Temps (s)", "Effort (N)"),
            use_container_width=True, key=f"{kp}_iface_anchor_comp")


def render_gear_animation(result, label: str) -> None:
    """Animation 2D (vue de côté) d'un train isolé, ne traçant **que les points
    caractéristiques de la configuration active**.

    La configuration est auto-détectée depuis les colonnes de la géométrie
    enregistrée par le moteur :

    - StraitScrut (jambe droite) : B, Gt, Gb, R (+ B1/B2/C/D si drag brace) ;
    - TrailingArm (balancier)    : A, B, C, R, S ;
    - Train à lame               : B, R.

    Toutes les positions sont en mètres dans le repère sol (×1000 → mm pour le
    tracé). Le sol est fixe à z=0 ; la roue est dessinée avec un rayon « effectif »
    (= R_z − sol) qui se comprime avec la déflexion du pneu.
    """
    import plotly.graph_objects as go

    geom = getattr(result, "geometry", None)
    if geom is None or getattr(geom, "empty", True) or "temps" not in getattr(geom, "columns", []):
        st.info(
            "Animation indisponible : ce résultat ne contient pas de géométrie. "
            "Relancez la simulation du train (la géométrie est générée au calcul).",
            icon="ℹ️",
        )
        return

    cols = set(geom.columns)

    def arr(name):
        return geom[name].to_numpy(dtype=float) * 1000.0  # m → mm

    time_s = geom["temps"].to_numpy(dtype=float)
    n = len(time_s)
    if n < 2:
        st.info("Animation indisponible : géométrie trop courte.", icon="ℹ️")
        return
    stride = max(1, n // 70)
    idx = list(range(0, n, stride))
    if idx[-1] != n - 1:
        idx.append(n - 1)

    ground = arr("ground_z")
    rx, rz, wheel_r = arr("rx"), arr("rz"), arr("wheel_radius")
    bx, bz = arr("bx"), arr("bz")

    is_ss = "gtx" in cols
    is_ta = "ax" in cols
    has_db = "b1x" in cols and bool(np.any(geom["b1x"].to_numpy(dtype=float) != 0.0))

    if is_ss:
        gtx, gtz, gbx, gbz = arr("gtx"), arr("gtz"), arr("gbx"), arr("gbz")
        kind_label = "Jambe droite (StraitStrut)"
    elif is_ta:
        ax_, az_, cx_, cz_ = arr("ax"), arr("az"), arr("cx"), arr("cz")
        kind_label = "Balancier (TrailingArm)"
    else:
        kind_label = "Train à lame (leaf spring)"

    theta = np.linspace(0.0, 2.0 * np.pi, 48)
    RED, GREY, DARK, ROSE, GREEN = "#8A1A1D", "#878786", "#4A4949", "#B97677", "#1F7A3D"

    if has_db:
        b1x, b1z, b2x, b2z = arr("b1x"), arr("b1z"), arr("b2x"), arr("b2z")
        cdx, cdz, ddx, ddz = arr("cdbx"), arr("cdbz"), arr("ddbx"), arr("ddbz")

    def _wheel(i):
        return go.Scatter(
            x=rx[i] + wheel_r[i] * np.sin(theta),
            y=rz[i] + wheel_r[i] * np.cos(theta),
            mode="lines", line=dict(color=RED, width=3),
            fill="toself", fillcolor="rgba(138,26,29,0.08)", name="Roue",
        )

    def _frame_traces(i):
        traces = []
        if is_ss:
            if has_db:
                # Ancrage isostatique : pas d'encastrement B, mais B1 (rotule) + B2
                # (linéaire annulaire) + drag brace C–D. Jambe tracée le long de Gt→Gb→R.
                traces.append(go.Scatter(x=[gtx[i], gbx[i], rx[i]], y=[gtz[i], gbz[i], rz[i]],
                                         mode="lines", line=dict(color=DARK, width=4), name="Jambe"))
                traces.append(go.Scatter(
                    x=[gtx[i], gbx[i], rx[i]], y=[gtz[i], gbz[i], rz[i]],
                    mode="markers+text", text=["Gt", "Gb", "R"], textposition="top center",
                    marker=dict(size=8, color=RED), name="Points"))
                traces.append(go.Scatter(x=[cdx[i], ddx[i]], y=[cdz[i], ddz[i]], mode="lines",
                                         line=dict(color=GREEN, width=4), name="Drag brace"))
                traces.append(go.Scatter(x=[b1x[i], b2x[i]], y=[b1z[i], b2z[i]], mode="lines",
                                         line=dict(color=GREEN, width=2, dash="dot"), name="Trunnion B1-B2"))
                traces.append(go.Scatter(
                    x=[b1x[i], b2x[i], cdx[i], ddx[i]], y=[b1z[i], b2z[i], cdz[i], ddz[i]],
                    mode="markers+text", text=["B1", "B2", "C", "D"], textposition="bottom center",
                    marker=dict(size=8, color=GREEN), name="Points drag brace"))
            else:
                traces.append(go.Scatter(x=[bx[i], rx[i]], y=[bz[i], rz[i]], mode="lines",
                                         line=dict(color=DARK, width=4), name="Jambe"))
                traces.append(go.Scatter(x=[gtx[i], gbx[i]], y=[gtz[i], gbz[i]], mode="lines",
                                         line=dict(color=ROSE, width=3, dash="dot"), name="Guidage"))
                traces.append(go.Scatter(
                    x=[bx[i], gtx[i], gbx[i], rx[i]], y=[bz[i], gtz[i], gbz[i], rz[i]],
                    mode="markers+text", text=["B", "Gt", "Gb", "R"], textposition="top center",
                    marker=dict(size=8, color=RED), name="Points"))
        elif is_ta:
            traces.append(go.Scatter(x=[ax_[i], bx[i], rx[i]], y=[az_[i], bz[i], rz[i]], mode="lines",
                                     line=dict(color=DARK, width=4), name="Balancier"))
            traces.append(go.Scatter(x=[cx_[i], ax_[i]], y=[cz_[i], az_[i]], mode="lines",
                                     line=dict(color=GREY, width=4), name="Amortisseur"))
            traces.append(go.Scatter(
                x=[ax_[i], bx[i], cx_[i], rx[i], rx[i]], y=[az_[i], bz[i], cz_[i], rz[i], ground[i]],
                mode="markers+text", text=["A", "B", "C", "R", "S"], textposition="top center",
                marker=dict(size=8, color=RED), name="Points"))
        else:
            traces.append(go.Scatter(x=[bx[i], rx[i]], y=[bz[i], rz[i]], mode="lines",
                                     line=dict(color=DARK, width=4), name="Lame"))
            traces.append(go.Scatter(x=[bx[i], rx[i]], y=[bz[i], rz[i]],
                                     mode="markers+text", text=["B", "R"], textposition="top center",
                                     marker=dict(size=8, color=RED), name="Points"))
        traces.append(_wheel(i))
        return traces

    xs = [rx - wheel_r, rx + wheel_r]
    zs = [rz + wheel_r, ground]
    if not (is_ss and has_db):  # B n'est pas tracé en config drag brace
        xs.append(bx)
        zs.append(bz)
    if is_ss:
        xs += [gtx, gbx]
        zs += [gtz, gbz]
        if has_db:
            xs += [b1x, b2x, cdx, ddx]
            zs += [b1z, b2z, cdz, ddz]
    elif is_ta:
        xs += [ax_, cx_]
        zs += [az_, cz_]
    allx = np.concatenate(xs)
    allz = np.concatenate(zs)
    xmin, xmax = float(allx.min()) - 120.0, float(allx.max()) + 120.0
    zmin = float(min(float(allz.min()), float(ground.min()))) - 60.0
    zmax = float(allz.max()) + 120.0

    ground_line = go.Scatter(x=[xmin, xmax], y=[float(ground[0]), float(ground[0])],
                             mode="lines", line=dict(color="#929292", width=2), name="Sol")

    frame_ms = max(1, int(round(float(np.mean(np.diff(time_s[idx])) * 1000.0))))

    def _anim_args(speed):
        return [None, dict(frame=dict(duration=max(1, int(round(frame_ms / speed))), redraw=True),
                           fromcurrent=True, transition=dict(duration=0))]

    fig = go.Figure(
        data=[ground_line] + _frame_traces(0),
        frames=[go.Frame(data=[ground_line] + _frame_traces(i), name=f"{time_s[i]*1000:.0f}") for i in idx],
    )
    fig.update_layout(
        height=560,
        xaxis=dict(title="X (mm)", range=[xmin, xmax], constrain="domain", showgrid=True, gridcolor="#E6E6E6"),
        yaxis=dict(title="Z (mm)", range=[zmin, zmax], scaleanchor="x", scaleratio=1.0, showgrid=True, gridcolor="#E6E6E6"),
        margin=dict(l=8, r=8, t=30, b=140),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        updatemenus=[dict(
            type="buttons", showactive=False, x=0.0, y=0.02, xanchor="left", direction="left",
            buttons=[
                dict(label="▶ 1x", method="animate", args=_anim_args(1.0)),
                dict(label="▶ 0.5x", method="animate", args=_anim_args(0.5)),
                dict(label="▶ 0.25x", method="animate", args=_anim_args(0.25)),
                dict(label="⏸ Pause", method="animate", args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")]),
            ],
        )],
        sliders=[dict(
            active=0, x=0.0, len=1.0, y=-0.08, currentvalue=dict(prefix="t = ", suffix=" ms"),
            steps=[dict(
                method="animate", label=f"{time_s[i]*1000:.0f}",
                args=[[f"{time_s[i]*1000:.0f}"], dict(mode="immediate", frame=dict(duration=0, redraw=True), transition=dict(duration=0))],
            ) for i in idx],
        )],
    )
    st.caption(
        f"Vue de côté — **{kind_label}**. Seuls les points caractéristiques de la "
        "configuration active sont tracés. Le sol est fixe ; la roue se comprime avec la déflexion."
    )
    st.plotly_chart(fig, use_container_width=True, key=f"{label}_gear_anim")


def render_full_gear_result(result, label: str) -> None:
    """Affiche le jeu complet de courbes d'un train isolé — mêmes onglets que les
    sections NLG/MLG de la page Résultats avion (efforts, pressions, hydraulique,
    course/déflexion, accél./vitesse, liaisons) **plus** le bilan énergétique.

    Auto-détecte le type de train (StraitStrut / TrailingArm) d'après les colonnes.
    """
    df = result.df
    cols = list(df.columns)
    t = df["Temps (s)"] if "Temps (s)" in cols else df[cols[0]]
    _is_leaf = any(c.startswith("LeafSpring.") for c in cols)
    if _is_leaf:
        p = "LeafSpring"
    elif any(c.startswith("StraitStrut.") for c in cols):
        p = "StraitStrut"
    else:
        p = "TrailingArm"
    is_ta = p == "TrailingArm"

    m1, m2, m3 = st.columns(3)
    m1.metric("Pas de temps", f"{len(df)}")
    if f"{p}.Ftot (N)" in cols:
        _flbl = "Effort lame max" if _is_leaf else "Effort amortisseur max"
        m2.metric(_flbl, f"{float(np.max(np.abs(df[f'{p}.Ftot (N)']))):.0f} N")
    if "Tyre.FTyre (N)" in cols:
        m3.metric("Fz pneu max", f"{float(np.max(np.abs(df['Tyre.FTyre (N)']))):.0f} N")

    # Les colonnes DragBrace existent toujours ; le drag brace est *actif* seulement
    # si l'effort de bielle est non nul (sinon config de base, ancrage simple en B).
    _bielle = "DragBrace.Effort bielle (N)"
    _has_db = _bielle in cols and float(np.abs(df[_bielle].to_numpy()).sum()) > 0.0
    if _is_leaf:
        _model_kind = "leaf_spring"
    elif is_ta:
        _model_kind = "trailing_arm_drag_brace" if _has_db else "trailing_arm"
    else:
        _model_kind = "strait_strut_drag_brace" if _has_db else "strait_strut"
    _labels = [
        "Animation", "Efforts (temps)", "Effort / course", "Pressions", "Conv. hydraulique",
        "Course & déflexion", "Ratio cinématique", "Accél. & vitesse", "Efforts aux interfaces",
        "Bilan énergétique", "Décomposition amortisseur",
    ]
    tabs = st.tabs(_labels)

    with tabs[0]:
        render_gear_animation(result, label)

    with tabs[1]:
        if _req(df, ["Tyre.FTyre (N)", "Reaction sol horizontale (N)", f"{p}.Ftot (N)"], f"{label} - Efforts"):
            st.plotly_chart(_gline(t, [
                ("Fz (pneu/sol)", df["Tyre.FTyre (N)"]),
                ("Fx (horizontal)", df["Reaction sol horizontale (N)"]),
                ("Effort amortisseur", df[f"{p}.Ftot (N)"]),
            ], f"{label} - Efforts en fonction du temps", "Temps (s)", "Effort (N)"), use_container_width=True)

    with tabs[2]:
        if _req(df, [f"{p}.d (m)", "Tyre.FTyre (N)", "Reaction sol horizontale (N)"], f"{label} - Effort/course"):
            st.plotly_chart(_gline(df[f"{p}.d (m)"] * 1000.0, [
                ("Fz (pneu/sol)", df["Tyre.FTyre (N)"]),
                ("Fx (horizontal)", df["Reaction sol horizontale (N)"]),
            ], f"{label} - Effort en fonction de la course", "Course amortisseur (mm)", "Effort (N)"), use_container_width=True)

    with tabs[3]:
        if _is_leaf:
            st.info("Modèle Train à lame : pas d'hydraulique ni de gaz, donc pas de pressions.", icon="ℹ️")
        else:
            pcols = [f"{p}.Pc (bar)", f"{p}.Pg (bar)", f"{p}.Pd (bar)", f"{p}.DeltaPc (bar)", f"{p}.DeltaPd (bar)"]
            if _req(df, pcols, f"{label} - Pressions"):
                st.plotly_chart(_gline(t, [
                    ("Pc", df[f"{p}.Pc (bar)"]), ("Pg", df[f"{p}.Pg (bar)"]), ("Pd", df[f"{p}.Pd (bar)"]),
                    ("DeltaPc", df[f"{p}.DeltaPc (bar)"]), ("DeltaPd", df[f"{p}.DeltaPd (bar)"]),
                ], f"{label} - Pressions en fonction du temps", "Temps (s)", "Pression (bar)"), use_container_width=True)

    with tabs[4]:
        if _is_leaf:
            st.info("Modèle Train à lame : pas de boucle hydraulique à converger.", icon="ℹ️")
        elif _req(df, ["Hydrau.Erreur convergence (-)", "Hydrau.Itérations convergence (-)"], f"{label} - Conv. hydraulique"):
            st.plotly_chart(_gline_dual(
                t,
                [("Erreur convergence", df["Hydrau.Erreur convergence (-)"])],
                [("Itérations", df["Hydrau.Itérations convergence (-)"])],
                f"{label} - Convergence hydraulique",
                "Temps (s)", "Erreur convergence (-)", "Itérations (-)",
            ), use_container_width=True)

    with tabs[5]:
        if _req(df, [f"{p}.d (m)", "Tyre.Defl (m)"], f"{label} - Course/déflexion"):
            _cd_series = [
                ("Course amortisseur (mm)", df[f"{p}.d (m)"] * 1000.0),
                ("Déflexion pneu (mm)", df["Tyre.Defl (m)"] * 1000.0),
            ]
            # Déplacement vertical du centre roue (TrailingArm) : variation de la
            # position verticale de R par rapport au pivot B (masse suspendue).
            _croue = "Course centre roue (m)"
            if is_ta and _croue in cols:
                _cr = df[_croue]
                _cd_series.append(
                    ("Déplacement vertical centre roue (mm)", (_cr - _cr.iloc[0]) * 1000.0)
                )
            st.plotly_chart(_gline(
                t, _cd_series,
                f"{label} - Course et déflexion", "Temps (s)", "Déplacement (mm)",
            ), use_container_width=True)
            if is_ta and _croue in cols:
                st.caption(
                    "Déplacement vertical centre roue = variation de la hauteur du centre "
                    "roue (R) par rapport au pivot B (masse suspendue), depuis l'instant initial."
                )

    with tabs[6]:
        # Ratio cinématique cumulé = course amortisseur / variation de la position
        # verticale du centre roue (R) par rapport au pivot de la masse suspendue (B).
        _geom = getattr(result, "geometry", None)
        if _is_leaf:
            st.info("Modèle Train à lame : pas d'amortisseur, ratio cinématique non défini.", icon="ℹ️")
        elif (_geom is None or getattr(_geom, "empty", True)
              or not {"rz", "bz", "temps"}.issubset(set(getattr(_geom, "columns", [])))):
            st.info(
                f"{label} - Ratio cinématique : géométrie (centre roue/pivot) indisponible. "
                "Relancez la simulation du train (la géométrie est générée au calcul).",
                icon="ℹ️",
            )
        elif _req(df, [f"{p}.d (m)"], f"{label} - Ratio cinématique"):
            course_mm = (df[f"{p}.d (m)"] * 1000.0).to_numpy(dtype=float)
            # Centre roue R relatif au pivot masse suspendue B (composante verticale), en mm.
            wheel_rel = (_geom["rz"].to_numpy(dtype=float) - _geom["bz"].to_numpy(dtype=float)) * 1000.0
            if len(wheel_rel) != len(course_mm):  # ré-échantillonnage éventuel : aligner sur la base temps
                wheel_rel = np.interp(
                    t.to_numpy(dtype=float), _geom["temps"].to_numpy(dtype=float), wheel_rel)
            delta_wheel = wheel_rel - wheel_rel[0]  # mm : débattement vertical roue / masse susp.
            # Masque l'origine (course ≈ 0 et Δ ≈ 0 → ratio 0/0) pour éviter les pics.
            eps = max(0.2, 0.02 * float(np.max(np.abs(delta_wheel)))) if delta_wheel.size else 0.2
            mask = np.abs(delta_wheel) >= eps
            if not np.any(mask):
                st.info(
                    f"{label} - Ratio cinématique : débattement trop faible pour un ratio significatif.",
                    icon="ℹ️",
                )
            else:
                ratio = course_mm[mask] / delta_wheel[mask]
                st.plotly_chart(_gline(
                    course_mm[mask],
                    [("Ratio cinématique (course / débattement)", ratio)],
                    f"{label} - Ratio cinématique",
                    "Course amortisseur (mm)", "Ratio course / débattement roue (-)",
                ), use_container_width=True)
                st.caption(
                    "Ratio **cumulé** = course amortisseur ÷ variation de la position verticale du "
                    "centre roue (R) par rapport au pivot de la masse suspendue (B), depuis l'instant "
                    "initial. Abscisse : course amortisseur."
                )

    with tabs[7]:
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

    with tabs[8]:
        render_interface_efforts(df, t, label, _model_kind, naming="isolated", key_prefix=label)

    with tabs[9]:
        _render_energy_balance(df, label)

    with tabs[10]:
        # Décompose l'effort total amortisseur : hydraulique + pneumatique (ressort
        # gazeux) + friction(s). Le Train à lame n'a pas de telle décomposition.
        if _is_leaf:
            st.info(
                "Modèle Train à lame : effort de lame (ressort + amortissement), "
                "sans décomposition hydraulique / pneumatique / friction.",
                icon="ℹ️",
            )
        elif _req(df, [f"{p}.Ftot (N)", f"{p}.Fhyd (N)", f"{p}.FGas (N)", f"{p}.FFriJoi (N)"],
                  f"{label} - Décomposition amortisseur"):
            series = [
                ("Effort total (Ftot)", df[f"{p}.Ftot (N)"]),
                ("Hydraulique (Fhyd)", df[f"{p}.Fhyd (N)"]),
                ("Pneumatique / ressort gaz (FGas)", df[f"{p}.FGas (N)"]),
                ("Friction joints (FFriJoi)", df[f"{p}.FFriJoi (N)"]),
            ]
            _bague = f"{p}.FFriBag (N)"  # friction de bague (StraitStrut uniquement)
            if _bague in cols:
                series.append(("Friction bague (FFriBag)", df[_bague]))
            st.plotly_chart(_gline(
                t, series,
                f"{label} - Décomposition de l'effort amortisseur",
                "Temps (s)", "Effort (N)",
            ), use_container_width=True)
            st.caption(
                "Effort total amortisseur = effort **hydraulique** + effort **pneumatique** "
                "(ressort gazeux) + efforts de **friction** (joints"
                + (" + bague" if _bague in cols else "") + ")."
            )

        # Efforts transverses aux bagues de guidage (StraitStrut uniquement) :
        # ce sont eux qui pilotent la friction de bague FFriBag.
        _xgt, _xgb = f"{p}.XGt (N)", f"{p}.XGb (N)"
        if not _is_leaf and _xgt in cols and _xgb in cols:
            st.markdown("**Efforts transverses aux bagues de guidage**")
            st.plotly_chart(_gline(
                t, [
                    ("Bague haute Gt (XGt)", df[_xgt]),
                    ("Bague basse Gb (XGb)", df[_xgb]),
                ],
                f"{label} - Efforts transverses aux bagues (Gt, Gb)",
                "Temps (s)", "Effort transverse (N)",
            ), use_container_width=True)
            st.caption(
                "XGt / XGb : réactions transverses (⊥ à l'axe de coulisse Gt-Gb) aux bagues "
                "haute (Gt, sur la tige) et basse (Gb, sur le fût), équilibre 2D de la tige "
                "avec décalage du centre roue R. Ces efforts pilotent la friction de bague FFriBag."
            )

        # Pressions de contact et coefficient de friction de bague (modèle DP4).
        _pgt, _pgb = f"{p}.PcontactGt (MPa)", f"{p}.PcontactGb (MPa)"
        _mugt, _mugb = f"{p}.MuGt (-)", f"{p}.MuGb (-)"
        if not _is_leaf and _pgt in cols and _pgb in cols:
            st.markdown("**Pressions de contact aux bagues**")
            st.plotly_chart(_gline(
                t, [
                    ("Bague haute Gt (MPa)", df[_pgt]),
                    ("Bague basse Gb (MPa)", df[_pgb]),
                ],
                f"{label} - Pression de contact aux bagues",
                "Temps (s)", "Pression de contact (MPa)",
            ), use_container_width=True)

        if not _is_leaf and _mugt in cols and _mugb in cols:
            st.markdown("**Coefficient de friction de bague — modèle DP4**")
            st.caption(
                "μ effectivement appliqué par la simulation (modèle DP4 : décroissance "
                "exponentielle en pression + montée asymptotique en vitesse). Les "
                "coefficients DP4 se règlent dans la **page de saisie** de la configuration "
                "(section « Friction de bague (DP4) »)."
            )
            st.plotly_chart(_gline(
                t, [
                    ("μ bague haute Gt", df[_mugt]),
                    ("μ bague basse Gb", df[_mugb]),
                ],
                f"{label} - Coefficient de friction de bague (DP4)",
                "Temps (s)", "Coefficient de friction μ (-)",
            ), use_container_width=True)

    if getattr(result, "warnings", None):
        with st.expander(f"⚠️ {len(result.warnings)} avertissement(s) — {label}"):
            for w in result.warnings:
                st.warning(str(w))
