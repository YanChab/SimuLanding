"""Moteur de simulation de drop test pour trains d'atterrissage.

Le moteur est volontairement séparé de toute interface utilisateur : il ne
dépend que de NumPy et reproduit la méthodologie décrite dans EtatDesLieux.md.
"""
from .errors import SimError, ErrorCollector, ErrorLevel
from .inputs import (
    AircraftBodyInputs,
    AircraftDropConfig,
    AircraftGearLayoutInputs,
    AircraftInputs,
    AircraftSimulationInputs,
    TrailingArmInputs,
    TrailingArmDragBraceInputs,
    StraitStrutInputs,
    StraitStrutDragBraceInputs,
    default_aircraft_inputs,
    default_trailing_arm_inputs,
    default_trailing_arm_drag_brace_inputs,
    default_strait_strut_inputs,
    default_strait_strut_drag_brace_inputs,
    compute_gas_oil_at_temperature,
    TEMP_REF_C,
)
from .simulation import run_simulation, run_pfd_simulation, SimulationResult
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
    "AircraftBodyInputs",
    "AircraftDropConfig",
    "AircraftGearLayoutInputs",
    "AircraftInputs",
    "AircraftSimulationInputs",
    "TrailingArmInputs",
    "TrailingArmDragBraceInputs",
    "StraitStrutInputs",
    "StraitStrutDragBraceInputs",
    "default_aircraft_inputs",
    "default_trailing_arm_inputs",
    "default_trailing_arm_drag_brace_inputs",
    "default_strait_strut_inputs",
    "default_strait_strut_drag_brace_inputs",
    "compute_gas_oil_at_temperature",
    "TEMP_REF_C",
    "run_simulation",
    "run_pfd_simulation",
    "SimulationResult",
    "save_simulation",
    "load_simulation",
    "list_saved",
    "list_projects",
    "delete_saved",
    "DEFAULT_SAVE_DIR",
    "DEFAULT_PROJECT",
]
