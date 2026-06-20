"""Modèle de données d'entrée du train à balancier (MLG) + valeurs par défaut.

Les valeurs sont saisies dans les **unités d'affichage** de l'Excel d'origine
(mm, bar, cc, cSt, MPa, °, °C). La méthode :meth:`MLGInputs.to_si` produit la
structure :class:`MLGParamsSI` utilisée en interne par le moteur (tout en SI).

Les valeurs par défaut reproduisent l'onglet « MLG » du classeur pour le cas
nominal (m = 1250 kg, Vz = 3.05 m/s, Vx = 39 m/s).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import units as U
from .errors import ErrorCollector, ErrorLevel


@dataclass
class Point3:
    """Point défini dans le repère avion, en millimètres."""

    x: float
    y: float
    z: float


@dataclass
class Rainure:
    """Rainure usinée dans la bague hydraulique (cotes en mm de course)."""

    debut: float
    fin: float
    profondeur: float


# --------------------------------------------------------------------------- #
#  Dépendance à la température (gaz + huile)
# --------------------------------------------------------------------------- #
# Température de référence (ambiante) à laquelle sont saisies les valeurs de gaz
# et d'huile. Au-dessus ou en dessous, ces valeurs sont recalculées comme dans
# les onglets « MLG » / « NLG » du classeur Excel d'origine.
TEMP_REF_C: float = 25.0


def _oil_viscosity_abs(temp_c: float) -> float:
    """Viscosité cinématique absolue (cSt) — loi de l'Excel (cellule O35)."""
    if temp_c > 0.0:
        return 20.0 * math.exp(-0.023 * temp_c)
    return 20.0 * math.exp(-0.077 * temp_c)


def compute_gas_oil_at_temperature(
    *,
    Pinitbp: float,
    Vgbp: float,
    Vh: float,
    Pinithp: float,
    Vghp: float,
    visc: float,
    temperature: float,
    temp_ref: float = TEMP_REF_C,
) -> dict[str, float]:
    """Recalcule les paramètres de gaz et d'huile à ``temperature``.

    Reproduit les formules des onglets « MLG » / « NLG » de l'Excel (cellules
    G41–G45 et O35), où les valeurs saisies correspondent à la température
    ambiante ``temp_ref`` (25 °C par défaut) :

    * volume d'huile : dilatation thermique ``Vh·(1 + 7e-4·ΔT)`` (G43) ;
    * volume gaz BP : compensé par la variation de volume d'huile (G42) ;
    * pression BP : loi de Gay-Lussac × correction de Boyle (G41) ;
    * pression HP : loi de Gay-Lussac (G44) ;
    * volume gaz HP : inchangé (G45) ;
    * viscosité : loi exponentielle en température (O35).

    Les valeurs renvoyées sont en unités d'affichage (bar, cc, cSt). À
    ``temp_ref``, elles sont identiques aux valeurs saisies.
    """
    ratio = (temperature + 273.15) / (temp_ref + 273.15)
    vh_t = Vh * (1.0 + 0.0007 * (temperature - temp_ref))
    vgbp_t = Vgbp + (Vh - vh_t)
    pinitbp_t = Pinitbp * ratio * (Vgbp / vgbp_t) if vgbp_t else Pinitbp
    visc_ref = _oil_viscosity_abs(temp_ref)
    visc_t = visc * _oil_viscosity_abs(temperature) / visc_ref if visc_ref else visc
    return {
        "Pinitbp": pinitbp_t,
        "Vgbp": vgbp_t,
        "Vh": vh_t,
        "Pinithp": Pinithp * ratio,
        "Vghp": Vghp,
        "visc": visc_t,
    }


def compute_bulk_modulus_from_aeration(
    *,
    aeration_pct: float,
    k_air: float,
    k_huile: float,
) -> float:
    """Calcule le module de compressibilité effectif (MPa) du mélange huile + gaz.

    Reproduit la formule des onglets Excel ``MLG``/``NLG`` (cellule O36) :

    ``Bulk = 1 / (alpha / Kair + (1 - alpha) / Khuile)``

    où ``alpha`` est la fraction volumique d'aération (en %) convertie en
    fraction, ``Kair`` et ``Khuile`` sont exprimés en MPa.
    """
    alpha = aeration_pct / 100.0
    if not (0.0 <= alpha < 1.0):
        raise ValueError("aeration_pct doit être dans [0, 100).")
    if k_air <= 0.0 or k_huile <= 0.0:
        raise ValueError("k_air et k_huile doivent être strictement positifs.")
    return 1.0 / (alpha / k_air + (1.0 - alpha) / k_huile)


def compute_bulk_modulus_at_temperature(
    *,
    aeration_pct: float,
    k_air_ref: float,
    k_huile_ref: float,
    temperature: float,
    k_huile_temp_coeff: float,
    temp_ref: float = TEMP_REF_C,
) -> dict[str, float]:
    """Calcule les compressibilités à ``temperature`` à partir des valeurs à 25 °C.

    Hypothèses de travail (modèle système 0D/1D) :

    - ``Kair(T)`` suit le rapport thermodynamique absolu
      ``(T+273.15)/(Tref+273.15)`` (gaz idéal, volume quasi constant) ;
    - ``Khuile(T)`` suit une loi affine relative
      ``Khuile_ref * (1 + cT * (T - Tref))`` ;
    - le bulk effectif est ensuite calculé par la même loi de mélange que
      l'Excel (MLG/NLG cellule O36).
    """
    ratio_t = (temperature + 273.15) / (temp_ref + 273.15)
    k_air_t = k_air_ref * ratio_t
    k_huile_t = k_huile_ref * (1.0 + k_huile_temp_coeff * (temperature - temp_ref))
    if k_huile_t <= 0.0:
        raise ValueError("Le module huile corrigé en température devient non positif.")

    bulk_ref = compute_bulk_modulus_from_aeration(
        aeration_pct=aeration_pct,
        k_air=k_air_ref,
        k_huile=k_huile_ref,
    )
    bulk_t = compute_bulk_modulus_from_aeration(
        aeration_pct=aeration_pct,
        k_air=k_air_t,
        k_huile=k_huile_t,
    )
    return {
        "k_air": k_air_t,
        "k_huile": k_huile_t,
        "bulk_ref": bulk_ref,
        "bulk": bulk_t,
    }


# --------------------------------------------------------------------------- #
#  Entrées en unités d'affichage
# --------------------------------------------------------------------------- #
@dataclass
class MLGInputs:
    # --- Conditions de chute ---------------------------------------------- #
    masse: float = 1250.0          # kg  (masse supportée)
    vz: float = 3.05               # m/s (vitesse verticale de chute)
    vx: float = 39.0               # m/s (vitesse horizontale avion)
    lift: float = 0.67             # -   (coefficient de portance, 0..1)
    pitch: float = 0.0             # deg (assiette)
    roll: float = 0.0              # deg (gîte / roll, alfar)
    temps_simu: float = 0.5        # s   (durée simulée)
    it: float = 0.0001             # s   (pas de temps)
    integrator: str = "euler"      # euler|rk4
    damper_core_solver: str = "legacy"  # legacy|implicit_adaptive|auto
    temperature: float = 25.0      # °C

    # --- Amortisseur (géométrie) ------------------------------------------ #
    Dpis: float = 56.0             # mm  diamètre piston
    Dbh: float = 34.0              # mm  diamètre bague hydraulique (BH)
    Dt: float = 50.0               # mm  diamètre tige
    Dp: float = 40.0               # mm  diamètre intérieur tige
    DInsideBh: float = 28.0        # mm  diamètre intérieur butée hydraulique BH
    DInsidePalierBh: float = 34.0  # mm  diamètre intérieur palier BH (fuite annulaire)
    Lbh: float = 200.0             # mm  longueur du trou de BH
    LPalierBh: float = 6.0         # mm  longueur du palier BH (fuite annulaire)
    excentricite_palier_bh: float = 0.0  # mm  désaxage BH/palier (0 = concentrique)
    course: float = 185.0          # mm  course totale (SAT)
    DTrouPis: float = 1.5          # mm  diamètre trou piston de détente
    NbTrouPis: float = 10.0        # -   nombre de trous piston
    HauteurPisBh: float = 10.0     # mm  hauteur du piston de BH
    DTrouDiap: float = 1.5         # mm  diamètre trou du clapet (diaphragme)
    NbTrouDiap: float = 1.0        # -   nombre de trous clapet
    endstop_smooth_mm: float = 2.0  # mm  longueur caractéristique de lissage

    # --- Joint d'étanchéité (friction) ------------------------------------ #
    # Friction du joint dépendant de la pression et de la taille du joint
    # (formule du module de classe MLG du classeur Excel). Le diamètre effectif
    # du joint est déduit du diamètre de tige et de la section du tore :
    # ASeal = Dt + 2·tore.
    tore: float = 2.78            # mm  section du joint torique (MLG!O40)
    fc: float = 0.3064566929133859  # N/mm  coefficient de friction sèche (MLG!O43)
    fh: float = 0.0207             # -   coefficient de friction lié à la pression

    # --- Ressort gazeux --------------------------------------------------- #
    Pinitbp: float = 10.0          # bar pression initiale basse pression
    Vgbp: float = 308.7597         # cc  volume gaz initial BP
    Vh: float = 373.9988           # cc  volume d'huile
    Pinithp: float = 70.0          # bar pression initiale haute pression
    Vghp: float = 79.7399          # cc  volume gaz initial HP
    gamma: float = 1.4             # -   coefficient polytropique

    # --- Huile ------------------------------------------------------------ #
    visc: float = 11.2541          # cSt viscosité cinématique
    aeration_pct: float = 0.05     # %   taux d'aération volumique (Excel R34=0.0005)
    k_air: float = 0.1             # MPa module équivalent gaz à 25 °C (Excel R35)
    # Valeurs par défaut orientées MIL-PRF-87257 (H-538), calibrées pour
    # reproduire ~1418 MPa à 40 °C (RADCOLUBE FR257 TDS 2025, 27.6 MPa).
    k_huile: float = 1500.0        # MPa module de l'huile pure à 25 °C
    k_huile_temp_coeff: float = -0.00364  # 1/°C => Khuile(40 °C) ≈ 1418 MPa
    bulk: float = 176.53           # MPa module effectif à 25 °C (aération 0.05 %)
    rho: float = 855.0             # kg/m³ masse volumique

    # --- Pneu ------------------------------------------------------------- #
    unsprung_mass: float = 20.0    # kg  masse non suspendue
    wheel_inertia: float = 0.17015  # kg.m² inertie polaire roue (j)
    unload_radius: float = 222.25  # mm  rayon libre
    kx: float = 1_000_000.0        # N/m raideur spring-back
    cx: float = 1612.4515          # N.s/m amortissement spring-back
    wheelmass: float = 10.4        # kg  masse roue (spring-back)

    # --- Balancier -------------------------------------------------------- #
    jyy: float = 1.0               # kg.m² inertie balancier autour de Y

    # --- Points (mm, repère avion) ---------------------------------------- #
    B: Point3 = field(default_factory=lambda: Point3(5540.0, -1190.0, 537.0))
    A: Point3 = field(default_factory=lambda: Point3(5714.0, -1190.0, 222.0))
    C: Point3 = field(default_factory=lambda: Point3(5860.0, -1190.0, 789.0))
    R: Point3 = field(default_factory=lambda: Point3(5675.0, -1350.0, 292.0))
    S: Point3 = field(default_factory=lambda: Point3(5675.0, -1350.0, 69.75))

    # --- Tables ----------------------------------------------------------- #
    # Pneu : (déflexion mm, charge kN)
    tyre_curve: list[tuple[float, float]] = field(
        default_factory=lambda: [
            (0.0, 0.0),
            (12.9, 3.162),
            (25.8, 9.485),
            (38.7, 16.7),
            (55.567, 26.133),
            (72.433, 35.567),
            (89.3, 45.0),
            (94.0, 50.0),
        ]
    )
    # μ / taux de glissement : (slip, mu)
    mu_curve: list[tuple[float, float]] = field(
        default_factory=lambda: [
            (0.0, 0.0),
            (0.05, 0.53),
            (0.08, 0.8),
            (0.1, 0.89),
            (0.15, 1.0),
            (0.2, 0.98),
            (0.25, 0.94),
            (0.3, 0.89),
            (0.4, 0.82),
            (0.5, 0.77),
            (0.6, 0.72),
            (0.7, 0.65),
            (0.8, 0.6),
            (0.9, 0.53),
            (1.0, 0.49),
        ]
    )
    # Rainures de la bague hydraulique
    diametre_rainure: float = 20.0  # mm
    rainures: list[Rainure] = field(
        default_factory=lambda: [
            Rainure(0.0, 200.0, 16.5),
            Rainure(0.0, 200.0, 17.0),
            Rainure(0.0, 200.0, 17.0),
            Rainure(20.0, 140.0, 15.5),
            Rainure(60.0, 200.0, 15.5),
            Rainure(0.0, 200.0, 17.0),
            Rainure(0.0, 200.0, 16.0),
            Rainure(0.0, 200.0, 17.0),
        ]
    )

    # ------------------------------------------------------------------ #
    def validate(self, collector: ErrorCollector | None = None) -> ErrorCollector:
        """Valide les entrées (niveau SAISIE). Retourne le collecteur d'erreurs."""
        c = collector or ErrorCollector()

        def positive(value: float, field_name: str, label: str) -> None:
            c.check(
                not (value > 0),
                code="VALEUR_NON_POSITIVE",
                message=f"{label} doit être strictement positif (valeur reçue : {value}).",
                field=field_name,
                hint=f"Saisir une valeur > 0 pour {label}.",
            )

        # Conditions de chute
        positive(self.masse, "masse", "La masse")
        positive(self.it, "it", "Le pas de temps")
        positive(self.temps_simu, "temps_simu", "La durée de simulation")
        c.check(
            self.it >= self.temps_simu,
            code="PAS_TROP_GRAND",
            message="Le pas de temps doit être nettement inférieur à la durée simulée.",
            field="it",
            hint="Diminuer le pas de temps (typiquement 1e-4 s).",
        )
        c.check(
            not (0.0 <= self.lift <= 1.0),
            code="LIFT_HORS_PLAGE",
            message=f"Le coefficient de portance doit être compris entre 0 et 1 (reçu : {self.lift}).",
            field="lift",
            hint="Saisir un coefficient de portance entre 0 et 1.",
        )
        c.check(
            self.vz <= 0,
            code="VZ_NON_POSITIVE",
            message="La vitesse verticale de chute doit être positive.",
            field="vz",
            hint="Saisir Vz > 0 (sens de chute).",
        )
        c.check(
            self.integrator not in {"euler", "rk4"},
            code="INTEGRATEUR_INVALIDE",
            message=(
                "L'intégrateur doit être 'euler' ou 'rk4' "
                f"(reçu : {self.integrator})."
            ),
            field="integrator",
            hint="Choisir 'euler' ou 'rk4'.",
        )
        c.check(
            self.damper_core_solver not in {"legacy", "implicit_adaptive", "auto"},
            code="SOLVEUR_AMORTISSEUR_INVALIDE",
            message=(
                "Le solveur noyau amortisseur doit être 'legacy', "
                "'implicit_adaptive' ou 'auto' "
                f"(reçu : {self.damper_core_solver})."
            ),
            field="damper_core_solver",
            hint="Choisir 'legacy', 'implicit_adaptive' ou 'auto'.",
        )

        # Géométrie amortisseur
        for name, label in [
            ("Dpis", "Le diamètre piston"),
            ("Dbh", "Le diamètre de bague hydraulique"),
            ("Dt", "Le diamètre de tige"),
            ("DInsidePalierBh", "Le diamètre intérieur du palier BH"),
            ("LPalierBh", "La longueur du palier BH"),
            ("course", "La course"),
            ("HauteurPisBh", "La hauteur de piston BH"),
            ("DTrouPis", "Le diamètre trou piston"),
            ("DTrouDiap", "Le diamètre trou clapet"),
            ("NbTrouPis", "Le nombre de trous piston"),
            ("NbTrouDiap", "Le nombre de trous clapet"),
            ("endstop_smooth_mm", "La longueur de lissage de butée"),
        ]:
            positive(getattr(self, name), name, label)

        c.check(
            self.Dpis <= self.Dbh,
            code="GEOMETRIE_SECTION_C",
            message="Le diamètre piston doit être supérieur au diamètre de bague hydraulique "
            "(sinon la section de compression est nulle ou négative).",
            field="Dpis",
            hint="Augmenter Dpis ou diminuer Dbh.",
        )
        c.check(
            self.Dpis <= self.Dt,
            code="GEOMETRIE_SECTION_D",
            message="Le diamètre piston doit être supérieur au diamètre de tige "
            "(sinon la section de détente est nulle ou négative).",
            field="Dpis",
            hint="Augmenter Dpis ou diminuer Dt.",
        )
        c.check(
            self.DInsidePalierBh < self.Dbh,
            code="GEOMETRIE_PALIER_BH",
            message="Le diamètre intérieur du palier BH doit être supérieur ou égal "
            "au diamètre extérieur de la bague BH.",
            field="DInsidePalierBh",
            hint="Augmenter le diamètre intérieur palier BH ou réduire Dbh.",
        )

        # Gaz
        positive(self.Pinitbp, "Pinitbp", "La pression initiale BP")
        positive(self.Vgbp, "Vgbp", "Le volume gaz BP")
        positive(self.Pinithp, "Pinithp", "La pression initiale HP")
        positive(self.Vghp, "Vghp", "Le volume gaz HP")
        positive(self.gamma, "gamma", "Le coefficient polytropique")
        c.check(
            self.Pinithp < self.Pinitbp,
            code="HP_INFERIEUR_BP",
            message="La pression haute pression doit être supérieure à la basse pression.",
            field="Pinithp",
            hint="Vérifier l'ordre des chambres BP/HP.",
        )

        # Huile
        positive(self.visc, "visc", "La viscosité")
        positive(self.k_air, "k_air", "Le module de compressibilité de l'azote")
        positive(self.k_huile, "k_huile", "Le module de compressibilité de l'huile pure")
        positive(self.bulk, "bulk", "Le module de compressibilité")
        positive(self.rho, "rho", "La masse volumique de l'huile")
        c.check(
            not (0.0 <= self.aeration_pct < 100.0),
            code="AERATION_HORS_PLAGE",
            message=(
                f"Le taux d'aération doit être compris entre 0 et 100 % "
                f"(reçu : {self.aeration_pct})."
            ),
            field="aeration_pct",
            hint="Saisir un pourcentage d'aération entre 0 et strictement inférieur à 100.",
        )
        c.check(
            self.k_huile * (1.0 + self.k_huile_temp_coeff * (self.temperature - TEMP_REF_C)) <= 0.0,
            code="KHUILE_T_NON_POSITIF",
            message="Le module de compressibilité de l'huile corrigé en température devient non positif.",
            field="k_huile_temp_coeff",
            hint="Réduire la sensibilité thermique ou ajuster Khuile.",
        )

        # Pneu
        positive(self.unload_radius, "unload_radius", "Le rayon libre du pneu")
        positive(self.wheel_inertia, "wheel_inertia", "L'inertie de la roue")
        positive(self.wheelmass, "wheelmass", "La masse de la roue")
        positive(self.jyy, "jyy", "L'inertie du balancier")
        c.check(
            len(self.tyre_curve) < 2,
            code="COURBE_PNEU_INSUFFISANTE",
            message="La courbe de déflexion du pneu doit comporter au moins deux points.",
            field="tyre_curve",
            hint="Renseigner la table déflexion / charge.",
        )
        c.check(
            len(self.mu_curve) < 2,
            code="COURBE_MU_INSUFFISANTE",
            message="La courbe μ / glissement doit comporter au moins deux points.",
            field="mu_curve",
            hint="Renseigner la table μ / slip.",
        )

        # Rainures
        c.check(
            len(self.rainures) < 1,
            code="AUCUNE_RAINURE",
            message="Au moins une rainure de bague hydraulique est nécessaire.",
            field="rainures",
            hint="Définir les rainures de la bague hydraulique.",
        )
        for i, r in enumerate(self.rainures):
            c.check(
                r.fin <= r.debut,
                code="RAINURE_INVALIDE",
                message=f"Rainure {i + 1} : la fin ({r.fin}) doit être supérieure au début ({r.debut}).",
                field="rainures",
                hint="Vérifier les cotes début/fin de la rainure.",
            )
        return c

    # ------------------------------------------------------------------ #
    def gas_oil_at_temperature(self) -> dict[str, float]:
        """Paramètres de gaz/huile recalculés à ``self.temperature`` (cf. Excel).

        Les valeurs sont en unités d'affichage (bar, cc, cSt) ; à 25 °C elles
        sont identiques aux valeurs saisies.
        """
        return compute_gas_oil_at_temperature(
            Pinitbp=self.Pinitbp,
            Vgbp=self.Vgbp,
            Vh=self.Vh,
            Pinithp=self.Pinithp,
            Vghp=self.Vghp,
            visc=self.visc,
            temperature=self.temperature,
        )

    # ------------------------------------------------------------------ #
    def to_si(self) -> "MLGParamsSI":
        """Convertit toutes les entrées en unités SI pour le moteur."""
        import numpy as np

        def pt(p: Point3) -> np.ndarray:
            return np.array([p.x * U.MM_TO_M, p.y * U.MM_TO_M, p.z * U.MM_TO_M])

        tyre = sorted(self.tyre_curve, key=lambda t: t[0])
        tyre_defl = np.array([d * U.MM_TO_M for d, _ in tyre])
        tyre_load = np.array([l * 1000.0 for _, l in tyre])  # kN -> N

        mu = sorted(self.mu_curve, key=lambda t: t[0])
        mu_x = np.array([s for s, _ in mu])
        mu_y = np.array([m for _, m in mu])

        # Gaz et huile recalculés à la température de chute (cf. Excel MLG/NLG).
        adj = self.gas_oil_at_temperature()
        bulk_adj = compute_bulk_modulus_at_temperature(
            aeration_pct=self.aeration_pct,
            k_air_ref=self.k_air,
            k_huile_ref=self.k_huile,
            temperature=self.temperature,
            k_huile_temp_coeff=self.k_huile_temp_coeff,
        )

        # Les profondeurs de rainures sont saturées au rayon de BH pour le calcul
        # (profondeur effective <= Dbh/2), afin d'éviter un blocage de simulation.
        rainures_profondeur_eff = np.minimum(
            np.array([r.profondeur for r in self.rainures], dtype=float),
            self.Dbh / 2.0,
        )

        return MLGParamsSI(
            masse=self.masse,
            vz=self.vz,
            vx=self.vx,
            lift=self.lift,
            pitch=self.pitch * U.DEG_TO_RAD,
            roll=self.roll * U.DEG_TO_RAD,
            temps_simu=self.temps_simu,
            it=self.it,
            integrator=self.integrator,
            damper_core_solver=self.damper_core_solver,
            Dpis=self.Dpis * U.MM_TO_M,
            Dbh=self.Dbh * U.MM_TO_M,
            Dt=self.Dt * U.MM_TO_M,
            Dp=self.Dp * U.MM_TO_M,
            DInsideBh=self.DInsideBh * U.MM_TO_M,
            DInsidePalierBh=self.DInsidePalierBh * U.MM_TO_M,
            Lbh=self.Lbh * U.MM_TO_M,
            LPalierBh=self.LPalierBh * U.MM_TO_M,
            excentricite_palier_bh=self.excentricite_palier_bh * U.MM_TO_M,
            course=self.course * U.MM_TO_M,
            DTrouPis=self.DTrouPis * U.MM_TO_M,
            NbTrouPis=self.NbTrouPis,
            HauteurPisBh=self.HauteurPisBh * U.MM_TO_M,
            DTrouDiap=self.DTrouDiap * U.MM_TO_M,
            NbTrouDiap=self.NbTrouDiap,
            endstop_smooth=self.endstop_smooth_mm * U.MM_TO_M,
            ASeal=(self.Dt + 2.0 * self.tore) * U.MM_TO_M,  # Ø joint = Dt + 2·tore
            fc=self.fc * 1000.0,  # N/mm -> N/m
            fh=self.fh,
            Pinitbp=adj["Pinitbp"] * U.BAR_TO_PA,
            Vgbp=adj["Vgbp"] * U.CC_TO_M3,
            Vh=adj["Vh"] * U.CC_TO_M3,
            Pinithp=adj["Pinithp"] * U.BAR_TO_PA,
            Vghp=adj["Vghp"] * U.CC_TO_M3,
            gamma=self.gamma,
            visc=adj["visc"] * U.CST_TO_M2S,
            bulk=bulk_adj["bulk"] * U.MPA_TO_PA,
            rho=self.rho,
            unsprung_mass=self.unsprung_mass,
            wheel_inertia=self.wheel_inertia,
            unload_radius=self.unload_radius * U.MM_TO_M,
            kx=self.kx,
            cx=self.cx,
            wheelmass=self.wheelmass,
            jyy=self.jyy,
            B=pt(self.B),
            A=pt(self.A),
            C=pt(self.C),
            R=pt(self.R),
            S=pt(self.S),
            tyre_defl=tyre_defl,
            tyre_load=tyre_load,
            mu_x=mu_x,
            mu_y=mu_y,
            diametre_rainure=self.diametre_rainure,  # gardé en mm (cf. metering)
            rainures_debut=np.array([r.debut for r in self.rainures]),
            rainures_fin=np.array([r.fin for r in self.rainures]),
            rainures_profondeur=rainures_profondeur_eff,
        )


@dataclass
class MLGParamsSI:
    """Paramètres du modèle MLG, intégralement en unités SI (sauf rainures en mm).

    Les rainures restent décrites en millimètres car la loi de metering
    (``CalculBH``) est tabulée millimètre par millimètre, comme dans le VBA.
    """

    masse: float
    vz: float
    vx: float
    lift: float
    pitch: float
    roll: float
    temps_simu: float
    it: float
    integrator: str
    damper_core_solver: str

    Dpis: float
    Dbh: float
    Dt: float
    Dp: float
    DInsideBh: float
    DInsidePalierBh: float
    Lbh: float
    LPalierBh: float
    excentricite_palier_bh: float
    course: float
    DTrouPis: float
    NbTrouPis: float
    HauteurPisBh: float
    DTrouDiap: float
    NbTrouDiap: float
    endstop_smooth: float

    ASeal: float
    fc: float
    fh: float

    Pinitbp: float
    Vgbp: float
    Vh: float
    Pinithp: float
    Vghp: float
    gamma: float

    visc: float
    bulk: float
    rho: float

    unsprung_mass: float
    wheel_inertia: float
    unload_radius: float
    kx: float
    cx: float
    wheelmass: float

    jyy: float

    B: "object"
    A: "object"
    C: "object"
    R: "object"
    S: "object"

    tyre_defl: "object"
    tyre_load: "object"
    mu_x: "object"
    mu_y: "object"

    diametre_rainure: float
    rainures_debut: "object"
    rainures_fin: "object"
    rainures_profondeur: "object"

    # --- Sections dérivées (m²) ------------------------------------------ #
    @property
    def Sc(self) -> float:
        return (self.Dpis ** 2 - self.Dbh ** 2) * math.pi / 4.0

    @property
    def Sd(self) -> float:
        return (self.Dpis ** 2 - self.Dt ** 2) * math.pi / 4.0

    @property
    def Sbh(self) -> float:
        return self.Dbh ** 2 * math.pi / 4.0

    @property
    def St(self) -> float:
        return self.Dt ** 2 * math.pi / 4.0

    @property
    def STrouPis(self) -> float:
        return self.NbTrouPis * self.DTrouPis ** 2 * math.pi / 4.0

    @property
    def STrouDiap(self) -> float:
        return self.NbTrouDiap * self.DTrouDiap ** 2 * math.pi / 4.0


def default_mlg_inputs() -> MLGInputs:
    """Retourne les entrées par défaut (cas nominal de l'onglet « MLG »)."""
    return MLGInputs()


__all__ = ["Point3", "Rainure", "MLGInputs", "MLGParamsSI", "default_mlg_inputs"]
