"""Rétro-ingénierie des paramètres (r1, r2, e) de la loi de section VBA."""
import math


def lens(e, r1, r2):
    a1 = (e * e + r1 * r1 - r2 * r2) / (2.0 * e * r1)
    a2 = (e * e + r2 * r2 - r1 * r1) / (2.0 * e * r2)
    a1 = min(1.0, max(-1.0, a1))
    a2 = min(1.0, max(-1.0, a2))
    rad = (-e + r1 + r2) * (e + r1 - r2) * (e - r1 + r2) * (e + r1 + r2)
    rad = max(0.0, rad)
    return r1 * r1 * math.acos(a1) + r2 * r2 * math.acos(a2) - 0.5 * math.sqrt(rad)


# Cibles VBA (fresh): base(16.5)+2*lens(17)=6.364 ; lens(15.5)=8.597
print("Hypothèse e = prof + r2 (formule lue), r1=17, r2=10 :")
for prof in [15.5, 16, 16.5, 17]:
    print(f"  prof={prof}: lens={lens(prof + 10, 17, 10):.3f}")

print("\nHypothèse e = r1 - prof + r2 :")
for prof in [15.5, 16, 16.5, 17]:
    e = 17 - prof + 10
    print(f"  prof={prof}: e={e}: lens={lens(e, 17, 10):.3f}")

print("\nHypothèse e = prof (sans +r2), r1=17, r2=10 :")
for prof in [15.5, 16, 16.5, 17]:
    print(f"  prof={prof}: lens={lens(prof, 17, 10):.3f}")

# Recherche r1,r2 pour e=prof+r2 reproduisant base=6.364 et lens(15.5)=8.597
print("\nRecherche (r1,r2) avec e=prof+r2 : base=6.364, lens(15.5)=8.597")
best = None
r1v = 5.0
while r1v <= 40:
    r2v = 3.0
    while r2v <= 25:
        try:
            base = lens(16.5 + r2v, r1v, r2v) + 2 * lens(17 + r2v, r1v, r2v)
            l155 = lens(15.5 + r2v, r1v, r2v)
            err = abs(base - 6.364) + abs(l155 - 8.597)
            if best is None or err < best[0]:
                best = (err, r1v, r2v, base, l155)
        except Exception:
            pass
        r2v += 0.5
    r1v += 0.5
print("  meilleur:", best)
