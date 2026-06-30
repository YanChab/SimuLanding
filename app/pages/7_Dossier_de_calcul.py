"""Page Dossier de calcul : rendu formaté du document maître ``docs/Dossier_de_calcul_complet.md``.

Le document (PFD, amortisseur/friction/gaz, méthodologie, bilan énergétique) est
rendu tel quel : titres, **tableaux GFM**, et **mathématiques LaTeX** ($…$ inline et
$$…$$ en bloc) via le moteur KaTeX intégré à Streamlit. Le seul bloc ``mermaid`` du
document s'affiche sous forme de code source (Streamlit n'a pas de rendu mermaid natif).
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_APP = Path(__file__).resolve().parent.parent
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

from theme import apply_theme  # noqa: E402

_DOC = _ROOT / "docs" / "Dossier_de_calcul_complet.md"


@st.cache_data(show_spinner=False)
def _load_doc(path_str: str, mtime: float) -> str:
    """Lit le document. ``mtime`` invalide le cache si le fichier change."""
    return Path(path_str).read_text(encoding="utf-8")


apply_theme()

st.title("📐 Dossier de calcul complet")
st.caption(
    "Document maître : PFD (efforts/torseurs), amortisseur hydraulique, friction, "
    "ressort gaz, méthodologie d'intégration et bilan énergétique. "
    "Source : docs/Dossier_de_calcul_complet.md."
)

if not _DOC.exists():
    st.error(f"Document introuvable : {_DOC}")
    st.stop()

content = _load_doc(str(_DOC), _DOC.stat().st_mtime)

# Bouton de téléchargement de la source markdown.
st.download_button(
    "⬇️ Télécharger le document (.md)",
    data=content,
    file_name="Dossier_de_calcul_complet.md",
    mime="text/markdown",
)

st.divider()

# Rendu : tableaux GFM + LaTeX ($…$ / $$…$$) gérés nativement par st.markdown.
st.markdown(content)
