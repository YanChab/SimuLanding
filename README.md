# SimuLanding

Application de simulation de drop test (essai de chute) pour trains d'atterrissage,
remplaçant le fichier Excel `DROSIM_SA61-_#Simulation drop test avion complet.xlsm`.

Le projet couvre aujourd'hui deux modèles :
- **TrailingArm (MLG)** ;
- **StraitStrut (NLG)**.

Pour StraitStrut, le profil par défaut est aligné sur la simulation de
référence projet **Strait Strut Reference**.

## Architecture

```
dropsim/      Moteur de calcul Python pur (NumPy), indépendant de l'UI.
              Reproduit fidèlement la méthodologie décrite dans EtatDesLieux.md.
  units.py        Conversions d'unités (affichage <-> SI)
  errors.py       Système de détection/localisation d'erreurs (SimError)
  inputs.py       Modèle de données d'entrée + valeurs par défaut + validation
  metering.py     Loi de section variable de la bague hydraulique (rainures)
  gas.py          Ressort gazeux double chambre (Newton-Raphson)
  hydraulic.py    Pertes de charge hydrauliques (Cd, ΔP)
  tyre.py         Modèle de pneu (déflexion, μ, spin-up, spring-back)
  engine.py       Boucle d'intégration temporelle TrailingArm
  engine_strait_strut.py  Boucle d'intégration temporelle StraitStrut
  simulation.py   Point d'entrée haut niveau (run_simulation)

app/          Interface Streamlit
  streamlit_app.py        Page d'accueil
  theme.py                Thème et styles partagés de l'UI
  components/gear_form.py Formulaire de saisie d'un train (composant réutilisable)
  pages/3_Comparaison.py            Comparaison de trains
  pages/4_Loi_hydraulique.py        Loi hydraulique (NLG/MLG)
  pages/5_Avion_complet.py          Saisie de l'avion complet
  pages/6_Resultats_avion_complet.py Résultats de l'avion complet

tests/        Tests de non-régression (goldens projet)
_extract/     Données extraites historiques (VBA et exports Excel)
```

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Lancement

```powershell
streamlit run app/streamlit_app.py
```

## Tests de validation

```powershell
# Suite complète (pré-commit / CI locale)
pytest -q

# Mode rapide local (exclut les tests les plus coûteux)
pytest -q -m "not slow" -n auto

# Suite complète parallélisée
pytest -q -n auto

# Profil des tests lents (diagnostic perf)
pytest -q --durations=15
```

Les tests coûteux sont marqués `slow` (intégrateur + régressions lourdes),
ce qui permet de garder une boucle de développement rapide sans perdre la
couverture complète avant livraison. La non-régression StraitStrut est
basée sur la référence projet (`tests/reference/golden_strait_strut_summary.json`).
