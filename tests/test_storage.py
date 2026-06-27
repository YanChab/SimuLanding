"""Tests du système de sauvegarde / rechargement des simulations."""
from __future__ import annotations

import numpy as np

from dropsim import (
    default_aircraft_inputs,
    default_strait_strut_inputs,
    default_trailing_arm_inputs,
    run_simulation,
)
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


def test_aircraft_inputs_roundtrip():
    inp = default_aircraft_inputs()
    restored = inputs_from_dict(inputs_to_dict(inp))
    assert restored == inp
    assert getattr(restored, "model_kind", "") == "aircraft"


def test_aircraft_swapped_types_and_overrides_roundtrip():
    """Types de train inversés par position + surcharges de chute survivent
    au cycle sérialisation/désérialisation."""
    from dropsim.inputs import AircraftGearDropOverride

    inp = default_aircraft_inputs()
    inp.nlg = default_trailing_arm_inputs()
    inp.mlg = default_strait_strut_inputs()
    inp.nlg_drop = AircraftGearDropOverride(vz=2.5, masse=500.0)
    restored = inputs_from_dict(inputs_to_dict(inp))
    assert restored == inp
    assert restored.nlg.model_kind == "trailing_arm"
    assert restored.mlg.model_kind == "strait_strut"
    assert restored.nlg_drop.vz == 2.5
    assert restored.nlg_drop.masse == 500.0


def test_aircraft_legacy_dict_without_per_position_type_loads():
    """Une sauvegarde antérieure (sans model_kind par train ni *_drop) se charge
    avec la convention historique : NLG StraitStrut, MLG TrailingArm."""
    legacy = inputs_to_dict(default_aircraft_inputs())
    # Simule un ancien format : on retire les nouveautés.
    legacy["nlg"].pop("model_kind", None)
    legacy["mlg"].pop("model_kind", None)
    legacy.pop("nlg_drop", None)
    legacy.pop("mlg_drop", None)

    restored = inputs_from_dict(legacy)
    assert restored.nlg.model_kind == "strait_strut"
    assert restored.mlg.model_kind == "trailing_arm"
    # Les surcharges absentes prennent leurs valeurs par défaut (héritage global).
    assert restored.nlg_drop.vz is None
    assert restored.mlg_drop.masse is None


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


def test_aircraft_save_load_roundtrip(tmp_path):
    inp = default_aircraft_inputs()
    result = run_simulation(inp)

    path = save_simulation(inp, result, name="Avion complet nominal", project="Programme AC", directory=tmp_path)
    assert path.exists()

    loaded_inp, loaded_res, meta = load_simulation(path)

    assert loaded_inp == inp
    assert meta["name"] == "Avion complet nominal"
    assert meta["project"] == "Programme AC"
    assert loaded_res.n_steps == result.n_steps
    assert list(loaded_res.df.columns) == list(result.df.columns)
    np.testing.assert_allclose(
        loaded_res.df["Aircraft.Fz total (N)"].to_numpy(),
        result.df["Aircraft.Fz total (N)"].to_numpy(),
    )


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
