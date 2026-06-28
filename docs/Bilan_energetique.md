# Audit du bilan énergétique — repartir de zéro

> **Objet.** Reconstruire, à partir du **théorème de l'énergie**, le bilan
> énergétique complet d'un drop test, et **identifier pourquoi « l'énergie à
> absorber » ≠ « l'énergie absorbée »** dans le bilan affiché (résidu / écart).
> Même démarche que le PFD : on pose tout à plat, on écrit les formules, **puis on
> confronte au code** (`engine.py`, `engine_aircraft.py`, page Résultats avion).
>
> Document destiné à être **commenté** avant toute correction.

---

## 1. Principe : le théorème de l'énergie

Pour le système complet (cellule + trains + roues), sans apport extérieur autre
que la pesanteur et l'avancement, l'énergie se conserve :

$$
\underbrace{E_{\text{apport}}(t)}_{\text{à absorber}}
= \underbrace{E_{\text{cin}}(t)}_{\text{réservoirs cinétiques}}
+ \underbrace{E_{\text{stock}}(t)}_{\text{stockée (réversible)}}
+ \underbrace{E_{\text{diss}}(t)}_{\text{dissipée (absorbée)}}
+ \ \varepsilon(t)
$$

- **Énergie à absorber** E_apport : énergie cinétique initiale d'impact + travail
  de la pesanteur pendant la course + énergie puisée dans l'avancement (spin‑up).
  C'est ce que le train **doit** encaisser.
- **Énergie absorbée** = part **dissipée** E_diss (irréversible : hydraulique,
  frottements, glissement pneu) **+** part **stockée** E_stock (réversible : gaz,
  élasticité pneu, butée).
- **Résidu** ε(t) : doit tendre vers 0 (erreur d'intégration seule).
  Tout résidu structurel = **terme manquant** dans le bilan.

> Le « bon » bilan se ferme : ε ne doit être que l'erreur du schéma
> (Euler/RK4), décroissante avec Δt. Un écart **constant ou croissant** trahit un
> réservoir ou un flux **oublié**.

---

## 2. Inventaire des réservoirs et des flux

### 2.1 Réservoirs cinétiques (instantanés)

| Réservoir | Expression | Présent page 6 ? |
|---|---|---|
| Translation cellule/CG | ½·m·ż² | ✅ |
| Tangage cellule | ½·Jyy·θ̇² | ✅ |
| **Masse non suspendue** (tige+roue) | ½·Mns·v² | ❌ **omis** |
| **Rotation roue** (spin‑up) | ½·J·ω² | ❌ **omis** |
| **Spring‑back pneu** (translation moyeu) | ½·mw·vx² | ❌ **omis** |
| **Rotation balancier** (MLG) | ½·Jbal·ω_bal² | ❌ **omis** |

### 2.2 Énergie stockée (réversible, restituable)

| Réservoir | Expression | Présent page 6 ? |
|---|---|---|
| Ressort gazeux | ∫ Fgas·dd | ✅ (signé) |
| Élasticité pneu (vertical) | ∫ Ftyre·d(defl) | ✅ (signé) |
| Élasticité spring‑back (horizontal) | ½·kx·δx² | ❌ **omis** |
| Butée de fin de course | ∫ Fbutée·dd | ❌ **omis** |

### 2.3 Énergie dissipée (irréversible = absorbée)

| Dissipation | Expression rigoureuse | Page 6 (recalcul UI) |
|---|---|---|
| Hydraulique | ∫ Fhyd·dd (travail signé) | ∫ max(0, −Fhyd·v)·dt (puissance) |
| Frottement joint | ∫ Ffrijoi·dd | inclus dans p_fric |
| Frottement bagues | ∫ Ffribag·dd | inclus dans p_fric |
| Glissement pneu/sol | ∫ μ·Fz·\|Vglis\|·dt | ✅ |
| Amortisseur spring‑back | ∫ cx·vx²·dt | ❌ **omis** |

### 2.4 Flux d'entrée (« à absorber »)

| Flux | Expression | Page 6 ? |
|---|---|---|
| Cinétique initiale | ΣE_cin(t=0) | partielle (cellule seule) |
| Travail pesanteur | m·g·(1−L)·(z₀−z) | ✅ |
| **Apport d'avancement** (spin‑up puise à Vx) | ∫ Fspin·Vx·dt | ❌ **omis** |

---

## 3. Équation de bilan complète (référence)

$$
E_{\text{apport}} = \underbrace{\sum E_{\text{cin}} + \sum E_{\text{stock}}}_{\text{récupérable}} + \underbrace{\sum E_{\text{diss}}}_{\text{absorbée définitivement}} + \varepsilon
$$

avec, en détail :

$$
E_{\text{apport}} = E_{\text{cin}}(0) + \int (\text{poids})\cdot \dot z\,\mathrm dt + \int F_{spin}\,V_x\,\mathrm dt
$$

$$
\sum E_{\text{cin}} = \tfrac12 m\dot z^2 + \tfrac12 J_{yy}\dot\theta^2 + \sum_{\text{trains}}\Big(\tfrac12 M_{ns} v^2 + \tfrac12 J\,\omega^2 + \tfrac12 m_w v_x^2 + \tfrac12 J_{bal}\,\omega_{bal}^2\Big)
$$

---

## 4. Confrontation au code

### 4.1 Moteur TrailingArm isolé (`engine.py`) — bilan **rigoureux** (référence)

Le moteur **suit tous** les réservoirs et flux ci‑dessus (l.1024‑1264) :

- dissipations en **travail signé F·dd** (l.1187‑1201), qui **se télescope
  exactement** avec le travail de la réaction d'amortisseur → le résidu n'est que
  l'erreur d'Euler (commentaire l.1190‑1195) ;
- spin‑up : apport `e_fwd = ∫Fspin·Vx·dt` et glissement
  `e_slip = ∫Fspin·(Vx−vx)·dt − ΔEc_rot − tr_x·vR_x·dt`, avec **ΔEc_rot exact**
  = ½J(ω²−ω₀²) (l.1218‑1234) — sinon résidu O(Δt²) constant ;
- gravité `e_grav` (l.1236), réservoirs cinétiques (l.1252‑1257).

$$
\varepsilon = E_{\text{cin}}(0) + e_{grav} + e_{fwd} - \big(\textstyle\sum E_{cin} + \sum E_{stock} + \sum E_{diss}\big)
$$

→ **résidu ≈ erreur d'intégration** (~0,3 % de l'apport, décroît avec Δt). **C'est
le modèle à suivre.**

### 4.2 Bilan **avion** (page `6_Resultats_avion_complet.py`) — sources des écarts

⚠️ Le bilan avion **n'utilise pas** les énergies suivies par le moteur : il est
**recalculé dans l'UI** à partir des colonnes de sortie (l.758‑890). D'où les
écarts :

1. **Apport incomplet** : `e_input = ½m·ż² + ½Jyy·θ̇²` (cellule) `+ gravité`
   seulement. **Manque** : la cinétique initiale des trains (Mns, roue, spring‑back,
   balancier) **et** l'apport d'avancement `∫Fspin·Vx·dt`.
2. **Réservoirs cinétiques omis** : masse non suspendue, rotation roue,
   spring‑back, **rotation balancier** (cf. §2.1). Leur énergie « disparaît » du
   bilan → écart.
3. **Stockage incomplet** : spring‑back élastique (½kx·δx²) et butée omis (§2.2).
4. **Dissipation en puissance, pas en travail** : `p_hyd = max(0, −Fhyd·v)` puis
   `cumtrapz` (l.789, 826). La version travail `∫Fhyd·dd` se télescope exactement ;
   la version puissance souffre du **lag de ΔP** et de l'erreur d'intégration
   (cf. commentaire l.1195 du moteur). De plus le `max(0, …)` **ignore les phases
   de restitution** (détente) → biais.
5. **Amortisseur spring‑back** `∫cx·vx²·dt` omis (§2.3).

Le code page 6 le reconnaît : « l'écart restant correspond aux termes internes
encore non modélisés » (caption l.850‑854).

---

## 5. Synthèse — pourquoi « à absorber » ≠ « absorbée »

| # | Cause de l'écart | Niveau | Effet |
|---|---|---|---|
| G1 | Cinétique des trains (Mns, roue, spring‑back, balancier) absente de l'apport ET des réservoirs | Apport + réservoirs | écart structurel |
| G2 | Apport d'avancement ∫Fspin·Vx·dt omis | Apport | sous‑estime l'apport |
| G3 | Stockage spring‑back (½kx·δx²) + butée omis | Stock | écart en fin de course |
| G4 | Dissipation hydraulique en **puissance** (+ max(0,·) + lag ΔP) au lieu de **travail F·dd** | Dissipation | biais + bruit |
| G5 | Amortisseur spring‑back cx·vx² omis | Dissipation | petit écart |
| G6 | Recalcul UI au lieu de réutiliser le bilan moteur (déjà fermé) | Architecture | duplication + dérive |

---

## 6. Recommandation (à valider)

**Propager le bilan rigoureux du moteur jusqu'à l'avion**, au lieu de le recalculer
dans l'UI :

1. Faire **tracker l'énergie par `engine_aircraft`** (somme des bilans par train,
   façon `engine.py` : travail signé F·dd, ΔEc_rot exact, apport d'avancement),
   **plus** la cinétique fuselage (translation + tangage).
2. Inclure **tous** les réservoirs (§2.1‑2.2) et l'apport d'avancement (§2.4).
3. Exposer `e_input`, `e_diss`, `e_stock`, `e_residual` comme **colonnes moteur**,
   et la page 6 ne fait plus que les **tracer** (plus de recalcul).

Cible : ε réduit à l'**erreur d'intégration** (décroissante avec Δt),
comme le moteur TrailingArm isolé.

---

## 7. À discuter (vos commentaires)

- Confirmer la liste des réservoirs (notamment la **rotation balancier** depuis le
  remodelage rigide §6.7 du PFD, et l'inertie propre du bras).
- Choisir la convention de dissipation : **travail F·dd** (recommandé, se ferme)
  vs **puissance F·v·dt**.
- Décider si l'on garde une part « stockée » séparée (gaz+pneu) dans l'affichage
  (utile pour distinguer absorbé **définitif** vs restituable).
