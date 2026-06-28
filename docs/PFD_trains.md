# PFD des trains — dérivation rigoureuse (vérification des hypothèses)

> **Objectif.** Reconstruire, à partir des **règles et conventions de la
> mécanique du solide** (et non de ce que fait le programme), le Principe
> Fondamental de la Dynamique pour chaque train. Méthode :
>
> 1. on **isole chaque solide** ;
> 2. on écrit le **torseur des actions mécaniques** en chaque point d'application ;
> 3. on écrit le **système d'équations** (théorèmes de la résultante et du moment
>    dynamiques) ;
> 4. on en déduit l'effort d'interface transmis à la cellule.
>
> Ce travail sert à **vérifier que les simplifications faites à l'origine**
> (issues du fichier Excel) sont justes. Ordre : **StraitStrut** (ce document),
> puis TrailingArm, puis la structure.
>
> ⚠️ *Ce document remplace une note antérieure qui concluait trop vite sur le
> signe de `Fx@B`. La conclusion de signe est ici **suspendue** : elle dépend de
> conventions (axe X, sens de Vx, sens du spin‑up) qui seront explicitées et
> confrontées au code dans un second temps.*

---

## 1. Conventions et notations

### 1.1 Repères

- **Repère galiléen sol** R₀ = (O, X, Y, Z) : X longitudinal **dirigé vers
  l'arrière de l'avion** (l'avion avance donc vers −X), Z vertical vers le haut,
  Y = Z × X. Trièdre direct.
- **Repère jambe** R₁ = (x₁, y₁, z₁) lié à l'axe du fût : z₁ porté par l'**axe du
  fût**, orienté de la roue R vers l'attache B ; x₁ dans le plan longitudinal,
  y₁ = z₁ × x₁. La jambe est inclinée de l'angle β (chasse + assiette) ; on note
  P = R(0→1) la matrice de passage. Pour une jambe verticale, R₁ ≡ R₀.

### 1.2 Torseur d'action mécanique

L'action d'un ensemble « a » sur un solide « b » est décrite par le **torseur**

$$
\{\mathcal{T}_{a\to b}\}_P=\begin{Bmatrix}\ \vec{R}_{a\to b}\ \\[2pt]\ \vec{M}_{P,a\to b}\ \end{Bmatrix},
\qquad
\vec{M}_{Q}=\vec{M}_{P}+\vec{QP}\times\vec{R}
$$

(R résultante, M_P moment au point P). **3ᵉ loi de Newton** :
{T(a→b)} = −{T(b→a)}.

### 1.3 PFD (Newton–Euler)

Pour un solide S de masse m, centre d'inertie G, dans R₀ galiléen :

$$
\sum \vec{R}_{ext\to S}=m\,\vec{a}_{G}\qquad\text{(résultante dynamique)}
$$
$$
\sum \vec{M}_{G,ext\to S}=\vec{\delta}_{G}=\frac{\mathrm d\vec{\sigma}_G}{\mathrm dt}\qquad\text{(moment dynamique en }G)
$$

On travaille en **problème plan** (x₁, z₁) (plan longitudinal), moments portés
par y₁. Le plan latéral (y₁) est traité par symétrie et n'intervient pas dans
`Fx@B`.

---

## 2. Modélisation du StraitStrut

### 2.1 Les solides isolés

| Solide | Description | Points remarquables | Masse |
|---|---|---|---|
| S₁ | **Tige** (coulisseau) + essieu + **roue** (masse non suspendue) | R, Gb, Gt | m₁ |
| S₂ | **Corps fixe** (fût), solidaire de la cellule | B, Gt, Gb, A | **négligée** (pas de G₂) |

La **roue** tourne librement autour de l'essieu (axe y₁) : son équation de
rotation (spin‑up) est **découplée** des équations de translation/attitude et
traitée à part (§5.4). S₁ regroupe tige + roue pour la résultante et le moment
de translation.

### 2.2 Les liaisons

| Liaison | Nature | Transmet | Ne transmet pas |
|---|---|---|---|
| S₁/S₂ (guidage Gt, Gb) | **glissière** d'axe z₁ (modélisée par 2 appuis ponctuels transverses) | efforts ⊥ axe + moments | effort **axial** z₁ |
| Oléo‑pneu + hydraulique | **actionneur interne** S₂ ↔ S₁ | effort **axial** F_tot (constitutif) : en **A** sur le corps, en **Gt** sur la tige, selon l'axe de coulisse | — |
| S₂ / cellule en B | **encastrement** | effort **et** moment | — |
| roue/sol en S | **contact** | effort de contact (Fx, Fz) | moment → rotation roue |

> **Variante d'ancrage du corps.** Une seconde configuration remplace
> l'encastrement B par un montage isostatique **rotule B1 + linéaire annulaire B2 +
> drag brace (bielle C–D)** ; la tige S₁ et l'axe de coulisse (R, Gt, Gb) y sont
> identiques. Dérivation complète au **§5b**.

> L'effort axial de la glissière idéale est nul : c'est l'**oléo** qui fournit
> l'effort axial F_tot = Sc·Pc − Sd·Pd + Sbh·Pg + **F_fric(joint) +
> F_fric(bagues)** + F_butée. ⚠️ **Les frottements (joint et bagues) sont déjà
> inclus dans F_tot** : on ne les rajoute donc **pas** séparément dans les bilans
> (sinon double comptage).

### 2.3 Conventions de signe explicites (à confronter plus tard)

- Avion en avance : il se déplace vers **−X** (X dirigé vers l'arrière), donc sa
  vitesse longitudinale **Vx < 0**.
- **Effort de contact** sur la roue, noté (Fx, Fz) : Fz = F_tyre ≥ 0 (vers le
  haut). Le signe de **Fx** dépend de la phase (spin‑up vs spring‑back) et
  **sera suivi symboliquement** — c'est lui qui fixe in fine le signe de `Fx@B`.
- Composantes en repère jambe : (fu, fw) = P·(Fx, Fz).

> ⚠️ **Décalage d'axe à instruire (confrontation).** Le programme saisit
> `vx = +36 m/s` (vitesse d'avance **positive**) : son axe longitudinal interne
> pointe donc **vers l'avant**, à l'**opposé** de X (arrière). Ce changement de
> sens entre la convention physique de ce document et celle du code est un
> **candidat direct** pour l'inversion de signe de `Fx@B` — à trancher au §5.4 et
> à l'étape de confrontation.

### 2.4 Paramétrage géométrique

**L'axe de coulisse est défini uniquement par les deux bagues Gt et Gb.** Sa
direction unitaire est û = (Gt − Gb)/‖Gt − Gb‖ (de Gb vers Gt, « vers le haut » du
fût) ; on prend ẑ₁ = û et x̂₁ transverse dans le plan longitudinal. Pour un point
P, on note (ξP, ζP) ses coordonnées jambe : **ξ = décalage transverse à l'axe**,
**ζ = position axiale**.

- **Sur l'axe de coulisse** (ξ = 0) : Gt, Gb et le point A (ci‑dessous).
- **Pouvant être décalés de l'axe** (ξ ≠ 0) : l'attache **B** (sur le corps fixe)
  et le centre roue **R** (sur la tige). Correction au modèle « tout coaxial » :
  un essieu déporté (R) ou une ferrure d'attache déportée (B) sont pris en compte
  par leurs offsets ξR, ξB.

**Point d'application de l'effort d'amortisseur — point A.** L'effort axial de
l'oléo s'applique en un point A **calculé automatiquement** depuis Gt, Gb et la
course :

$$
A = G_t + \text{course}\cdot\frac{G_t - G_b}{\lVert G_t - G_b\rVert}
$$

A est donc sur la droite (Gt Gb), décalé de la **course** depuis Gt **du côté
opposé à Gb** : il reste **sur l'axe** (ξA = 0, ζA = ζt + course) et se déplace
avec l'enfoncement.

**Centre d'inertie de la tige.** G₁ est placé au **milieu de R et Gt** :
G₁ = (R + Gt)/2, soit ξ₁ = ξR/2 et ζ₁ = (ζR + ζt)/2.

**Appartenance des bagues (important pour la friction).** La bague haute **Gt est
portée par la tige** (elle **coulisse** : sa position avance avec la masse non
suspendue, comme R) ; la bague basse **Gb est portée par le corps fixe** (solidaire
de la cellule). L'**entraxe Gt–Gb varie donc avec la course**, ce qui modifie la
répartition des réactions de bague Xgt/Xgb (§2.2, règle du levier) et **donc
l'effort de frottement de bague** ``ffribag``. (Le modèle initial figeait Gt sur le
corps fixe — corrigé.)

Le point de contact S est sous R : vecteur RS = −R_eff·Z.

---

## 3. Isolement du solide S₁ (tige + roue)

### 3.1 Inventaire des torseurs d'actions extérieures

| Action | Point | Résultante (rep. jambe) | Moment propre |
|---|---|---|---|
| Pesanteur | G₁ | P₁ (poids m₁g) | 0 |
| Contact sol → roue | R (offset ξR) | (fu, fw) | 0 (le moment de spin part en rotation roue) |
| Oléo S₂ → S₁ | Gt | (0, −F_tot) | 0 |
| Guide haut S₂ → S₁ | Gt | (Xt, 0) | 0 |
| Guide bas S₂ → S₁ | Gb | (Xb, 0) | 0 |

### 3.2 Théorème de la résultante dynamique

Projection sur x₁ et z₁ (accélération a_G1 = (γ1u, γ1w)) :

$$
\boxed{\;f_u + X_t + X_b + P_{1u} = m_1\,\gamma_{1u}\;}\tag{1}
$$
$$
\boxed{\;f_w - F_{tot} + P_{1w} = m_1\,\gamma_{1w}\;}\tag{2}
$$

L'équation (2) est l'équation d'**enfoncement de la masse non suspendue** (DDL
axial d).

### 3.3 Théorème du moment dynamique (en Gb, projeté sur y₁)

Moment d'une force (Fu, Fw) appliquée en (ξ, ζ), réduit en Gb (sur l'axe) :
M_y = (ζ − ζb)·Fu − ξ·Fw. L'oléo (en A) et les bagues étant **sur l'axe**, seul le
**décalage ξR de la roue** introduit un terme nouveau (le chargement vertical fw
charge alors les bagues) :

$$
\boxed{\;(\zeta_t-\zeta_b)\,X_t + (\zeta_R-\zeta_b)\,f_u - \xi_R\,f_w + (\zeta_1-\zeta_b)P_{1u} - \xi_1 P_{1w} = \delta_{1y}\;}\tag{3}
$$

(l'oléo en Gt, sur l'axe, a un moment nul en Gb ; Xb aussi). δ1y = moment
dynamique de S₁ en Gb (nul si attitude imposée et S₁ sans inertie de rotation
propre).

---

## 4. Isolement du solide S₂ (corps fixe)

### 4.1 Inventaire des torseurs d'actions extérieures

**Masse du corps fixe négligée** → pas de poids ni d'inertie : S₂ est en
**équilibre** (membres de droite nuls).

| Action | Point | Résultante (rep. jambe) | Moment propre |
|---|---|---|---|
| Cellule → S₂ (encastrement) | B (offset ξB) | (Bu, Bw) | M_B |
| Oléo S₁ → S₂ (réaction) | A | (0, +F_tot) | 0 |
| Guide haut S₁ → S₂ (réaction) | Gt | (−Xt, 0) | 0 |
| Guide bas S₁ → S₂ (réaction) | Gb | (−Xb, 0) | 0 |

### 4.2 Équilibre de la résultante (S₂ sans masse)

$$
\boxed{\;B_u - X_t - X_b = 0\;}\tag{4}
$$
$$
\boxed{\;B_w + F_{tot} = 0\;}\tag{5}
$$

### 4.3 Équilibre des moments (en B, projeté sur y₁)

B pouvant être **décalé** de l'axe (ξB ≠ 0), l'effort d'amortisseur (en A, sur
l'axe) crée un moment à l'attache via cet offset (terme +ξB·F_tot) :

$$
\boxed{\;M_B + \xi_B\,F_{tot} - (\zeta_t-\zeta_B)X_t - (\zeta_b-\zeta_B)X_b = 0\;}\tag{6}
$$

---

## 5. Système complet et résolution

### 5.1 Efforts de guidage (de (1) et (3))

De (1) : Xt + Xb = m1·γ1u − fu − P1u. De (3) on tire Xt, puis Xb. À masses
négligées :

$$
X_t = \frac{(\zeta_R-\zeta_b)\,f_u - \xi_R\,f_w}{\zeta_t-\zeta_b},\qquad X_b = -f_u - X_t
$$

> **Simplification programme** (à vérifier) : si la roue est **coaxiale** (ξR = 0),
> on retombe sur la pure **règle du levier** Xt = (ζR−ζb)/(ζt−ζb)·fu,
> Xb = −fu − Xt → **conforme** au code (`xgt+xgb=-xr`). **Nouveau terme si R
> déportée** (ξR ≠ 0) : le chargement **vertical** fw charge aussi les bagues
> (−ξR·fw) — absent du code, qui suppose la coaxialité.

### 5.2 Effort d'interface en B

L'effort exercé **par la cellule sur le train** est (Bu, Bw, M_B) ; l'effort
exercé **par le train sur la cellule** (celui qui dimensionne l'attache et qui
entre dans le PFD avion) est son **opposé** : F_B(train→cellule) = −(Bu, Bw).

De (4) [S₂ sans masse] : B_u = X_t + X_b, et de (1) : X_t + X_b = m_1γ_{1u} − f_u
− P_{1u}. Donc :

$$
\boxed{\;F_{B,u}^{\,train\to cell} = -B_u = f_u + P_{1u} - m_1\gamma_{1u}\;}
$$

De (5) [S₂ sans masse] : B_w = −F_tot, soit un résultat **exact** :

$$
\boxed{\;F_{B,w}^{\,train\to cell} = -B_w = F_{tot}\;}
$$

### 5.3 Lecture du résultat

- **Composante axiale/verticale** : S₂ sans masse → **F_B,w = F_tot (exact)**.
  C'est l'effort d'amortisseur (frottements joint + bagues **inclus dans F_tot**)
  transmis à la cellule. **Signe non litigieux.**
- **Composante transverse/horizontale** : à masses négligées,
  $$\boxed{\;F_{B,u}^{\,train\to cell}\approx f_u\;}$$
  c.‑à‑d. **égale à la composante transverse de l'effort de contact** (fu,
  projetée en repère jambe). **Tout le signe de `Fx@B` se réduit donc au signe de
  l'effort de contact horizontal fu** — d'où l'importance de fixer rigoureusement
  Fx (§5.4).
- **Effet des décalages B, R** : les offsets ξB, ξR **ne changent pas** F_B,u (la
  résultante transverse (1)+(4) en est indépendante) ; ils ne modifient que la
  **répartition des bagues** (Xt, Xb) et le **moment d'interface** M_B (terme
  ξB·F_tot). Le verdict de signe sur `Fx@B` reste donc **inchangé** par les
  décalages.

### 5.4 Rotation de la roue et signe de l'effort de contact

Équation de rotation de la roue (essieu y₁, inertie J) :
$$
J\,\dot\Omega = R_{eff}\,F_{spin},\qquad F_{spin}=\mu\,F_{tyre}\,\mathrm{sgn}(g_{liss}),\quad g_{liss}=V_x-\Omega R_{eff}
$$

- **Phase spin‑up** : au toucher, la roue ne tourne pas ; le point de contact
  accompagne l'avion **vers l'avant (−X)** par rapport au sol. La friction
  sol→roue **s'oppose** à ce glissement → elle est dirigée **vers l'arrière
  (+X)**. Donc l'effort de contact longitudinal **Fx > 0** (selon +X) en phase
  spin‑up.
- L'effort réellement transmis au moyeu passe par la **raideur de pneu** (modèle
  spring‑back) : f_pneu = −kx·δx − cx·(dδx/dt), qui en quasi‑statique équilibre
  la friction.

> **Le point à trancher (étape suivante)** : selon que l'on transmette à la
> cellule **l'effort de contact** Fx ou **l'effort élastique au moyeu** f_pneu
> (de signes opposés en régime transitoire), `Fx@B` change de signe. Le présent
> bilan montre que c'est **la composante transverse de l'action réellement
> appliquée à S₁ en R** qui doit apparaître — il faudra donc identifier sans
> ambiguïté quelle force physique agit sur le moyeu, et la confronter à
> `fx_spring_wheel` (code) et à la convention Vx/X.

---

## 5b. Variante d'ancrage — StraitStrut + drag brace

> **Principe.** La **tige + roue (S₁)** et l'**axe de coulisse** (points R, Gt, Gb)
> sont **strictement identiques** au StraitStrut standard : tout le §3 (enfoncement,
> guidage Xt/Xb, friction, spin‑up) reste **inchangé**. Seul l'**ancrage du corps
> S₂ à la structure** change : l'**encastrement unique B** (qui transmettait effort
> **et** moment) est remplacé par un **montage isostatique à trois liaisons** :
>
> - **B1 — rotule** (sphérique) : transmet 3 efforts, **aucun moment** ;
> - **B2 — linéaire annulaire** d'axe (B1 B2) : transmet 2 efforts **⊥ à l'axe**,
>   **aucun moment**, **aucun effort axial** (glissement libre le long de B1 B2) ;
> - **drag brace** — **bielle à 2 rotules** entre **C** (lié au **corps**) et **D**
>   (lié à la **structure**) : c'est une **pièce à deux forces** → un **unique
>   effort selon l'axe (C D)**.
>
> B1 + B2 forment un **axe de trunnion** (B1 fixe un point ; B2 bloque les 2
> translations transverses) : il ne resterait qu'**un seul DDL**, la **rotation du
> corps autour de l'axe B1 B2**. La **drag brace** bloque ce dernier DDL. Le corps
> est donc **isostatiquement** maintenu.

### 5b.1 Coordonnées par défaut (repère avion, mm, à pitch 0°)

| Point | X | Y | Z | Rôle |
|---|---|---|---|---|
| B1 | 1650 | 70 | 1078 | rotule corps ↔ structure |
| B2 | 1650 | −70 | 1078 | linéaire annulaire (axe B1 B2) |
| C | 1620 | 0 | 700 | rotule **corps** ↔ drag brace |
| D | 1950 | 0 | 1120 | rotule drag brace ↔ **structure** |

Vecteurs unitaires : axe trunnion **û_B = (B1 − B2)/‖B1 − B2‖ = (0, 1, 0)** (selon
**Y**, latéral) ; axe de bielle **û_CD = (D − C)/‖D − C‖ = (330, 0, 420)/534,1 ≈
(0,618 ; 0 ; 0,786)** (dans le plan X‑Z, vers l'**arrière** et le **haut**). La
drag brace est donc une **contre‑fiche de traînée** : elle reprend les charges
**fore/aft** autour de l'axe latéral.

### 5b.2 Liaisons, inconnues et isostatisme

| Liaison | Nature | Inconnues d'effort |
|---|---|---|
| B1 (corps↔structure) | rotule | **R_B1 = (X₁, Y₁, Z₁)** → 3 |
| B2 (corps↔structure) | linéaire annulaire d'axe û_B | **R_B2 ⊥ û_B** (R_B2·û_B = 0) → 2 |
| drag brace (en C) | bielle à 2 rotules | **T** selon û_CD → 1 |

Total = **6 inconnues** = **6 équations** d'équilibre du corps (3 résultante + 3
moment, corps **sans masse** → membre de droite nul). Système **isostatique**.

### 5b.3 Isolement de la drag brace (pièce à deux forces)

Bielle sans masse, chargée **uniquement** par deux rotules (C, D) → effort porté
par la droite (C D). Sur le **corps** en C : **+T·û_CD** ; sur la **structure** en
D : **−T·û_CD** (T > 0 = traction de la bielle). Aucun moment transmis.

### 5b.4 Isolement du corps S₂ (masse négligée → équilibre)

L'action **interne** de la tige sur le corps (oléo **+F_tot·ẑ₁** en A ; réactions
de guidage **−Xt** en Gt, **−Xb** en Gb — identiques au §4.1, Xt/Xb issus du §3)
se réduit en un **torseur connu** (R_int, M_int) :

$$
\vec R_{int} = F_{tot}\,\hat z_1 - (X_t + X_b)\,\hat x_1,\qquad
\vec M_{int/B1} = \vec{B_1A}\times(F_{tot}\hat z_1) + \vec{B_1G_t}\times(-X_t\hat x_1) + \vec{B_1G_b}\times(-X_b\hat x_1)
$$

**Équilibre de la résultante (3 éq.) :**

$$
\boxed{\;\vec R_{int} + \vec R_{B1} + \vec R_{B2} + T\,\hat u_{CD} = \vec 0\;}\tag{4'}
$$

**Équilibre du moment en B1 (3 éq., R_B1 sans moment en B1) :**

$$
\boxed{\;\vec M_{int/B1} + \vec{B_1B_2}\times \vec R_{B2} + \vec{B_1C}\times (T\,\hat u_{CD}) = \vec 0\;}\tag{6'}
$$

### 5b.5 Résolution (structure du calcul)

La résolution se découple proprement grâce à la géométrie du trunnion :

1. **Drag brace T — projection du moment (6′) sur l'axe trunnion û_B.** Comme
   B₁B₂ ∥ û_B, le terme B₁B₂ × R_B2 est **⊥ û_B** (projection nulle), et R_B1 ne
   donne aucun moment en B1 :

   $$
   \boxed{\;T = -\,\frac{\vec M_{int/B1}\cdot \hat u_B}{\big(\vec{B_1C}\times \hat u_{CD}\big)\cdot \hat u_B}\;}
   $$

   → **la drag brace reprend exactement la composante du moment interne autour de
   l'axe trunnion** (moment de traînée/charge axiale). C'est sa fonction.

2. **Linéaire annulaire R_B2 — 2 composantes restantes de (6′)** (⊥ û_B), une fois
   T connu.
3. **Rotule R_B1 — résultante (4′)**, une fois R_B2 et T connus.

### 5b.6 Efforts transmis à la structure et cohérence

Les efforts **du train sur la structure** (entrant dans le PFD avion §7) sont les
**réactions** aux trois points :

- en **B1** : −R_B1 ; en **B2** : −R_B2 ; en **D** (drag brace) : −T·û_CD.

Leur **somme** vaut, par (4′), **−R_int = −F_tot·ẑ₁ + (Xt+Xb)·x̂₁**. La **résultante
globale transmise est donc identique** à celle du modèle encastré (§5.2 :
F_B,w = F_tot vertical, F_B,u = fu transverse) — **seule la répartition** sur trois
points (B1, B2, D) **et la suppression du moment d'encastrement** changent : le
moment M_B du §4.3 est désormais **repris par le couple {B1, B2, drag brace}**.

> **Conséquences pour l'implémentation (étape suivante).** (i) Le cœur S₁
> (enfoncement, Xt/Xb, friction, spin‑up, énergie) est **réutilisé tel quel** ;
> (ii) on ajoute la résolution **3D** du corps (4′)(6′) pour produire les efforts
> en B1, B2, D ; (iii) ces trois efforts remplacent l'unique torseur d'interface B
> dans le PFD avion. La cinématique d'enfoncement (axe de coulisse R/Gt/Gb) est
> **inchangée**.

### 5b.7 Hypothèses propres à la variante

- **H‑db1** : corps fixe **sans masse** (déjà au §4) → équilibre statique du corps.
- **H‑db2** : liaisons **parfaites** (rotule B1, linéaire annulaire B2, rotules de
  la bielle) → **sans frottement**, aucun moment parasite.
- **H‑db3** : **drag brace sans masse** ni flambage → pièce à deux forces exacte.
- **H‑db4** : montage **isostatique** (6 inconnues / 6 équations) → efforts
  déterminés sans hypothèse de raideur.

---

## 6. TrailingArm (MLG)

Même méthode, en **repère sol** (X arrière, Z haut). ⚠️ **Le torseur d'interface
se calcule en 3D** (efforts **et** moments) : la rotation du balancier reste plane
(autour de Y), mais les **décalages en Y** — roue déportée (R_y ≠ B_y),
amortisseur oblique (A‑C en Y) — produisent des composantes **Fy** et surtout des
**moments Mx, Mz** au pivot, qu'un calcul purement plan raterait.

### 6.1 Les solides isolés

| Solide | Description | Points | Masse |
|---|---|---|---|
| S′₁ | **Balancier** (bras) + essieu + **roue** | R, A, B | m′ (roue = masse non susp.) |
| S′₂ | **Amortisseur** (bielle oléo‑pneu/hydraulique) | A, C | **négligée** (bielle à 2 forces) |

### 6.2 Les liaisons

| Liaison | Nature | Transmet | Ne transmet pas |
|---|---|---|---|
| Balancier / cellule en B | **pivot** d'axe Y | effort (X,Z) + moments X,Z | **moment autour de Y** |
| Amortisseur / cellule en C | **rotule** | effort seul | tout moment |
| Amortisseur / balancier en A | **rotule** | effort seul | tout moment |
| roue / sol en R | **contact** | (Fx, Fz) | moment → rotation roue |

> L'amortisseur est **rotulé aux deux bouts** (A et C) et de masse négligée → c'est
> une **bielle à deux forces** : son effort est **porté par l'axe A‑C**, de norme
> F_tot (même modèle interne oléo/hydraulique qu'au §2, mais ici **sans bagues ni
> efforts transverses** puisque pivoté aux deux extrémités). On garde la même
> convention de contact (Fx, Fz) qu'au StraitStrut (§2.3).

### 6.3 Isolement de l'amortisseur (bielle à 2 forces)

Effort axial F_tot le long de A‑C (F_tot > 0 en compression : l'amortisseur
repousse ses extrémités) :

$$
\boxed{\;\vec T_A = F_{tot}\,\frac{A-C}{\lVert A-C\rVert}\;}\ (\text{sur le balancier en }A),
\qquad
\boxed{\;\vec F_C = -\vec T_A = F_{tot}\,\frac{C-A}{\lVert A-C\rVert}\;}\ (\text{sur la cellule en }C)
$$

> **Code** (`engine.py` l.329, 334) : `ta_x = -ftot*(C_x-A_x)/entraxe`
> (= F_tot·(A−C)_x/‖A−C‖) et `fc_x = -ta_x`. **Conforme.**

### 6.4 Isolement du balancier (R, A, B)

| Action | Point | Résultante (rep. sol) | Moment propre |
|---|---|---|---|
| Pesanteur | G′ | poids m′g = (0, 0, −m′g) | 0 |
| Contact sol → roue | R | T_R = (Fx, Fy, Fz) **(3D)** | 0 (le moment de spin part en rotation roue) |
| Amortisseur → balancier | A | T_A = F_tot·(A−C)/‖A−C‖ **(3D)** | 0 |
| Pivot cellule → balancier | B | T_B **(3D)** | **moments Mx, Mz** (pas de My) |

**Théorème de la résultante dynamique** :

$$
\boxed{\;\vec T_R + \vec T_A + \vec T_B + \vec P' = m'\,\vec a_{G'}\;}\tag{7}
$$

**Théorème du moment dynamique en B** (projeté sur Y ; le pivot ne reprend aucun
moment Y) :

$$
\boxed{\;(\vec{BR}\times \vec T_R)_Y + (\vec{BA}\times \vec T_A)_Y + (\vec{BG'}\times \vec P')_Y = J_B\,\ddot\theta\;}\tag{8}
$$

(8) est l'équation de **rotation du balancier** (DDL d'angle θ, accélération θ̈).

### 6.5 Efforts d'interface (pivot B et rotule C)

De (7) : T_B = m′·a_G′ − T_R − T_A − P′. L'effort transmis **à la cellule** au
pivot est son opposé (3ᵉ loi). **On conserve la masse du balancier+roue** (m′) :

$$
\boxed{\;\vec F_B = -\vec T_B = \vec T_R + \vec T_A + \vec P' - m'\,\vec a_{G'}\;},\qquad \boxed{\;\vec F_C = -\vec T_A\;}
$$

(F_C, issue de la bielle à 2 forces, est inchangée par la masse du balancier.)

> **Divergence avec le code** : `engine.py` pose `tb = -ta - tr` (l.330),
> `fb = -tb = ta + tr` (l.335), c.‑à‑d. **balancier sans masse** (P′ et m′·a_G′
> négligés). En tenant compte de la masse, il faut **ajouter P′ − m′·a_G′** (poids
> + inertie de translation du balancier+roue) à F_B. La rotation θ est, elle, déjà
> gardée via (8) ; `fc = -ta` (l.334) reste conforme.

**Moment transmis au pivot B (Mx, Mz) — calcul 3D.** Le pivot d'axe Y reprend
l'effort 3D **et** les moments autour de X et Z (pas autour de Y, axe libre). Le
moment des efforts du balancier réduit en B (d'Alembert : l'inertie −m′·a_G′ agit
en G′) est :

$$
\boxed{\;\vec M_B = \vec{BA}\times\vec T_A + \vec{BR}\times\vec T_R + \vec{BG'}\times(\vec P' - m'\,\vec a_{G'})\;}
$$

La composante **My n'est pas transmise** (elle équilibre la rotation, eq (8) :
J_yy·θ̈) ; le pivot ne réagit que **Mx et Mz**. En notant BA = A−B, BR = R−B :

$$
M_{B,x} = (BA_y\,T_{A,z} - BA_z\,T_{A,y}) + (BR_y\,T_{R,z} - BR_z\,T_{R,y}) + (\text{terme masse})_x
$$
$$
M_{B,z} = (BA_x\,T_{A,y} - BA_y\,T_{A,x}) + (BR_x\,T_{R,y} - BR_y\,T_{R,x}) + (\text{terme masse})_z
$$

> **Code** (`engine.py` l.342‑343) : `mb_x`, `mb_z` = (BA×T_A + BR×T_R)\_{x,z}
> (sans terme de masse). **Conforme** pour m′ = 0. C'est le **décalage R_y ≠ B_y**
> (roue déportée) qui rend Mx, Mz non nuls — d'où la **nécessité du calcul 3D**.

### 6.6 Lecture du résultat

- **Résultante transmise à la cellule** : F_B + F_C = (T_R + T_A + P′ − m′·a_G′)
  + (−T_A) = **T_R + P′ − m′·a_G′** : la réaction de contact **corrigée du poids et
  de l'inertie** du balancier+roue. (À masse négligée on retrouve exactement T_R —
  contrôle de cohérence du modèle simplifié, cf. modèle scientifique §9.2.)
- **Composante horizontale au pivot** : le poids étant vertical (P′_x = 0),
  F_B,x = **Fx + T_A,x − m′·a_G′,x** : contact horizontal **+** projection
  horizontale de l'amortisseur **−** inertie horizontale du balancier+roue.
- **Comparaison StraitStrut ↔ TrailingArm** : la **résultante horizontale** vaut,
  à la correction d'inertie près, **Fx** dans les deux cas (StraitStrut :
  fu − m₁·γ1u ; TrailingArm : Fx − m′·a_G′,x). Les deux trains transmettent donc
  **la même réaction de contact horizontale** ; seule la **répartition** diffère
  (StraitStrut : tout en B ; TrailingArm : réparti pivot B / rotule C, le terme
  d'amortisseur T_A,x au pivot étant compensé par F_C,x = −T_A,x à la rotule).
- **Moments 3D au pivot** : Mx, Mz sont non nuls dès qu'il existe un **décalage en
  Y** (roue déportée, amortisseur oblique). Sur le cas par défaut, R_y − B_y ≈
  −0,16 m donne **Mx ≈ −7000 N·m** et Mz ≈ −950 N·m : un calcul purement plan les
  **annulerait à tort**. → l'assemblage TrailingArm **doit** être 3D.
- **Signe** : comme au §5.4, tout repose sur le **signe de l'effort de contact
  Fx** (convention commune Vx/X). La cohérence NLG↔MLG se joue sur cette
  **définition unique de Fx**, pas sur la mécanique de transmission (identique en
  résultante). Or `tr_x = kx·δx + cx·(dδx/dt)` (code, l.229) est **de signe
  opposé à `fx_spring_wheel`** du StraitStrut (§1.3) → décalage à instruire.

### 6.7 Balancier corps rigide — masse active (modèle PFD complet)

> ⚠️ **Modèle nouveau.** Le modèle historique est **incohérent** : balancier sans
> masse en translation (fb = ta + tr) **mais** doté d'une inertie de rotation
> jyy ≠ 0. Le modèle ci‑dessous traite le balancier comme un **vrai corps
> rigide** (masse m′, centre d'inertie G′, inertie propre I_{G′}). Il **change la
> trajectoire** (la masse agit dans la dynamique).
>
> **Référence de validation.** En **réutilisant jyy comme inertie au pivot**
> (I_B = jyy fixe) et G′ = milieu(B, R), la limite **m′ → 0 redonne exactement
> l'historique** — y compris la rotation : avec m′ = 0, (6a) donne
> T_B = −(T_A+T_R) et (6b) se réduit à jyy·θ̈ = [(A−B)×T_A + (R−B)×T_R]_Y, soit
> l'équation de rotation du code (l.197‑202). On valide donc m′ = 0 contre
> l'historique, et m′ > 0 par **bilan d'énergie**.

**Paramétrage retenu** (un seul nouveau paramètre d'entrée) :
- **m′** : masse balancier + roue (nouveau, = `m_arm`) ;
- **G′ = milieu(B, R)** par défaut (pas de nouvel input) ;
- **I_B = jyy** (réutilisé), d'où I_{G′} = jyy − m′·‖BG′‖² (rester I_{G′} ≥ 0 ⇒
  m′ ≤ jyy/‖BG′‖²).

**Cinématique** (plan X–Z ; pivot B en translation verticale avec la cellule,
bras en rotation θ autour de B) :

$$
\vec a_{G'} = \vec a_B + \ddot\theta\,(\hat y \times \vec r_{BG'}) - \dot\theta^{2}\,\vec r_{BG'},
\qquad \vec r_{BG'} = G' - B
$$

**PFD du balancier (corps rigide).** Inconnues : réaction pivot $\vec T_B$ (2
comp.) et $\ddot\theta$ (1).

$$
\boxed{\;m'\,\vec a_{G'} = \vec T_A + \vec T_R + \vec T_B + \vec P'\;}\tag{6a}
$$
$$
\boxed{\;I_{G'}\,\ddot\theta = \big[(A-G')\times\vec T_A + (R-G')\times\vec T_R + (B-G')\times\vec T_B\big]_Y\;}\tag{6b}
$$

(6a)+(6b) = 3 équations scalaires → $\vec T_B$ et $\ddot\theta$. Effort transmis à
la cellule : $\vec F_B = -\vec T_B$ (pivot), $\vec F_C = -\vec T_A$ (rotule).

**Couplage structure.** $\vec F_B + \vec F_C$ pilotent la masse suspendue (train
isolé) ou le fuselage (avion, §7) ; $\ddot\theta$ remplace l'équation de rotation
historique (jyy). La **boucle d'intégration** avance θ, θ̇ **et** la cellule de
façon couplée.

**Différences clés avec §6.5** (modèle interface) : ici la rotation est pilotée
par I_{G′} (et non jyy), le poids m′g crée un moment, et l'inertie m′·a_{G′}
entre **dans la trajectoire** (pas seulement dans l'effort reporté).

---

## 7. Structure (fuselage) — PFD avion 2 DDL

Un seul solide : le **fuselage** (masse m, inertie de tangage J_yy, CG en G).
Repère sol, plan X‑Z. **2 degrés de liberté** : translation verticale z_cg et
**tangage θ** (rotation autour de Y en G). La translation longitudinale X est
**imposée** (Vx constante) → pas de DDL associé (les efforts X sont repris par la
contrainte de roulage, mais **contribuent au tangage**).

### 7.1 Les points d'interface (efforts issus des §4 et §6)

| Train | Liaison(s) | Point(s) | Effort transmis à la cellule |
|---|---|---|---|
| NLG (StraitStrut) | encastrement | B_N | F_B^N = (FxN, FzN) **+ moment M_B^N** |
| MLG gauche (TrailingArm) | pivot + rotule | B_L, C_L | F_B^L (pivot) + F_C^L (rotule), **pas de moment** |
| MLG droite (TrailingArm) | pivot + rotule | B_R, C_R | F_B^R (pivot) + F_C^R (rotule), **pas de moment** |

Le pivot ne transmet pas de moment de tangage (My) ; la rotule aucun moment ;
seul l'**encastrement NLG** transmet M_B^N.

### 7.2 Inventaire des torseurs sur le fuselage

| Action | Point | Résultante (rep. sol) | Moment propre |
|---|---|---|---|
| Poids allégé de la portance | G | (0, −m·g·(1−L)) | 0 |
| NLG → fuselage | B_N | (FxN, FzN) | M_B^N |
| MLG g. pivot → fuselage | B_L | (FxBL, FzBL) | 0 |
| MLG g. rotule → fuselage | C_L | (FxCL, FzCL) | 0 |
| MLG d. pivot → fuselage | B_R | (FxBR, FzBR) | 0 |
| MLG d. rotule → fuselage | C_R | (FxCR, FzCR) | 0 |

(L = coefficient de portance ∈ [0,1], supposée **constante** pendant la chute.)

### 7.3 Théorème de la résultante (vertical Z → z̈_cg)

$$
\boxed{\;m\,\ddot z_{cg} = \sum_i F_{z,i} - m\,g\,(1-L)\;}\tag{9}
$$

avec Σ_i F_z,i = FzN + FzBL + FzCL + FzBR + FzCR (= « Aircraft.Fz total »). La
résultante **horizontale (X) n'est pas un DDL** (Vx imposée).

### 7.4 Théorème du moment dynamique en G (tangage → θ̈)

Moment autour de Y en G. Pour chaque interface P_i = (x_i, z_i), effort
(Fx,i, Fz,i) et moment propre M_yi :

$$
\boxed{\;J_{yy}\,\ddot\theta = \sum_i\Big[(x_i-x_G)\,F_{z,i} - (z_i-z_G)\,F_{x,i}\Big] - M_B^{N}\;}\tag{10}
$$

(convention m_pitch = −M_y ; seul l'encastrement NLG apporte le moment propre
M_B^N ; pivots et rotules n'en apportent pas.)

> **Code** (`engine_aircraft.py` l.886‑892) : `mpitch += (px-cgx)*fz -
> (pz-cgz)*fx - my` puis `theta_ddot = mpitch / jyy`. **Conforme** : la somme
> porte sur **tous** les points d'interface (B du NLG ; B **et** C de chaque MLG),
> `my` n'étant non nul que pour l'encastrement NLG.

### 7.5 Lecture et intégration

- Les efforts horizontaux Fx,i **n'agissent que par le tangage** (terme
  −(z_i−z_G)·Fx,i) : c'est **le seul canal** par lequel le signe de `Fx@B`
  influence la dynamique avion (pas de DDL longitudinal).
- **Couplage** : (9) et (10) sont intégrées en parallèle (z_cg, θ) ; à chaque pas
  les positions et efforts des trois trains sont recalculés (cinématique rigide
  des stations + noyaux locaux NLG/MLG). Cf. modèle scientifique §15.
- **Cohérence des signes — point central** : pour que le tangage soit correct,
  **les trois trains doivent injecter Fx,i dans la même convention**. Or le NLG
  (`fx_spring_wheel`) et les MLG (`tr_x`) sont de **signes opposés** (§1.3, §6.6).
  C'est **ici** que l'incohérence se matérialise dans la dynamique avion → verdict
  à rendre en confrontation.

---

## 8. Hypothèses/simplifications à vérifier (synthèse pour la suite)

| # | Hypothèse du programme | Statut |
|---|---|---|
| H1 | Masse du corps fixe S₂ négligée (pas de G₂) ; inertie transverse de S₁ (m₁γ₁u) | S₂ : posé ; S₁ transverse à quantifier |
| H2 | Répartition des bagues par règle du levier (Xb, Xt) | ✅ retrouvée (§5.1) |
| H3 | F_B,w ≈ F_tot (vertical = effort amortisseur) | ✅ cohérent (§5.3) |
| H4 | F_B,u ≈ effort de contact horizontal | ✅ structure du bilan ; **signe à fixer** |
| H5 | DDL horizontal de la roue découplé (spring‑back) | à examiner (§5.4) |
| H6 | Liaison B = encastrement (transmet un moment M_B) | posé ; cohérent avec le modèle NLG |
| H7 | Roue/attache **coaxiales** (ξR = ξB = 0) pour les bagues et M_B | à vérifier — le modèle géométrique réel autorise des décalages (§2.4) |
| H8 | Amortisseur = **bielle à 2 forces** (F_tot porté par A‑C) | ✅ (rotulé aux deux bouts) |
| H9 | Portance **constante** (coefficient L) ; pas de DDL longitudinal (Vx imposée) | posé ; cohérent avec le modèle avion (§7) |

---

## 9. Confrontation finale (à faire)

Toutes les pièces sont maintenant posées (StraitStrut §2‑5, TrailingArm §6,
structure §7). Reste :

- **Verdict de signe sur `Fx@B`** : reprise des H1–H9 et de la convention Vx/X,
  pour trancher le décalage **`tr_x` (MLG) ↔ `fx_spring_wheel` (NLG)** de **signes
  opposés** (§1.3, §6.6) — qui se matérialise dans le **tangage avion** (§7.5).
- **Quantification des termes négligés/ajoutés** : masse du balancier (§6.5,
  désormais conservée vs code), inertie transverse de S₁, décalages ξR/ξB.
