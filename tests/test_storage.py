"""Tests du système de sauvegarde / rechargement des simulations."""
from __future__ import annotations

import numpy as np

from dropsim import default_mlg_inputs, run_simulation
from dropsim.storage import (
    inputs_from_dict,
    inputs_to_dict,
    list_saved,
    load_simulation,
    save_simulation,
)


def test_inputs_roundtrip():
    inp = default_mlg_inputs()
    restored = inputs_from_dict(inputs_to_dict(inp))
    assert restored == inp


def test_save_load_roundtrip(tmp_path):
    inp = default_mlg_inputs()
    result = run_simulation(inp)

    path = save_simulation(inp, result, name="Cas nominal", directory=tmp_path)
    assert path.exists()

    loaded_inp, loaded_res, meta = load_simulation(path)

    assert loaded_inp == inp
    assert meta["name"] == "Cas nominal"
    assert loaded_res.n_steps == result.n_steps
    assert list(loaded_res.df.columns) == list(result.df.columns)
    np.testing.assert_allclose(
        loaded_res.df["Tyre.FTyre (N)"].to_numpy(),
        result.df["Tyre.FTyre (N)"].to_numpy(),
    )
    assert loaded_res.summary_rows == result.summary_rows


def test_list_saved(tmp_path):
    inp = default_mlg_inputs()
    result = run_simulation(inp)
    save_simulation(inp, result, name="Premier", directory=tmp_path)
    save_simulation(inp, result, name="Deuxieme", directory=tmp_path)

    entries = list_saved(tmp_path)
    names = {e["name"] for e in entries}
    assert {"Premier", "Deuxieme"} <= names
