"""Point d'entrée pipeline ``run_pfd_simulation`` : dispatch vers les moteurs PFD."""
import numpy as np

from dropsim import (
    default_strait_strut_inputs,
    default_trailing_arm_inputs,
    run_pfd_simulation,
)


def test_pipeline_dispatch_strait_strut():
    r = run_pfd_simulation(default_strait_strut_inputs())
    assert "fx_b" in r and np.max(np.abs(r["fx_b"])) > 0.0


def test_pipeline_dispatch_trailing_arm():
    r = run_pfd_simulation(default_trailing_arm_inputs())
    # torseur 3D présent (moments au pivot)
    assert "mb_x" in r and np.max(np.abs(r["mb_x"])) > 0.0


def test_pipeline_trailing_arm_mass_option():
    p_in = default_trailing_arm_inputs()
    r0 = run_pfd_simulation(p_in, m_arm=0.0)
    rm = run_pfd_simulation(p_in, m_arm=50.0)
    assert np.max(np.abs(rm["fb_z"] - r0["fb_z"])) > 1.0
