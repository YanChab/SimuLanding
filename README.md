# SimuLanding

Application de simulation de drop test (essai de chute) pour trains d'atterrissage,
remplaçant le fichier Excel `DROSIM_SA61-_#Simulation drop test avion complet.xlsm`.

Phase 1 : train d'atterrissage **principal à balancier (MLG)**.

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
  engine.py       Boucle d'intégration temporelle (Euler explicite fidèle)
  simulation.py   Point d'entrée haut niveau (run_simulation)

app/          Interface Streamlit
  streamlit_app.py        Page d'accueil
  pages/1_Saisie.py       Saisie des données du train
  pages/2_Resultats.py    Courbes de résultats

tests/        Tests de validation vs la référence Excel
_extract/     Données extraites de l'Excel (VBA, référence Results_MLG.csv)
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
pytest tests/
```
