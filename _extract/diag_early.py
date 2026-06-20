"""Diagnostic pas-à-pas : engine Python vs CSV frais sur les premiers instants."""
import numpy as np
import pandas as pd

from dropsim import default_trailing_arm_inputs
from dropsim.engine import run_trailing_arm

fresh = pd.read_csv("_extract/reference/Results_MLG_fresh.csv")
t = pd.to_numeric(fresh["Temps (s)"], errors="coerce").to_numpy()


def fcol(name):
    for c in fresh.columns:
        if name == str(c).strip():
            return pd.to_numeric(fresh[c], errors="coerce").to_numpy()
    for c in fresh.columns:
        if name in str(c):
            return pd.to_numeric(fresh[c], errors="coerce").to_numpy()
    return None


o = run_trailing_arm(default_trailing_arm_inputs().to_si())
D = o.data

pairs = [
    ("AccMs", "AccMs.RsolZ", "accms"),
    ("VitMs", "VitMs.RsolZ", "vitms"),
    ("ThAY", "ThAY", "th_ay"),
    ("ThRY", "ThRY", "th_ry"),
    ("Tdefl", "Tyre.Defl", "tyre_defl"),
    ("Ftyre", "Tyre.FTyre", "tyre_ftyre"),
    ("v", "MLG.v", "trailing_arm_v"),
    ("d_mm", "MLG.d", "trailing_arm_d"),
    ("Pc", "MLG.Pc", "pc"),
    ("Pg", "MLG.Pg", "pg"),
    ("Sec", "Section de la BH", None),
]

print("keys py:", [k for k in D.keys()])
for tt in [0.0, 0.0005, 0.001, 0.002, 0.004, 0.006, 0.01, 0.015, 0.02]:
    j = int(np.nanargmin(np.abs(t - tt)))
    i = int(round(tt / 0.0001))
    print(f"\n--- t={tt} (fresh row {j}, py idx {i}) ---")
    for label, fname, pyname in pairs:
        fv = fcol(fname)
        fv = fv[j] if fv is not None else float("nan")
        if pyname and pyname in D:
            pv = D[pyname][i]
        else:
            pv = float("nan")
        scale = 1000.0 if label == "d_mm" else 1.0
        print(f"  {label:7s} fresh {fv*scale:12.5f} | py {pv*scale:12.5f}")
