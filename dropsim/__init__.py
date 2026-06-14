"""Moteur de simulation de drop test pour trains d'atterrissage.

Le moteur est volontairement séparé de toute interface utilisateur : il ne
dépend que de NumPy et reproduit la méthodologie décrite dans EtatDesLieux.md.
"""
from .errors import SimError, ErrorCollector, ErrorLevel
from .inputs import MLGInputs, default_mlg_inputs
from .simulation import run_simulation, SimulationResult

__all__ = [
    "SimError",
    "ErrorCollector",
    "ErrorLevel",
    "MLGInputs",
    "default_mlg_inputs",
    "run_simulation",
    "SimulationResult",
]
