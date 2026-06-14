"""Compare le moteur Python à la référence Excel FRAÎCHE (mêmes cotes courantes)."""
import numpy as np
import pandas as pd

from dropsim import default_mlg_inputs
from dropsim.engine import run_mlg

fresh = pd.read_csv("_extract/reference/Results_MLG_fresh.csv")
sec = pd.read_csv("_extract/reference/section_fresh.csv")


def col(df, name):
    for c in df.columns:
        if name in str(c):
            return pd.to_numeric(df[c], errors="coerce").to_numpy()
    return None


o = run_mlg(default_mlg_inputs().to_si())
D = o.data

fz = col(fresh, "FTyre")
fx = col(fresh, "TR_bal.RsolX")
dd = col(fresh, "MLG.d")
pg = col(fresh, "Pg")
pc = col(fresh, "Pc")

print("section fresh @0..3mm:", sec["section_mm2"].head(4).tolist())
print("=== FRESH (Excel, cotes actuelles) vs PYTHON ===")
print("Course max mm: fresh", round(np.nanmax(dd) * 1000, 2), "| py", round(np.nanmax(D["mlg_d"]) * 1000, 2))
print("Fz tyre max  : fresh", round(np.nanmax(fz), 1), "| py", round(np.nanmax(D["tyre_ftyre"]), 1))
if fx is not None:
    print("Fx max       : fresh", round(np.nanmax(np.abs(fx)), 1), "| py", round(np.nanmax(np.abs(D["tr_x"])), 1))
print("Pg max bar   : fresh", round(np.nanmax(pg), 2), "| py", round(np.nanmax(D["pg"]), 2))
print("Pc max bar   : fresh", round(np.nanmax(pc), 2), "| py", round(np.nanmax(D["pc"]), 2))

# Comparaison alignée dans le temps
t = col(fresh, "Temps")
print("\n=== Aligné dans le temps ===")
for tt in [0.01, 0.02, 0.03, 0.05, 0.08, 0.12]:
    j = int(np.nanargmin(np.abs(t - tt)))
    i = int(round(tt / 0.0001))
    print(
        f"t={tt}",
        "| v", round(col(fresh, "MLG.v")[j], 3), round(D["mlg_v"][i], 3),
        "| d_mm", round(dd[j] * 1000, 2), round(D["mlg_d"][i] * 1000, 2),
        "| Fz", round(fz[j], 0), round(D["tyre_ftyre"][i], 0),
        "| Pc", round(pc[j], 1), round(D["pc"][i], 1),
    )
