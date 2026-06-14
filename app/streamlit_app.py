"""Application de simulation de drop test — train d'atterrissage à balancier (MLG).

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

# Permet d'importer le paquet moteur quel que soit le dossier de lancement.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dropsim import default_mlg_inputs  # noqa: E402

st.set_page_config(
    page_title="SimuLanding — Drop test MLG",
    page_icon="🛬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

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
    [data-testid="stVerticalBlock"] { gap: 0.12rem; }
    [data-testid="stHorizontalBlock"] { gap: 0.35rem; }
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
    /* Espace au-dessus des tableaux pour ne pas masquer leur titre */
    div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
        margin-top: 0.5rem; overflow: visible; }
    /* Le titre (markdown) juste avant un tableau garde son espace */
    div[data-testid="stMarkdownContainer"] { overflow: visible; }
    hr { margin: 0.25rem 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Entrées par défaut conservées d'une page à l'autre.
if "inputs" not in st.session_state:
    st.session_state.inputs = default_mlg_inputs()


# --------------------------------------------------------------------------- #
#  Page d'accueil
# --------------------------------------------------------------------------- #
def accueil() -> None:
    st.title("🛬 SimuLanding — Simulation de drop test")
    st.subheader("Train d'atterrissage à balancier (MLG)")

    st.markdown(
        """
Cette application remplace le classeur Excel de simulation de chute (*drop test*).
Elle reproduit **exactement** la méthodologie de calcul d'origine (intégration
d'Euler explicite, ressort gazeux double chambre, pertes hydrauliques à section
variable, cinématique du balancier).

**Comment l'utiliser :**

1. Ouvrez la page **Saisie** (bandeau en haut) pour renseigner ou ajuster les
   données du train d'atterrissage. Les valeurs par défaut correspondent au cas
   nominal de l'Excel.
2. Lancez le calcul : les erreurs éventuelles sont **localisées précisément**
   (champ concerné, cause, conseil de correction).
3. Consultez la page **Résultats** pour visualiser les courbes et la synthèse.
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
        "Phase 1 — architecture de train à balancier."
    )


# --------------------------------------------------------------------------- #
#  Navigation en bandeau supérieur
# --------------------------------------------------------------------------- #
pages = [
    st.Page(accueil, title="Accueil", icon="🏠", default=True),
    st.Page("pages/1_Saisie.py", title="Saisie", icon="📝"),
    st.Page("pages/2_Resultats.py", title="Résultats", icon="📈"),
]
nav = st.navigation(pages, position="top")
nav.run()
