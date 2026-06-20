"""Tests de non-régression du modèle StraitStrut (NLG).

Ce fichier protège le nouveau chemin de calcul NLG contre les dérives
involontaires, indépendamment des tests TrailingArm.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pytest

from dropsim import default_strait_strut_inputs, run_simulation

_HERE = os.path.dirname(__file__)
GOLDEN_JSON = os.path.join(_HERE, "reference", "golden_strait_strut_summary.json")

GOLDEN_RTOL = 1e-4
GOLDEN_ATOL = 1e-6

REGRESSION_CASES: dict[str, dict[str, float]] = {
    "nominal": {},
    "froid": {"temperature": -20.0},
    "lourd": {"masse": 1100.0},
}


def _inputs_for(overrides: dict[str, float]):
    inp = default_strait_strut_inputs()
    for key, value in overrides.items():
        setattr(inp, key, value)
    inp.integrator = "rk4"
    inp.damper_core_solver = "auto_precise"
    return inp


def _load_golden() -> dict:
    with open(GOLDEN_JSON, encoding="utf-8") as fh:
        return json.load(fh)


def regenerate_golden() -> None:
    golden: dict[str, dict] = {}
    for name, overrides in REGRESSION_CASES.items():
        result = run_simulation(_inputs_for(overrides))
        golden[name] = {
            "overrides": overrides,
            "summary": result.summary,
            "summary_rows": [
                [label, value, unit] for (label, value, unit) in result.summary_rows
            ],
        }
    os.makedirs(os.path.dirname(GOLDEN_JSON), exist_ok=True)
    with open(GOLDEN_JSON, "w", encoding="utf-8") as fh:
        json.dump(golden, fh, indent=2, ensure_ascii=False)


@pytest.fixture(scope="module")
def golden() -> dict:
    return _load_golden()


def test_golden_file_present(golden):
    assert set(golden) == set(REGRESSION_CASES)


@pytest.mark.parametrize("case_name", list(REGRESSION_CASES))
def test_golden_summary(case_name, golden):
    ref = golden[case_name]
    result = run_simulation(_inputs_for(REGRESSION_CASES[case_name]))

    assert ref["overrides"] == REGRESSION_CASES[case_name]

    for key, expected in ref["summary"].items():
        actual = result.summary[key]
        if isinstance(expected, float):
            assert actual == pytest.approx(expected, rel=GOLDEN_RTOL, abs=GOLDEN_ATOL)
        else:
            assert actual == expected


@pytest.mark.parametrize("case_name", list(REGRESSION_CASES))
def test_golden_summary_rows(case_name, golden):
    ref_rows = golden[case_name]["summary_rows"]
    result = run_simulation(_inputs_for(REGRESSION_CASES[case_name]))

    assert len(result.summary_rows) == len(ref_rows)
    for (label, value, unit), (ref_label, ref_value, ref_unit) in zip(
        result.summary_rows, ref_rows
    ):
        assert label == ref_label
        assert unit == ref_unit
        assert value == pytest.approx(ref_value, rel=GOLDEN_RTOL, abs=GOLDEN_ATOL)


def test_outputs_are_strait_strut_named():
    result = run_simulation(default_strait_strut_inputs())
    cols = list(result.df.columns)
    assert any(c.startswith("StraitStrut.") for c in cols)
    assert "StraitStrut.d (m)" in cols
    assert "StraitStrut.Ftot (N)" in cols


def test_basic_physical_bounds_hold():
    result = run_simulation(default_strait_strut_inputs())
    s = result.summary

    assert result.n_steps > 0
    assert not result.df.empty

    for key in (
        "Course max (mm)",
        "Effort vertical max Fz (N)",
        "Pression gaz max (bar)",
        "Accélération max (g)",
    ):
        assert np.isfinite(s[key])
        assert s[key] > 0.0

    # Course bornée: tolérance de 20 mm au-delà de la butée mécanique.
    assert s["Course max (mm)"] <= default_strait_strut_inputs().course + 20.0
