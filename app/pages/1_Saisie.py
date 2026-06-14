"""Page **Saisie** : formulaire des données du train à balancier (MLG).

Toutes les valeurs sont saisies dans les unités d'affichage de l'Excel d'origine.
À la validation, les erreurs sont détectées à trois niveaux (saisie, pré-calcul,
exécution) et **localisées** : le champ fautif est surligné et accompagné d'un
message clair et d'un conseil de correction.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dropsim import MLGInputs, SimError, default_mlg_inputs, run_simulation  # noqa: E402
from dropsim.inputs import Point3, Rainure  # noqa: E402

st.set_page_config(page_title="Saisie — SimuLanding", page_icon="📝", layout="wide")

if "inputs" not in st.session_state:
    st.session_state.inputs = default_mlg_inputs()

# Erreurs localisées issues de la dernière validation : {champ: message}.
field_errors: dict[str, str] = st.session_state.get("field_errors", {})

st.title("📝 Saisie des données du train d'atterrissage")
st.caption("Architecture à balancier (MLG) — unités : mm · bar · cc · cSt · MPa · ° · °C")


# --------------------------------------------------------------------------- #
#  Helper de champ numérique avec surlignage d'erreur localisée
# --------------------------------------------------------------------------- #
def num(label: str, field: str, default: float, *, step: float = 1.0,
        fmt: str | None = None, help: str | None = None, min_value=None) -> None:
    """Affiche un ``number_input`` lié à ``field`` et surligne l'erreur éventuelle."""
    err = field_errors.get(field)
    shown = f"⚠️ {label}" if err else label
    st.number_input(
        shown,
        value=float(default),
        step=step,
        format=fmt,
        help=help,
        min_value=min_value,
        key=f"f_{field}",
    )
    if err:
        st.markdown(
            f"<span style='color:#d33;font-size:0.8em'>↳ {err}</span>",
            unsafe_allow_html=True,
        )


inp: MLGInputs = st.session_state.inputs

# --------------------------------------------------------------------------- #
#  Conditions de chute
# --------------------------------------------------------------------------- #
st.header("Conditions de chute")
c = st.columns(4)
with c[0]:
    num("Masse supportée (kg)", "masse", inp.masse, step=10.0, min_value=0.0)
    num("Vitesse verticale Vz (m/s)", "vz", inp.vz, step=0.1, min_value=0.0)
with c[1]:
    num("Vitesse horizontale Vx (m/s)", "vx", inp.vx, step=1.0, min_value=0.0)
    num("Coefficient de portance (0..1)", "lift", inp.lift, step=0.01)
with c[2]:
    num("Assiette / pitch (°)", "pitch", inp.pitch, step=0.5)
    num("Gîte / roll (°)", "roll", inp.roll, step=0.5)
with c[3]:
    num("Durée simulée (s)", "temps_simu", inp.temps_simu, step=0.05, fmt="%.4f")
    num("Pas de temps It (s)", "it", inp.it, step=0.0001, fmt="%.5f")
    num("Température (°C)", "temperature", inp.temperature, step=1.0)

# --------------------------------------------------------------------------- #
#  Amortisseur
# --------------------------------------------------------------------------- #
st.header("Amortisseur (géométrie)")
c = st.columns(4)
with c[0]:
    num("Ø piston Dpis (mm)", "Dpis", inp.Dpis, step=0.5)
    num("Ø bague hydraulique Dbh (mm)", "Dbh", inp.Dbh, step=0.5)
    num("Ø tige Dt (mm)", "Dt", inp.Dt, step=0.5)
with c[1]:
    num("Ø intérieur tige Dp (mm)", "Dp", inp.Dp, step=0.5)
    num("Ø intérieur BH (mm)", "DInsideBh", inp.DInsideBh, step=0.5)
    num("Longueur trou BH (mm)", "Lbh", inp.Lbh, step=1.0)
with c[2]:
    num("Course totale SAT (mm)", "course", inp.course, step=1.0)
    num("Ø trou piston détente (mm)", "DTrouPis", inp.DTrouPis, step=0.1, fmt="%.2f")
    num("Nb trous piston", "NbTrouPis", inp.NbTrouPis, step=1.0)
with c[3]:
    num("Hauteur piston BH (mm)", "HauteurPisBh", inp.HauteurPisBh, step=0.5)
    num("Ø trou clapet (mm)", "DTrouDiap", inp.DTrouDiap, step=0.1, fmt="%.2f")
    num("Nb trous clapet", "NbTrouDiap", inp.NbTrouDiap, step=1.0)

# --------------------------------------------------------------------------- #
#  Ressort gazeux
# --------------------------------------------------------------------------- #
st.header("Ressort gazeux (double chambre)")
c = st.columns(3)
with c[0]:
    num("Pression init. BP (bar)", "Pinitbp", inp.Pinitbp, step=1.0)
    num("Volume gaz init. BP (cc)", "Vgbp", inp.Vgbp, step=1.0, fmt="%.4f")
with c[1]:
    num("Volume d'huile (cc)", "Vh", inp.Vh, step=1.0, fmt="%.4f")
    num("Pression init. HP (bar)", "Pinithp", inp.Pinithp, step=1.0)
with c[2]:
    num("Volume gaz init. HP (cc)", "Vghp", inp.Vghp, step=1.0, fmt="%.4f")
    num("Coefficient polytropique γ", "gamma", inp.gamma, step=0.01, fmt="%.2f")

# --------------------------------------------------------------------------- #
#  Huile
# --------------------------------------------------------------------------- #
st.header("Huile")
c = st.columns(3)
with c[0]:
    num("Viscosité cinématique (cSt)", "visc", inp.visc, step=0.1, fmt="%.4f")
with c[1]:
    num("Module de compressibilité (MPa)", "bulk", inp.bulk, step=1.0, fmt="%.2f")
with c[2]:
    num("Masse volumique ρ (kg/m³)", "rho", inp.rho, step=1.0)

# --------------------------------------------------------------------------- #
#  Pneu
# --------------------------------------------------------------------------- #
st.header("Pneu et spring-back")
c = st.columns(3)
with c[0]:
    num("Masse non suspendue (kg)", "unsprung_mass", inp.unsprung_mass, step=0.5)
    num("Inertie polaire roue (kg·m²)", "wheel_inertia", inp.wheel_inertia, step=0.01, fmt="%.5f")
with c[1]:
    num("Rayon libre (mm)", "unload_radius", inp.unload_radius, step=1.0, fmt="%.2f")
    num("Raideur spring-back Kx (N/m)", "kx", inp.kx, step=10000.0)
with c[2]:
    num("Amortissement spring-back Cx (N·s/m)", "cx", inp.cx, step=10.0, fmt="%.4f")
    num("Masse roue spring-back (kg)", "wheelmass", inp.wheelmass, step=0.5)

st.markdown("**Courbe pneu** — déflexion (mm) → charge (kN)")
tyre_df = st.data_editor(
    pd.DataFrame(inp.tyre_curve, columns=["Déflexion (mm)", "Charge (kN)"]),
    num_rows="dynamic",
    use_container_width=True,
    key="tyre_curve_editor",
)

st.markdown("**Courbe d'adhérence** — taux de glissement → μ")
mu_df = st.data_editor(
    pd.DataFrame(inp.mu_curve, columns=["Slip", "μ"]),
    num_rows="dynamic",
    use_container_width=True,
    key="mu_curve_editor",
)

# --------------------------------------------------------------------------- #
#  Balancier et géométrie
# --------------------------------------------------------------------------- #
st.header("Balancier et géométrie")
num("Inertie balancier Jyy (kg·m²)", "jyy", inp.jyy, step=0.1, fmt="%.4f")

st.markdown("**Points (mm, repère avion)**")
points_df = st.data_editor(
    pd.DataFrame(
        {
            "Point": ["B", "A", "C", "R", "S"],
            "X": [inp.B.x, inp.A.x, inp.C.x, inp.R.x, inp.S.x],
            "Y": [inp.B.y, inp.A.y, inp.C.y, inp.R.y, inp.S.y],
            "Z": [inp.B.z, inp.A.z, inp.C.z, inp.R.z, inp.S.z],
        }
    ),
    use_container_width=True,
    hide_index=True,
    disabled=["Point"],
    key="points_editor",
)

# --------------------------------------------------------------------------- #
#  Rainures de la bague hydraulique
# --------------------------------------------------------------------------- #
st.header("Rainures de la bague hydraulique")
num("Ø rainure (mm)", "diametre_rainure", inp.diametre_rainure, step=1.0)
st.markdown("**Cotes des rainures** — début / fin / profondeur (mm)")
rainures_df = st.data_editor(
    pd.DataFrame(
        [(r.debut, r.fin, r.profondeur) for r in inp.rainures],
        columns=["Début (mm)", "Fin (mm)", "Profondeur (mm)"],
    ),
    num_rows="dynamic",
    use_container_width=True,
    key="rainures_editor",
)


# --------------------------------------------------------------------------- #
#  Construction d'un MLGInputs depuis les widgets
# --------------------------------------------------------------------------- #
def _build_inputs() -> MLGInputs:
    def g(field: str) -> float:
        return float(st.session_state[f"f_{field}"])

    def pt(row) -> Point3:
        return Point3(float(row["X"]), float(row["Y"]), float(row["Z"]))

    pts = {r["Point"]: pt(r) for _, r in points_df.iterrows()}

    return MLGInputs(
        masse=g("masse"), vz=g("vz"), vx=g("vx"), lift=g("lift"),
        pitch=g("pitch"), roll=g("roll"), temps_simu=g("temps_simu"),
        it=g("it"), temperature=g("temperature"),
        Dpis=g("Dpis"), Dbh=g("Dbh"), Dt=g("Dt"), Dp=g("Dp"),
        DInsideBh=g("DInsideBh"), Lbh=g("Lbh"), course=g("course"),
        DTrouPis=g("DTrouPis"), NbTrouPis=g("NbTrouPis"),
        HauteurPisBh=g("HauteurPisBh"), DTrouDiap=g("DTrouDiap"),
        NbTrouDiap=g("NbTrouDiap"),
        Pinitbp=g("Pinitbp"), Vgbp=g("Vgbp"), Vh=g("Vh"),
        Pinithp=g("Pinithp"), Vghp=g("Vghp"), gamma=g("gamma"),
        visc=g("visc"), bulk=g("bulk"), rho=g("rho"),
        unsprung_mass=g("unsprung_mass"), wheel_inertia=g("wheel_inertia"),
        unload_radius=g("unload_radius"), kx=g("kx"), cx=g("cx"),
        wheelmass=g("wheelmass"), jyy=g("jyy"),
        B=pts["B"], A=pts["A"], C=pts["C"], R=pts["R"], S=pts["S"],
        tyre_curve=[(float(a), float(b)) for a, b in tyre_df.itertuples(index=False)],
        mu_curve=[(float(a), float(b)) for a, b in mu_df.itertuples(index=False)],
        diametre_rainure=g("diametre_rainure"),
        rainures=[
            Rainure(float(a), float(b), float(c))
            for a, b, c in rainures_df.itertuples(index=False)
        ],
    )


# --------------------------------------------------------------------------- #
#  Actions
# --------------------------------------------------------------------------- #
st.divider()
col_run, col_reset, _ = st.columns([1, 1, 4])
launch = col_run.button("▶️ Lancer le calcul", type="primary", use_container_width=True)
reset = col_reset.button("↺ Réinitialiser", use_container_width=True)

if reset:
    for key in list(st.session_state.keys()):
        if key.startswith("f_") or key.endswith("_editor"):
            del st.session_state[key]
    st.session_state.inputs = default_mlg_inputs()
    st.session_state.pop("field_errors", None)
    st.session_state.pop("result", None)
    st.rerun()

if launch:
    new_inputs = _build_inputs()
    st.session_state.inputs = new_inputs

    # Niveau SAISIE : on remonte TOUTES les erreurs d'un coup.
    collector = new_inputs.validate()
    if collector.has_errors:
        st.session_state.field_errors = {
            e.field or "_global": str(e.message) + (f" — {e.hint}" if e.hint else "")
            for e in collector.errors
        }
        st.session_state.pop("result", None)
        st.rerun()
    else:
        st.session_state.field_errors = {}
        try:
            with st.spinner("Calcul en cours…"):
                result = run_simulation(new_inputs)
            st.session_state.result = result
            st.success(
                "Calcul terminé. Consultez la page **Résultats**.", icon="✅"
            )
            if result.warnings:
                with st.expander(f"⚠️ {len(result.warnings)} avertissement(s)"):
                    for w in result.warnings:
                        st.warning(str(w))
        except SimError as exc:
            # Erreur de pré-calcul ou d'exécution : on la localise.
            st.session_state.pop("result", None)
            if exc.field:
                st.session_state.field_errors = {
                    exc.field: str(exc.message) + (f" — {exc.hint}" if exc.hint else "")
                }
            st.error(
                f"**[{exc.level.value}] {exc.code}** "
                f"{'(champ : ' + exc.field + ') ' if exc.field else ''}: "
                f"{exc.message}"
                + (f"\n\n💡 {exc.hint}" if exc.hint else ""),
                icon="🛑",
            )
            st.rerun()

# --------------------------------------------------------------------------- #
#  Panneau de synthèse des erreurs localisées
# --------------------------------------------------------------------------- #
if field_errors:
    st.divider()
    st.subheader("🛑 Erreurs détectées")
    st.caption("Les champs concernés sont surlignés ci-dessus avec un ⚠️.")
    for field, msg in field_errors.items():
        label = "Général" if field == "_global" else f"Champ « {field} »"
        st.error(f"**{label}** : {msg}")
