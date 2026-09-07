# -*- coding: utf-8 -*-
"""
Top-level orchestrator matching the call contract of
Codes/structuralModule/utils_opensees.py::generateDynamicAnalysisModel, but
building and running the model directly in-process via OpenSeesPy instead of
writing .tcl files and shelling out to an external OpenSees executable.

Reuses model_builders.build_model, gravity_analysis.perform_gravity_analysis, and
eigen_analysis.run_eigen from the sibling openseespy_eigen package -- model
definition and the periods needed for Rayleigh damping are identical to Eigen/
Pushover. Does not touch utils_opensees.py or the BuildingModels/<ID>/
DynamicAnalysis/ directory the Tcl path owns.
"""

import numpy as np

from model_builders import build_model
from gravity_analysis import perform_gravity_analysis
from eigen_analysis import run_eigen

from damping import define_damping
from ground_motion import resolve_gm, define_ground_motion_loading, GM_SCALE_G
from collapse_solver import run_dynamic_analysis, DRIFT_LIMIT_DEFAULT


def _load_ground_accel(file_path, scale_factor):
    """Raw single-column acceleration record (g), scaled to in/s^2 -- same file
    and scale factor used for ops.timeSeries('Path', ...), loaded again here in
    Python so absolute floor acceleration can be reconstructed (see
    collapse_solver._ground_accel_at's docstring)."""
    return np.loadtxt(file_path) * scale_factor


def generateDynamicAnalysisModel_ops(ID, bm, gm_set_dir, hazard_level, gm_index, pairing,
                                      num_modes=4, drift_limit=DRIFT_LIMIT_DEFAULT,
                                      max_run_time=3600):
    """Same unit of work as one RunNRHAXx.tcl/RunNRHAZz.tcl invocation: one
    archetype, one ground-motion pair, one pairing direction. `BuildingModel` must
    already have had `read_in_txt_inputs()` called on it.

    Returns the run_dynamic_analysis() result dict, plus the resolved GM info and
    modal periods used for damping (for reporting/verification)."""
    build_model(bm)
    perform_gravity_analysis(building_id=ID)

    periods = run_eigen(num_modes)
    damping_info = define_damping(bm, periods)

    gm = resolve_gm(gm_set_dir, hazard_level, gm_index)
    define_ground_motion_loading(bm, gm['gm_x_file'], gm['gm_z_file'], gm['dt'],
                                  gm['scale_factor'], pairing)

    # scale_factor already includes GM_SCALE_G (see ground_motion.resolve_gm) --
    # reuse it directly so the Python-side ground-acceleration arrays used for
    # absolute-acceleration reconstruction match what ops.timeSeries saw exactly.
    # `pairing` decides which FILE drives which DOF (see
    # define_ground_motion_loading's docstring) -- ground_accel_x/z here must
    # follow the same swap, not just the file's own X/Z label.
    accel_from_x_file = _load_ground_accel(gm['gm_x_file'], gm['scale_factor'])
    accel_from_z_file = _load_ground_accel(gm['gm_z_file'], gm['scale_factor'])
    if pairing == 1:
        ground_accel_x, ground_accel_z = accel_from_x_file, accel_from_z_file
    else:
        ground_accel_x, ground_accel_z = accel_from_z_file, accel_from_x_file

    result = run_dynamic_analysis(
        bm, gm['dt'], gm['gm_time'], drift_limit=drift_limit, max_run_time=max_run_time,
        ground_accel_x=ground_accel_x, ground_accel_z=ground_accel_z,
    )
    result['ground_motion'] = gm
    result['modal_periods'] = periods
    result['damping'] = damping_info
    return result
