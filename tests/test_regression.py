"""Tests de **non-régression** du moteur `dropsim` (cf. *Améliorations §5.1*).

Objectif : protéger les évolutions futures (intégrateur, butée lissée, raffinements
physiques) contre toute dérive **involontaire** des résultats. Trois familles :

1. **Golden tests de synthèse** — fige un *snapshot* des grandeurs de synthèse
   (``summary`` + ``summary_rows``, équivalent du bloc B46:C61 « Summary MLG »)
   pour plusieurs cas (nominal, froid/lourd, léger/lent) et compare à tolérance
   serrée. Détecte toute dérive sur **n'importe quelle** grandeur de sortie.
2. **Non-régression de courbe** — compare la courbe complète au CSV de référence
   Excel (``_extract/reference/Results_MLG.csv``) non seulement sur les pics mais
   aussi en **écart RMS** sur tout l'historique temporel.
3. **Invariants physiques** — sur un balayage masse/vitesse/température, vérifie
   des **monotonies** physiques (Fz croît avec la masse, course croît avec
   l'énergie d'impact…) et la bonne **terminaison** aux bornes.

Régénération du golden (après un changement de physique *assumé*) :

    python -c "import tests.test_regression as t; t.regenerate_golden()"

Le fichier ``tests/reference/golden_summary.json`` doit alors être relu, validé
et committé sciemment.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
import pytest

from dropsim import default_trailing_arm_inputs, run_simulation

# --------------------------------------------------------------------------- #
#  Chemins de référence
# --------------------------------------------------------------------------- #
_HERE = os.path.dirname(__file__)
GOLDEN_JSON = os.path.join(_HERE, "reference", "golden_summary.json")
REF_CSV = os.path.join(_HERE, "..", "_extract", "reference", "Results_MLG.csv")

# Tolérance relative sur les grandeurs de synthèse (golden). Suffisamment serrée
# pour attraper toute dérive réelle, tout en absorbant les variations d'arrondi
# entre plateformes (BLAS, ordre de réduction…).
GOLDEN_RTOL = 1e-4
GOLDEN_ATOL = 1e-6


# --------------------------------------------------------------------------- #
#  Définition des cas de référence (doit rester synchronisée avec le golden)
# --------------------------------------------------------------------------- #
# Chaque cas applique des surcharges aux entrées nominales. Tout ajout/retrait
# ici implique une régénération du golden (cf. regenerate_golden).
REGRESSION_CASES: dict[str, dict[str, float]] = {
    "nominal": {},
    "froid_lourd": {"temperature": -20.0, "masse": 1400.0},
    "leger_lent": {"masse": 1000.0, "vz": 2.0, "vx": 20.0},
}


def _inputs_for(overrides: dict[str, float]):
    inp = default_trailing_arm_inputs()
    for key, value in overrides.items():
        setattr(inp, key, value)
    return inp


def _precise_inputs_for(overrides: dict[str, float]):
    inp = _inputs_for(overrides)
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


def regenerate_golden() -> None:
    """Régénère ``golden_summary.json`` à partir des cas de référence.

    À n'utiliser **qu'après** un changement de physique délibéré : relire et
    committer le fichier produit en connaissance de cause.
    """
    golden: dict[str, dict] = {}
    for name, overrides in REGRESSION_CASES.items():
        result = run_simulation(_precise_inputs_for(overrides))
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


# --------------------------------------------------------------------------- #
#  1. Golden tests de synthèse
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def golden() -> dict:
    return _load_golden()


def test_golden_file_present(golden):
    assert set(golden) == set(REGRESSION_CASES), (
        "Le golden et REGRESSION_CASES doivent décrire les mêmes cas."
    )


@pytest.mark.parametrize("case_name", list(REGRESSION_CASES))
def test_golden_summary(case_name, golden):
    ref = golden[case_name]
    result = run_simulation(_precise_inputs_for(REGRESSION_CASES[case_name]))

    # Les surcharges enregistrées doivent correspondre à celles du test.
    assert ref["overrides"] == REGRESSION_CASES[case_name]

    # 1a. Bloc summary (dict clé -> valeur).
    for key, expected in ref["summary"].items():
        actual = result.summary[key]
        if isinstance(expected, float):
            assert actual == pytest.approx(expected, rel=GOLDEN_RTOL, abs=GOLDEN_ATOL), (
                f"[{case_name}] summary['{key}'] : {actual} ≠ {expected}"
            )
        else:  # int (nombre de pas) -> égalité stricte
            assert actual == expected, f"[{case_name}] summary['{key}']"


@pytest.mark.parametrize("case_name", list(REGRESSION_CASES))
def test_golden_summary_rows(case_name, golden):
    ref_rows = golden[case_name]["summary_rows"]
    result = run_simulation(_precise_inputs_for(REGRESSION_CASES[case_name]))

    assert len(result.summary_rows) == len(ref_rows)
    for (label, value, unit), (ref_label, ref_value, ref_unit) in zip(
        result.summary_rows, ref_rows
    ):
        assert label == ref_label, f"[{case_name}] libellé : {label} ≠ {ref_label}"
        assert unit == ref_unit, f"[{case_name}] unité ({label}) : {unit} ≠ {ref_unit}"
        assert value == pytest.approx(ref_value, rel=GOLDEN_RTOL, abs=GOLDEN_ATOL), (
            f"[{case_name}] '{label}' : {value} ≠ {ref_value}"
        )


# --------------------------------------------------------------------------- #
#  2. Non-régression de courbe contre le CSV Excel de référence
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def reference_curve() -> pd.DataFrame | None:
    if not os.path.exists(REF_CSV):
        return None
    return pd.read_csv(REF_CSV)


@pytest.mark.skipif(not os.path.exists(REF_CSV), reason="CSV de référence absent")
def test_curve_fz_rms_against_excel(reference_curve):
    """Écart RMS sur toute la courbe d'effort vertical Fz(t) vs Excel < 2 %.

    Contrôle plus exigeant que la seule comparaison des pics : valide la *forme*
    de la réponse temporelle sur l'ensemble de l'historique.
    """
    result = run_simulation(default_trailing_arm_inputs())
    sim = result.df

    t_ref = reference_curve["Temps (s)"].to_numpy()
    fz_ref = reference_curve["Tyre.FTyre (N)"].to_numpy()
    t_sim = sim["Temps (s)"].to_numpy()
    fz_sim = sim["Tyre.FTyre (N)"].to_numpy()

    # Rééchantillonnage du modèle sur la base de temps de référence.
    fz_sim_on_ref = np.interp(t_ref, t_sim, fz_sim)
    rms = float(np.sqrt(np.mean((fz_sim_on_ref - fz_ref) ** 2)))
    peak = float(np.max(np.abs(fz_ref)))
    assert rms <= 0.02 * peak, f"RMS Fz {rms:.0f} N > 2 % du pic ({0.02 * peak:.0f} N)"


@pytest.mark.skipif(not os.path.exists(REF_CSV), reason="CSV de référence absent")
def test_curve_stroke_rms_against_excel(reference_curve):
    """Écart RMS sur la course d'amortisseur d(t) vs Excel < 2 % de la course max."""
    result = run_simulation(default_trailing_arm_inputs())
    sim = result.df
    ref_stroke_col = _first_available_column(
        reference_curve, "TrailingArm.d (m)", "MLG.d (m)"
    )
    sim_stroke_col = _first_available_column(sim, "TrailingArm.d (m)", "MLG.d (m)")

    t_ref = reference_curve["Temps (s)"].to_numpy()
    d_ref = reference_curve[ref_stroke_col].to_numpy()
    t_sim = sim["Temps (s)"].to_numpy()
    d_sim = sim[sim_stroke_col].to_numpy()

    d_sim_on_ref = np.interp(t_ref, t_sim, d_sim)
    rms = float(np.sqrt(np.mean((d_sim_on_ref - d_ref) ** 2)))
    peak = float(np.max(np.abs(d_ref)))
    assert rms <= 0.02 * peak, f"RMS course {rms * 1000:.1f} mm > 2 % du pic"


# --------------------------------------------------------------------------- #
#  3. Invariants physiques sur un balayage paramétrique
# --------------------------------------------------------------------------- #
def test_fz_increases_with_mass():
    """À vitesse fixée, l'effort vertical max croît avec la masse supportée."""
    masses = [900.0, 1250.0, 1600.0]
    fz = [
        run_simulation(_inputs_for({"masse": m})).summary["Effort vertical max Fz (N)"]
        for m in masses
    ]
    assert fz[0] < fz[1] < fz[2], f"Fz non monotone vs masse : {fz}"


def test_stroke_increases_with_impact_velocity():
    """À masse fixée, la course max croît avec la vitesse verticale d'impact."""
    vitesses = [2.0, 3.05, 4.0]
    stroke = [
        run_simulation(_inputs_for({"vz": v})).summary["Course max (mm)"]
        for v in vitesses
    ]
    assert stroke[0] < stroke[1] < stroke[2], f"Course non monotone vs Vz : {stroke}"


def test_fx_increases_with_forward_velocity():
    """À masse fixée, l'effort horizontal de spin-up croît avec la vitesse avion."""
    vx_values = [10.0, 25.0, 39.0]
    fx = [
        run_simulation(_inputs_for({"vx": v})).summary["Effort horizontal max Fx (N)"]
        for v in vx_values
    ]
    assert fx[0] < fx[1] < fx[2], f"Fx non monotone vs Vx : {fx}"


@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {"masse": 1000.0},
        {"masse": 1600.0},
        {"vz": 2.0},
        {"vz": 4.0},
        {"vx": 0.0},
        {"vx": 39.0},
        {"temperature": -40.0},
        {"temperature": 60.0},
    ],
)
def test_physical_bounds_hold(overrides):
    """Sur tout le balayage : grandeurs finies, positives et physiquement bornées."""
    result = run_simulation(_inputs_for(overrides))
    s = result.summary

    # Terminaison correcte.
    assert result.n_steps > 0
    assert not result.df.empty

    # Positivité et finitude des grandeurs clés.
    for key in (
        "Course max (mm)",
        "Effort vertical max Fz (N)",
        "Pression gaz max (bar)",
        "Accélération max (g)",
    ):
        assert np.isfinite(s[key]), f"{key} non fini ({overrides})"
        assert s[key] > 0.0, f"{key} ≤ 0 ({overrides})"

    # La course reste bornée : la butée de fin de course est un ressort raide
    # (K = 1e8 N/m) qui autorise une légère pénétration physique au-delà de la
    # course mécanique. On tolère cette pénétration (quelques mm) mais on
    # détecte toute divergence (course aberrante de plusieurs cm).
    course_max_mm = default_trailing_arm_inputs().course
    assert s["Course max (mm)"] <= course_max_mm + 15.0, (
        f"Course {s['Course max (mm)']:.1f} mm bien au-delà de la butée "
        f"{course_max_mm} mm ({overrides}) — divergence probable"
    )

    # Sans vitesse d'avancement, pas d'effort de spin-up.
    if overrides.get("vx", default_trailing_arm_inputs().vx) == 0.0:
        assert s["Effort horizontal max Fx (N)"] == pytest.approx(0.0, abs=1.0)
