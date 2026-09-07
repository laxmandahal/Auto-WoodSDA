# -*- coding: utf-8 -*-
"""
Ground-motion selection and loading, porting BuildingModels/RunDynamic.tcl (the
actual master driver template -- BuildingModels/GM_sets/<Name>/<level>/ layout;
`Codes/structuralModule/RunNRHAXx.tcl`/`RunNRHAZz.tcl` are the same logic wired to
$SGE_TASK_ID for HPC array jobs) plus DefineBiDirectionalTimeHistory.tcl's
timeSeries/pattern setup (BuildingInfo/*/BaselineTclFiles/OpenSees3DModels/
DynamicAnalysis/).

GroundMotionInfo/*.txt convention (confirmed against BuildingModels/GM_sets/
BoelterHall/1/): GMFileNames.txt, GMNumPoints.txt, GMTimeSteps.txt hold one line
PER COMPONENT (H1/H2), 2*NumGM lines total for NumGM pairs -- pair `p`'s X/H1
component is at 0-based line `2*p`, Z/H2 at `2*p+1` (this is what
RunDynamic.tcl's `groundMotionXIDs`/`groundMotionZIDs` -- odd/even 1-based lists --
and `GM_XNumber-1`/`GM_ZNumber-1` indexing resolve to). BiDirectionMCEScaleFactors.txt
holds one line PER PAIR (`MCEScaleFactors[GMIDs]`, GMIDs = 0-based pair index directly,
no *2) -- the committed BoelterHall/1 sample happens to have 2*NumGM duplicated lines
instead of NumGM unique ones (confirmed with the repo owner: that data file is stale,
not a code bug), so reading it pair-indexed against that particular file just picks up
a duplicate/mismatched-but-still-physically-valid value -- fine for the smoke test,
not a translation issue.

No Python-side source of truth for "how many ground motions / which hazard levels"
exists in the current Tcl pipeline (GMset_Num is hardcoded independently in
RunNRHAXx.tcl/RunNRHAZz.tcl and again in Codes/damageModule/ProcessMSAResults.py) --
this module derives it from the GM_sets/<Name>/ folder structure instead.
"""

import os

import numpy as np
import openseespy.opensees as ops

# Ground-motion history values are acceleration in g; DefineUnitsAndConstants.tcl's
# `set g [expr 32.174 * $ft/($sec*$sec)]` (ft=12, sec=1) = 386.088 in/s^2 is what
# scales them. NOT the same constant as openseespy_eigen/model_builders.py's
# GRAVITY_G (386.4, 32.2*12) -- that one is a separate literal baked into the mass
# calculation only; this is the actual Tcl `$g` variable used for scaling.
GM_SCALE_G = 32.174 * 12.0


def list_hazard_levels(gm_set_dir):
    """Hazard-level subfolder names (e.g. '1', '2', ...), sorted numerically.
    Each holds GroundMotionInfo/ + histories/ -- see module docstring."""
    levels = [d for d in os.listdir(gm_set_dir)
              if os.path.isdir(os.path.join(gm_set_dir, d)) and d.isdigit()]
    return sorted(levels, key=int)


def num_gm_pairs(gm_set_dir, hazard_level):
    """Number of GM pairs in a hazard level, from GMFileNames.txt's line count / 2
    -- replaces the hardcoded GMset_Num literal in RunNRHAXx.tcl/RunNRHAZz.tcl."""
    info_dir = os.path.join(gm_set_dir, str(hazard_level), 'GroundMotionInfo')
    with open(os.path.join(info_dir, 'GMFileNames.txt')) as f:
        n_lines = sum(1 for _ in f)
    if n_lines % 2 != 0:
        raise ValueError(f"GMFileNames.txt in {info_dir} has an odd line count ({n_lines}) "
                          "-- expected H1/H2 pairs.")
    return n_lines // 2


def bucket_global_counter(gm_set_dir, global_counter):
    """Replicates RunDynamic.tcl's GMset_Series cumulative-sum bucketing (ScaleID/
    GMindex), deriving GMset_Num from the folder structure (num_gm_pairs) instead of
    a hardcoded literal. `global_counter` is 1-based across all hazard levels, same
    semantics as the old $SGE_TASK_ID. Returns (hazard_level, gm_index) -- gm_index
    is the 0-based pair index within that hazard level (Tcl's GMindex/GMIDs)."""
    levels = list_hazard_levels(gm_set_dir)
    counts = [num_gm_pairs(gm_set_dir, lvl) for lvl in levels]
    cumulative = np.cumsum(counts)

    scale_id = int(np.sum(global_counter > cumulative))
    if scale_id >= len(levels):
        raise ValueError(f"global_counter={global_counter} exceeds the total GM count "
                          f"({cumulative[-1] if len(cumulative) else 0}) across all hazard levels.")
    gm_num_base = 0 if scale_id == 0 else int(cumulative[scale_id - 1])
    gm_index = global_counter - gm_num_base - 1
    return levels[scale_id], gm_index


def resolve_gm(gm_set_dir, hazard_level, gm_index):
    """Reads the 4 GroundMotionInfo files for one hazard level and returns the file
    paths/parameters for GM pair `gm_index` (0-based). Mirrors RunDynamic.tcl's
    GM_XFileName/GM_ZFileName `format` logic and dt/numPoints/MCE_SF lookups."""
    level_dir = os.path.join(gm_set_dir, str(hazard_level))
    info_dir = os.path.join(level_dir, 'GroundMotionInfo')
    hist_dir = os.path.join(level_dir, 'histories')

    with open(os.path.join(info_dir, 'GMFileNames.txt')) as f:
        names = [line.strip() for line in f]
    time_steps = np.loadtxt(os.path.join(info_dir, 'GMTimeSteps.txt'))
    num_points = np.loadtxt(os.path.join(info_dir, 'GMNumPoints.txt'))
    scale_factors = np.loadtxt(os.path.join(info_dir, 'BiDirectionMCEScaleFactors.txt'))

    x_line = 2 * gm_index      # 0-based line index for the H1/X component
    z_line = 2 * gm_index + 1  # 0-based line index for the H2/Z component

    gm_x_file = os.path.join(hist_dir, names[x_line] + '.txt')
    gm_z_file = os.path.join(hist_dir, names[z_line] + '.txt')
    # RunDynamic.tcl reads dt/numPoints from the Z-component's line (GM_ZNumber-1);
    # paired X/Z components share a time step in every committed GM set, so this is
    # equivalent to the X line in practice, but matched exactly for fidelity.
    dt = float(time_steps[z_line])
    n_points = int(num_points[z_line])
    scale_factor = float(scale_factors[gm_index]) * GM_SCALE_G

    return {
        'gm_x_file': gm_x_file, 'gm_z_file': gm_z_file,
        'dt': dt, 'num_points': n_points, 'scale_factor': scale_factor,
        'gm_time': dt * n_points,
    }


GM_X_SERIES_TAG = 101
GM_Z_SERIES_TAG = 102
GM_X_ACCEL_SERIES_TAG = 111
GM_Z_ACCEL_SERIES_TAG = 112


def define_ground_motion_loading(bm, gm_x_file, gm_z_file, dt, scale_factor, pairing):
    """Port of DefineBiDirectionalTimeHistory.tcl's timeSeries/pattern block. The
    Tcl original tags these 1/2 (applied) and 11/12 (duplicate, for the absolute-
    acceleration recorders) -- this port uses 101/102/111/112 instead, since tag 1
    collides with model_builders.define_gravity_loads's `ops.timeSeries('Constant', 1)`
    (Tcl's implicit-series `pattern Plain 101 Constant {...}` has no explicit tag
    to collide with; openseespy's explicit ops.timeSeries call does). The tag
    numbers themselves aren't a load-bearing modeling detail, just bookkeeping.
    `pairing`: 1 puts gm_x_file on global X (dof 1) and gm_z_file on global Z
    (dof 3); 2 swaps them (the "H1 in X vs H1 in Z" flip)."""
    if pairing not in (1, 2):
        raise ValueError("pairing must be 1 or 2")

    ops.timeSeries('Path', GM_X_SERIES_TAG, '-dt', dt, '-filePath', gm_x_file, '-factor', scale_factor)
    ops.timeSeries('Path', GM_Z_SERIES_TAG, '-dt', dt, '-filePath', gm_z_file, '-factor', scale_factor)
    ops.timeSeries('Path', GM_X_ACCEL_SERIES_TAG, '-dt', dt, '-filePath', gm_x_file, '-factor', scale_factor)
    ops.timeSeries('Path', GM_Z_ACCEL_SERIES_TAG, '-dt', dt, '-filePath', gm_z_file, '-factor', scale_factor)

    if pairing == 1:
        ops.pattern('UniformExcitation', 2, 1, '-accel', GM_X_SERIES_TAG)
        ops.pattern('UniformExcitation', 3, 3, '-accel', GM_Z_SERIES_TAG)
    else:
        ops.pattern('UniformExcitation', 2, 3, '-accel', GM_X_SERIES_TAG)
        ops.pattern('UniformExcitation', 3, 1, '-accel', GM_Z_SERIES_TAG)
