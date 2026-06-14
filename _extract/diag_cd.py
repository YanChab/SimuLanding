import math
from dropsim import default_mlg_inputs
from dropsim.hydraulic import _cd, calcul_hydrau

p = default_mlg_inputs().to_si()
print("Sc=", p.Sc, "Sd=", p.Sd, "bulk=", p.bulk, "it=", p.it, "rho=", p.rho, "visc=", p.visc, "course=", p.course)

# Conditions fresh à t=0.006
v = 0.12283
d = 9.75e-5
sec = 6.364065497194127e-6
pg = 9.92339e5  # Pa
pc_prev = 10.40e5  # estimation (Pc juste avant ~10.4 bar)

qc = p.Sc * v
deq = math.sqrt(math.pi * sec / 4.0)
re_bh = (abs(qc) * deq / sec) / p.visc
arg = re_bh * deq
cd = _cd(arg, 0.003)
print(f"qc={qc:.6e} deq={deq:.6e} re_bh={re_bh:.3e} re*deq={arg:.4f} regime={'lam' if arg/0.003<50 else 'turb'} cd={cd:.5f}")
dpc_direct = 0.5 * p.rho * (qc / (sec * cd)) ** 2
print(f"DeltaPc direct (sans compress) = {dpc_direct/1e5:.4f} bar  (fresh=1.709)")

dpc, dpd, qcf = calcul_hydrau(p, v, d, pc_prev, pg, sec)
print(f"DeltaPc via calcul_hydrau (avec compress) = {dpc/1e5:.4f} bar  qc_final={qcf:.6e}")
