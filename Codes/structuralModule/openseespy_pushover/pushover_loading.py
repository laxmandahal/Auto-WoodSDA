# -*- coding: utf-8 -*-
"""
Port of definePushoverLoading3DModel (Codes/structuralModule/utils_opensees.py line 1101).
Tcl's `pattern Plain 200 Linear {...}` implicitly creates a Linear time series;
openseespy needs it explicit (same pattern as define_gravity_loads's Constant series
in openseespy_eigen/model_builders.py).

Load magnitudes are the raw Cvx (ASCE 7 vertical distribution factor) values from
BuildingModel.SeismicDesignParameter -- these are a load *shape* only (the actual
force scale is irrelevant since the analysis is displacement-controlled), applied at
the central leaning column node of each story, exactly as the original Tcl does.
"""

import openseespy.opensees as ops

PUSHOVER_LOAD_PATTERN_TAG = 200
PUSHOVER_TIME_SERIES_TAG = 2


def define_pushover_loading(bm, direction):
    """direction: 'X' or 'Z'. Port of definePushoverXLoading3DModel /
    definePushoverZLoading3DModel."""
    if direction not in ('X', 'Z'):
        raise ValueError("direction must be 'X' or 'Z'")

    ops.timeSeries('Linear', PUSHOVER_TIME_SERIES_TAG)
    ops.pattern('Plain', PUSHOVER_LOAD_PATTERN_TAG, PUSHOVER_TIME_SERIES_TAG)

    cvx = bm.SeismicDesignParameter['Cvx']
    for i in range(bm.numberOfStories):
        node = int(bm.leaningColumnNodesOpenSeesTags[i + 1, 0])
        fx = cvx[i] if direction == 'X' else 0
        fz = cvx[i] if direction == 'Z' else 0
        ops.load(node, fx, 0, fz, 0, 0, 0)
