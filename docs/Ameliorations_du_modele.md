# Pistes d'amélioration du modèle `dropsim`

> Audit du programme actuel, établi à partir du code, de l'interface, du
> stockage et des tests automatisés. Ce document ne reprend pas le contenu de
> `Idees.md` ; il se base uniquement sur l'état réel du dépôt.

---

## 1. État actuel observé

### 1.0 Addendum (2026-06-21)

Depuis la dernière mise à jour, les points suivants sont actés dans le dépôt :

- le modèle StraitStrut peut basculer en implicite/adaptatif quand nécessaire
  (stratégie `auto_fast` / `auto_precise`) ;
- le profil par défaut StraitStrut est aligné sur la référence projet
  **Strait Strut Reference** ;
- le golden StraitStrut est désormais calé sur cette référence projet ;
- la suite complète est verte (`62 passed`).

### 1.1 Mise à jour récente StraitStrut (NLG)

Depuis la dernière itération, la non-régression dédiée StraitStrut est alignée
sur la référence projet **Strait Strut Reference** via le golden
`tests/reference/golden_strait_strut_summary.json`.

Les comparaisons directes au CSV Excel `Results_NLG.csv` restent possibles pour
l'analyse historique ponctuelle, mais ne sont plus la baseline active du profil
par défaut StraitStrut.

Le projet dispose déjà de points solides :

- moteur physique structuré par sous-domaines (`gas.py`, `hydraulic.py`,
  `metering.py`, `tyre.py`, `geometry.py`, `engine.py`) ;
- interface Streamlit déjà riche (saisie, résultats, comparaison, loi
  hydraulique) ;
- validation de base en place (`tests/test_validation.py`,
  `tests/test_storage.py`) ;
- diagnostics utiles déjà présents : bilan énergétique, convergence
  hydraulique, torseur, animation, ratio cinématique.

En revanche, l'audit met aussi en évidence plusieurs zones à renforcer :

- la stratégie de référence doit rester explicitée (référence projet vs
  références historiques Excel) pour éviter des ambiguïtés de maintenance ;
- le schéma de stockage JSON est resté à `simuland/1` alors que la sémantique
  de plusieurs noms de colonnes a changé ;
- les libellés d'affichage, les clés internes, les références Excel et la
  documentation ont divergé à plusieurs endroits ;
- la page de saisie concentre encore beaucoup de paramètres physiques,
  numériques et de configuration, ce qui rend l'évolution plus fragile.

---

## 2. Priorités recommandées

### 2.1 Maintenir la non-régression complète — priorité critique

**Constat.** La suite complète est verte, mais il faut verrouiller ce statut
dans la durée.

- les golden files doivent rester régénérés de façon contrôlée ;
- les changements de libellés d'affichage doivent rester découplés des clés
  de test ;
- la politique de référence (profil projet) doit rester documentée.

**Amélioration proposée.**

- contrôler toute régénération de golden en revue ;
- conserver des tests focalisés sur des clés stables ;
- ajouter une cible simple de validation complète du dépôt avant chaque push.

**Impact.** Très fort. Sans cela, les futures évolutions resteront difficiles à
sécuriser.

---

### 2.2 Introduire un vrai versionnage de schéma pour les résultats et sauvegardes — priorité critique

**Constat.** Le fichier de sauvegarde reste en `simuland/1`, alors que des
changements incompatibles ont déjà eu lieu : renommage du modèle, suppression de
compatibilités historiques, renommage des clés internes et des libellés.

**Amélioration proposée.**

- passer à un schéma explicite `simuland/2` ;
- distinguer clairement :
  - les **clés machine stables** ;
  - les **libellés UI modifiables** ;
  - les **exports orientés utilisateur** ;
- prévoir une migration de lecture si l'on souhaite encore rouvrir d'anciens
  fichiers.

**Impact.** Très fort. C'est le point qui protège le projet contre les futures
ruptures silencieuses.

---

### 2.3 Découpler les identifiants internes des libellés affichés — priorité forte

**Constat.** Les colonnes résultats servent à la fois :

- d'identifiant logique (`OUTPUT_COLUMNS`) ;
- de libellé visible dans l'UI ;
- de nom exporté dans les CSV ;
- de référence dans les tests.

Le renommage de `MLG.*` vers `TrailingArm.*` a montré que ce couplage fragilise
à la fois les tests, les golden files et les exports.

**Amélioration proposée.**

- garder une clé interne purement stable, par exemple `trailing_arm_d` ;
- générer les libellés utilisateur dans une couche dédiée ;
- faire dépendre les tests des clés stables plutôt que des libellés visibles.

**Impact.** Fort. Réduit fortement le coût des renommages et de la maintenance.

---

### 2.4 Réorganiser la page de saisie — priorité forte

**Constat.** `app/pages/1_Saisie.py` concentre aujourd'hui :

- les entrées physiques ;
- les paramètres numériques ;
- les conversions ;
- des aides visuelles ;
- des migrations de session ;
- le déclenchement de calcul.

Le fichier est devenu dense et mélange logique métier et UI.

**Amélioration proposée.**

- séparer les réglages en sections ou pages :
  - paramètres physiques du train ;
  - paramètres gaz/huile ;
  - paramètres numériques/solveur ;
  - diagnostics avancés ;
- extraire les composants de formulaire réutilisables ;
- réduire la logique de migration dans la page elle-même.

**Impact.** Fort côté maintenabilité et robustesse UI.

---

### 2.5 Mettre en place une validation continue simple — priorité forte

**Constat.** Le dépôt possède des tests utiles, mais l'état réel montre qu'une
partie des régressions a pu passer jusqu'à casser la suite complète.

**Amélioration proposée.**

- ajouter un workflow CI minimal (`pytest`) ;
- distinguer un jeu de tests rapide et un jeu complet ;
- échouer explicitement si les fichiers de référence ne correspondent plus au
  format attendu.

**Impact.** Fort. Sécurise les itérations futures.

---

## 3. Améliorations techniques du moteur

### 3.1 Clarifier le contrat du solveur `auto_fast` / `auto_precise`

**Constat.** Le moteur mélange aujourd'hui plusieurs notions : intégrateur RK4,
chemin explicite historique, heuristique de sélection implicite/adaptative et
profil rapide/précis.

**Amélioration proposée.**

- documenter formellement la signification de chaque mode ;
- isoler la stratégie de sélection dans une couche testable indépendamment ;
- tracer les statistiques de bascule implicite dans les résultats de synthèse.

**Impact.** Moyen à fort. Rend le comportement du solveur plus explicable.

---

### 3.2 Structurer les sorties de diagnostic

**Constat.** Le moteur produit déjà beaucoup d'informations utiles
(convergence, énergie, torseur, fuite, géométrie), mais elles restent dispersées
dans de longues tables de colonnes.

**Amélioration proposée.**

- regrouper les diagnostics par familles ;
- distinguer dans le résultat final :
  - grandeurs physiques principales ;
  - diagnostics numériques ;
  - données d'animation ;
  - données de debug.

**Impact.** Moyen. Facilite l'exploitation du moteur et des exports.

---

### 3.3 Introduire une API de post-traitement dédiée

**Constat.** Une partie des métriques de synthèse et du formatage se trouve dans
`simulation.py`, ce qui mélange calcul, structuration et reporting.

**Amélioration proposée.**

- créer une couche de post-traitement dédiée ;
- centraliser les métriques, unités, labels et exports ;
- éviter que les tests dépendent directement du tableau brut quand ils veulent
  seulement vérifier une grandeur dérivée.

**Impact.** Moyen. Simplifie la maintenance de la page Résultats et des tests.

---

## 4. Améliorations de qualité logicielle

### 4.1 Mettre à jour la documentation de premier niveau

**Constat.** Le `README.md` décrit encore en partie l'ancien état du projet :

- vocabulaire MLG ;
- mention d'un moteur Euler explicite fidèle ;
- architecture partiellement datée.

**Amélioration proposée.**

- réaligner le README sur le modèle TrailingArm actuel ;
- documenter les pages existantes, les commandes utiles et la stratégie de
  validation ;
- préciser l'état du stockage et des fichiers de référence.

**Impact.** Moyen. Important pour l'onboarding et les reprises futures.

---

### 4.2 Réduire la dette des scripts `_extract`

**Constat.** Les scripts utilitaires historiques restent utiles, mais plusieurs
portent encore fortement la terminologie MLG/Excel et servent de facto de
boîte à outils non homogène.

**Amélioration proposée.**

- distinguer clairement les scripts encore maintenus ;
- renommer/normaliser ceux qui font partie du flux de validation ;
- documenter lesquels sont de simple exploration ponctuelle.

**Impact.** Moyen. Réduit la confusion autour du périmètre réellement supporté.

---

### 4.3 Ajouter des tests de cohérence UI / données exportées

**Constat.** Plusieurs régressions récentes touchent l'interface et les noms de
colonnes visibles, alors que les tests couvrent surtout le cœur physique.

**Amélioration proposée.**

- tester que les colonnes exportées attendues existent ;
- tester que les onglets sensibles (graphe personnalisé, ratio cinématique,
  convergence) restent compatibles avec les résultats générés ;
- verrouiller le nom du fichier exporté si souhaité.

**Impact.** Moyen. Très utile après les récents renommages.

---

## 5. Ordre recommandé de traitement

### Immédiat

1. Réparer `tests/test_regression.py` et le golden file.
2. Introduire un vrai schéma `simuland/2` pour les sauvegardes/résultats.
3. Découpler clés internes et libellés affichés.

### Court terme

1. Réorganiser la page Saisie.
2. Mettre en place une CI simple.
3. Mettre à jour le `README.md`.

### Moyen terme

1. Structurer l'API de post-traitement.
2. Reclasser les diagnostics et les exports.
3. Nettoyer/documenter les scripts `_extract`.

---

## 6. Recommandation principale

L'amélioration la plus importante à court terme n'est pas une nouvelle
fonction physique : c'est la **stabilisation du contrat logiciel** du moteur
et de ses résultats.

En pratique, la priorité numéro 1 est :

**remettre la suite complète de non-régression au vert et figer un schéma de
sortie/versionnement robuste.**

Sans cela, chaque évolution future du modèle continuera à coûter plus cher en
maintenance, en diagnostics et en risque de divergence entre code, tests,
exports et documentation.
