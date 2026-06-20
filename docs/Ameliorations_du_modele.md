# Pistes d'amélioration du modèle `dropsim`

> Recensement des axes d'amélioration du moteur de simulation de drop test
> (train à balancier MLG). Classé par nature et par priorité, avec pour chaque
> point le **constat** (état actuel du code), l'**amélioration proposée** et
> l'**impact** estimé. Sert de feuille de route technique.

---

## Synthèse des priorités

| # | Amélioration | Nature | Impact | Risque | Effort |
|---|---|---|---|---|---|
| 5.2 | Bilan énergétique en sortie — ✅ **fait** | Diagnostic | Fort | Faible | Faible |
| 5.1 | Tests de non-régression — ✅ **fait** | Validation | Fort | Faible | Moyen |
| 2.1 | Butée de contact lissée — ✅ **fait** | Robustesse | Moyen | Faible | Faible |
| 1.1 | Intégrateur RK4 / adaptatif — 🔄 **en cours** | Numérique | Fort | Moyen | Élevé |
| 1.2 | Convergence réelle des solveurs | Numérique | Moyen | Moyen | Moyen |
| 3.x | Raffinements physiques (γ, friction, pneu) | Physique | Variable | Moyen | Variable |
| 3.5 | Compressibilité et pertes de charge | Physique | Moyen | Moyen | Moyen |
| 4.1 | Dynamique 3D / masse non suspendue | Physique | Moyen | Élevé | Élevé |

**Ordre de démarrage recommandé** (gain rapide, risque faible) :
1. Bilan énergétique en sortie (§5.2) — ✅ fait ;
2. Tests de non-régression (§5.1) — ✅ fait ;
3. Butée de contact lissée (§2.1) — stabilité ;
4. puis expérimenter un intégrateur RK4/adaptatif (§1.1) en gardant Euler en option.

---

## 1. Schéma d'intégration numérique

### 1.1 Intégrateur d'ordre supérieur et pas adaptatif — *impact fort*

**Constat.** Toute l'intégration temporelle est en **Euler explicite d'ordre 1**
à pas fixe (`engine.py`). La stabilité dépend d'un pas de temps $\Delta t$ choisi
manuellement (typiquement $10^{-4}$ s).

**Proposition.**
- Passer à un intégrateur d'ordre supérieur (**RK4**) ou **semi-implicite /
  symplectique** : meilleure précision à pas égal, ou pas plus grand à précision
  égale.
- Introduire un **pas de temps adaptatif** avec contrôle d'erreur (ex. RK45) pour
  éviter les divergences silencieuses et adapter le pas aux phases raides.
- Le couplage raide (butée $K = 10^8$ N/m, hydraulique) est un cas typiquement
  **raide** : un schéma implicite serait plus stable.
- Conserver Euler en **option** pour comparer et garder la fidélité au classeur.

**État d'avancement (juin 2026).**
- Le sélecteur `integrator = euler|rk4` est disponible en entrée (UI + modèle).
- Le mode `rk4` est actif sur les intégrations cinématiques à accélération tenue
  constante pendant le pas (masse suspendue, rotation balancier, spring-back).
- Le couplage complet gaz/hydraulique reste évalué explicitement au pas (même
  structure de boucle que l'historique), donc le RK4 actuel n'est pas encore un
  schéma fully-coupled de toute la chaîne.
- Un mode noyau `damper_core_solver = legacy|implicit_adaptive` est disponible.
  Le mode `implicit_adaptive` applique une résolution implicite locale avec
  sous-pas adaptatifs sur le noyau gaz/hydraulique (essai activable, non défaut).
- Une non-régression automatique compare désormais `euler` et `rk4` au pas
  nominal sur quatre garde-fous pratiques :
  - écart de pic vertical $F_z$ ≤ 0,5 % ;
  - écart de course max ≤ 0,5 mm ;
  - écart d'accélération max ≤ 0,05 g ;
  - résidu énergétique max RK4 ≤ 1,2 × résidu Euler.
- Une comparaison de convergence par raffinement de pas est couverte dans les
  tests : passage de $10^{-4}$ s à $5\times10^{-5}$ s pour `euler` et `rk4`,
  avec contrôle de baisse du résidu énergétique et bornes d'écart coarse/fine
  sur les grandeurs de synthèse.

**Retour de benchmark (nominal, RK4, $\Delta t=10^{-4}$ s).**
- `implicit_adaptive` améliore légèrement la cohérence des grandeurs de sortie
  (écarts faibles, résidu énergétique similaire), mais coûte environ ×2,5 en
  temps CPU vs `legacy` sur le cas nominal.

**Prochaine sous-étape.**
- Étendre l'intégration d'ordre supérieur à l'ensemble du pas couplé (ou
  introduire un sous-pas contrôlé) puis comparer systématiquement
  `euler`/`rk4` sur résidu énergétique, pics d'efforts et stabilité.

### 1.2 Convergence réelle des solveurs internes — *impact moyen*

**Constat.** Les sous-itérations Newton-Raphson sont à **nombre fixe** :
- ressort gazeux : 12 itérations (avec un `tol` mais sans repli) ;
- hydraulique : **4 itérations « en dur »** (`For i = 0 To 3`), non convergées
  par construction, pour fidélité au VBA ;
- géométrie (position A, R) : 6 itérations fixes.

**Proposition.**
- Remplacer les boucles à itérations fixes par un **critère de convergence**
  (résidu sous tolérance) avec garde-fou sur le nombre max d'itérations.
- Ajouter un **repli** (damped Newton, line search) en cas de non-convergence.
- ⚠️ Pour l'hydraulique, conserver le comportement VBA derrière une **option**
  (le couplage auto-référent à 4 itérations est nécessaire pour reproduire
  exactement les pressions du classeur).

---

## 2. Robustesse numérique

### 2.1 Butée de fin de course lissée — *impact moyen*

**Constat.** La butée hors de l'intervalle $[0, \text{course}]$ est un ressort
très raide $K = 10^8$ N/m, qui introduit une **discontinuité brutale** de
l'effort.

**Proposition.** Modèle de contact **lissé** : raideur progressive (polynomiale
ou exponentielle) + amortissement de contact, pour réduire les chocs numériques
et améliorer la stabilité du schéma explicite.

### 2.2 Diagnostics de divergence enrichis — *impact faible*

**Constat.** Plusieurs `np.linalg.solve` / tests `det == 0` peuvent diverger ;
les messages d'erreur existent mais le repli est absent.

**Proposition.** Damped Newton / line search en cas de jacobien mal conditionné,
et journalisation du conditionnement pour diagnostiquer les cas extrêmes.

### 2.3 Seuils flottants au lieu d'égalités exactes — *impact faible*

**Constat.** Les branches `if v != 0.0` (friction, hydraulique) reposent sur une
comparaison flottante **exacte**, fragile.

**Proposition.** Utiliser un seuil $|v| < \varepsilon$ (avec $\varepsilon$
paramétrable) pour décider de l'activation des termes dépendant de la vitesse.

---

## 3. Précision physique

### 3.1 Loi polytropique à exposant variable — *impact variable*

**Constat.** L'exposant polytropique est **fixe** ($\gamma = 1{,}4$). En réalité
$\gamma$ varie entre compression rapide (adiabatique) et lente (isotherme).

**Clarification physique (état de l'art).** En pratique, l'effet de la dynamique
(vitesse de compression, durée du choc, échanges thermiques avec la paroi) agit
surtout sur l'**exposant polytropique effectif** $n_{eff}$ de la loi
$P\,V^{n_{eff}}=\text{cte}$, et non sur le $\gamma$ thermodynamique pur
($\gamma = C_p/C_v$) pris isolément. Le comportement observé est :
- régime lent, bien refroidi : $n_{eff} \rightarrow 1$ (quasi isotherme) ;
- régime rapide, peu d'échange thermique : $n_{eff} \rightarrow \gamma(T)$
  (quasi adiabatique).

**Proposition (niveau 1, faible risque).** Conserver l'architecture actuelle et
introduire un $n_{eff}$ dépendant d'un rapport de temps caractéristiques :

$$
n_{eff} = 1 + (\gamma(T)-1)\,\frac{\tau_{th}}{\tau_{th}+\tau_c},
\quad
{}\tau_c = \frac{V}{|\dot V|+\varepsilon}
$$

avec mise a jour pression par pas :

$$
P_{k+1}=P_k\left(\frac{V_k}{V_{k+1}}\right)^{n_{eff,k}}
$$

Ce formalisme reproduit naturellement la transition lent/rapide sans changer le
reste du solveur.

**Proposition (niveau 2, fidelite accrue).** Ajouter $\gamma(T)$ (table ou loi
analytique simple) afin de capturer la variation de proprietes du gaz avec la
temperature.

**Proposition (niveau 3, modele thermo complet).** Remplacer la loi polytropique
imposee par une equation d'energie gaz :

$$
m c_v(T)\frac{dT}{dt} = -P\frac{dV}{dt} - hA\,(T-T_{paroi}),
\quad
P=\frac{mRT}{V}
$$

Dans ce cas, $n_{eff}$ devient emergent et n'est plus un parametre direct.

**Plan d'integration recommande (differe).**
1. **Ne pas activer maintenant** dans le mode par defaut ; documenter et garder
  le mode actuel pour la regression VBA.
2. Ajouter un drapeau de configuration, par exemple
  `gas_model = "legacy_gamma_constant" | "dynamic_polytropic" | "thermo_coupled"`.
3. Commencer par `dynamic_polytropic` (1 parametre principal $\tau_{th}$ a
  calibrer), puis envisager `thermo_coupled` uniquement si les ecarts essais
  restent significatifs.

**Impact attendu.** Amelioration de la prediction des pics de pression et de la
raideur apparente du ressort gaz quand on change l'echelle temporelle de
l'impact, sans perturber les cas deja valides tant que le mode legacy reste
actif.

### 3.2 Friction : stick-slip et bagues de guidage — *impact moyen*

**Constat.** La friction des joints (Coulomb + terme de pression) est
semi-empirique. La friction des **bagues de guidage** (`FFriBag`, présente dans
le module VBA NLG mais **commentée** côté MLG) n'est pas modélisée.

**Proposition.**
- Ajouter le **stick-slip** (friction statique > friction dynamique) pour les
  faibles vitesses.
- Porter `FFriBag` (friction des bagues, fonction des efforts transverses
  $X_{Gt}, X_{Gb}$) déjà présente dans le VBA.

### 3.3 Interpolation spline des tables pneu — *impact faible*

**Constat.** Les tables déflexion/charge et $\mu$/glissement sont interpolées
**linéairement** : efforts « anguleux », dérivées discontinues.

**Proposition.** Interpolation **spline** (C¹/C²) pour lisser les efforts et
leurs dérivées. Documenter / calibrer le facteur $0{,}55$ sur $\mu$ et le rayon
effectif $R_{eff} = R_0 - \delta/3$.

### 3.4 Amortissement vertical du pneu — *impact faible*

**Constat.** Seul le ressort **horizontal** (spring-back) possède un amortisseur
$c_x$ ; le pneu **vertical** est purement élastique (aucune dissipation
verticale).

**Proposition.** Ajouter un terme d'amortissement vertical du pneu (modèle
ressort-amortisseur), si les données d'hystérésis pneu sont disponibles.

### 3.5 Compressibilité de l'huile et pertes de charge: étude comparative — *impact moyen à fort*

**Constat.** Le modèle actuel traite correctement la compressibilité au bon
endroit physique: dans le **bilan de volume** de la chambre (`gas.py`) via le
module volumique $B$, tandis que la **perte de charge** reste fondée sur une loi
orifice/Bernoulli quasi-incompressible (`hydraulic.py`) avec masse volumique
constante. C'est une hypothèse standard pour les amortisseurs hydrauliques tant
que les variations de pression restent loin de la cavitation et que les effets
thermiques restent secondaires.

**Comparatif des formulations possibles.**

| Formulation | Idée | Avantage | Limite | Insertion dans `dropsim` |
|---|---|---|---|---|
| Actuelle | $\Delta P = \tfrac12\rho(Q/(SC_d))^2\,\mathrm{sign}(Q)$, compressibilité seulement dans le bilan de volume | Simple, robuste, fidèle au VBA | Densité figée, pas de cavitation, pas d'air dissous | `hydraulic.py` + `gas.py` |
| Quasi-compressible | Remplacer $\rho$ par une densité moyenne $\bar\rho(P,T)$ ou un coefficient corrigé | Faible coût, améliore les très fortes pressions | Gain limité si l'huile reste peu compressible | `hydraulic.py` |
| Compressible avec densité variable | Résoudre $\Delta P$ avec une loi d'état $\rho(P,T)$ et débit massique $\dot m$ | Plus cohérent si la pression varie fortement | Newton plus raide, calibration plus lourde | `hydraulic.py` |
| Compressible avec cavitation / aération | Ajouter un plafond de pression basse et un $B_{eff}$ dégradé par l'air dissous | Représente les pics raides et la perte d'amortissement | Requiert paramètres supplémentaires et validation expérimentale | `hydraulic.py` + `gas.py` |

**Lecture comparative.**
- Pour un amortisseur d'atterrisseur, la formulation la plus utilisée en modèle
  système reste celle du projet: huile faiblement compressible au niveau du
  volume de chambre, pertes de charge locales de type orifice.
- La formulation **quasi-compressible** est le meilleur compromis si l'on veut
  améliorer la physique sans changer l'architecture numérique: on conserve la
  structure du solveur, mais on évalue $\rho$ et/ou $C_d$ à partir d'une
  pression moyenne sur la branche hydraulique.
- La formulation **massique** (débit massique au lieu de débit volumique) n'a
  d'intérêt que si l'on cherche à traiter des écarts de pression très élevés ou
  des variations thermiques marquées; elle rend le Newton plus délicat sans
  bénéfice majeur sur le cas nominal.
- Le traitement **cavitation / aération** devient pertinent si les calculs ou
  les essais montrent une chute de pression proche de la pression de vapeur ou
  une dérive nette des pics mesurés à grande vitesse. C'est le vrai saut de
  fidélité, mais aussi le plus coûteux en calibration.

**Comment l'implanter proprement dans le modèle.**
- Conserver le mode actuel comme **référence** et ajouter un drapeau de
  configuration, par exemple `hydraulic_model = "legacy" | "quasi_compressible" | "massique" | "cavitation"`.
- Isoler la loi de débit dans une fonction dédiée, de façon à pouvoir choisir
  entre un débit volumique classique et une version corrigée sans réécrire la
  boucle Newton.
- Introduire une loi d'état locale simple, par exemple $\rho(P) = \rho_0
  (1 + (P-P_0)/B)$, uniquement dans la branche choisie par le drapeau.
- Si la cavitation est activée, borner la pression minimale à une valeur de
  référence (pression de vapeur ou pression d'aération) et faire décroître
  l'amortissement effectif quand la chambre se désaère.
- Garder la version actuelle en mode par défaut pour préserver la comparabilité
  avec l'Excel et les tests de non-régression.

**Priorité recommandée.**
1. Étape 1: formulation quasi-compressible avec densité moyenne, car elle se
   branche sans changer la topologie du solveur.
2. Étape 2: ajout d'un $B_{eff}$ ou d'une cavitation simplifiée si les écarts
   avec l'essai restent concentrés sur les pics de pression ou le rebond.
3. Étape 3: passage au débit massique seulement si une campagne d'essais ou une
   étude de sensibilité montre que la variation de densité n'est plus négligeable.

---

## 4. Mécanisme et modélisation 3D

### 4.1 Dynamique 3D et masse non suspendue propre — *impact moyen*

**Constat.** Le balancier est traité **dans le plan X-Z** ; l'obliquité en Y
n'est prise qu'en **projection** de l'effort d'amortisseur. La `unsprung_mass`
(masse non suspendue) est saisie mais la roue n'a **pas d'équation verticale
propre** distincte.

**Proposition.**
- Donner à la masse non suspendue sa **propre dynamique verticale** (2ᵉ ddl).
- À terme, modèle **multicorps 3D** complet pour les cas fortement obliques
  (pitch/roll importants).

---

## 5. Validation et qualité logicielle

### 5.1 Tests de non-régression contre l'Excel — *impact fort* — ✅ **implémenté**

**Constat.** Couverture de tests **faible** (5 tests).

**Réalisé.** Une batterie de tests de non-régression (`tests/test_regression.py`,
21 tests) protège désormais les évolutions futures contre toute dérive
involontaire des résultats. Trois familles :
- **Golden tests de synthèse** — un *snapshot* des grandeurs de synthèse
  (`summary` + `summary_rows`, équivalent du bloc B46:C61 « Summary MLG ») est
  figé dans `tests/reference/golden_summary.json` pour **3 cas** (nominal,
  froid/lourd, léger/lent) et comparé à tolérance serrée ($r=10^{-4}$). Toute
  dérive sur n'importe quelle grandeur est détectée. Une fonction
  `regenerate_golden()` permet de régénérer le *golden* après un changement de
  physique **assumé**.
- **Non-régression de courbe** — au-delà des seuls pics, l'**écart RMS** sur tout
  l'historique temporel de $F_z(t)$ et de la course $d(t)$ est comparé au CSV de
  référence Excel (`_extract/reference/Results_MLG.csv`, seuil 2 % du pic).
- **Invariants physiques** — sur un balayage masse/vitesse/température : monotonies
  ($F_z\nearrow$ avec la masse, course $\nearrow$ avec $V_z$, $F_x\nearrow$ avec
  $V_x$), finitude/positivité des grandeurs clés, course bornée par la butée et
  absence d'effort de spin-up à $V_x=0$.

> **Limite.** La référence Excel ne couvre qu'**un seul** point de fonctionnement.
> La non-régression *multi-cas contre l'Excel* n'est donc pas possible faute de
> données ; elle est remplacée par des **golden tests Python** (régression contre
> soi-même) + invariants physiques, ce qui couvre l'objectif réel (sécuriser les
> évolutions). Élargir la référence Excel à plusieurs cas reste souhaitable.

### 5.2 Bilan énergétique en sortie — *impact fort, risque faible* — ✅ **implémenté**

**Constat.** Aucun **bilan d'énergie** n'était calculé.

**Réalisé.** Le moteur (`engine.py`) accumule désormais, à chaque pas, et expose
en sortie (préfixe `Énergie…`) **tous** les chemins énergétiques du modèle :

*Réservoirs cinétiques* (état courant) :
- masse suspendue $E_{cin} = \tfrac{1}{2} M_s \dot z^2$ ;
- rotation du balancier $E_{bal} = \tfrac{1}{2} J_{yy}\,\dot\theta_y^2$ ;
- rotation de la roue (spin) $E_{rot} = \tfrac{1}{2} J_{roue}\,\omega^2$ ;
- translation horizontale de la roue $E_{horiz} = \tfrac{1}{2} m_{roue}\,\dot x^2$.

*Énergies stockées* (réversibles) :
- gaz $E_{gaz} = \sum F_{gas}\,\mathrm{d}d$ ;
- pneu vertical $E_{pneu} = \sum F_{tyre}\,\mathrm{d}\delta$ ;
- ressort horizontal du pneu $E_{ress,x} = \tfrac{1}{2} k_x\,\Delta x^2$ ;
- butée $E_{butée} = \sum F_{butée}\,\mathrm{d}d$.

*Énergies dissipées* (travaux signés $F\,\mathrm{d}d$, qui se télescopent
exactement avec le travail de la réaction d'amortisseur sur les corps) :
- hydraulique $E_{hyd} = \sum F_{hyd}\,\mathrm{d}d$ ;
- friction de joint $E_{fric} = \sum F_{frijoi}\,\mathrm{d}d$ ;
- amortisseur horizontal $E_{amort,x} = \sum c_x\,\dot x^2\,\mathrm{d}t$ ;
- **glissement au contact pneu/sol** $E_{glis}$ (chaleur du spin-up).

*Apports* :
$E_{in} = E_{cin}^{init} + W_{gravité} + E_{avancement}$, où $E_{avancement}$ est
l'énergie puisée dans le mouvement d'avancement de l'aéronef par la friction de
contact ($\sum F_{spin}\,V_x\,\mathrm{d}t$).

**Fermeture du bilan d'avancement.** L'énergie d'avancement se répartit en quatre
parts : (1) le gain d'énergie cinétique de rotation de la roue, évalué par sa
**variation exacte** $\tfrac{1}{2} J_{roue}(\omega^2 - \omega_0^2)$ — nécessaire
car le couple de spin-up est quasi-impulsionnel ($\alpha$ très grand), si bien
qu'un produit $F_{spin}(R_0-\delta)\,\omega\,\Delta t$ laisserait une erreur
$O(\Delta t^2)$ **constante** ; (2) le travail sur la translation propre de la
roue $F_{spin}\,\dot x$ ; (3) le **travail de l'effort longitudinal $T_x$ sur le
moyeu $R$ lorsque le balancier pivote** ($T_x\,\dot x_R$) — l'effort de contact
pousse le moyeu horizontalement et injecte de l'énergie dans le mécanisme
(balancier → amortisseur → masse suspendue) ; (4) le reste est la chaleur de
glissement $E_{glis}$. Par construction, apport − glissement = énergie entrant
réellement dans la roue et le mécanisme.

La cohérence
$E_{in} \approx E_{cin} + E_{bal} + E_{rot} + E_{horiz} + E_{gaz} + E_{pneu} + E_{ress,x} + E_{butée} + E_{hyd} + E_{fric} + E_{amort,x} + E_{glis}$
est tracée dans l'onglet **Bilan énergétique** de la page Résultats et vérifiée
par un **test de conservation** (`tests/test_energy.py`). **Tous les chemins
énergétiques étant comptabilisés, le résidu se réduit à la seule erreur
d'intégration d'Euler explicite** : il vaut **~0,3 % de l'énergie d'impact** au
pas par défaut et **décroît linéairement avec le pas de temps** (vérifié par
test : diviser $\Delta t$ par 2 réduit le résidu de moitié). Le seuil du test est
fixé à 2 %. Ce bilan, **purement passif**, ne modifie pas la physique et sert de
détecteur de bugs pour les évolutions futures.

### 5.3 Performance (vectorisation / JIT) — *impact faible*

**Constat.** La boucle d'intégration pas-à-pas en Python pur est lente pour les
longues simulations.

**Proposition.** Vectorisation partielle, ou compilation **Numba** des boucles
chaudes, si la performance devient limitante. À ne faire qu'après avoir sécurisé
la validation (§5.1) pour pouvoir comparer.

---

## Notes de mise en œuvre

- Toute évolution touchant la physique doit être **précédée** des tests de
  non-régression (§5.1) pour garantir la fidélité au classeur Excel de référence.
- Les changements modifiant le comportement numérique (intégrateur, butée,
  convergence) devraient être **optionnels** (drapeau de configuration) afin de
  conserver un mode « fidèle VBA » par défaut.
- Le bilan énergétique (§5.2) est le point d'entrée idéal : purement diagnostique,
  il ne modifie pas les résultats et outille toutes les améliorations suivantes.

---

*Document de feuille de route — projet SimuLanding, moteur `dropsim`. À mettre à
jour au fur et à mesure de l'implémentation des points ci-dessus.*
