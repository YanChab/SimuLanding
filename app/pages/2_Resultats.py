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
_APP = Path(__file__).resolve().parent.parent
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

from dropsim.engine import OUTPUT_COLUMNS  # noqa: E402
from dropsim.geometry import deter_pos_bal_a, deter_pos_bal_r, rotate_about  # noqa: E402
from dropsim import (  # noqa: E402
    save_simulation,
    load_simulation,
    list_saved,
    list_projects,
    delete_saved,
    DEFAULT_PROJECT,
)
from theme import apply_theme  # noqa: E402

apply_theme()

st.title("📈 Résultats de la simulation")

# Hauteur fixe (en pixels) allouée à chaque graphe : fiable avec Streamlit/Plotly.
GRAPH_HEIGHT = 640

result = st.session_state.get("result")

# --------------------------------------------------------------------------- #
#  Sauvegarde / chargement des simulations
# --------------------------------------------------------------------------- #
with st.expander("💾 Sauvegarder / charger une simulation", expanded=result is None):
    _NEW_PROJECT = "➕ Nouveau projet…"
    existing_projects = list_projects()

    col_save, col_load = st.columns(2)

    with col_save:
        st.markdown("**Sauvegarder la simulation courante**")
        if result is None:
            st.caption("Aucun résultat à sauvegarder pour l'instant.")
        else:
            # Choix du projet : un projet existant ou un nouveau.
            cur_proj = st.session_state.get("current_project", DEFAULT_PROJECT)
            proj_options = existing_projects + [_NEW_PROJECT]
            if cur_proj in existing_projects:
                proj_index = existing_projects.index(cur_proj)
            else:
                proj_index = len(proj_options) - 1  # "Nouveau projet…"
            proj_choice = st.selectbox(
                "Projet", proj_options, index=proj_index, key="save_project_choice"
            )
            if proj_choice == _NEW_PROJECT:
                project = st.text_input(
                    "Nom du nouveau projet",
                    value="" if cur_proj in existing_projects else cur_proj,
                    key="save_project_new",
                    placeholder=DEFAULT_PROJECT,
                ).strip() or DEFAULT_PROJECT
            else:
                project = proj_choice

            default_name = st.session_state.get(
                "result_name", f"Simulation {len(list_saved(project=project)) + 1}"
            )
            save_name = st.text_input(
                "Nom de la sauvegarde", value=default_name, key="save_name_input"
            )
            if st.button("💾 Enregistrer", width="stretch"):
                inputs = st.session_state.get("inputs")
                if inputs is None:
                    st.error("Entrées introuvables — relancez le calcul.")
                else:
                    path = save_simulation(
                        inputs, result, name=save_name, project=project
                    )
                    st.session_state.result_name = save_name
                    st.session_state.current_project = project
                    st.success(
                        f"Sauvegardé dans « {project} » : {path.name}", icon="✅"
                    )

    with col_load:
        st.markdown("**Charger une simulation enregistrée**")
        if not existing_projects:
            st.caption("Aucune simulation enregistrée.")
        else:
            sel_proj = st.session_state.get("current_project", existing_projects[0])
            load_proj_index = (
                existing_projects.index(sel_proj)
                if sel_proj in existing_projects
                else 0
            )
            load_project = st.selectbox(
                "Projet", existing_projects, index=load_proj_index, key="load_project"
            )
            saved = list_saved(project=load_project)
            if not saved:
                st.caption("Aucune simulation dans ce projet.")
            else:
                labels = {
                    f"{e['name']}  ·  {e['saved_at'][:16].replace('T', ' ')}": e["path"]
                    for e in saved
                }
                choice = st.selectbox(
                    "Sauvegardes disponibles", list(labels.keys()), key="load_choice"
                )
                c_load, c_del = st.columns(2)
                if c_load.button("📂 Charger", width="stretch"):
                    inputs, loaded, meta = load_simulation(labels[choice])
                    st.session_state.inputs = inputs
                    st.session_state.result = loaded
                    st.session_state.result_name = meta["name"]
                    st.session_state.current_project = meta.get(
                        "project", DEFAULT_PROJECT
                    )
                    st.rerun()
                if c_del.button("🗑️ Supprimer", width="stretch"):
                    delete_saved(labels[choice])
                    st.rerun()

if result is None:
    st.info(
        "Aucun résultat disponible. Renseignez les données dans la page **Saisie** "
        "puis lancez le calcul, ou chargez une simulation enregistrée ci-dessus.",
        icon="ℹ️",
    )
    st.stop()

df = result.df
COL = OUTPUT_COLUMNS  # clé interne -> libellé de colonne

# Colonne « course » exprimée en mm pour l'affichage.
course_mm = df[COL["trailing_arm_d"]] * 1000.0


def _compute_kinematic_curve(inputs, n_pts: int = 401) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """Calcule la cinématique pure (indépendante du drop test) sur toute la course.

    Retourne ``(course_amort_mm, course_roue_mm, ratio)`` où :
    - ``course_amort_mm`` est la course amortisseur imposée sur [0, course],
    - ``course_roue_mm`` est le déplacement vertical du centre roue (Rz - Rz0),
    - ``ratio`` = d(course_amortisseur) / d(course_roue).
    """
    if inputs is None:
        return None

    p = inputs.to_si()

    A = p.A.astype(float).copy()
    B = p.B.astype(float).copy()
    C = p.C.astype(float).copy()
    R = p.R.astype(float).copy()

    # Même traitement d'attitude que dans le moteur pour garder une cohérence géométrique.
    S = R.copy()
    S[2] = R[2] - p.unload_radius
    A = rotate_about(A, S, p.pitch, p.roll)
    B = rotate_about(B, S, p.pitch, p.roll)
    C = rotate_about(C, S, p.pitch, p.roll)
    R = rotate_about(R, S, p.pitch, p.roll)

    entraxe_init = float(np.linalg.norm(C - A))
    lg_ab = float(np.hypot(B[0] - A[0], B[2] - A[2]))
    lg_rb = float(np.hypot(B[0] - R[0], B[2] - R[2]))
    lg_ra = float(np.hypot(A[0] - R[0], A[2] - R[2]))
    dy_ca = float(C[1] - A[1])

    # Domaine réellement calculable géométriquement.
    d_max_geom = max(0.0, min(float(p.course), entraxe_init - abs(dy_ca) - 1.0e-9))
    if d_max_geom <= 0.0:
        return None

    d_vals = np.linspace(0.0, d_max_geom, n_pts)
    rz_vals = np.zeros_like(d_vals)
    rz0 = float(R[2])

    # Continuité numérique : on réutilise A/R du point précédent comme amorce Newton.
    A_cur = A.copy()
    R_cur = R.copy()
    for i, d in enumerate(d_vals):
        entraxe = entraxe_init - float(d)
        deter_pos_bal_a(A_cur, B, C, entraxe, lg_ab)
        deter_pos_bal_r(R_cur, A_cur, B, lg_ra, lg_rb)
        rz_vals[i] = R_cur[2]

    course_amort_mm = d_vals * 1000.0
    course_roue_mm = (rz_vals - rz0) * 1000.0

    d_course_amort = np.gradient(course_amort_mm)
    d_course_roue = np.gradient(course_roue_mm)
    ratio = np.divide(
        d_course_amort,
        d_course_roue,
        out=np.full_like(d_course_roue, np.nan),
        where=np.abs(d_course_roue) > 1.0e-12,
    )
    return course_amort_mm, course_roue_mm, ratio


# --------------------------------------------------------------------------- #
#  Synthèse + graphes (côte à côte)
# --------------------------------------------------------------------------- #
col_summary, _col_spacer, col_graphs = st.columns([1, 0.1, 2], gap="large")

with col_summary:
    st.subheader("Synthèse")
    rows = getattr(result, "summary_rows", None)
    if rows:
        import pandas as pd

        summary_df = pd.DataFrame(
            [
                {
                    "Paramètre": f"{lbl} ({unit})" if unit and unit != "-" else lbl,
                    "Valeur": val,
                }
                for lbl, val, unit in rows
            ]
        )
        st.dataframe(
            summary_df,
            column_config={
                "Paramètre": st.column_config.TextColumn("Paramètre"),
                "Valeur": st.column_config.NumberColumn("Valeur", format="%.4g", alignment="right"),
            },
            hide_index=True,
            width="stretch",
            height=38 + 35 * len(rows),
        )
    else:
        s = result.summary
        m = st.columns(2)
        m[0].metric("Course max", f"{s['Course max (mm)']:.2f} mm")
        m[1].metric("Effort vertical max Fz", f"{s['Effort vertical max Fz (N)']:.0f} N")
        m[0].metric("Effort horizontal max Fx", f"{s['Effort horizontal max Fx (N)']:.0f} N")
        m[1].metric("Effort amortisseur max", f"{s['Effort amortisseur max (N)']:.0f} N")


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
        title=dict(text=title, y=0.98, yanchor="top"),
        margin=dict(l=10, r=10, t=80, b=55),
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0),
        height=GRAPH_HEIGHT,
    )
    _apply_graph_paper(fig, xlab, ylab)
    return fig


t = df[COL["temps"]]

# Persistance inter-pages de la configuration du graphe personnalisé.
PERSO_CFG_KEY = "results_custom_plot_cfg"


def _sanitize_perso_cfg(cfg: dict, options: list[str], none_label: str) -> dict:
    """Nettoie une configuration personnalisée en fonction des colonnes disponibles."""
    x_default = options[0]
    y_default = COL["tyre_ftyre"] if COL["tyre_ftyre"] in options else options[1]

    x_label = cfg.get("x", x_default)
    if x_label not in options:
        x_label = x_default

    curves = cfg.get("curves", [])
    clean_curves: list[dict[str, object]] = []
    for i in range(5):
        item = curves[i] if i < len(curves) else {}
        label = item.get("label", y_default if i == 0 else none_label)
        if i == 0 and label == none_label:
            label = y_default
        allowed = options if i == 0 else [none_label] + options
        if label not in allowed:
            label = y_default if i == 0 else none_label
        clean_curves.append({"label": label, "right": bool(item.get("right", False))})

    return {"x": x_label, "curves": clean_curves}

# --------------------------------------------------------------------------- #
#  Courbes — un seul graphe par onglet
# --------------------------------------------------------------------------- #
with col_graphs:
    tab_eff_t, tab_eff_c, tab_press, tab_conv, tab_cine, tab_ratio, tab_acc, tab_torseur, tab_energie, tab_perso, tab_anim = st.tabs(
        [
            "Efforts (temps)",
            "Effort / course",
            "Pressions",
            "Conv. hydraulique",
            "Course & déflexion",
            "Ratio cinématique",
            "Accél. & vitesse",
            "Torseur B & C",
            "Bilan énergétique",
            "Personnalisé",
            "Animation",
        ]
    )

with tab_eff_t:
    st.plotly_chart(
        line(
            t,
            [
                ("Fz (pneu/sol)", df[COL["tyre_ftyre"]]),
                ("Fx (horizontal)", df[COL["tr_x"]]),
                ("Effort amortisseur", df[COL["trailing_arm_ftot"]]),
            ],
            "Efforts en fonction du temps",
            "Temps (s)",
            "Effort (N)",
        ),
        width="stretch",
        config={"responsive": True},
    )

with tab_eff_c:
    st.plotly_chart(
        line(
            course_mm,
            [
                ("Fz (pneu/sol)", df[COL["tyre_ftyre"]]),
                ("Fx (horizontal)", df[COL["tr_x"]]),
            ],
            "Effort en fonction de la course",
            "Course amortisseur (mm)",
            "Effort (N)",
        ),
        width="stretch",
        config={"responsive": True},
    )

with tab_press:
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
        width="stretch",
        config={"responsive": True},
    )

with tab_conv:
    conv_keys = ["hyd_conv_err", "hyd_conv_iter"]
    missing_cols = [COL[k] for k in conv_keys if COL[k] not in df.columns]

    if missing_cols:
        st.info(
            "Données de convergence hydraulique indisponibles pour ce résultat "
            "(simulation sauvegardée avec une ancienne version du modèle). "
            "Relancez un calcul pour afficher cet onglet."
        )
    else:
        conv_err = df[COL["hyd_conv_err"]]
        conv_iter = df[COL["hyd_conv_iter"]]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Erreur moyenne", f"{float(np.mean(conv_err)):.3e}")
        c2.metric("Erreur max", f"{float(np.max(conv_err)):.3e}")
        c3.metric("Itérations moyennes", f"{float(np.mean(conv_iter)):.2f}")
        c4.metric("Itérations max", f"{float(np.max(conv_iter)):.0f}")

        fig_conv = go.Figure()
        fig_conv.add_trace(
            go.Scatter(
                x=t,
                y=conv_iter,
                mode="lines",
                name="Itérations",
                yaxis="y",
            )
        )
        fig_conv.add_trace(
            go.Scatter(
                x=t,
                y=conv_err,
                mode="lines",
                name="Erreur de convergence",
                yaxis="y2",
            )
        )
        fig_conv.update_layout(
            title=dict(text="Convergence hydraulique au cours du temps", y=0.98, yanchor="top"),
            margin=dict(l=10, r=10, t=80, b=55),
            legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0),
            height=GRAPH_HEIGHT,
            plot_bgcolor=GRAPH_PAPER_BG,
            paper_bgcolor="white",
            xaxis=_grid_axis("Temps (s)"),
            yaxis=_grid_axis("Itérations (-)"),
            yaxis2={
                **_grid_axis("Erreur (-)"),
                "overlaying": "y",
                "side": "right",
                "showgrid": False,
                "zeroline": False,
                "minor": {"showgrid": False},
            },
        )

        st.plotly_chart(
            fig_conv,
            width="stretch",
            config={"responsive": True},
        )

with tab_cine:
    st.plotly_chart(
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
        width="stretch",
        config={"responsive": True},
    )

with tab_ratio:
    inputs_for_kin = st.session_state.get("inputs")
    kin_curve = _compute_kinematic_curve(inputs_for_kin)

    if kin_curve is None:
        st.info(
            "Données de ratio cinématique indisponibles pour ce résultat "
            "(entrées introuvables ou géométrie hors domaine). "
            "Chargez/relancez une simulation pour afficher cet onglet."
        )
    else:
        course_amort_mm, course_roue_mm, kin_ratio = kin_curve
        finite_ratio = kin_ratio[np.isfinite(kin_ratio)]
        c1, c2, c3 = st.columns(3)
        c1.metric("Ratio moyen", f"{float(np.mean(finite_ratio)):.3f}")
        c2.metric("Ratio max", f"{float(np.max(finite_ratio)):.3f}")
        c3.metric("Ratio min", f"{float(np.min(finite_ratio)):.3f}")

        fig_ratio = go.Figure()
        fig_ratio.add_trace(
            go.Scatter(
                x=course_amort_mm,
                y=kin_ratio,
                mode="lines",
                name="Ratio cinématique (course amortisseur / course roue)",
                yaxis="y",
            )
        )
        fig_ratio.add_trace(
            go.Scatter(
                x=course_amort_mm,
                y=course_roue_mm,
                mode="lines",
                name="Course roue",
                yaxis="y2",
            )
        )
        fig_ratio.update_layout(
            title=dict(
                text="Ratio cinématique et course roue en fonction de la course amortisseur",
                y=0.98,
                yanchor="top",
            ),
            margin=dict(l=10, r=10, t=80, b=55),
            legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0),
            height=GRAPH_HEIGHT,
            plot_bgcolor=GRAPH_PAPER_BG,
            paper_bgcolor="white",
            xaxis=_grid_axis("Course amortisseur (mm)"),
            yaxis=_grid_axis("Ratio cinématique (-)"),
            yaxis2={
                **_grid_axis("Course roue (mm)"),
                "overlaying": "y",
                "side": "right",
                "showgrid": False,
                "zeroline": False,
                "minor": {"showgrid": False},
            },
        )

        st.plotly_chart(
            fig_ratio,
            width="stretch",
            config={"responsive": True},
        )

with tab_acc:
    st.plotly_chart(
        line(
            t,
            [
                ("Accélération masse susp. (g)", df[COL["accms"]] / 9.81),
                ("Vitesse amortisseur (m/s)", df[COL["trailing_arm_v"]]),
            ],
            "Accélération et vitesse en fonction du temps",
            "Temps (s)",
            "g  /  m·s⁻¹",
        ),
        width="stretch",
        config={"responsive": True},
    )

with tab_torseur:
    st.caption(
        "Torseur d'effort transmis par le train à la masse suspendue via ses "
        "deux attaches : **C** (tête d'amortisseur) est une **rotule** — elle ne "
        "transmet qu'un **effort**, sans moment ; **B** (pivot du balancier) est "
        "un **pivot d'axe Y** — il reprend l'**effort** et les **moments autour "
        "de X et Z** (l'axe Y étant libre en rotation, aucun moment n'y est "
        "transmis). La résultante (somme des deux efforts) est égale à la "
        "réaction sol."
    )

    torseur_keys = [
        "tors_res_norm",
        "torsC_fx",
        "torsC_fz",
        "torsB_fx",
        "torsB_fz",
        "torsB_mx",
        "torsB_mz",
    ]
    missing_cols = [COL[k] for k in torseur_keys if COL[k] not in df.columns]

    if missing_cols:
        st.info(
            "Données torseur indisponibles pour ce résultat (simulation sauvegardée "
            "avec une ancienne version du modèle). Relancez un calcul pour afficher "
            "cet onglet."
        )
    else:
        def _amax(key: str) -> float:
            return float(np.abs(df[COL[key]]).max())

        m1, m2 = st.columns(2)
        m1.metric("‖Résultante‖ max", f"{_amax('tors_res_norm'):.0f} N")
        m2.metric("|Moment au pivot B| max", f"{max(_amax('torsB_mx'), _amax('torsB_mz')):.0f} N·m")

        st.plotly_chart(
            line(
                t,
                [
                    ("Effort rotule C — X", df[COL["torsC_fx"]]),
                    ("Effort rotule C — Z", df[COL["torsC_fz"]]),
                    ("Effort pivot B — X", df[COL["torsB_fx"]]),
                    ("Effort pivot B — Z", df[COL["torsB_fz"]]),
                ],
                "Efforts de liaison aux attaches C (rotule) et B (pivot)",
                "Temps (s)",
                "Effort (N)",
            ),
            width="stretch",
            config={"responsive": True},
        )
        st.plotly_chart(
            line(
                t,
                [
                    ("Moment X au pivot B", df[COL["torsB_mx"]]),
                    ("Moment Z au pivot B", df[COL["torsB_mz"]]),
                ],
                "Moments de liaison (axes X et Z) repris par le pivot B",
                "Temps (s)",
                "Moment (N·m)",
            ),
            width="stretch",
            config={"responsive": True},
        )

with tab_energie:
    st.caption(
        "Bilan énergétique **diagnostic** : suit la transformation de l'énergie "
        "cinétique d'impact (augmentée du travail de la gravité et de l'énergie "
        "puisée dans l'avancement lors du spin-up de la roue) en énergie "
        "**stockée** (gaz, butée, pneu) et **dissipée** (hydraulique, friction "
        "joint, amortisseur horizontal, glissement pneu/sol). Tous les chemins "
        "énergétiques étant comptabilisés, le **résidu** = apport − (cinétique "
        "courante + stockée + dissipée) se réduit à la seule erreur "
        "numérique du schéma d'intégration RK4 : il reste faible (~0,3 % de "
        "l'apport au pas par défaut) et décroît avec le pas de temps. Un résidu "
        "élevé révélerait une dérive numérique ou un bug."
    )

    def _last(key: str) -> float:
        return float(df[COL[key]].to_numpy()[-1])

    def _amax_e(key: str) -> float:
        return float(np.abs(df[COL[key]]).max())

    e_input0 = float(df[COL["e_input"]].to_numpy()[0])
    ref = abs(e_input0) if abs(e_input0) > 1e-9 else 1.0
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Énergie d'impact", f"{e_input0:.0f} J")
    e2.metric(
        "Dissipée amortisseur (hyd + fric)",
        f"{_last('e_hyd') + _last('e_fric'):.0f} J",
    )
    e3.metric(
        "Dissipée glissement pneu",
        f"{_last('e_slip'):.0f} J",
    )
    e4.metric(
        "|Résidu| max",
        f"{_amax_e('e_residual'):.0f} J",
        f"{100.0 * _amax_e('e_residual') / ref:.2f} % de l'apport",
        delta_color="off",
    )

    st.plotly_chart(
        line(
            t,
            [
                ("Apport total", df[COL["e_input"]]),
                ("Cinétique masse susp.", df[COL["e_kin"]]),
                ("Cinétique rotation roue", df[COL["e_kin_spin"]]),
                ("Stockée gaz", df[COL["e_gas"]]),
                ("Dissipée hydraulique", df[COL["e_hyd"]]),
                ("Dissipée friction joint", df[COL["e_fric"]]),
                ("Dissipée glissement pneu", df[COL["e_slip"]]),
            ],
            "Répartition de l'énergie au cours de l'impact",
            "Temps (s)",
            "Énergie (J)",
        ),
        width="stretch",
        config={"responsive": True},
    )
    st.plotly_chart(
        line(
            t,
            [
                ("Résidu de bilan", df[COL["e_residual"]]),
            ],
            "Résidu du bilan énergétique (indicateur de cohérence)",
            "Temps (s)",
            "Énergie (J)",
        ),
        width="stretch",
        config={"responsive": True},
    )

with tab_perso:
    st.caption(
        "Choisissez l'abscisse et jusqu'à 5 grandeurs en ordonnée. Chaque courbe "
        "peut être tracée sur l'axe Y de gauche ou de droite (second axe)."
    )
    options = list(df.columns)
    none_label = "— aucune —"

    # Migration douce : récupère l'état historique s'il existe encore.
    legacy_curves = []
    for i in range(5):
        legacy_curves.append(
            {
                "label": st.session_state.get(f"perso_y{i}", none_label),
                "right": bool(st.session_state.get(f"perso_axis{i}", False)),
            }
        )
    legacy_cfg = {
        "x": st.session_state.get("perso_x", options[0]),
        "curves": legacy_curves,
    }

    cfg = st.session_state.get(PERSO_CFG_KEY, legacy_cfg)
    cfg = _sanitize_perso_cfg(cfg, options, none_label)
    st.session_state[PERSO_CFG_KEY] = cfg

    # Clés widgets temporaires : peuvent être détruites entre pages.
    x_widget_key = "_perso_x"
    if x_widget_key not in st.session_state:
        st.session_state[x_widget_key] = cfg["x"]

    if st.session_state[x_widget_key] not in options:
        st.session_state[x_widget_key] = options[0]
    x_label = st.selectbox("Abscisse (X)", options, key=x_widget_key)

    selections: list[tuple[str, bool]] = []
    for i in range(5):
        c_curve, c_axis = st.columns([3, 1])
        opts = ([none_label] + options) if i > 0 else options

        y_widget_key = f"_perso_y{i}"
        axis_widget_key = f"_perso_axis{i}"
        if y_widget_key not in st.session_state:
            st.session_state[y_widget_key] = cfg["curves"][i]["label"]
        if axis_widget_key not in st.session_state:
            st.session_state[axis_widget_key] = cfg["curves"][i]["right"]

        if st.session_state[y_widget_key] not in opts:
            st.session_state[y_widget_key] = opts[0]

        y_sel = c_curve.selectbox(f"Courbe {i + 1}", opts, key=y_widget_key)
        on_right = c_axis.checkbox("Axe droit", key=axis_widget_key)
        if y_sel != none_label:
            selections.append((y_sel, on_right))

    # Sauvegarde explicite de la configuration dans une clé persistante.
    st.session_state[PERSO_CFG_KEY] = {
        "x": x_label,
        "curves": [
            {
                "label": st.session_state.get(f"_perso_y{i}", none_label),
                "right": bool(st.session_state.get(f"_perso_axis{i}", False)),
            }
            for i in range(5)
        ],
    }

    if not selections:
        st.info("Sélectionnez au moins une grandeur en ordonnée.", icon="ℹ️")
    else:
        any_right = any(right for _, right in selections)
        left_labels = [lbl for lbl, right in selections if not right]
        right_labels = [lbl for lbl, right in selections if right]

        def _nice_range(labels: list[str], ndiv: int) -> tuple[float, float, float]:
            """Plage [min, max] arrondie et pas pour ``ndiv`` intervalles."""
            vals = np.concatenate([df[lbl].to_numpy(dtype=float) for lbl in labels])
            vals = vals[np.isfinite(vals)]
            lo, hi = float(np.min(vals)), float(np.max(vals))
            if lo == hi:
                lo, hi = lo - 1.0, hi + 1.0
            span = hi - lo
            raw = span / ndiv
            mag = 10.0 ** np.floor(np.log10(raw))
            step = mag * min(m for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
            lo = np.floor(lo / step) * step
            hi = lo + step * ndiv
            return lo, hi, step

        NDIV = 8
        fig = go.Figure()
        for lbl, right in selections:
            fig.add_trace(
                go.Scatter(
                    x=df[x_label], y=df[lbl], mode="lines", name=lbl,
                    yaxis="y2" if right else "y",
                )
            )
        title = f"Courbes en fonction de {x_label}"
        yaxis = _grid_axis(" / ".join(left_labels) if left_labels else "")
        if left_labels:
            lo, hi, step = _nice_range(left_labels, NDIV)
            yaxis.update(range=[lo, hi], tick0=lo, dtick=step)
        fig.update_layout(
            title=dict(text=title, y=0.98, yanchor="top"),
            margin=dict(l=10, r=10, t=80, b=55),
            legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0),
            height=GRAPH_HEIGHT,
            plot_bgcolor=GRAPH_PAPER_BG,
            paper_bgcolor="white",
            xaxis=_grid_axis(x_label),
            yaxis=yaxis,
        )
        if any_right:
            right_axis = _grid_axis(" / ".join(right_labels))
            lo, hi, step = _nice_range(right_labels, NDIV)
            right_axis.update(
                overlaying="y", side="right",
                showgrid=False, zeroline=False,
                minor=dict(showgrid=False),
                range=[lo, hi], tick0=lo, dtick=step,
            )
            fig.update_layout(yaxis2=right_axis)
        st.plotly_chart(fig, width="stretch", config={"responsive": True})

with tab_anim:
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
            "Utilisez les boutons de vitesse (1x, 0.5x, 0.25x) et le curseur pour "
            "parcourir le temps."
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

        # Durée de frame en "temps réel" sur les images affichées.
        if len(idx) > 1:
            sampled_dt_ms = float(np.mean(np.diff(gt[idx])) * 1000.0)
        else:
            sampled_dt_ms = 40.0
        real_time_frame_ms = max(1, int(round(sampled_dt_ms)))

        def _anim_args(speed_factor: float) -> list[object]:
            duration = max(1, int(round(real_time_frame_ms / speed_factor)))
            return [None, dict(
                frame=dict(duration=duration, redraw=True),
                fromcurrent=True,
                transition=dict(duration=0),
            )]

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
            # Reserve bottom space for animation controls to avoid overlap.
            margin=dict(l=10, r=10, t=30, b=140),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            updatemenus=[dict(
                type="buttons", showactive=False, x=0.0, y=0.02, xanchor="left",
                direction="left",
                buttons=[
                    dict(label="▶ 1x (réel)", method="animate", args=_anim_args(1.0)),
                    dict(label="▶ 0.5x", method="animate", args=_anim_args(0.5)),
                    dict(label="▶ 0.25x", method="animate", args=_anim_args(0.25)),
                    dict(label="⏸ Pause", method="animate",
                         args=[[None], dict(frame=dict(duration=0, redraw=False),
                                            mode="immediate")]),
                ],
            )],
            sliders=[dict(
                active=0, x=0.0, len=1.0, y=-0.08,
                currentvalue=dict(prefix="t = ", suffix=" ms"),
                steps=[dict(method="animate", label=f"{gt[i]*1000:.0f}",
                            args=[[f"{gt[i]*1000:.0f}"],
                                  dict(mode="immediate",
                                       frame=dict(duration=0, redraw=True),
                                       transition=dict(duration=0))])
                       for i in idx],
            )],
        )
        st.plotly_chart(fig, width="stretch")

# --------------------------------------------------------------------------- #
#  Données et export
# --------------------------------------------------------------------------- #
st.divider()
with st.expander("Séries temporelles (tableau)"):
    st.dataframe(df, width="stretch", height=320)

st.download_button(
    "⬇️ Exporter les résultats (CSV)",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="resultats_trailing_arm.csv",
    mime="text/csv",
)
