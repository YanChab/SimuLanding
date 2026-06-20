"""Tests du système de sauvegarde / rechargement des simulations."""
from __future__ import annotations

import numpy as np

from dropsim import default_trailing_arm_inputs, default_strait_strut_inputs, run_simulation
from dropsim.storage import (
    DEFAULT_PROJECT,
    inputs_from_dict,
    inputs_to_dict,
    list_projects,
    list_saved,
    load_simulation,
    save_simulation,
)


def test_inputs_roundtrip():
    inp = default_trailing_arm_inputs()
    restored = inputs_from_dict(inputs_to_dict(inp))
    assert restored == inp


def test_strait_strut_inputs_roundtrip():
    inp = default_strait_strut_inputs()
    restored = inputs_from_dict(inputs_to_dict(inp))
    assert restored == inp
    assert getattr(restored, "model_kind", "") == "strait_strut"


def test_save_load_roundtrip(tmp_path):
    inp = default_trailing_arm_inputs()
    result = run_simulation(inp)

    path = save_simulation(inp, result, name="Cas nominal", directory=tmp_path)
    assert path.exists()

    loaded_inp, loaded_res, meta = load_simulation(path)

    assert loaded_inp == inp
    assert meta["name"] == "Cas nominal"
    assert meta["project"] == DEFAULT_PROJECT
    assert loaded_res.n_steps == result.n_steps
    assert list(loaded_res.df.columns) == list(result.df.columns)
    np.testing.assert_allclose(
        loaded_res.df["Tyre.FTyre (N)"].to_numpy(),
        result.df["Tyre.FTyre (N)"].to_numpy(),
    )
    assert loaded_res.summary_rows == result.summary_rows


def test_list_saved(tmp_path):
    inp = default_trailing_arm_inputs()
    result = run_simulation(inp)
    save_simulation(inp, result, name="Premier", directory=tmp_path)
    save_simulation(inp, result, name="Deuxieme", directory=tmp_path)

    entries = list_saved(tmp_path)
    names = {e["name"] for e in entries}
    assert {"Premier", "Deuxieme"} <= names


def test_projects(tmp_path):
    inp = default_trailing_arm_inputs()
    result = run_simulation(inp)
    save_simulation(inp, result, name="Essai 1", project="Avion A", directory=tmp_path)
    save_simulation(inp, result, name="Essai 2", project="Avion A", directory=tmp_path)
    save_simulation(inp, result, name="Essai 1", project="Avion B", directory=tmp_path)

    assert list_projects(tmp_path) == ["Avion A", "Avion B"]

    names_a = {e["name"] for e in list_saved(tmp_path, project="Avion A")}
    assert names_a == {"Essai 1", "Essai 2"}

    saved_b = list_saved(tmp_path, project="Avion B")
    assert len(saved_b) == 1
    assert saved_b[0]["project"] == "Avion B"

    # Le filtrage par projet isole bien les sauvegardes homonymes.
    _, _, meta = load_simulation(saved_b[0]["path"])
    assert meta["project"] == "Avion B"
