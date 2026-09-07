# -*- coding: utf-8 -*-
"""
Direct port of BuildingInfo/*/BaselineTclFiles/OpenSees3DModels/PushoverAnalysis/
RunStaticPushover.tcl: same convergence test (EnergyIncr, tol 1e-6, 400 iters),
same primary algorithm (KrylovNewton), same DisplacementControl integrator, and the
same retry ladder on a failed step (Newton -initial -> Broyden(8) ->
NewtonLineSearch(0.8)).

Unlike the Tcl original (bulk `analyze(Nsteps)` under the primary algorithm, only
falling back to a manual per-step loop if that bulk call fails), this port always
loops `analyze(1)` one step at a time so it can read back the base shear / control
displacement in Python after every converged step -- functionally identical (the
ladder only ever engages when a step's `ok != 0`, exactly as in the Tcl version),
but avoids depending on OpenSees's file-recorder output being row-count-consistent
across two separate recorders (confirmed to drift out of sync between the
reaction and displacement recorders on a real run -- not used here).

Base shear is obtained by summing reactions at the story-1 (base) nodes that
actually carry a load path in the push direction: the panels running parallel to
the push direction, plus the leaning-column base nodes -- exactly the node set the
original Tcl recorders (XPanelBaseNodesHorizontalReactions.out +
LeaningColumnBaseNodeXHorizontalReactions.out, or the Z equivalents) capture. The
perpendicular-direction panels' base nodes are isolated in that DOF (no element
couples it) and are correctly omitted, same as the original.

Solver: the original Tcl uses `system UmfPack -lvalueFact 40`. This port uses
BandGeneral instead -- not verified/needed here, and BandGeneral is the solver
already proven reliable for these small models in the gravity/eigen port
(Codes/structuralModule/openseespy_eigen/gravity_analysis.py). Solver choice does
not change results, only the numerical method used to reach them.
"""

import numpy as np
import openseespy.opensees as ops


def _base_shear_nodes(bm, direction):
    nodes = []
    if direction == 'X':
        for j in range(bm.numberOfXDirectionWoodPanels[0]):
            nodes.append(int(bm.XDirectionWoodPanelsBotTag[0, j]))
        dof = 1
    else:
        for j in range(bm.numberOfZDirectionWoodPanels[0]):
            nodes.append(int(bm.ZDirectionWoodPanelsBotTag[0, j]))
        dof = 3
    for j in range(bm.leaningColumnNodesOpenSeesTags.shape[1]):
        nodes.append(int(bm.leaningColumnNodesOpenSeesTags[0, j]))
    return nodes, dof


def _try_step(tol, max_iter, test_type, algorithm_type):
    """One converged step under the primary algorithm, falling back through the
    same ladder RunStaticPushover.tcl uses if it fails. Returns ops.analyze(1)'s
    return code (0 = converged)."""
    ok = ops.analyze(1)
    if ok != 0:
        ops.test('NormDispIncr', tol, 2000, 0)
        ops.algorithm('Newton', '-initial')
        ok = ops.analyze(1)
        ops.test(test_type, tol, max_iter, 0)
        ops.algorithm(algorithm_type)
    if ok != 0:
        ops.algorithm('Broyden', 8)
        ok = ops.analyze(1)
        ops.algorithm(algorithm_type)
    if ok != 0:
        ops.algorithm('NewtonLineSearch', 0.8)
        ok = ops.analyze(1)
        ops.algorithm(algorithm_type)
    return ok


def run_static_pushover(bm, direction):
    """direction: 'X' or 'Z'. `bm` must already have build_model()/gravity/loading
    applied. Returns roof_drift_pct, base_shear, control_disp arrays (one entry
    per converged step) plus `ok` (0 if every step converged, else the return
    code of the first step that never converged, and the arrays stop there)."""
    if direction not in ('X', 'Z'):
        raise ValueError("direction must be 'X' or 'Z'")

    ctrl_node = int(bm.leaningColumnNodesOpenSeesTags[bm.numberOfStories, 0])
    ctrl_dof = 1 if direction == 'X' else 3
    base_nodes, base_dof = _base_shear_nodes(bm, direction)
    total_story_height = sum(bm.storyHeights)

    # PushoverParameter values are 0-D ndarrays (as_vector([scalar]) squeeze,
    # see Codes/schema/loader.py) -- float() unwraps them directly, no [0] index.
    dincr = float(bm.PushoverParameter['Increment'])
    drift_limit_pct = float(bm.PushoverParameter['PushoverXDrift'] if direction == 'X'
                             else bm.PushoverParameter['PushoverZDrift'])
    dmax = drift_limit_pct / 100.0 * total_story_height

    tol = 1.0e-6
    max_iter = 400
    test_type = 'EnergyIncr'
    algorithm_type = 'KrylovNewton'

    ops.constraints('Transformation')
    ops.numberer('RCM')
    ops.system('BandGeneral')
    ops.test(test_type, tol, max_iter, 0)
    ops.algorithm(algorithm_type)
    ops.integrator('DisplacementControl', ctrl_node, ctrl_dof, dincr)
    ops.analysis('Static')

    n_steps = int(dmax / dincr)
    roof_drift_pct = []
    base_shear = []
    control_disp = []
    ok = 0
    for _ in range(n_steps):
        ok = _try_step(tol, max_iter, test_type, algorithm_type)
        if ok != 0:
            break
        ops.reactions()
        shear = -sum(ops.nodeReaction(n, base_dof) for n in base_nodes)
        disp = ops.nodeDisp(ctrl_node, ctrl_dof)
        base_shear.append(shear)
        control_disp.append(disp)
        roof_drift_pct.append(disp / total_story_height * 100.0)

    return {
        'ok': ok,
        'roof_drift_pct': np.array(roof_drift_pct),
        'base_shear': np.array(base_shear),
        'control_disp': np.array(control_disp),
    }
