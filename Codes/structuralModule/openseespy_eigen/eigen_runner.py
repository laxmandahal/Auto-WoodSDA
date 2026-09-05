# -*- coding: utf-8 -*-
"""
Top-level orchestrator matching the call contract of
Codes/structuralModule/utils_opensees.py::generateModalAnalysisModel, but building
the model directly in-process via OpenSeesPy instead of writing .tcl files and
shelling out to an external OpenSees executable.

Does not touch utils_opensees.py or the BuildingModels/<ID>/EigenValueAnalysis/
directory the Tcl path owns -- this is an additive, standalone alternative.
"""

from model_builders import build_model
from gravity_analysis import perform_gravity_analysis
from eigen_analysis import run_eigen


def generateModalAnalysisModel_ops(ID, BuildingModel, NumModes=4):
    """Same contract as generateModalAnalysisModel(ID, BuildingModel, BaseDirectory,
    NumModes, GenerateModelSwitch=True): returns a list of `NumModes` periods.
    `BuildingModel` must already have had `read_in_txt_inputs()` called on it."""
    build_model(BuildingModel)
    perform_gravity_analysis(building_id=ID)
    periods = run_eigen(NumModes)
    return periods
