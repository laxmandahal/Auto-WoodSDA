# -*- coding: utf-8 -*-
"""
Port of setupEigenAnalysis (Codes/structuralModule/utils_opensees.py line 1134).
Tcl's `modalProperties -file ... -unorm` command has no direct openseespy
equivalent and isn't needed for periods -- periods come straight from the
eigenvalues. `mode_shape.out` (nodeEigenvector) is dropped for this phase: it
is not consumed anywhere in the current Python code path (damping takes
ModalPeriod as a parameter, not by reading this file) -- a deliberate,
documented scope decision, not a silent omission.
"""

import numpy as np
import openseespy.opensees as ops


def run_eigen(num_modes=4):
    """ops.eigen(n) (default ARPACK-based solver) fails outright on small systems
    (confirmed: 'NCV must be greater than NEV' on a toy 2-DOF case) -- these
    building models are small, so -fullGenLapack is used for reliability; the
    performance warning it prints is irrelevant at this model scale."""
    eigenvalues = ops.eigen('-fullGenLapack', num_modes)
    periods = [2 * np.pi / np.sqrt(lam) for lam in eigenvalues]
    return periods
