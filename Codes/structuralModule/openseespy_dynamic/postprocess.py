# -*- coding: utf-8 -*-
"""
Reduces one run_dynamic_analysis() result down to the EDPs (engineering demand
parameters) a loss-assessment pipeline actually wants: peak story drift ratio
(SDR) per story and peak floor acceleration (PFA) per floor, in both horizontal
directions, plus the collapse flag.

Unlike collapse_solver.check_collapse (a faithful port of MaxDriftTesterBiDirection,
including its story-1-always-zero quirk -- see that function's docstring), this is
NEW code with no direct Tcl analog: Dynamic analysis has no active file recorders
in the current Tcl pipeline for this EDP shape (defineAllRecorders3DModel's Dynamic
branch only enables NodeAccelerations + StoryDrifts, and defineStoryDriftRecorders3DModel's
Dynamic branch -- Mid/Corner leaning-column recorder pairs -- computes REAL
inter-story drift for every story, story 1 included, using h1 for story 1 and htyp
for the rest). So story-1 SDR here is computed correctly (floor-1 displacement /
h1), matching what those recorders would have produced, not the collapse-checker's
internal shortcut.
"""

import numpy as np


def peak_story_drift_ratio(history, story_heights):
    """Returns (peak_sdr_x, peak_sdr_z), each a list of one value per story
    (index 0 = story 1)."""
    n_stories = len(story_heights)
    disp_x = np.asarray(history['story_disp_x'])  # shape (n_steps, n_stories+1)
    disp_z = np.asarray(history['story_disp_z'])

    def peak_for(disp):
        peaks = []
        for i in range(n_stories):
            h = story_heights[i]
            drift = (disp[:, i + 1] - disp[:, i]) / h
            peaks.append(float(np.max(np.abs(drift))) if len(drift) else 0.0)
        return peaks

    return peak_for(disp_x), peak_for(disp_z)


def peak_floor_acceleration(history, g=386.088):
    """Returns (peak_pfa_x, peak_pfa_z) in units of g, one value per floor
    (1..N, ground floor excluded -- see collapse_solver.run_dynamic_analysis's
    accel_floor_nodes)."""
    accel_x = np.asarray(history['abs_accel_x'])
    accel_z = np.asarray(history['abs_accel_z'])
    if accel_x.size == 0:
        return [], []
    peak_x = np.max(np.abs(accel_x), axis=0) / g
    peak_z = np.max(np.abs(accel_z), axis=0) / g
    return peak_x.tolist(), peak_z.tolist()


def summarize_dynamic(result, story_heights):
    """`result`: the dict returned by collapse_solver.run_dynamic_analysis (or
    dynamic_runner.generateDynamicAnalysisModel_ops, a superset of it)."""
    history = result['history']
    sdr_x, sdr_z = peak_story_drift_ratio(history, story_heights)
    pfa_x, pfa_z = peak_floor_acceleration(history)
    return {
        'ok': result['ok'],
        'collapse_flag': result['collapse_flag'],
        'collapse_dof': result['collapse_dof'],
        'final_time': result['final_time'],
        'gm_time': result['gm_time'],
        'peak_sdr_x': sdr_x,
        'peak_sdr_z': sdr_z,
        'peak_pfa_x_g': pfa_x,
        'peak_pfa_z_g': pfa_z,
    }
