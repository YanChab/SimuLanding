"""Compare ma table de section (build_section_table) à la table VBA fraîche."""
import numpy as np
import pandas as pd

from dropsim import default_mlg_inputs
from dropsim.metering import build_section_table, section_bh

sec = pd.read_csv("_extract/reference/section_fresh.csv")
pos_mm = pd.to_numeric(sec["pos_mm"], errors="coerce").to_numpy()
sec_mm2 = pd.to_numeric(sec["section_mm2"], errors="coerce").to_numpy()

p = default_mlg_inputs().to_si()
tab_pos, tab_sec = build_section_table(p)

print("m(mm) | VBA_mm2 | mine_mm2")
for m in [0, 5, 10, 15, 16, 17, 18, 20, 25, 30, 40, 50, 60, 70, 90, 120, 150, 180]:
    # VBA table indexée par m (ligne m)
    vba = sec_mm2[m] if m < len(sec_mm2) else float("nan")
    # ma section à la course d = m mm
    mine = section_bh(m / 1000.0, tab_pos, tab_sec) * 1e6
    print(f"{m:5d} | {vba:8.3f} | {mine:8.3f}")
