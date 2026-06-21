"""Non-regression du mode avion complet.

La reference initiale de ce lot est volontairement basee sur le comportement du
mode avion complet Python valide dans le projet, et non sur le fichier Excel.
Quand une nouvelle reference metier sera choisie, regenerer explicitement le
fichier golden et le relire avant commit.

Regeneration:

    /Users/neoyan/SimuLanding/.venv/bin/python -c "import tests.test_aircraft_regression as t; t.regenerate_golden()"
"""
from __future__ import annotations

import json
import os

import pytest

from dropsim import default_aircraft_inputs, run_simulation

_HERE = os.path.dirname(__file__)
GOLDEN_JSON = os.path.join(_HERE, "reference", "golden_aircraft_summary.json")
GOLDEN_RTOL = 1e-4
GOLDEN_ATOL = 1e-6
FINAL_ATOL = 5e-2

EXPECTED_FINAL_KEYS: tuple[str, ...] = (
    "Aircraft.CG.z (m)",
    "Aircraft.CG.vz (m/s)",
    "Aircraft.Pitch (rad)",
    "Aircraft.PitchRate (rad/s)",
    "Aircraft.Fz total (N)",
    "NLG.d (m)",
    "MLG left.d (m)",
    "MLG right.d (m)",
)

AIRCRAFT_REGRESSION_CASES: dict[str, dict[str, float]] = {
    "nominal": {},
}


def _inputs_for(overrides: dict[str, float]):
    inp = default_aircraft_inputs()
    for key, value in overrides.items():
        if hasattr(inp.drop, key):
            setattr(inp.drop, key, value)
        elif hasattr(inp.body, key):
            setattr(inp.body, key, value)
        elif hasattr(inp.simulation, key):
            setattr(inp.simulation, key, value)
        else:
            raise AttributeError(f"Champ avion non gere pour override: {key}")
    return inp


def _load_golden() -> dict:
    with open(GOLDEN_JSON, encoding="utf-8") as fh:
        return json.load(fh)


def regenerate_golden() -> None:
    golden: dict[str, dict] = {}
    for name, overrides in AIRCRAFT_REGRESSION_CASES.items():
        result = run_simulation(_inputs_for(overrides))
        df = result.df
        golden[name] = {
            "summary": result.summary,
            "final": {
                key: float(df[key].iloc[-1])
                for key in EXPECTED_FINAL_KEYS
            },
            "columns": list(df.columns),
        }
    os.makedirs(os.path.dirname(GOLDEN_JSON), exist_ok=True)
    with open(GOLDEN_JSON, "w", encoding="utf-8") as fh:
        json.dump(golden, fh, indent=2, ensure_ascii=False)


@pytest.fixture(scope="module")
def golden() -> dict:
    return _load_golden()


def test_aircraft_golden_file_present(golden):
    assert set(golden) == set(AIRCRAFT_REGRESSION_CASES)


def test_aircraft_golden_structure_strict(golden):
    for case_name in AIRCRAFT_REGRESSION_CASES:
        ref = golden[case_name]
        assert set(ref.keys()) == {"summary", "final", "columns"}, (
            f"[{case_name}] top-level keys invalid: {set(ref.keys())}"
        )
        assert isinstance(ref["summary"], dict), f"[{case_name}] summary must be a dict"
        assert isinstance(ref["final"], dict), f"[{case_name}] final must be a dict"
        assert isinstance(ref["columns"], list), f"[{case_name}] columns must be a list"
        assert set(ref["final"].keys()) == set(EXPECTED_FINAL_KEYS), (
            f"[{case_name}] final keys invalid: {set(ref['final'].keys())}"
        )
        assert len(ref["columns"]) > 0, f"[{case_name}] columns must not be empty"
        for key, value in ref["final"].items():
            assert isinstance(value, (int, float)), f"[{case_name}] final['{key}'] must be numeric"



@pytest.mark.slow
@pytest.mark.regression
@pytest.mark.parametrize("case_name", list(AIRCRAFT_REGRESSION_CASES))
def test_aircraft_golden_summary(case_name, golden):
    result = run_simulation(_inputs_for(AIRCRAFT_REGRESSION_CASES[case_name]))
    ref = golden[case_name]

    for key, expected in ref["summary"].items():
        actual = result.summary[key]
        if isinstance(expected, float):
            assert actual == pytest.approx(expected, rel=GOLDEN_RTOL, abs=GOLDEN_ATOL), (
                f"[{case_name}] summary['{key}'] : {actual} != {expected}"
            )
        else:
            assert actual == expected, f"[{case_name}] summary['{key}']"


@pytest.mark.slow
@pytest.mark.regression
@pytest.mark.parametrize("case_name", list(AIRCRAFT_REGRESSION_CASES))
def test_aircraft_golden_final_state(case_name, golden):
    result = run_simulation(_inputs_for(AIRCRAFT_REGRESSION_CASES[case_name]))
    df = result.df
    ref = golden[case_name]

    assert list(df.columns) == ref["columns"]
    for key, expected in ref["final"].items():
        actual = float(df[key].iloc[-1])
        assert actual == pytest.approx(expected, rel=GOLDEN_RTOL, abs=FINAL_ATOL), (
            f"[{case_name}] final['{key}'] : {actual} != {expected}"
        )
