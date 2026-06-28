"""Tests du modèle « Train à lame » (leaf spring, PFD §6c)."""
from __future__ import annotations

import numpy as np
from dataclasses import replace

from dropsim import (
    default_aircraft_inputs,
    default_leaf_spring_inputs,
    run_simulation,
)
from dropsim.engine_leaf_spring import leaf_spring_step, run_leaf_spring
from dropsim.inputs import _leaf_geom_si
from dropsim.storage import inputs_from_dict, inputs_to_dict


def test_leaf_defaults():
    inp = default_leaf_spring_inputs()
    assert inp.model_kind == "leaf_spring"
    assert inp.lame_raideur == 2000.0          # N/mm
    assert inp.lame_amortissement == 1000.0     # N/(m/s)
    assert inp.unsprung_mass == 10.0
    assert (inp.B.x, inp.B.y, inp.B.z) == (3500.0, 0.0, 1000.0)


def test_leaf_step_force():
    # F = k·d + c·ḋ ; k en N/m, c en N·s/m.
    f, fs, fd = leaf_spring_step(0.01, 2.0, 2.0e6, 1000.0)
    assert fs == 2.0e6 * 0.01
    assert fd == 1000.0 * 2.0
    assert f == fs + fd


def test_leaf_isolated_energy_closes():
    """Le bilan énergétique se referme au niveau de l'erreur d'intégration."""
    inp = default_leaf_spring_inputs()
    inp.it = 1.0e-5
    res = run_simulation(inp)
    df = res.df
    ein = df["Énergie.Apport total (J)"].to_numpy()
    eres = df["Énergie.Résidu de bilan (J)"].to_numpy()
    ratio = np.max(np.abs(eres)) / max(1.0, np.max(np.abs(ein)))
    assert ratio < 0.01, f"résidu trop élevé : {ratio:.3%}"
    # Quelques sorties cohérentes.
    assert df["LeafSpring.d (m)"].max() > 0.0
    assert df["Tyre.FTyre (N)"].max() > 0.0
    # |Ftot| = |k·d + c·ḋ| cohérent avec FRessort + FAmortisseur.
    np.testing.assert_allclose(
        df["LeafSpring.Ftot (N)"].to_numpy(),
        (df["LeafSpring.FRessort (N)"] + df["LeafSpring.FAmortisseur (N)"]).to_numpy(),
        atol=1e-6,
    )


def test_leaf_vector_engine_matches_geom():
    """Le moteur direct (avec géométrie) tourne et produit un torseur en B."""
    inp = default_leaf_spring_inputs()
    g = _leaf_geom_si(inp)
    out = run_leaf_spring(inp.to_si(), k_leaf=g.k_leaf, c_leaf=g.c_leaf, B_pos=g.B, R_pos=g.R).data
    # Moment de tangage non nul (bras de levier BR horizontal).
    assert np.max(np.abs(out["torsB_mz"])) > 0.0


def test_leaf_roundtrip():
    inp = default_leaf_spring_inputs()
    restored = inputs_from_dict(inputs_to_dict(inp))
    assert restored == inp
    assert restored.model_kind == "leaf_spring"


def test_leaf_aircraft_mode():
    """Un NLG à lame fonctionne en avion complet, bilan énergétique borné."""
    inp = replace(default_aircraft_inputs(), nlg=default_leaf_spring_inputs())
    inp.simulation.it = 2.0e-5
    res = run_simulation(inp)
    fdf = res.full_df
    assert fdf["NLG.d (m)"].max() > 0.0
    assert fdf["NLG.Ftot (N)"].max() > 0.0
    ein = fdf["Énergie.Apport total (J)"].to_numpy()
    eres = fdf["Énergie.Résidu de bilan (J)"].to_numpy()
    assert np.max(np.abs(eres)) / max(1.0, np.max(np.abs(ein))) < 0.05
