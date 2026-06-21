"""Validation du moteur Python par rapport à la référence Excel.

Compare les grandeurs caractéristiques (course max, effort vertical max, effort
horizontal max) calculées par le moteur avec :

* les valeurs de synthèse de l'onglet « MLG » (Course max = 172.11 mm,
  Fz max = 47311 N, Fx max = 17811 N) ;
* les maxima de la courbe de référence ``_extract/reference/Results_MLG.csv``.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pytest

from dropsim import default_aircraft_inputs, default_trailing_arm_inputs, run_simulation
from dropsim.simulation import _negative_pressure_warnings

REF_CSV = os.path.join(
    os.path.dirname(__file__), "..", "_extract", "reference", "Results_MLG.csv"
)

# Valeurs de synthèse lues dans la nouvelle simulation de référence
EXCEL_FZ_MAX = 44537.83
EXCEL_FX_MAX = 19145.76
EXCEL_COURSE_MAX_MM = 173.29
FZ_TOL_REL = 0.015  # butée lissée par défaut: léger écart assumé vs référence Excel


@pytest.fixture(scope="module")
def result():
    return run_simulation(default_trailing_arm_inputs())


def test_simulation_runs(result):
    assert result.n_steps > 0
    assert not result.df.empty


def test_course_max(result):
    course = result.summary["Course max (mm)"]
    assert course == pytest.approx(EXCEL_COURSE_MAX_MM, rel=0.01), course


def test_fz_max(result):
    fz = result.summary["Effort vertical max Fz (N)"]
    assert fz == pytest.approx(EXCEL_FZ_MAX, rel=FZ_TOL_REL), fz


def test_fx_max(result):
    fx = result.summary["Effort horizontal max Fx (N)"]
    assert fx == pytest.approx(EXCEL_FX_MAX, rel=0.01), fx


@pytest.mark.skipif(not os.path.exists(REF_CSV), reason="CSV de référence absent")
def test_against_reference_curve(result):
    ref = pd.read_csv(REF_CSV)
    ref_fz = np.nanmax(ref["Tyre.FTyre (N)"].to_numpy())
    ref_d = np.nanmax(ref["MLG.d (m)"].to_numpy()) * 1000.0

    assert result.summary["Effort vertical max Fz (N)"] == pytest.approx(ref_fz, rel=FZ_TOL_REL)
    assert result.summary["Course max (mm)"] == pytest.approx(ref_d, rel=0.01)


def test_negative_pressure_warning_detects_each_channel():
    full = {
        "temps": np.array([0.0, 0.01, 0.02]),
        "pg": np.array([10.0, -0.5, 11.0]),
        "pc": np.array([20.0, 19.0, -1.2]),
        "pd": np.array([5.0, -0.2, 6.0]),
    }

    warnings = _negative_pressure_warnings(full)
    fields = {w.field for w in warnings}

    assert len(warnings) == 3
    assert fields == {"pg", "pc", "pd"}
    assert all(w.code == "PRESSION_NEGATIVE" for w in warnings)


def test_negative_pressure_warning_ignores_positive_series():
    full = {
        "temps": np.array([0.0, 0.01, 0.02]),
        "pg": np.array([10.0, 10.2, 11.0]),
        "pc": np.array([20.0, 19.0, 18.8]),
        "pd": np.array([5.0, 5.1, 6.0]),
    }

    warnings = _negative_pressure_warnings(full)
    assert warnings == []


def test_aircraft_defaults_validate_and_convert_to_si():
    inp = default_aircraft_inputs()

    collector = inp.validate()
    assert not collector.has_errors

    params = inp.to_si()
    assert params.masse == pytest.approx(inp.body.masse)
    assert params.vz == pytest.approx(inp.drop.vz)
    assert params.pitch == pytest.approx(inp.drop.pitch * np.pi / 180.0)
    assert params.nlg.integrator == inp.simulation.integrator
    assert params.mlg.integrator == inp.simulation.integrator
    assert params.nlg.temps_simu == pytest.approx(inp.simulation.temps_simu)
    assert params.mlg.it == pytest.approx(inp.simulation.it)


def test_aircraft_validation_rejects_invalid_global_fields():
    inp = default_aircraft_inputs()
    inp.body.masse = -1.0
    inp.simulation.integrator = "bogus"
    inp.layout.mlg_right_station.y = inp.layout.mlg_left_station.y

    collector = inp.validate()
    assert collector.has_errors
    fields = {err.field for err in collector.errors}
    assert "body.masse" in fields
    assert "simulation.integrator" in fields
    assert "layout.mlg_left_station" in fields


def test_aircraft_to_si_propagates_global_settings_to_nested_gears():
    inp = default_aircraft_inputs()
    inp.simulation.integrator = "euler"
    inp.simulation.temperature = -15.0
    inp.drop.pitch = 3.0
    inp.drop.vx = 52.0

    params = inp.to_si()
    assert params.nlg.integrator == "euler"
    assert params.mlg.integrator == "euler"
    assert params.nlg.vx == pytest.approx(52.0)
    assert params.mlg.vx == pytest.approx(52.0)
    assert params.pitch == pytest.approx(np.deg2rad(3.0))


def test_aircraft_simulation_smoke_runs_with_expected_outputs():
    inp = default_aircraft_inputs()
    result = run_simulation(inp)

    assert result.n_steps > 0
    assert not result.df.empty
    assert "Aircraft.CG.z (m)" in result.df.columns
    assert "Aircraft.Fz total (N)" in result.df.columns
    assert "NLG.d (m)" in result.df.columns
    assert "NLG.Pg (bar)" in result.df.columns
    assert "MLG left.Ftot (N)" in result.df.columns
    assert "MLG right.Pd (bar)" in result.df.columns
