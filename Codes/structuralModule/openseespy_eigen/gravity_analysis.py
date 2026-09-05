# -*- coding: utf-8 -*-
"""
Direct port of BuildingInfo/*/BaselineTclFiles/OpenSees3DModels/EigenValueAnalysis/
PerformGravityAnalysis.tcl (confirmed byte-identical across Eigen/Pushover/Dynamic
baseline copies). Fixed 100-step LoadControl static analysis, no retry logic --
the original Tcl never checks analyze()'s return code either; this port adds a
warning (does not fail) if gravity doesn't converge, a deliberate small improvement
agreed with the user rather than silently ignoring a non-convergence.
"""

import warnings

import openseespy.opensees as ops


def perform_gravity_analysis(building_id=None):
    tol = 1.0e-8
    ops.constraints('Transformation')
    ops.numberer('RCM')
    ops.system('BandGeneral')
    ops.test('EnergyIncr', tol, 100)
    ops.algorithm('Newton')
    n_steps = 100
    ops.integrator('LoadControl', 1.0 / n_steps)
    ops.analysis('Static')
    ok = ops.analyze(n_steps)
    if ok != 0:
        label = f" for {building_id}" if building_id else ""
        warnings.warn(f"Gravity analysis did not converge (ok={ok}){label}")
    ops.loadConst('-time', 0.0)
