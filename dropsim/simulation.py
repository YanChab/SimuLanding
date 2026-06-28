"""Point d'entrée haut niveau de la simulation trailing arm.

Enchaîne : validation des entrées (niveau SAISIE) → conversion SI → contrôles de
cohérence (niveau PRÉ-CALCUL) → intégration temporelle (niveau EXÉCUTION) →
synthèse des résultats. Toute erreur détectée est localisée précisément via
:class:`~dropsim.errors.SimError`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .engine import OUTPUT_COLUMNS, run_trailing_arm
from .engine_aircraft import OUTPUT_COLUMNS_AC, run_aircraft
from .engine_strait_strut import OUTPUT_COLUMNS_SS, run_strait_strut
from .errors import ErrorCollector, ErrorLevel, SimError
from .inputs import AircraftInputs, TrailingArmInputs, StraitStrutInputs
from .integration_pfd_aircraft import run_aircraft_pfd
from .integration_pfd_strait import run_strait_strut_pfd
from .integration_pfd_trailing import run_trailing_arm_pfd


AIRCRAFT_LEGACY_COLUMN_KEYS: tuple[str, ...] = (
    "temps",
    "aircraft_cg_z",
    "aircraft_cg_vz",
    "aircraft_cg_az",
    "aircraft_pitch",
    "aircraft_pitch_rate",
    "aircraft_pitch_acc",
    "aircraft_fz_total",
    "aircraft_fz_nlg",
    "aircraft_fz_mlg_left",
    "aircraft_fz_mlg_right",
    "aircraft_mx_total",
    "nlg_stroke",
    "nlg_velocity",
    "nlg_ftot",
    "nlg_pg",
    "nlg_pc",
    "nlg_pd",
    "nlg_tyre_defl",
    "mlg_left_stroke",
    "mlg_left_velocity",
    "mlg_left_ftot",
    "mlg_left_pg",
    "mlg_left_pc",
    "mlg_left_pd",
    "mlg_left_tyre_defl",
    "mlg_left_fx",
    "mlg_right_stroke",
    "mlg_right_velocity",
    "mlg_right_ftot",
    "mlg_right_pg",
    "mlg_right_pc",
    "mlg_right_pd",
    "mlg_right_tyre_defl",
    "mlg_right_fx",
)


def _aircraft_df_from_data(data: dict[str, np.ndarray]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            OUTPUT_COLUMNS_AC[k]: data[k]
            for k in AIRCRAFT_LEGACY_COLUMN_KEYS
            if k in data and k in OUTPUT_COLUMNS_AC
        }
    )


def _aircraft_full_df_from_data(data: dict[str, np.ndarray]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            OUTPUT_COLUMNS_AC[k]: data[k]
            for k in OUTPUT_COLUMNS_AC
            if k in data
        }
    )


@dataclass
class SimulationResult:
    """Résultats de simulation prêts pour l'affichage."""

    df: pd.DataFrame                      # séries temporelles (libellés avec unités)
    summary: dict[str, float]            # grandeurs synthétiques
    n_steps: int
    warnings: list[SimError] = field(default_factory=list)
    geometry: pd.DataFrame | None = None  # positions des points (mm) pour l'animation
    summary_rows: list[tuple[str, float, str]] = field(default_factory=list)
    full_df: pd.DataFrame | None = None  # colonnes complètes (mode avion)


def _subsample(data: dict[str, np.ndarray], max_points: int = 1000) -> dict[str, np.ndarray]:
    """Réduit le nombre de points pour l'affichage sans changer la dynamique."""
    if not data:
        return {}
    n = len(next(iter(data.values())))
    if n <= max_points:
        return data
    step = max(1, n // max_points)
    return {k: v[::step] for k, v in data.items()}


def _negative_pressure_warnings(full: dict[str, np.ndarray]) -> list[SimError]:
    """Détecte les pressions négatives et génère des avertissements explicites."""
    warnings: list[SimError] = []
    temps = full.get("temps")

    pressure_specs = (
        ("pg", "pression gaz"),
        ("pc", "pression compression"),
        ("pd", "pression détente"),
    )

    for key, label in pressure_specs:
        series = full.get(key)
        if series is None or len(series) == 0:
            continue
        idx_min = int(np.argmin(series))
        min_val = float(series[idx_min])
        if min_val >= 0.0:
            continue
        t_s = float(temps[idx_min]) if temps is not None and idx_min < len(temps) else float("nan")
        warnings.append(
            SimError(
                code="PRESSION_NEGATIVE",
                message=(
                    f"La {label} devient négative: {min_val:.3f} bar "
                    f"(t = {t_s*1000.0:.2f} ms)."
                ),
                level=ErrorLevel.RUNTIME,
                field=key,
                hint=(
                    "Vérifier les conditions d'entrée (pression initiale, température, "
                    "masse, vitesse d'impact) et le mode de calcul."
                ),
                context={"key": key, "min_bar": min_val, "index": idx_min, "time_s": t_s},
            )
        )

    return warnings


def _build_aircraft_result(
    engine_out,
    *,
    max_points: int,
) -> SimulationResult:
    data = _subsample(engine_out.data, max_points=max_points)
    df = _aircraft_df_from_data(data)
    full_df = _aircraft_full_df_from_data(data)
    geom = _subsample(engine_out.geometry, max_points=max_points) if engine_out.geometry else {}
    geom_df = pd.DataFrame(geom) if geom else None
    if geom_df is not None:
        geom_df.insert(0, "temps", data["temps"])
    full = engine_out.data
    summary = {
        "Course max NLG (mm)": float(np.max(full["nlg_stroke"]) * 1000.0),
        "Course max MLG gauche (mm)": float(np.max(full["mlg_left_stroke"]) * 1000.0),
        "Course max MLG droite (mm)": float(np.max(full["mlg_right_stroke"]) * 1000.0),
        "Effort vertical total max Fz (N)": float(np.max(full["aircraft_fz_total"])),
        "Moment de tangage max (N.m)": float(np.max(np.abs(full["aircraft_mx_total"]))),
        "Accélération CG max (g)": float(np.max(np.abs(full["aircraft_cg_az"])) / 9.81),
        "Nombre de pas": int(engine_out.n_steps),
    }
    warnings = list(engine_out.warnings)
    warnings.extend(_negative_pressure_warnings(full))
    return SimulationResult(
        df=df,
        summary=summary,
        n_steps=engine_out.n_steps,
        warnings=warnings,
        geometry=geom_df,
        summary_rows=[],
        full_df=full_df,
    )


def run_aircraft_simulation(
    inputs: AircraftInputs,
    max_points: int = 1000,
    progress_callback: callable | None = None,
) -> SimulationResult:
    """Chemin dédié au mode avion complet, sans dispatch générique."""
    collector = ErrorCollector()
    inputs.validate(collector)
    if collector.has_errors:
        collector.raise_if_any()

    params = inputs.to_si()
    engine_out = run_aircraft(params, progress_callback=progress_callback)
    return _build_aircraft_result(engine_out, max_points=max_points)


def run_simulation(
    inputs: AircraftInputs | TrailingArmInputs | StraitStrutInputs,
    max_points: int = 1000,
    progress_callback: callable | None = None,
) -> SimulationResult:
    """Valide, exécute et synthétise une simulation de drop test trailing arm.

    ``progress_callback`` est une fonction optionnelle appelée à chaque itération
    avec (étape_courante, nombre_total_étapes) pour afficher la progression.

    Raises
    ------
    SimError
        Au premier problème bloquant (saisie invalide, incohérence, divergence).
    """
    # Niveau SAISIE : validation complète du formulaire.
    collector = ErrorCollector()
    inputs.validate(collector)
    if collector.has_errors:
        collector.raise_if_any()

    # Conversion SI.
    params = inputs.to_si()

    # Niveau PRÉ-CALCUL : cohérence des sections dérivées.
    is_aircraft = (
        getattr(inputs, "model_kind", "") == "aircraft"
        or (
            hasattr(inputs, "body")
            and hasattr(inputs, "simulation")
            and hasattr(inputs, "drop")
            and hasattr(inputs, "layout")
            and hasattr(inputs, "nlg")
            and hasattr(inputs, "mlg")
        )
        or (
            getattr(params, "nlg", None) is not None
            and getattr(params, "mlg", None) is not None
        )
    )
    if hasattr(params, "Sc") and hasattr(params, "Sd"):
        pre = ErrorCollector()
        pre.check(
            params.Sc <= 0,
            code="SECTION_COMPRESSION_INVALIDE",
            message="La section de compression est nulle ou négative.",
            level=ErrorLevel.PRECALCUL,
            field="Dpis",
            hint="Vérifier Dpis et Dbh (Dpis doit être > Dbh).",
        )
        pre.check(
            params.Sd <= 0,
            code="SECTION_DETENTE_INVALIDE",
            message="La section de détente est nulle ou négative.",
            level=ErrorLevel.PRECALCUL,
            field="Dpis",
            hint="Vérifier Dpis et Dt (Dpis doit être > Dt).",
        )
        if pre.has_errors:
            pre.raise_if_any()

    # Niveau EXÉCUTION.
    is_strait_strut = getattr(inputs, "model_kind", "") == "strait_strut" and not is_aircraft
    if is_aircraft:
        engine_out = run_aircraft(params, progress_callback=progress_callback)
        col_map = OUTPUT_COLUMNS_AC
    elif is_strait_strut:
        ss = inputs  # type: ignore[assignment]
        # Angles totaux jambe (rad) = structural (deg→rad) + avion (déjà en rad via to_si)
        alfap_rad = getattr(ss, "strut_pitch", 0.0) * math.pi / 180.0 + params.pitch
        alfar_rad = getattr(ss, "strut_roll", 0.0) * math.pi / 180.0 + params.roll
        engine_out = run_strait_strut(
            params,
            progress_callback=progress_callback,
            seal_precomp_pa=getattr(ss, "seal_precomp_pa", 110_649.0),
            bague_guide_m=getattr(ss, "bague_guide", 50.0) / 1000.0,
            bague_piston_m=getattr(ss, "bague_piston", 50.0) / 1000.0,
            alfap=alfap_rad,
            alfar=alfar_rad,
            h_pivot_z_m=getattr(ss, "h_pivot_z", 600.0) / 1000.0,
            h_guide_top_z_m=getattr(ss, "h_guide_top_z", 500.0) / 1000.0,
            h_guide_bot_z_m=getattr(ss, "h_guide_bot_z", 200.0) / 1000.0,
        )
        col_map = OUTPUT_COLUMNS_SS
    else:
        engine_out = run_trailing_arm(params, progress_callback=progress_callback)
        col_map = OUTPUT_COLUMNS

    data = _subsample(engine_out.data, max_points=max_points)
    if is_aircraft:
        df = _aircraft_df_from_data(data)
        full_df = _aircraft_full_df_from_data(data)
    else:
        df = pd.DataFrame({col_map[k]: v for k, v in data.items() if k in col_map})
        full_df = None
    geom = _subsample(engine_out.geometry, max_points=max_points) if engine_out.geometry else {}
    geom_df = pd.DataFrame(geom) if geom else None
    if geom_df is not None:
        geom_df.insert(0, "temps", data["temps"])
    full = engine_out.data
    if is_aircraft:
        summary = {
            "Course max NLG (mm)": float(np.max(full["nlg_stroke"]) * 1000.0),
            "Course max MLG gauche (mm)": float(np.max(full["mlg_left_stroke"]) * 1000.0),
            "Course max MLG droite (mm)": float(np.max(full["mlg_right_stroke"]) * 1000.0),
            "Effort vertical total max Fz (N)": float(np.max(full["aircraft_fz_total"])),
            "Moment de tangage max (N.m)": float(np.max(np.abs(full["aircraft_mx_total"]))),
            "Accélération CG max (g)": float(np.max(np.abs(full["aircraft_cg_az"])) / 9.81),
            "Nombre de pas": int(engine_out.n_steps),
        }
        summary_rows: list[tuple[str, float, str]] = []
    else:
        summary = {
            "Course max (mm)": float(np.max(full["trailing_arm_d"]) * 1000.0),
            "Effort vertical max Fz (N)": float(np.max(full["tyre_ftyre"])),
            "Effort horizontal max Fx (N)": float(np.max(np.abs(full["tr_x"]))),
            "Effort amortisseur max (N)": float(np.max(np.abs(full["trailing_arm_ftot"]))),
            "Pression gaz max (bar)": float(np.max(full["pg"])),
            "Pression compression max (bar)": float(np.max(full["pc"])),
            "Accélération max (g)": float(np.max(np.abs(full["accms"])) / 9.81),
            "Nombre de pas": int(engine_out.n_steps),
        }
        summary_rows = _build_summary_rows(full, inputs)

    warnings = list(engine_out.warnings)
    warnings.extend(_negative_pressure_warnings(full))

    return SimulationResult(
        df=df,
        summary=summary,
        n_steps=engine_out.n_steps,
        warnings=warnings,
        geometry=geom_df,
        summary_rows=summary_rows,
        full_df=full_df,
    )


def _build_summary_rows(
    full: dict[str, np.ndarray], inputs: TrailingArmInputs
) -> list[tuple[str, float, str]]:
    """Reproduit la synthèse B46:C61 de l'onglet « Summary MLG ».

    Les efforts sont en N, les courses en mm, les vitesses en m/s, les pressions
    en bar et l'accélération en g. ``Load factor`` et ``Ground load factor`` sont
    sans dimension.
    """
    fz = full["tyre_ftyre"]          # Tyre.FTyre (N)
    fx = full["tr_x"]                # TR.RsolX (N) — effort horizontal
    stroke = full["trailing_arm_d"]           # MLG.d (m)
    vel = full["trailing_arm_v"]              # MLG.v (m/s)
    pg = full["pg"]                  # MLG.Pg (bar)
    pc = full["pc"]                  # MLG.Pc (bar)
    pd_ = full["pd"]                 # MLG.Pd (bar)
    acc = full["accms"]             # AccMs.RsolZ (m/s²)

    # Spin up : maximum de l'effort horizontal.
    i_spin = int(np.argmax(fx))
    fx_spin = float(fx[i_spin])
    fz_spin = float(fz[i_spin])
    stroke_spin_m = float(stroke[i_spin])

    # Spring back : instant où l'effort horizontal Fx est minimal.
    i_sb = int(np.argmin(fx))
    fx_springback = float(fx[i_sb])
    fz_springback = float(fz[i_sb])
    stroke_springback_m = float(stroke[i_sb])

    # Fz max.
    i_fzmax = int(np.argmax(fz))
    fz_max = float(fz[i_fzmax])
    stroke_fzmax_m = float(stroke[i_fzmax])

    masse = inputs.masse
    lift = inputs.lift
    ground_load_factor = fz_max / 9.81 / masse if masse else 0.0
    load_factor = ground_load_factor + lift

    return [
        ("Fx Spin up", fx_spin, "N"),
        ("Fz Spin up", fz_spin, "N"),
        ("Stroke spin up", stroke_spin_m * 1000.0, "mm"),
        ("Fx Spring back", fx_springback, "N"),
        ("Fz Spring back", fz_springback, "N"),
        ("Stroke Spring back", stroke_springback_m * 1000.0, "mm"),
        ("Fz Max", fz_max, "N"),
        ("Stroke Fzmax", stroke_fzmax_m * 1000.0, "mm"),
        ("Max damper stroke", float(np.max(stroke)) * 1000.0, "mm"),
        ("Max damper velocity", float(np.max(vel)), "m/s"),
        ("Max gas pressure", float(np.max(pg)), "bar"),
        ("Max comp pressure", float(np.max(pc)), "bar"),
        ("Max rebound pressure", float(np.max(pd_)), "bar"),
        ("Max Vertical acc", float(np.max(np.abs(acc))) / 9.81, "g"),
        ("Load factor", load_factor, "-"),
        ("Ground load factor", ground_load_factor, "-"),
    ]



def run_pfd_simulation(
    inputs: AircraftInputs | TrailingArmInputs | StraitStrutInputs,
    *,
    m_arm: float = 0.0,
) -> dict[str, np.ndarray]:
    """Point d'entrée du modèle reconstruit **IntegrationPFD**.

    Dispatche vers les moteurs PFD (``integration_pfd_*``) qui réutilisent les
    sous-modèles constitutifs validés mais assemblent l'interface **strictement
    selon ``docs/PFD_trains.md``** (signe Fx@B corrigé, torseur MLG 3D, masse
    balancier optionnelle via ``m_arm``). Renvoie un dict de tableaux numpy.

    Pour ``m_arm = 0`` les résultats reproduisent les moteurs historiques
    (corrigés) à la précision machine.
    """
    collector = ErrorCollector()
    inputs.validate(collector)
    if collector.has_errors:
        collector.raise_if_any()

    params = inputs.to_si()
    model_kind = getattr(inputs, "model_kind", "")
    is_aircraft = model_kind == "aircraft" or (
        getattr(params, "nlg", None) is not None
        and getattr(params, "mlg", None) is not None
    )

    if is_aircraft:
        return run_aircraft_pfd(inputs, m_arm=m_arm)
    if model_kind == "strait_strut":
        ss = inputs  # type: ignore[assignment]
        alfap_rad = getattr(ss, "strut_pitch", 0.0) * math.pi / 180.0 + params.pitch
        alfar_rad = getattr(ss, "strut_roll", 0.0) * math.pi / 180.0 + params.roll
        return run_strait_strut_pfd(
            params,
            seal_precomp_pa=getattr(ss, "seal_precomp_pa", 110_649.0),
            bague_guide_m=getattr(ss, "bague_guide", 50.0) / 1000.0,
            bague_piston_m=getattr(ss, "bague_piston", 50.0) / 1000.0,
            alfap=alfap_rad,
            alfar=alfar_rad,
            h_pivot_z_m=getattr(ss, "h_pivot_z", 600.0) / 1000.0,
            h_guide_top_z_m=getattr(ss, "h_guide_top_z", 500.0) / 1000.0,
            h_guide_bot_z_m=getattr(ss, "h_guide_bot_z", 200.0) / 1000.0,
        )
    return run_trailing_arm_pfd(params, m_arm=m_arm)


__all__ = ["run_simulation", "run_pfd_simulation", "SimulationResult"]
