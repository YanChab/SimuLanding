"""Moteur de simulation de drop test pour trains d'atterrissage.

Le moteur est volontairement séparé de toute interface utilisateur : il ne
dépend que de NumPy et reproduit la méthodologie décrite dans EtatDesLieux.md.
"""
from .errors import SimError, ErrorCollector, ErrorLevel
from .inputs import (
    TrailingArmInputs,
    StraitStrutInputs,
    default_trailing_arm_inputs,
    default_strait_strut_inputs,
    compute_gas_oil_at_temperature,
    TEMP_REF_C,
)
from .simulation import run_simulation, SimulationResult
from .storage import (
    save_simulation,
    load_simulation,
    list_saved,
    list_projects,
    delete_saved,
    DEFAULT_SAVE_DIR,
    DEFAULT_PROJECT,
)

__all__ = [
    "SimError",
    "ErrorCollector",
    "ErrorLevel",
    "TrailingArmInputs",
    "StraitStrutInputs",
    "default_trailing_arm_inputs",
    "default_strait_strut_inputs",
    "compute_gas_oil_at_temperature",
    "TEMP_REF_C",
    "run_simulation",
    "SimulationResult",
    "save_simulation",
    "load_simulation",
    "list_saved",
    "list_projects",
    "delete_saved",
    "DEFAULT_SAVE_DIR",
    "DEFAULT_PROJECT",
]
