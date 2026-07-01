"""Tests unitaires du repli des éditions d'un ``st.data_editor`` (fonction pure
``_apply_editor_state``), cœur du correctif du bug « saisie prise en compte une
fois sur deux » (streamlit#7749) dans app/components/gear_form.py.

On teste uniquement la logique pandas (pas de Streamlit lancé) : édition de
cellule, ajout et suppression de lignes, indices positionnels.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

# Rendre importable app/ et app/components/ (le module importe theme + streamlit).
_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "app", _ROOT / "app" / "components"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

pytest.importorskip("streamlit")  # gear_form importe streamlit au chargement.
from components.gear_form import _apply_editor_state  # noqa: E402


def _rain_df():
    return pd.DataFrame(
        [(0.0, 10.0, 1.0), (10.0, 20.0, 2.0)],
        columns=["Début (mm)", "Fin (mm)", "Profondeur (mm)"],
    )


def test_edit_cell_registers_immediately():
    """Une édition de cellule est prise en compte dès le premier repli (pas de
    double saisie)."""
    df = _rain_df()
    out = _apply_editor_state(df, {"edited_rows": {1: {"Profondeur (mm)": 5.5}}})
    assert out.loc[1, "Profondeur (mm)"] == 5.5
    # Les autres valeurs sont inchangées.
    assert out.loc[0, "Début (mm)"] == 0.0
    assert out.loc[1, "Fin (mm)"] == 20.0


def test_edit_multiple_columns_same_row():
    df = _rain_df()
    out = _apply_editor_state(df, {"edited_rows": {0: {"Début (mm)": 1.0, "Fin (mm)": 9.0}}})
    assert out.loc[0, "Début (mm)"] == 1.0
    assert out.loc[0, "Fin (mm)"] == 9.0


def test_added_row_appended_once():
    df = _rain_df()
    out = _apply_editor_state(df, {"added_rows": [{"Début (mm)": 20.0, "Fin (mm)": 30.0, "Profondeur (mm)": 3.0}]})
    assert len(out) == 3
    assert out.loc[2, "Fin (mm)"] == 30.0


def test_added_row_partial_columns_are_nan():
    df = _rain_df()
    out = _apply_editor_state(df, {"added_rows": [{"Début (mm)": 20.0}]})
    assert len(out) == 3
    assert out.loc[2, "Début (mm)"] == 20.0
    assert pd.isna(out.loc[2, "Fin (mm)"])


def test_deleted_row_removed_and_reindexed():
    df = _rain_df()
    out = _apply_editor_state(df, {"deleted_rows": [0]})
    assert len(out) == 1
    # L'index est réinitialisé (0..n-1) après suppression.
    assert list(out.index) == [0]
    assert out.loc[0, "Fin (mm)"] == 20.0


def test_empty_state_is_identity():
    df = _rain_df()
    out = _apply_editor_state(df, {})
    pd.testing.assert_frame_equal(out, df)


def test_combined_edit_delete_add():
    df = _rain_df()
    state = {
        "edited_rows": {0: {"Profondeur (mm)": 9.0}},
        "deleted_rows": [1],
        "added_rows": [{"Début (mm)": 40.0, "Fin (mm)": 50.0, "Profondeur (mm)": 4.0}],
    }
    out = _apply_editor_state(df, state)
    # Ligne 0 éditée, ligne 1 supprimée, une ligne ajoutée → 2 lignes au total.
    assert len(out) == 2
    assert out.loc[0, "Profondeur (mm)"] == 9.0
    assert out.loc[1, "Début (mm)"] == 40.0


def test_source_df_not_mutated():
    df = _rain_df()
    _apply_editor_state(df, {"edited_rows": {0: {"Début (mm)": 99.0}}})
    assert df.loc[0, "Début (mm)"] == 0.0  # l'original reste intact
