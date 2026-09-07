# -*- coding: utf-8 -*-
"""
Direct port of the two procs in BuildingInfo/*/BaselineTclFiles/OpenSees3DModels/
DynamicAnalysis/: `MaxDriftTesterBiDirection.tcl` (collapse check) and
`DynamicAnalysisBiDirectionCollapseSolver.tcl` (the timestep/algorithm retry
ladder) -- these are baseline files, never Python-written, so this is a fresh
translation rather than a rewire of an existing writer function.

Solver: the original Tcl uses `system UmfPack -lvalueFact 30`. This port uses
BandGeneral instead -- same documented substitution as the gravity/eigen/pushover
ports (not verified/needed, BandGeneral already proven reliable on these small
models). Everything else (test/algorithm/integrator sequence, tier and step
counts, tolerance/iteration scaling, HHT fallback, wall-clock bailout) is a 1:1
translation.
"""

import time

import numpy as np
import openseespy.opensees as ops

DRIFT_LIMIT_DEFAULT = 0.1  # hardcoded in DefineBiDirectionalTimeHistory.tcl's call
                            # to the solver -- NOT BuildingModel.DynamicParameter
                            # ['CollapseLimit'] -- confirmed with the user to
                            # preserve exactly rather than wire that in.

# Tier 1..5 use a fixed substep count regardless of remaining time; tier 0 uses
# min(remaining_steps - 1, 64), recomputed before each algorithm attempt (see
# _attempt_steps / run_dynamic_analysis).
_FIXED_TIER_STEPS = {1: 32, 2: 32, 3: 16, 4: 16, 5: 8}


def check_collapse(bm, drift_limit=DRIFT_LIMIT_DEFAULT):
    """Port of MaxDriftTesterBiDirection: peak inter-story drift ratio check, X
    first, Z only if X didn't already flag collapse.

    Faithful-port note: for story index i==0 the original Tcl computes
    nodeDisp(FloorNodes[0], dof) / h1 -- i.e. the BASE node's own displacement,
    not a difference against floor 1. Since the base node is fully fixed, this
    term is always exactly zero, so story-1's actual inter-story drift is never
    checked by this proc. That's a property of the original Tcl itself (confirmed
    by reading MaxDriftTesterBiDirection.tcl directly), reproduced here rather
    than silently fixed."""
    n_stories = bm.numberOfStories
    floor_nodes = [int(bm.leaningColumnNodesOpenSeesTags[i, 0]) for i in range(n_stories + 1)]
    h1 = float(bm.storyHeights[0])
    htyp = float(bm.storyHeights[0] if n_stories == 1 else bm.storyHeights[1])

    for dof in (1, 3):
        drifts = []
        for i in range(n_stories):
            if i == 0:
                d = ops.nodeDisp(floor_nodes[0], dof) / h1
            else:
                d = (ops.nodeDisp(floor_nodes[i], dof) - ops.nodeDisp(floor_nodes[i - 1], dof)) / htyp
            drifts.append(d)
        if any(abs(d) > drift_limit for d in drifts):
            return True, dof, drifts
    return False, None, None


def _attempt_steps(n_steps, dt_current, record_fn):
    """Runs up to n_steps single steps at dt_current, stopping at the first
    non-converged step (matches ops.analyze(n_steps, dt_current)'s own semantics
    of stopping early and leaving prior committed steps in place) -- done as a
    Python loop instead of one bulk analyze() call so drift/acceleration can be
    recorded after every successful step (same reasoning as the pushover port:
    no dependence on file-recorder output)."""
    ok = 0
    for _ in range(n_steps):
        ok = ops.analyze(1, dt_current)
        if ok != 0:
            break
        record_fn()
    return ok


def _ground_accel_at(t, values, gm_dt):
    """Nearest-sample lookup into a raw ground-acceleration array (already scaled
    to in/s^2) at analysis time t. Used to reconstruct ABSOLUTE floor acceleration
    (relative + ground input) in Python, since OpenSeesPy's ops.nodeAccel() has no
    equivalent to the Tcl Node recorder's `-timeSeries <tag>` option (which adds
    the input series' current value automatically) -- this is the direct
    alternative: the same raw array already loaded for ops.timeSeries('Path', ...),
    indexed at its own dt rather than re-querying OpenSees for it."""
    if values is None:
        return 0.0
    idx = int(round(t / gm_dt))
    idx = max(0, min(idx, len(values) - 1))
    return float(values[idx])


def run_dynamic_analysis(bm, dt, gm_time, drift_limit=DRIFT_LIMIT_DEFAULT, max_run_time=3600,
                          ground_accel_x=None, ground_accel_z=None):
    """Port of DynamicAnalysisBiDirectionCollapseSolver. `dt` is the ground motion's
    own time step (used as `dt_anal_Step`, matching DefineBiDirectionalTimeHistory.tcl's
    `set dtAn [expr 1.0*$GM_dt]`); `gm_time` is dt*num_points.

    Returns a dict: ok (0 = fully accomplished), collapse_flag, collapse_dof,
    final_time, story_drift_history (list of per-step [story...] arrays, X and Z
    interleaved by dof key), abs_accel_history (per-floor absolute acceleration,
    approximated as relative accel + ground input -- see note below)."""
    initial_tol = 1.0e-8
    incr_tol_factor = 10.0
    initial_max_iter = 500
    incr_max_iter = 100
    test_type = 'EnergyIncr'
    backup_test_type = 'NormDispIncr'
    print_flag = 0

    n_stories = bm.numberOfStories
    floor_nodes = [int(bm.leaningColumnNodesOpenSeesTags[i, 0]) for i in range(n_stories + 1)]
    # Absolute floor acceleration recorded for floors 1..N only (excludes the
    # fixed base), matching defineNodeAccelerationRecorders3DModel's own node set.
    accel_floor_nodes = floor_nodes[1:]

    history = {'time': [], 'story_disp_x': [], 'story_disp_z': [],
               'abs_accel_x': [], 'abs_accel_z': []}

    def record_step():
        t = ops.getTime()
        history['time'].append(t)
        history['story_disp_x'].append([ops.nodeDisp(n, 1) for n in floor_nodes])
        history['story_disp_z'].append([ops.nodeDisp(n, 3) for n in floor_nodes])
        gx = _ground_accel_at(t, ground_accel_x, dt)
        gz = _ground_accel_at(t, ground_accel_z, dt)
        history['abs_accel_x'].append([ops.nodeAccel(n, 1) + gx for n in accel_floor_nodes])
        history['abs_accel_z'].append([ops.nodeAccel(n, 3) + gz for n in accel_floor_nodes])

    ops.wipeAnalysis()
    ops.constraints('Transformation')
    ops.numberer('RCM')
    ops.system('BandGeneral')
    ops.test(test_type, initial_tol, initial_max_iter, print_flag)
    ops.algorithm('NewtonLineSearch', 0.75)
    ops.integrator('Newmark', 0.50, 0.25)
    ops.analysis('Transient')

    tol = initial_tol
    max_iter = initial_max_iter
    time_step_count = 0
    control_time = ops.getTime()
    ok = 0
    collapse_flag = False
    collapse_dof = None
    start_t = time.time()

    while control_time < 0.996 * gm_time and ok == 0:
        dt_current = dt / (2 ** time_step_count)
        control_time = ops.getTime()  # refreshed every pass, matches Tcl's own
                                        # `set controlTime [getTime]` at the top
                                        # of each while iteration

        def next_n_steps():
            remain_time = gm_time - ops.getTime()
            new_remain_steps = round(remain_time / dt_current)
            if time_step_count == 0:
                return min(new_remain_steps - 1, 64)
            return _FIXED_TIER_STEPS[time_step_count]

        # --- primary 4-algorithm cascade at the current tier ---
        ops.system('BandGeneral')
        ops.test(test_type, tol, max_iter, print_flag)
        ops.algorithm('NewtonLineSearch', 0.75)
        ok = _attempt_steps(next_n_steps(), dt_current, record_step)

        if ok != 0:
            ops.system('BandGeneral')
            ops.test(test_type, tol, max_iter, print_flag)
            ops.algorithm('KrylovNewton')
            ok = _attempt_steps(next_n_steps(), dt_current, record_step)

        if ok != 0:
            ops.system('BandGeneral')
            ops.test(test_type, tol, max_iter, print_flag)
            ops.algorithm('KrylovNewton', '-initial')
            ok = _attempt_steps(next_n_steps(), dt_current, record_step)

        if ok != 0:
            ops.system('BandGeneral')
            ops.test(test_type, tol, int(max_iter // 2), print_flag)
            ops.algorithm('BFGS')
            ok = _attempt_steps(next_n_steps(), dt_current, record_step)

        collapse_flag, collapse_dof, _ = check_collapse(bm, drift_limit)
        if collapse_flag:
            ok = 0
            break
        if time.time() - start_t > max_run_time:
            break

        # --- finest-tier-only HHT fallback, two rounds (4-substep then 1-substep) ---
        for hht_round_steps in (4, 1):
            if ok != 0 and time_step_count == 5:
                ops.system('BandGeneral')
                ops.test(backup_test_type, tol, max_iter, print_flag)
                ops.integrator('HHTHSIncrReduct', 0.5, 0.95)

            if ok != 0 and time_step_count == 5:
                ops.algorithm('NewtonLineSearch', 0.75)
                ok = _attempt_steps(hht_round_steps, dt_current, record_step)
            if ok != 0 and time_step_count == 5:
                ops.algorithm('KrylovNewton')
                ok = _attempt_steps(hht_round_steps, dt_current, record_step)
            if ok != 0 and time_step_count == 5:
                ops.algorithm('KrylovNewton', '-initial')
                ok = _attempt_steps(hht_round_steps, dt_current, record_step)
            if ok != 0 and time_step_count == 5:
                ops.algorithm('BFGS')
                ok = _attempt_steps(hht_round_steps, dt_current, record_step)

            collapse_flag, collapse_dof, _ = check_collapse(bm, drift_limit)
            if collapse_flag:
                ok = 0
                break
            if time.time() - start_t > max_run_time:
                break
        if collapse_flag or time.time() - start_t > max_run_time:
            break

        # restore the Newmark integrator if the HHT fallback ran (tier 5 only) --
        # the Tcl proc doesn't explicitly restore it either; the next tier-0
        # iteration's `integrator` call only happens via a fresh Model.tcl/gravity
        # setup, not mid-solve, so this mirrors that (no explicit reset here).

        if ok == 0 and 1 <= time_step_count <= 5:
            time_step_count -= 1
            tol /= incr_tol_factor
            max_iter -= incr_max_iter
        if ok != 0 and 0 <= time_step_count <= 4:
            time_step_count += 1
            tol *= incr_tol_factor
            max_iter += incr_max_iter
            ok = 0
            # falls through to the while condition, which re-reads control_time
            # at the top of the next pass -- matches the Tcl `continue` (the only
            # thing skipped is control_time being refreshed here too, which the
            # top-of-loop assignment above already does redundantly-safely)

    final_time = ops.getTime()
    return {
        'ok': ok,
        'collapse_flag': collapse_flag,
        'collapse_dof': collapse_dof,
        'final_time': final_time,
        'gm_time': gm_time,
        'history': history,
    }
