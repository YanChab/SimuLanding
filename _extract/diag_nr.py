import math
import numpy as np
from dropsim import default_mlg_inputs
from dropsim.hydraulic import _cd

p = default_mlg_inputs().to_si()

v = 0.12283
d = 9.75e-5
sec = 6.364065497194127e-6
pg = 9.92339e5
rho = p.rho

qc0 = p.Sc * v
deq = math.sqrt(math.pi * sec / 4.0)
re_bh = (abs(qc0) * deq / sec) / p.visc
cd = _cd(re_bh * deq, 0.003)
inv_scd2 = (1.0 / (sec * cd)) ** 2


def nr(pc_prev, n):
    coupl = p.Sc * (p.course - d) / (p.bulk * p.it)
    x = np.array([pc_prev, qc0], dtype=float)
    traj = []
    for _ in range(n):
        f0 = x[1] - p.Sc * v + coupl * (x[0] - pc_prev)
        f1 = (x[0] - pg) - 0.5 * rho * (x[1] ** 2) * inv_scd2 * np.sign(x[1])
        jac = np.array([[coupl, 1.0], [1.0, -x[1] * rho * inv_scd2 * np.sign(x[1])]])
        x = x - np.linalg.solve(jac, np.array([f0, f1]))
        traj.append((x[0] / 1e5, x[1], (x[0] - pg) / 1e5))
    return traj


for pcp in [10.4e5, 11.0e5, 11.6e5]:
    print(f"\npc_prev={pcp/1e5:.2f} bar  (coupl={p.Sc*(p.course-d)/(p.bulk*p.it):.3e})")
    for it, (pc, q, dpc) in enumerate(nr(pcp, 8), 1):
        print(f"  iter{it}: Pc={pc:8.4f} bar  Qc={q:.4e}  DeltaPc={dpc:.4f} bar")
print("\nfresh DeltaPc cible = 1.709 bar, Pc=11.632")
