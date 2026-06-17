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
| 5.1 | Tests de non-régression vs Excel | Validation | Fort | Faible | Moyen |
| 2.1 | Butée de contact lissée | Robustesse | Moyen | Faible | Faible |
| 1.1 | Intégrateur RK4 / adaptatif | Numérique | Fort | Moyen | Élevé |
| 1.2 | Convergence réelle des solveurs | Numérique | Moyen | Moyen | Moyen |
| 3.x | Raffinements physiques (γ, friction, pneu) | Physique | Variable | Moyen | Variable |
| 4.1 | Dynamique 3D / masse non suspendue | Physique | Moyen | Élevé | Élevé |

**Ordre de démarrage recommandé** (gain rapide, risque faible) :
1. Bilan énergétique en sortie (§5.2) — ne change pas la physique ;
2. Tests de non-régression contre l'Excel (§5.1) — sécurise les évolutions ;
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

**Proposition.** Modèle thermodynamique avec **échange de chaleur** (γ effectif
fonction de la vitesse de compression / d'un temps caractéristique), pour
affiner les pics de pression.

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

### 5.1 Tests de non-régression contre l'Excel — *impact fort*

**Constat.** Couverture de tests **faible** (5 tests).

**Proposition.** Ajouter une batterie de tests :
- **non-régression numérique** contre les valeurs Excel de référence, à
  plusieurs **températures**, **masses** et **vitesses** ;
- tests aux **bornes** (course max, divergence attendue) ;
- figer des **snapshots** des grandeurs de synthèse (B46:C61) pour détecter toute
  dérive.

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
