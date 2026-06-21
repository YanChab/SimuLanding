# Implantation simulation avion complet

## 1. Objet du document

Ce document fige le cadrage fonctionnel et technique de la V1 du mode **avion complet** dans SimuLanding.

Il rassemble :
- les questions de conception posées en amont ;
- les réponses retenues ;
- le design technique concret proposé pour l'implémentation ;
- l'ordre de réalisation recommandé.

---

## 2. Questions de cadrage et réponses retenues

### 2.1 Périmètre V1

**Question**
Quel périmètre dynamique doit être implémenté en premier ?

**Réponse retenue**
V1 en **2 DDL** :
- translation verticale globale de l'avion ;
- rotation en tangage autour du centre de gravité.

Pas de roulis en V1.

### 2.2 Architecture trains

**Question**
Quelle configuration train doit être supportée en premier ?

**Réponse retenue**
Configuration V1 figée :
- **1 NLG** de type StraitStrut ;
- **2 MLG** symétriques de type TrailingArm.

Les deux MLG sont supposés identiques en paramètres et symétriques dans le repère avion.

### 2.3 Référence vérité / golden

**Question**
Sur quelle vérité de référence doit-on s'appuyer pour la non-régression avion complet ?

**Réponse retenue**
Ne **pas** utiliser les résultats du fichier Excel, jugés faux pour ce périmètre.

La stratégie retenue est la suivante :
- on implémente d'abord le modèle avion complet ;
- on valide ensemble la cohérence physique et métier des résultats ;
- une fois les résultats jugés cohérents, on utilise une **simulation sauvegardée** comme **référence projet** pour définir le golden avion complet.

### 2.4 Couplage temporel

**Question**
Quel schéma temporel utiliser pour le premier couplage avion + trains ?

**Réponse retenue**
V1 avec **pas de temps global unique** pour tout le système :
- avion ;
- NLG ;
- MLG gauche ;
- MLG droit.

Pas de sous-pas locaux en V1.

### 2.5 Niveau de fidélité V1

**Question**
Quels phénomènes physiques inclure dès la première version ?

**Réponse retenue**
V1 limitée à :
- dynamique verticale ;
- tangage ;
- interaction avec les trois trains.

Évolutions gardées pour plus tard :
- évolution temporelle du lift ;
- freinage / efforts longitudinaux ;
- enrichissements dynamiques supplémentaires.

### 2.6 UI - page de saisie

**Question**
Comment structurer la page de saisie avion complet ?

**Réponse retenue**
Une page de saisie dédiée incluant les sections suivantes :
- Paramètres avion ;
- Paramètres simulation ;
- Configuration de chute ;
- Géométrie NLG et MLG dans le repère avion ;
- Paramètres NLG ;
- Paramètres MLG.

### 2.7 UI - persistance d'affichage entre pages

**Question**
Quel comportement souhaite-t-on lors du changement de page dans l'application ?

**Réponse retenue**
Le changement de page ne doit **pas** réinitialiser :
- les données saisies ;
- le résultat courant ;
- l'état d'affichage déjà configuré sur une page.

L'objectif est de retrouver la page dans l'état où elle était avant navigation.

### 2.8 Sorties prioritaires

**Question**
Quelles sorties doivent être présentes dans la page Résultats ?

**Réponse retenue**
Trois sections principales :

1. **Avion complet**
- animation de la chute ;
- grandeurs dynamiques au centre de gravité ;
- déplacement, vitesse, accélération ;
- angle, vitesse angulaire, accélération angulaire en rotation.

2. **Section MLG**
- toutes les courbes et données actuellement disponibles sur les résultats TrailingArm.

3. **Section NLG**
- toutes les courbes et données actuellement disponibles sur les résultats StraitStrut.

---

## 3. Vision fonctionnelle V1

La V1 du mode avion complet doit permettre de simuler un fuselage rigide reposant sur :
- un train avant NLG de type StraitStrut ;
- deux trains principaux MLG de type TrailingArm.

Le modèle avion complet doit :
- lire une configuration avion complète ;
- calculer la cinématique globale du centre de gravité ;
- projeter cette cinématique sur chaque train ;
- exécuter le calcul local de chaque train à chaque pas ;
- remonter les efforts de contact et efforts transmis ;
- résoudre la dynamique globale verticale + pitch ;
- exposer des résultats globaux et détaillés par train.

---

## 4. Design technique concret proposé

## 4.1 Principe général de l'architecture

L'implémentation doit reposer sur trois niveaux bien séparés :

1. **Entrées avion complet**
- une structure de données dédiée ;
- indépendante des entrées train isolées actuelles ;
- capable de référencer un sous-ensemble NLG et un sous-ensemble MLG.

2. **Moteur avion complet**
- orchestre la dynamique du fuselage ;
- appelle les noyaux train déjà existants sous forme de calcul local par pas ;
- agrège les efforts et moments globaux.

3. **Post-traitement / UI**
- présente les résultats avion complet ;
- réutilise autant que possible les sorties existantes NLG / MLG ;
- garde l'état d'affichage en session.

---

## 4.2 Nouvelles structures de données

### 4.2.1 `AircraftInputs`

Créer dans `dropsim/inputs.py` une nouvelle dataclass du type :
- `AircraftInputs`

Contenu recommandé :

**A. Paramètres avion**
- masse avion ou masse supportée globale ;
- position du centre de gravité dans le repère avion ;
- inertie en tangage `jyy_aircraft` ;
- lift global initial ;
- éventuellement nombre de trains, mais en V1 ce sera figé implicitement à 1 NLG + 2 MLG.

**B. Paramètres simulation**
- durée simulée ;
- pas de temps ;
- intégrateur ;
- options solveur implicite/explicite si nécessaires au niveau train.

**C. Configuration de chute**
- vitesse verticale initiale ;
- vitesse horizontale initiale si conservée pour usage futur ;
- assiette initiale ;
- vitesse angulaire initiale en tangage si utile ;
- hauteur / condition initiale de contact si nécessaire.

**D. Géométrie NLG / MLG dans le repère avion**
- position du point de contact ou de la roue NLG dans le repère avion ;
- position MLG gauche ;
- position MLG droit ;
- points géométriques MLG nécessaires (A/B/C/R/S ou équivalent) ;
- géométrie spécifique StraitStrut (pivot, guides, angle de jambe).

**E. Paramètres NLG**
- bloc reprenant les paramètres du `StraitStrutInputs` isolé.

**F. Paramètres MLG**
- bloc reprenant les paramètres du `TrailingArmInputs` isolé.

### 4.2.2 Sous-objets recommandés

Pour éviter une dataclass géante illisible, il est recommandé d'introduire :
- `AircraftBodyInputs`
- `AircraftSimulationInputs`
- `AircraftDropConfig`
- `AircraftGearLayoutInputs`
- `AircraftNLGConfig`
- `AircraftMLGConfig`

Puis `AircraftInputs` agrège ces blocs.

---

## 4.3 Moteur physique avion complet

### 4.3.1 Nouveau module

Créer un nouveau module, par exemple :
- `dropsim/engine_aircraft.py`

Il contiendra :
- la boucle temporelle avion complet ;
- les sorties globales ;
- les sorties détaillées par train ;
- les données géométriques nécessaires à l'animation.

### 4.3.2 Modèle dynamique global

Le fuselage est un corps rigide 2 DDL :
- `z_cg` : déplacement vertical du centre de gravité ;
- `theta_pitch` : rotation autour de l'axe Y au CG.

Les équations globales à résoudre à chaque pas sont de la forme :

- somme des forces verticales = masse × accélération verticale ;
- somme des moments autour du CG = inertie × accélération angulaire.

Contributions attendues :
- NLG ;
- MLG gauche ;
- MLG droit ;
- poids effectif ;
- lift global si conservé constant en V1.

### 4.3.3 Cinématique locale des trains

À chaque pas global :

1. on connaît l'état avion :
- `z_cg`, `vz_cg`, `az_cg` ;
- `theta`, `omega`, `alpha`.

2. on en déduit pour chaque train :
- déplacement vertical local du point d'attache / de référence ;
- vitesse verticale locale ;
- éventuellement l'effet de la rotation sur la vitesse verticale locale.

3. ces grandeurs alimentent le calcul local de chaque train.

### 4.3.4 Réutilisation des moteurs train existants

Les moteurs actuels `engine.py` et `engine_strait_strut.py` sont orientés “simulation complète isolée”.

Pour l'avion complet, il faut extraire ou créer un **noyau de pas local par train**.

Concrètement, il est recommandé d'introduire une API de type :
- `trailing_arm_step(...)`
- `strait_strut_step(...)`

Ces fonctions doivent :
- recevoir l'état local du train au début du pas ;
- recevoir la cinématique imposée par la structure ;
- calculer l'état local au pas suivant ;
- retourner les efforts transmis au fuselage et les grandeurs de sortie.

### 4.3.5 Gestion de la symétrie des MLG

En V1, les deux MLG sont symétriques et identiques.

Deux options existent :

1. **Deux états indépendants**
- plus robuste pour la suite ;
- permet plus tard d'introduire des dissymétries.

2. **Un seul état dupliqué**
- plus simple mais moins extensible.

Recommandation :
- implémenter **deux états indépendants**, même si les paramètres sont les mêmes.

---

## 4.4 Résultats et format de sortie

### 4.4.1 Nouveau résultat haut niveau

Dans `dropsim/simulation.py`, étendre `SimulationResult` ou créer une structure dédiée pour inclure :
- un tableau global avion ;
- un tableau NLG ;
- un tableau MLG gauche ;
- un tableau MLG droit ;
- une synthèse avion complet ;
- des géométries d'animation.

### 4.4.2 Colonnes globales avion complet

Prévoir au minimum :
- temps ;
- `Aircraft.CG.z` ;
- `Aircraft.CG.vz` ;
- `Aircraft.CG.az` ;
- `Aircraft.pitch` ;
- `Aircraft.pitch_rate` ;
- `Aircraft.pitch_acc` ;
- somme Fz sol ;
- Fz NLG ;
- Fz MLG gauche ;
- Fz MLG droit ;
- moments globaux autour du CG.

### 4.4.3 Sorties détaillées train

Pour chaque section MLG / NLG, il faut réexposer les séries déjà disponibles aujourd'hui :
- course ;
- vitesse ;
- effort total ;
- effort pneu ;
- pressions ;
- convergence hydraulique ;
- énergies ;
- torseurs ;
- toute autre courbe déjà affichée dans les pages actuelles.

---

## 4.5 Interface utilisateur

### 4.5.1 Nouvelle page de saisie

Créer une page dédiée, par exemple :
- `app/pages/5_Avion_complet.py`

Sections attendues :
- Paramètres avion ;
- Paramètres simulation ;
- Configuration de chute ;
- Géométrie NLG et MLG dans le repère avion ;
- Paramètres NLG ;
- Paramètres MLG.

### 4.5.2 Conservation de l'état entre pages

Exigence explicite : ne pas perdre l'affichage en changeant de page.

Implémentation recommandée via `st.session_state` :
- stocker séparément les entrées avion complet ;
- stocker le résultat avion complet ;
- stocker les choix d'onglets, graphes, filtres, sélections utilisateur ;
- éviter toute réinitialisation automatique lors de la navigation ;
- ne recréer les defaults qu'en absence totale d'état.

Clés recommandées :
- `aircraft_inputs`
- `aircraft_result`
- `aircraft_result_name`
- `aircraft_ui_state`

### 4.5.3 Page résultats avion complet

Créer une page dédiée ou étendre la page existante pour ajouter trois sections :

1. **Avion complet**
- animation de la chute ;
- dynamique CG ;
- dynamique en tangage.

2. **MLG**
- même richesse que les résultats TrailingArm actuels.

3. **NLG**
- même richesse que les résultats StraitStrut actuels.

Recommandation :
- utiliser des sous-onglets ou des accordéons pour conserver une interface lisible.

---

## 4.6 Sauvegarde et golden futur

### 4.6.1 Sauvegarde

Étendre `dropsim/storage.py` pour supporter :
- sérialisation des entrées avion complet ;
- sérialisation des résultats avion complet ;
- compatibilité avec le système projet/sauvegarde existant.

### 4.6.2 Golden futur

Quand les résultats seront validés métier :
- sauvegarder un cas de référence avion complet ;
- définir un golden avion complet dédié ;
- créer un fichier de test du type `tests/test_aircraft_regression.py`.

Le golden devra être bâti uniquement à partir d'une **référence projet validée**, jamais directement à partir du classeur Excel.

---

## 4.7 Stratégie d'implémentation en lots

### Lot 1 — Modèle de données
- créer les dataclasses avion complet ;
- validation ;
- conversion SI ;
- defaults initiaux.

### Lot 2 — Noyaux de pas locaux trains
- isoler/refactorer la logique step NLG ;
- isoler/refactorer la logique step MLG ;
- garantir qu'ils restent compatibles avec les moteurs isolés existants.

### Lot 3 — Boucle avion complet
- créer `engine_aircraft.py` ;
- implémenter le couplage global 2 DDL ;
- produire les séries globales + locales.

### Lot 4 — UI saisie
- nouvelle page de saisie avion complet ;
- persistance de l'état d'affichage.

### Lot 5 — UI résultats
- animation avion complet ;
- section globale ;
- sections MLG et NLG.

### Lot 6 — Sauvegarde
- support complet dans `storage.py`.

### Lot 7 — Validation métier puis golden
- revue des résultats ;
- choix d'une simulation sauvegardée comme référence ;
- création des tests de non-régression avion complet.

---

## 5. Hypothèses V1 explicites

Pour éviter tout glissement de périmètre, la V1 repose sur les hypothèses suivantes :
- 2 DDL uniquement ;
- 1 NLG + 2 MLG ;
- pas global unique ;
- lift constant si utilisé ;
- pas de freinage ;
- pas de roulis ;
- pas de vérité Excel imposée ;
- golden différé jusqu'à validation métier.

---

## 6. Risques techniques identifiés

1. **Réutilisation des moteurs existants**
Les moteurs train actuels sont conçus comme simulateurs complets isolés. Il faudra extraire proprement un noyau “pas local” sans casser la non-régression existante.

2. **Conventions de repère et de signe**
Le passage repère avion / repère train / repère sol devra être verrouillé très tôt par des tests simples.

3. **Structure des résultats**
Le volume de séries va fortement augmenter. Il faudra distinguer clairement :
- sorties globales avion ;
- sorties NLG ;
- sorties MLG gauche ;
- sorties MLG droit.

4. **Animation**
L'animation avion complet demandera des géométries cohérentes entre le corps rigide et les trois trains. Il faut la concevoir dès le format de sortie, même si la première version visuelle reste simple.

---

## 7. Recommandation de démarrage

Le meilleur point de départ est :

1. créer les dataclasses `AircraftInputs` et sous-blocs ;
2. écrire la validation + conversion SI ;
3. extraire le noyau de pas local StraitStrut ;
4. extraire le noyau de pas local TrailingArm ;
5. brancher ensuite la boucle avion complet.

C'est l'ordre le plus propre pour éviter de mêler UI, persistance et physique trop tôt.

---

## 8. Critère de succès V1

La V1 sera considérée réussie lorsque :
- une simulation avion complet peut être saisie, exécutée, sauvegardée et relue ;
- les trois sections de résultat (avion, MLG, NLG) sont exploitables ;
- l'état d'affichage est conservé entre les pages ;
- les résultats sont jugés cohérents métier ;
- une référence projet peut ensuite être figée pour servir de golden avion complet.
