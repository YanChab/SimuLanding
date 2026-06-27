"""Application de simulation de drop test — train d'atterrissage à balancier (trailing arm).

Remplace le classeur Excel ``DROSIM`` par une interface web locale :

* page **Saisie** : renseignement des données du train (unités d'affichage de
  l'Excel : mm, bar, cc, °C, °) avec détection et localisation des erreurs ;
* page **Résultats** : courbes des grandeurs simulées et synthèse.

Le moteur de calcul (paquet ``dropsim``) reproduit fidèlement la méthodologie
VBA d'origine ; il est validé à mieux que 0,2 % par rapport à la référence Excel.

La navigation est placée en **bandeau supérieur** afin que chaque page dispose de
toute la largeur disponible.

Lancement :  ``streamlit run app/streamlit_app.py``
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Permet d'importer le paquet moteur (racine) et les modules locaux app/ (theme,
# components) quel que soit le dossier de lancement.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_APP = Path(__file__).resolve().parent
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

from dropsim import default_trailing_arm_inputs, default_strait_strut_inputs  # noqa: E402
from theme import apply_theme  # noqa: E402

st.set_page_config(
    page_title="SimuLanding — Drop test Trailing Arm",
    page_icon="🛬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Charte graphique (palette SuiviProcess + polices auto-hébergées).
apply_theme()

# --------------------------------------------------------------------------- #
#  Style global : interface dense + champs sans boutons +/- + pleine largeur
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <style>
    /* Pleine largeur et marges réduites */
    .block-container { padding-top: 2.2rem; padding-bottom: 0.6rem;
                       padding-left: 1.2rem; padding-right: 1.2rem; max-width: 100%; }
    /* Densité : espacements verticaux et horizontaux resserrés */
    [data-testid="stVerticalBlock"] { gap: 0.35rem; }
    [data-testid="stHorizontalBlock"] { gap: 0rem; }
    /* Champs numériques : masquer les boutons + / - (steppers) */
    button[data-testid="stNumberInputStepUp"],
    button[data-testid="stNumberInputStepDown"] { display: none !important; }
    /* Labels de champs plus compacts */
    div[data-testid="stNumberInput"] label,
    div[data-testid="stTextInput"] label { font-size: 0.72rem; margin-bottom: 0; line-height: 1.05; }
    div[data-testid="stNumberInput"] input { padding-top: 0.1rem; padding-bottom: 0.1rem;
                                             font-size: 0.82rem; }
    /* Champs numériques : largeur réduite pour compacter */
    div[data-testid="stNumberInput"] { max-width: 9.5rem; margin-bottom: 0; }
    div[data-testid="stNumberInput"] div[data-baseweb="input"] { max-width: 9.5rem; }
    /* Titres de section resserrés */
    h2 { margin-top: 0.2rem; margin-bottom: 0.02rem; font-size: 1rem; }
    h3 { margin-top: 0.1rem; margin-bottom: 0.02rem; font-size: 0.9rem; }
    /* Captions/markdown de tableaux resserrés mais visibles */
    div[data-testid="stMarkdownContainer"] p { margin-bottom: 0.05rem; font-size: 0.82rem; }
    /* Titre en gras juste avant un tableau : marge haute pour ne pas chevaucher l'élément précédent */
    div[data-testid="stMarkdownContainer"] p:has(strong) { margin-top: 0.7rem; }
    /* Espace autour des tableaux pour ne pas masquer leur titre ni chevaucher le suivant */
    div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
        margin-top: 0.4rem; margin-bottom: 0.6rem; }
    /* Graphes Plotly : marge basse pour éviter le chevauchement avec l'élément suivant */
    div[data-testid="stPlotlyChart"] { margin-top: 0.3rem; margin-bottom: 0.6rem; }
    /* Le titre (markdown) juste avant un tableau garde son espace */
    div[data-testid="stMarkdownContainer"] { overflow: visible; }
    hr { margin: 0.25rem 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Entrées par défaut conservées d'une page à l'autre.
if "model_kind" not in st.session_state:
    st.session_state.model_kind = "trailing_arm"
if "inputs" not in st.session_state:
    if st.session_state.model_kind == "strait_strut":
        st.session_state.inputs = default_strait_strut_inputs()
    else:
        st.session_state.inputs = default_trailing_arm_inputs()


# --------------------------------------------------------------------------- #
#  Page d'accueil
# --------------------------------------------------------------------------- #
def accueil() -> None:
    st.markdown(
        "<div class='sp-logo'>SIMULANDING</div>",
        unsafe_allow_html=True,
    )
    st.title("🛬 SimuLanding — Simulation de drop test")
    st.subheader("Avion complet : 1 NLG + 2 MLG couplés (ou train isolé)")

    st.markdown(
        """
Cette application remplace le classeur Excel de simulation de chute (*drop test*).
Elle reproduit **exactement** la méthodologie de calcul d'origine (intégration
RK4, ressort gazeux double chambre, pertes hydrauliques à section variable,
cinématique de jambe).

**Comment l'utiliser :**

1. Ouvrez la page **Avion complet** (bandeau en haut) : saisissez les données
    de l'avion et de chaque train, et choisissez le type de chaque train
    (**StraitStrut** ou **TrailingArm**).
2. Lancez la simulation voulue avec les trois boutons : **avion complet**,
    **NLG seul** ou **MLG seul**.
3. Consultez la page **Résultats avion** pour les courbes et la synthèse, et la
    page **Comparaison** pour superposer deux simulations avion complet.
"""
    )

    col1, col2 = st.columns(2)
    with col1:
        st.info(
            "**Unités d'affichage** : mm · bar · cc · cSt · MPa · ° · °C\n\n"
            "Les conversions en unités SI sont gérées automatiquement par le moteur.",
            icon="📐",
        )
    with col2:
        st.success(
            "**Fidélité** : moteur validé à < 0,2 % de la référence Excel "
            "(course, efforts, pressions).",
            icon="✅",
        )

    st.caption(
        "Architecture : moteur `dropsim` (Python/NumPy) séparé de l'interface. "
        "Phase 1 — modèle TrailingArm robuste + démarrage modèle StraitStrut."
    )


# --------------------------------------------------------------------------- #
#  Navigation en bandeau supérieur
# --------------------------------------------------------------------------- #
pages = [
    st.Page(accueil, title="Accueil", icon="🏠", default=True),
    st.Page("pages/5_Avion_complet.py", title="Avion complet", icon="🛫"),
    st.Page("pages/6_Resultats_avion_complet.py", title="Resultats avion", icon="📊"),
    st.Page("pages/3_Comparaison.py", title="Comparaison", icon="⚖️"),
    st.Page("pages/4_Loi_hydraulique.py", title="Loi hydraulique", icon="🧮"),
]
nav = st.navigation(pages, position="top")
nav.run()
