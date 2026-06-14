"""Thème visuel partagé de l'application (palette SuiviProcess + polices).

Centralise :

* les **couleurs** de la charte (bordeaux, roses, gris) exposées en variables CSS
  réutilisables (``--sp-...``) ;
* les déclarations ``@font-face`` des **polices auto-hébergées**
  (``app/static/fonts/``) : Eurostile (titres), Roboto (corps), Freshbot (logo) ;
* l'habillage des **composants Streamlit** (navbar, boutons, liens, tableaux,
  cartes info/success, textes secondaires…).

Appeler :func:`apply_theme` au tout début de chaque page, après
``st.set_page_config`` lorsqu'il est présent.
"""
from __future__ import annotations

import streamlit as st

# Palette de la charte graphique.
BORDEAUX = "#8A1A1D"      # Primaire : navbar, boutons, liens actifs
ROSE = "#B97677"          # Hover, bordures, badges
GRIS_MOYEN = "#878786"    # Texte secondaire, icônes
GRIS_CLAIR = "#B7B7B6"    # Fonds de cartes, bordures subtiles
GRIS_FONCE = "#4A4949"    # Texte principal, titres
GRIS_META = "#929292"     # Sous-titres, métadonnées

# Chemin servi par Streamlit (enableStaticServing) pour les polices.
_FONTS = "app/static/fonts"

_CSS = f"""
<style>
/* --- Polices auto-hébergées ------------------------------------------- */
@font-face {{
    font-family: 'Eurostile';
    src: url('{_FONTS}/Eurostile-bold.woff2') format('woff2'),
         url('{_FONTS}/Eurostile-bold.woff') format('woff');
    font-weight: 700; font-style: normal; font-display: swap;
}}
@font-face {{
    font-family: 'Roboto';
    src: url('{_FONTS}/Roboto-Regular.woff2') format('woff2'),
         url('{_FONTS}/Roboto-Regular.woff') format('woff');
    font-weight: 400; font-style: normal; font-display: swap;
}}
@font-face {{
    font-family: 'Roboto';
    src: url('{_FONTS}/Roboto-Medium.woff2') format('woff2'),
         url('{_FONTS}/Roboto-Medium.woff') format('woff');
    font-weight: 500; font-style: normal; font-display: swap;
}}
@font-face {{
    font-family: 'Roboto';
    src: url('{_FONTS}/Roboto-Bold.woff2') format('woff2'),
         url('{_FONTS}/Roboto-Bold.woff') format('woff');
    font-weight: 700; font-style: normal; font-display: swap;
}}
@font-face {{
    font-family: 'Freshbot';
    src: url('{_FONTS}/Freshbot.woff2') format('woff2'),
         url('{_FONTS}/Freshbot.woff') format('woff');
    font-weight: 400; font-style: normal; font-display: swap;
}}

/* --- Variables de palette --------------------------------------------- */
:root {{
    --sp-bordeaux: {BORDEAUX};
    --sp-rose: {ROSE};
    --sp-gris-moyen: {GRIS_MOYEN};
    --sp-gris-clair: {GRIS_CLAIR};
    --sp-gris-fonce: {GRIS_FONCE};
    --sp-gris-meta: {GRIS_META};
    --font-heading: 'Eurostile', 'Roboto', sans-serif;
    --font-sans: 'Roboto', system-ui, -apple-system, sans-serif;
    --font-logo: 'Freshbot', 'Eurostile', sans-serif;
}}

/* --- Typographie globale ---------------------------------------------- */
html, body, .stApp, [data-testid="stAppViewContainer"],
div[data-testid="stMarkdownContainer"], p, span, label, input, button, table {{
    font-family: var(--font-sans);
}}
.stApp {{ color: var(--sp-gris-fonce); }}

/* Titres : Eurostile Bold, gris foncé */
h1, h2, h3, h4, h5, h6 {{
    font-family: var(--font-heading) !important;
    font-weight: 700 !important;
    color: var(--sp-gris-fonce);
}}
/* Le titre principal de page rappelle le bordeaux */
h1 {{ color: var(--sp-bordeaux); }}

/* Sous-titres / métadonnées / captions */
[data-testid="stCaptionContainer"], .stCaption, small {{
    color: var(--sp-gris-meta) !important;
}}

/* --- Liens ------------------------------------------------------------ */
a, a:visited {{ color: var(--sp-bordeaux); text-decoration: none; }}
a:hover {{ color: var(--sp-rose); text-decoration: underline; }}

/* --- Navigation en bandeau supérieur ---------------------------------- */
header[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stNavBar"], [data-testid="stTopNav"] {{
    background-color: var(--sp-bordeaux);
}}
[data-testid="stNavBar"] a, [data-testid="stTopNav"] a,
[data-testid="stNavBar"] span, [data-testid="stTopNav"] span {{
    color: #ffffff !important;
    font-family: var(--font-heading);
}}
[data-testid="stNavBar"] a:hover, [data-testid="stTopNav"] a:hover {{
    color: var(--sp-rose) !important;
}}
/* Lien de page actif */
[data-testid="stNavBar"] a[aria-current="page"],
[data-testid="stTopNav"] a[aria-current="page"] {{
    color: #ffffff !important;
    border-bottom: 3px solid var(--sp-rose);
}}

/* --- Boutons ---------------------------------------------------------- */
.stButton > button, .stDownloadButton > button {{
    font-family: var(--font-heading);
    border: 1px solid var(--sp-bordeaux);
}}
.stButton > button[kind="primary"], .stDownloadButton > button {{
    background-color: var(--sp-bordeaux);
    color: #ffffff;
}}
.stButton > button[kind="primary"]:hover, .stDownloadButton > button:hover {{
    background-color: var(--sp-rose);
    border-color: var(--sp-rose);
    color: #ffffff;
}}
.stButton > button[kind="secondary"] {{
    background-color: #ffffff;
    color: var(--sp-bordeaux);
}}
.stButton > button[kind="secondary"]:hover {{
    background-color: var(--sp-rose);
    border-color: var(--sp-rose);
    color: #ffffff;
}}

/* --- Cartes info / success / warning ---------------------------------- */
div[data-testid="stAlert"] {{
    border-radius: 6px;
    border: 1px solid var(--sp-gris-clair);
}}

/* --- Tableaux / éditeurs de données ----------------------------------- */
div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {{
    border: 1px solid var(--sp-gris-clair);
    border-radius: 6px;
}}

/* --- Champs : focus bordeaux ------------------------------------------ */
input:focus, textarea:focus,
div[data-baseweb="input"]:focus-within {{
    border-color: var(--sp-bordeaux) !important;
    box-shadow: 0 0 0 1px var(--sp-bordeaux) !important;
}}

/* --- Logo « SIMULANDING » ---------------------------------------------- */
.sp-logo {{
    font-family: var(--font-logo);
    color: var(--sp-bordeaux);
    font-size: 3rem;
    line-height: 1.1;
    letter-spacing: 1px;
    margin: 0.2rem 0 0.4rem 0;
}}

/* --- Divider ---------------------------------------------------------- */
hr {{ border-color: var(--sp-gris-clair); }}
</style>
"""


def apply_theme() -> None:
    """Injecte la charte graphique (couleurs + polices) dans la page courante."""
    st.markdown(_CSS, unsafe_allow_html=True)
