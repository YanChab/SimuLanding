import math
import numpy as np
from dropsim import default_trailing_arm_inputs
from dropsim.hydraulic import _cd

p = default_trailing_arm_inputs().to_si()
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
coupl = p.Sc * (p.course - d) / (p.bulk * p.it)


def vba_exact(dpc_prev, niter=4):
    """Reproduit EXACTEMENT le schéma VBA : MLG.Pc = Pg + mDeltaPc évolue, 4 iters."""
    m_delta_pc = dpc_prev
    x0 = pg + m_delta_pc   # xRes(0) = MLG.Pc à l'entrée
    x1 = qc0               # xRes(1) = MLG.Qc = Sc*v
    for i in range(niter):
        pc_ref = pg + m_delta_pc   # MLG.Pc property (live, évolue)
        f0 = x1 - p.Sc * v + coupl * (x0 - pc_ref)
        f1 = (x0 - pg) - 0.5 * rho * (x1 ** 2) * inv_scd2 * np.sign(x1)
        jac = np.array([[coupl, 1.0], [1.0, -x1 * rho * inv_scd2 * np.sign(x1)]])
        dx = np.linalg.solve(jac, np.array([f0, f1]))
        x0 -= dx[0]
        x1 -= dx[1]
        m_delta_pc = x0 - pg   # MLG.DeltaPc = xRes(0) - Pg  (mise à jour DANS la boucle)
    return (x0 - pg) / 1e5, x1


print(f"coupl={coupl:.4e}  direct_dpc={0.5*rho*(qc0/(sec*cd))**2/1e5:.3f} bar")
print("fresh cible: DeltaPc=1.709 bar, Qc~9.75e-5\n")
for dpcp in [0.0, 0.3e5, 0.5e5, 0.6e5, 1.0e5]:
    dpc, q = vba_exact(dpcp, 4)
    print(f"dpc_prev={dpcp/1e5:.2f} bar -> DeltaPc={dpc:.4f} bar  Qc={q:.4e}")
