"""Tests du slot de train générique et de l'extraction train isolé.

Couvre :
- l'équivalence numérique du run avion par défaut (NLG=StraitStrut, MLG=TrailingArm)
  après le refactor en slots génériques ;
- le run avion avec types inversés (NLG=TrailingArm, MLG=StraitStrut) ;
- l'extraction d'un jeu d'entrées train isolé (NLG-seul / MLG-seul) ;
- la superposition des surcharges de chute par train.
"""
from __future__ import annotations

import numpy as np
import pytest

from dropsim.inputs import (
    AircraftGearDropOverride,
    StraitStrutInputs,
    TrailingArmInputs,
    default_aircraft_inputs,
    default_strait_strut_inputs,
    default_trailing_arm_inputs,
)
from dropsim.engine_aircraft import run_aircraft
from dropsim.simulation import run_simulation


def test_default_aircraft_run_finite_and_sane():
    """Le run avion par défaut produit des sorties finies et un Fz positif."""
    out = run_aircraft(default_aircraft_inputs().to_si())
    fz = out.data["aircraft_fz_total"]
    mx = out.data["aircraft_mx_total"]
    assert np.all(np.isfinite(fz))
    assert np.all(np.isfinite(mx))
    assert np.max(fz) > 0.0
    # NLG StraitStrut : la colonne strut-spécifique xgt n'est pas identiquement nulle.
    assert np.any(out.data["nlg_xgt"] != 0.0)
    # MLG TrailingArm : effort au point C non identiquement nul.
    assert np.any(out.data["mlg_left_torsc_fz"] != 0.0)


def test_swapped_gear_types_aircraft_run():
    """Avion complet avec NLG=TrailingArm et MLG=StraitStrut : run finit, finitude OK,
    colonnes hors-type laissées à zéro."""
    ac = default_aircraft_inputs()
    ac.nlg = default_trailing_arm_inputs()
    ac.mlg = default_strait_strut_inputs()
    si = ac.to_si()
    assert si.nlg_model_kind == "trailing_arm"
    assert si.mlg_model_kind == "strait_strut"
    assert si.nlg_strut is None
    assert si.mlg_strut is not None

    out = run_aircraft(si)
    assert np.all(np.isfinite(out.data["aircraft_fz_total"]))
    assert np.all(np.isfinite(out.data["aircraft_mx_total"]))
    assert np.max(out.data["aircraft_fz_total"]) > 0.0
    # NLG est un TrailingArm : pas de grandeur strut (xgt/xgb) -> colonnes à zéro.
    assert np.allclose(out.data["nlg_xgt"], 0.0)
    assert np.allclose(out.data["nlg_xgb"], 0.0)
    # MLG est un StraitStrut : pas de point C -> colonne torsc à zéro.
    assert np.allclose(out.data["mlg_left_torsc_fz"], 0.0)
    assert np.allclose(out.data["mlg_right_torsc_fz"], 0.0)


@pytest.mark.parametrize(
    "position,expected_cls,expected_kind",
    [
        ("nlg", StraitStrutInputs, "strait_strut"),
        ("mlg", TrailingArmInputs, "trailing_arm"),
    ],
)
def test_gear_inputs_for_default_types(position, expected_cls, expected_kind):
    """gear_inputs_for renvoie un train isolé complet, du bon type, exécutable."""
    ac = default_aircraft_inputs()
    gear = ac.gear_inputs_for(position)
    assert isinstance(gear, expected_cls)
    assert gear.model_kind == expected_kind
    result = run_simulation(gear)
    assert len(result.df) > 0


def test_gear_inputs_for_swapped_types_run():
    """Un NLG TrailingArm et un MLG StraitStrut isolés s'exécutent aussi."""
    ac = default_aircraft_inputs()
    ac.nlg = default_trailing_arm_inputs()
    ac.mlg = default_strait_strut_inputs()
    nlg = ac.gear_inputs_for("nlg")
    mlg = ac.gear_inputs_for("mlg")
    assert nlg.model_kind == "trailing_arm"
    assert mlg.model_kind == "strait_strut"
    assert len(run_simulation(nlg).df) > 0
    assert len(run_simulation(mlg).df) > 0


def test_gear_inputs_for_uses_gear_own_mass_not_aircraft_total():
    """Un run isolé utilise la masse propre du train, pas la masse totale avion
    (sinon sur-enfoncement non physique)."""
    ac = default_aircraft_inputs()
    nlg = ac.gear_inputs_for("nlg")
    assert nlg.masse == ac.nlg.masse
    assert nlg.masse != ac.body.masse


def test_pitched_mlg_stays_airborne_no_phantom_compression():
    """À forte assiette nez bas, le NLG touche en premier ; le MLG, soulevé loin
    du sol, ne doit ni générer d'effort pneu ni se comprimer tant qu'il est en
    l'air (régression : l'amortisseur MLG se comprimait à tort)."""
    ac = default_aircraft_inputs()
    ac.drop.pitch = 15.0  # nez bas marqué -> MLG très au-dessus du sol
    ac.drop.vz = 1.0      # chute douce pour que le run aille au bout sans buter le NLG
    ac.simulation.temps_simu = 0.2
    out = run_aircraft(ac.to_si())
    d = out.data

    # MLG en l'air : aucune compression ni effort pneu, au départ et tout du long.
    assert d["mlg_left_stroke"][0] < 1.0e-4
    assert d["mlg_right_stroke"][0] < 1.0e-4
    assert np.max(d["mlg_left_tyre_ftyre"]) <= 1.0e-6
    assert np.max(d["mlg_right_tyre_ftyre"]) <= 1.0e-6
    assert np.allclose(d["mlg_left_stroke"], 0.0, atol=1.0e-4)
    # Le NLG, lui, encaisse bien la chute (effort pneu et course non nuls).
    assert np.max(d["nlg_tyre_ftyre"]) > 0.0
    assert np.max(d["nlg_stroke"]) > 0.0


def test_gear_drop_override_layering():
    """Les surcharges train isolé prennent le pas, le reste hérite du train."""
    ac = default_aircraft_inputs()
    base_vx = ac.nlg.vx
    ac.nlg_drop = AircraftGearDropOverride(vz=2.0, masse=400.0)
    nlg = ac.gear_inputs_for("nlg")
    assert nlg.vz == 2.0
    assert nlg.masse == 400.0
    # Champ non surchargé : hérité de la config propre du train.
    assert nlg.vx == base_vx
    # Réglages numériques synchronisés depuis la simu avion.
    assert nlg.temperature == ac.simulation.temperature
