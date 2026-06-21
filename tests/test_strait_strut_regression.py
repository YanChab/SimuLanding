"""Tests de non-régression du modèle StraitStrut (NLG).

Ce fichier protège le nouveau chemin de calcul NLG contre les dérives
involontaires, indépendamment des tests TrailingArm.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
import pytest

from dropsim import default_strait_strut_inputs, run_simulation

_HERE = os.path.dirname(__file__)
GOLDEN_JSON = os.path.join(_HERE, "reference", "golden_strait_strut_summary.json")
REF_CSV = os.path.join(_HERE, "..", "_extract", "reference", "Results_NLG.csv")

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


def _first_available_column(df: pd.DataFrame, *names: str) -> str:
    for name in names:
        if name in df.columns:
            return name
    raise KeyError(f"Aucune des colonnes attendues n'est présente: {names}")


@pytest.fixture(scope="module")
def reference_curve() -> pd.DataFrame | None:
    if not os.path.exists(REF_CSV):
        return None
    return pd.read_csv(REF_CSV)


def _interpolate_on_reference_time(
    sim_df: pd.DataFrame,
    ref_df: pd.DataFrame,
    sim_col: str,
    ref_col: str,
    max_time: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    t_ref_name = _first_available_column(ref_df, "Temps (s)", "Temps")
    t_sim_name = _first_available_column(sim_df, "Temps (s)", "Temps")

    t_ref = ref_df[t_ref_name].to_numpy(dtype=float)
    t_sim = sim_df[t_sim_name].to_numpy(dtype=float)
    y_ref = ref_df[ref_col].to_numpy(dtype=float)
    y_sim = sim_df[sim_col].to_numpy(dtype=float)

    valid = np.isfinite(t_ref) & np.isfinite(y_ref)
    t_ref = t_ref[valid]
    y_ref = y_ref[valid]

    if t_ref.size == 0:
        raise AssertionError("Courbe de référence vide après nettoyage")

    in_domain = (t_ref >= t_sim[0]) & (t_ref <= t_sim[-1])
    if max_time is not None:
        in_domain &= t_ref <= max_time
    t_ref = t_ref[in_domain]
    y_ref = y_ref[in_domain]

    if t_ref.size == 0:
        raise AssertionError("Aucun recouvrement temporel entre simulation et référence")

    y_sim_interp = np.interp(t_ref, t_sim, y_sim)
    return y_sim_interp, y_ref


def _rms_error(sim_series: np.ndarray, ref_series: np.ndarray) -> float:
    return float(np.sqrt(np.mean((sim_series - ref_series) ** 2)))



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
@pytest.mark.slow
@pytest.mark.regression
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
@pytest.mark.slow
@pytest.mark.regression
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


@pytest.mark.slow
@pytest.mark.regression
def test_excel_reference_curve_rms(reference_curve):
    if reference_curve is None:
        pytest.skip("Référence NLG absente: _extract/reference/Results_NLG.csv")

    result = run_simulation(default_strait_strut_inputs())
    sim = result.df
    ref = reference_curve
    peak_ref_time = float(
        ref.loc[ref["NLG.d"].astype(float).idxmax(), "Temps (s)"]
    )
    compression_window_end = min(peak_ref_time + 0.02, 0.22)

    metrics = {
        "Tyre.FTyre": {
            "sim_col": "Tyre.FTyre (N)",
            "ref_col": "Tyre.FTyre",
            "rms_max": 1200.0,
            "max_time": compression_window_end,
        },
        "StraitStrut.d": {
            "sim_col": "StraitStrut.d (m)",
            "ref_col": "NLG.d",
            "rms_max": 0.012,
            "max_time": compression_window_end,
        },
        "StraitStrut.Pg": {
            "sim_col": "StraitStrut.Pg (bar)",
            "ref_col": "NLG.Pg",
            "rms_max": 8.0,
            "max_time": compression_window_end,
        },
        "StraitStrut.Pc": {
            "sim_col": "StraitStrut.Pc (bar)",
            "ref_col": "NLG.Pc",
            "rms_max": 28.0,
            "max_time": compression_window_end,
        },
        "StraitStrut.Pd": {
            "sim_col": "StraitStrut.Pd (bar)",
            "ref_col": "NLG.Pd",
            "rms_max": 24.0,
            "max_time": compression_window_end,
        },
    }

    for metric_name, cfg in metrics.items():
        assert cfg["sim_col"] in sim.columns, f"Colonne simulation manquante: {cfg['sim_col']}"
        assert cfg["ref_col"] in ref.columns, f"Colonne référence manquante: {cfg['ref_col']}"
        y_sim, y_ref = _interpolate_on_reference_time(
            sim_df=sim,
            ref_df=ref,
            sim_col=cfg["sim_col"],
            ref_col=cfg["ref_col"],
            max_time=cfg.get("max_time"),
        )
        rms = _rms_error(y_sim, y_ref)
        assert rms <= cfg["rms_max"], (
            f"RMS trop élevée pour {metric_name}: {rms:.6g} > {cfg['rms_max']:.6g}"
        )
