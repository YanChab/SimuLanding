"""Application de simulation de drop test — train d'atterrissage à balancier (MLG).

Remplace le classeur Excel ``DROSIM`` par une interface web locale :

* page **Saisie** : renseignement des données du train (unités d'affichage de
  l'Excel : mm, bar, cc, °C, °) avec détection et localisation des erreurs ;
* page **Résultats** : courbes des grandeurs simulées et synthèse.

Le moteur de calcul (paquet ``dropsim``) reproduit fidèlement la méthodologie
VBA d'origine ; il est validé à mieux que 0,2 % par rapport à la référence Excel.

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
)

# Entrées par défaut conservées d'une page à l'autre.
if "inputs" not in st.session_state:
    st.session_state.inputs = default_mlg_inputs()

st.title("🛬 SimuLanding — Simulation de drop test")
st.subheader("Train d'atterrissage à balancier (MLG)")

st.markdown(
    """
Cette application remplace le classeur Excel de simulation de chute (*drop test*).
Elle reproduit **exactement** la méthodologie de calcul d'origine (intégration
d'Euler explicite, ressort gazeux double chambre, pertes hydrauliques à section
variable, cinématique du balancier).

**Comment l'utiliser :**

1. Ouvrez la page **Saisie** (menu de gauche) pour renseigner ou ajuster les
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
