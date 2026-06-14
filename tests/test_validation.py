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

from dropsim import default_mlg_inputs, run_simulation

REF_CSV = os.path.join(
    os.path.dirname(__file__), "..", "_extract", "reference", "Results_MLG.csv"
)

# Valeurs de synthèse lues dans l'onglet MLG (C26..C28)
EXCEL_FZ_MAX = 47311.0
EXCEL_FX_MAX = 17811.0
EXCEL_COURSE_MAX_MM = 172.11


@pytest.fixture(scope="module")
def result():
    return run_simulation(default_mlg_inputs())


def test_simulation_runs(result):
    assert result.n_steps > 0
    assert not result.df.empty


def test_course_max(result):
    course = result.summary["Course max (mm)"]
    assert course == pytest.approx(EXCEL_COURSE_MAX_MM, rel=0.01), course


def test_fz_max(result):
    fz = result.summary["Effort vertical max Fz (N)"]
    assert fz == pytest.approx(EXCEL_FZ_MAX, rel=0.01), fz


def test_fx_max(result):
    fx = result.summary["Effort horizontal max Fx (N)"]
    assert fx == pytest.approx(EXCEL_FX_MAX, rel=0.01), fx


@pytest.mark.skipif(not os.path.exists(REF_CSV), reason="CSV de référence absent")
def test_against_reference_curve(result):
    ref = pd.read_csv(REF_CSV)
    ref_fz = np.nanmax(ref["Tyre.FTyre (N)"].to_numpy())
    ref_d = np.nanmax(ref["MLG.d (m)"].to_numpy()) * 1000.0

    assert result.summary["Effort vertical max Fz (N)"] == pytest.approx(ref_fz, rel=0.01)
    assert result.summary["Course max (mm)"] == pytest.approx(ref_d, rel=0.01)
