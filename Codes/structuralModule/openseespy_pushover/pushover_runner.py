# -*- coding: utf-8 -*-
"""
Top-level orchestrator matching the call contract of
Codes/structuralModule/utils_opensees.py::generatePushoverAnalysisModel, but
building and running the model directly in-process via OpenSeesPy instead of
writing .tcl files and shelling out to an external OpenSees executable.

Reuses model_builders.build_model from the sibling openseespy_eigen package
(model definition -- nodes, panels, leaning column, masses, gravity loads -- is
identical between Eigen and Pushover; only the loading + analysis differ) rather
than duplicating it. Does not touch utils_opensees.py or the BuildingModels/<ID>/
PushoverAnalysis/ directory the Tcl path owns.
"""

from model_builders import build_model
from gravity_analysis import perform_gravity_analysis
from pushover_loading import define_pushover_loading
from pushover_analysis import run_static_pushover


def generatePushoverAnalysisModel_ops(ID, BuildingModel, direction):
    """direction: 'X' or 'Z'. `BuildingModel` must already have had
    read_in_txt_inputs() called on it. Returns the run_static_pushover() result
    dict (roof_drift_pct, base_shear, control_disp, ok)."""
    build_model(BuildingModel)
    perform_gravity_analysis(building_id=ID)
    define_pushover_loading(BuildingModel, direction)
    return run_static_pushover(BuildingModel, direction)
