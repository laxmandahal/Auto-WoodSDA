# -*- coding: utf-8 -*-
"""
OpenSeesPy model-building functions -- direct in-process port of the model-building
subset of Codes/structuralModule/utils_opensees.py's Tcl-writing functions
(EigenValueAnalysis path only; utils_opensees.py itself is untouched and still used
for Pushover/Dynamic).

Every function here takes the same `BuildingModel` instance (Codes/structuralModule/
BuildingModelClass.py, already schema-migrated) the original Tcl-writing functions take,
and reproduces the identical loop bounds/array-indexing -- this is a translation of an
existing, working model, not a redesign. Line references in comments point at the
original Tcl-writing function in utils_opensees.py this was ported from.

Units: kips, inches, seconds (unchanged from the original Tcl model).
"""

import numpy as np
import openseespy.opensees as ops

# One-time model constants (from BuildingInfo/*/BaselineTclFiles/OpenSees3DModels/
# EigenValueAnalysis/DefineVariables.tcl, confirmed byte-for-byte -- these are not
# read from any per-archetype input, they're fixed modeling constants)
PDELTA_TRANSF = 1
LARGE_NUMBER = 1e9
SMALL_NUMBER = 1e-12
STIFF_MAT = 1200
SOFT_MAT = 1300

# g used by defineMasses3DModel (utils_opensees.py line 1058) -- note this does NOT
# match DefineUnitsAndConstants.tcl's own `set g [expr 32.174*$ft]` (=386.088); that
# Tcl variable is unused for mass computation (Python already bakes loads/g into a
# literal number before writing the `mass` command), so 32.2*12 is the value that
# actually determines today's results and is what this port must match.
GRAVITY_G = 32.2 * 12


def setup_model():
    """One-time model builder + constants (replaces sourcing DefineVariables.tcl /
    DefineUnitsAndConstants.tcl / DefineFunctionsAndProcedures.tcl)."""
    ops.wipe()
    ops.model('basic', '-ndm', 3, '-ndf', 6)
    ops.geomTransf('PDelta', PDELTA_TRANSF, 0, 0, -1)
    ops.uniaxialMaterial('Elastic', STIFF_MAT, LARGE_NUMBER)
    ops.uniaxialMaterial('Elastic', SOFT_MAT, SMALL_NUMBER)


def define_nodes(bm):
    """Port of defineNodes3DModel (utils_opensees.py line 10)."""
    n_stories = bm.numberOfStories

    # X-direction wood panel nodes
    for i in range(1, n_stories + 1):
        for j in range(1, bm.numberOfXDirectionWoodPanels[i - 1] + 1):
            ops.node(int(bm.XDirectionWoodPanelsBotTag[i - 1, j - 1]),
                     bm.XDirectionWoodPanelsXCoordinates[i - 1, j - 1],
                     bm.floorHeights[i - 1],
                     bm.XDirectionWoodPanelsZCoordinates[i - 1, j - 1])
            ops.node(int(bm.XDirectionWoodPanelsTopTag[i - 1, j - 1]),
                     bm.XDirectionWoodPanelsXCoordinates[i - 1, j - 1],
                     bm.floorHeights[i],
                     bm.XDirectionWoodPanelsZCoordinates[i - 1, j - 1])

    # Z-direction wood panel nodes
    for i in range(1, n_stories + 1):
        for j in range(1, bm.numberOfZDirectionWoodPanels[i - 1] + 1):
            ops.node(int(bm.ZDirectionWoodPanelsBotTag[i - 1, j - 1]),
                     bm.ZDirectionWoodPanelsXCoordinates[i - 1, j - 1],
                     bm.floorHeights[i - 1],
                     bm.ZDirectionWoodPanelsZCoordinates[i - 1, j - 1])
            ops.node(int(bm.ZDirectionWoodPanelsTopTag[i - 1, j - 1]),
                     bm.ZDirectionWoodPanelsXCoordinates[i - 1, j - 1],
                     bm.floorHeights[i],
                     bm.ZDirectionWoodPanelsZCoordinates[i - 1, j - 1])

    # Main leaning column nodes (one per floor level, 0..n_stories)
    num_leaning_col = bm.leaningColumnNodesOpenSeesTags.shape[1]
    for j in range(num_leaning_col):
        for i in range(1, n_stories + 2):
            ops.node(int(bm.leaningColumnNodesOpenSeesTags[i - 1, j]),
                      bm.leaningColumnNodesXCoordinates[i - 1, j],
                      bm.floorHeights[i - 1],
                      bm.leaningColumnNodesZCoordinates[i - 1, j])

    # Leaning column top nodes for zero-length springs (tag+1, per story 1..n_stories)
    for j in range(num_leaning_col):
        for i in range(1, n_stories + 1):
            ops.node(int(bm.leaningColumnNodesOpenSeesTags[i - 1, j]) + 1,
                      bm.leaningColumnNodesXCoordinates[i - 1, j],
                      bm.floorHeights[i - 1],
                      bm.leaningColumnNodesZCoordinates[i - 1, j])

    # Leaning column bottom nodes for zero-length springs (tag+2, per story 2..n_stories+1)
    for j in range(num_leaning_col):
        for i in range(2, n_stories + 2):
            ops.node(int(bm.leaningColumnNodesOpenSeesTags[i - 1, j]) + 2,
                      bm.leaningColumnNodesXCoordinates[i - 1, j],
                      bm.floorHeights[i - 1],
                      bm.leaningColumnNodesZCoordinates[i - 1, j])


def define_rigid_floor_diaphragm(bm):
    """Port of defineRigidFloorDiaphragm3DModel (utils_opensees.py line 105).
    ops.rigidDiaphragm takes the master node as an explicit arg, unlike Tcl's flat
    list where the first node is implicitly master."""
    perp_dirn = 2
    n_stories = bm.numberOfStories

    for i in range(1, n_stories + 1):
        nodes = []
        for ii in range(bm.leaningColumnNodesOpenSeesTags.shape[1]):
            nodes.append(int(bm.leaningColumnNodesOpenSeesTags[i, ii]))
        for j in range(bm.numberOfXDirectionWoodPanels[i - 1]):
            nodes.append(int(bm.XDirectionWoodPanelsTopTag[i - 1, j]))
        for j in range(bm.numberOfZDirectionWoodPanels[i - 1]):
            nodes.append(int(bm.ZDirectionWoodPanelsTopTag[i - 1, j]))
        if i < n_stories:
            for j in range(bm.numberOfXDirectionWoodPanels[i]):
                nodes.append(int(bm.XDirectionWoodPanelsBotTag[i, j]))
            for j in range(bm.numberOfZDirectionWoodPanels[i]):
                nodes.append(int(bm.ZDirectionWoodPanelsBotTag[i, j]))

        ops.rigidDiaphragm(perp_dirn, nodes[0], *nodes[1:])


def define_fixities(bm):
    """Port of defineFixities3DModel (utils_opensees.py line 147)."""
    n_stories = bm.numberOfStories

    for i in range(n_stories):
        for j in range(bm.numberOfXDirectionWoodPanels[i]):
            bot_dofs = (1, 1, 1, 1, 1, 1) if i == 0 else (0, 1, 0, 1, 0, 1)
            ops.fix(int(bm.XDirectionWoodPanelsBotTag[i, j]), *bot_dofs)
            ops.fix(int(bm.XDirectionWoodPanelsTopTag[i, j]), 0, 1, 0, 1, 0, 1)

    for i in range(n_stories):
        for j in range(bm.numberOfZDirectionWoodPanels[i]):
            bot_dofs = (1, 1, 1, 1, 1, 1) if i == 0 else (0, 1, 0, 1, 0, 1)
            ops.fix(int(bm.ZDirectionWoodPanelsBotTag[i, j]), *bot_dofs)
            ops.fix(int(bm.ZDirectionWoodPanelsTopTag[i, j]), 0, 1, 0, 1, 0, 1)

    for j in range(bm.leaningColumnNodesOpenSeesTags.shape[1]):
        for i in range(n_stories + 1):
            dofs = (1, 1, 1, 1, 1, 1) if i == 0 else (0, 0, 0, 1, 0, 1)
            ops.fix(int(bm.leaningColumnNodesOpenSeesTags[i, j]), *dofs)


def _pinching4_material(mat_tag, mat_props, mat_id_1based, wall_length, wall_height,
                          dmg_type='energy'):
    """Direct port of the Tcl proc `procUniaxialPinching` (BuildingInfo/*/BaselineTclFiles/
    OpenSees3DModels/EigenValueAnalysis/DefineFunctionsAndProcedures.tcl lines 13-46).
    Scaling, symmetric mirrored negative backbone, and gK=gD=gF=gFLim=gE=0 (degradation
    off beyond the first-cycle term) are load-bearing numeric details from the original
    proc, preserved exactly."""
    idx = int(mat_id_1based - 1)
    f_scale = wall_length / 12.0
    d_scale = wall_height / 100.0
    f = [mat_props[k][idx] * f_scale / 1000.0 for k in ('f1', 'f2', 'f3', 'f4')]
    d = [mat_props[k][idx] * d_scale for k in ('d1', 'd2', 'd3', 'd4')]
    rDisp = mat_props['rDisp'][idx]
    rForce = mat_props['rForce'][idx]
    uForce = mat_props['uForce'][idx]
    gD1 = mat_props['gD1'][idx]
    gDlim = mat_props['gDlim'][idx]
    gK1 = mat_props['gK1'][idx]
    gKlim = mat_props['gKlim'][idx]

    ops.uniaxialMaterial(
        'Pinching4', mat_tag,
        f[0], d[0], f[1], d[1], f[2], d[2], f[3], d[3],
        -f[0], -d[0], -f[1], -d[1], -f[2], -d[2], -f[3], -d[3],
        rDisp, rForce, uForce, rDisp, rForce, uForce,
        gK1, 0, 0, 0, gKlim,
        gD1, 0, 0, 0, gDlim,
        0, 0, 0, 0, 0,
        0, dmg_type,
    )


def define_wood_panel_materials(bm):
    """Port of defineWoodPanelMaterials3DModel (utils_opensees.py line 240)."""
    n_stories = bm.numberOfStories
    wood_panel_mat_tag = 600000
    outer_tag = 610000
    inner_tag = 620000

    for i in range(n_stories):
        for j in range(bm.numberOfXDirectionWoodPanels[i]):
            _pinching4_material(outer_tag, bm.MaterialProperty, bm.XPanelMaterial[2 * i, j],
                                 bm.XPanelLength[i, j], bm.XPanelHeight[i, j])
            outer_tag += 1
            _pinching4_material(inner_tag, bm.MaterialProperty, bm.XPanelMaterial[2 * i + 1, j],
                                 bm.XPanelLength[i, j], bm.XPanelHeight[i, j])
            inner_tag += 1

    for i in range(n_stories):
        for j in range(bm.numberOfZDirectionWoodPanels[i]):
            _pinching4_material(outer_tag, bm.MaterialProperty, bm.ZPanelMaterial[2 * i, j],
                                 bm.ZPanelLength[i, j], bm.ZPanelHeight[i, j])
            outer_tag += 1
            _pinching4_material(inner_tag, bm.MaterialProperty, bm.ZPanelMaterial[2 * i + 1, j],
                                 bm.ZPanelLength[i, j], bm.ZPanelHeight[i, j])
            inner_tag += 1

    # Parallel-combine outer+inner into the tag defineWoodPanels() actually references
    wood_panel_mat_tag = 600000
    outer_tag = 610000
    inner_tag = 620000
    for i in range(n_stories):
        for j in range(bm.numberOfXDirectionWoodPanels[i]):
            ops.uniaxialMaterial('Parallel', wood_panel_mat_tag, outer_tag, inner_tag)
            wood_panel_mat_tag += 1
            outer_tag += 1
            inner_tag += 1
    for i in range(n_stories):
        for j in range(bm.numberOfZDirectionWoodPanels[i]):
            ops.uniaxialMaterial('Parallel', wood_panel_mat_tag, outer_tag, inner_tag)
            wood_panel_mat_tag += 1
            outer_tag += 1
            inner_tag += 1


def define_wood_panels(bm):
    """Port of defineWoodPanels3DModel (utils_opensees.py line 199)."""
    n_stories = bm.numberOfStories
    ele_tag = 700000
    mat_tag = 600000

    for i in range(n_stories):
        for j in range(bm.numberOfXDirectionWoodPanels[i]):
            ops.element('twoNodeLink', ele_tag,
                        int(bm.XDirectionWoodPanelsBotTag[i, j]), int(bm.XDirectionWoodPanelsTopTag[i, j]),
                        '-mat', mat_tag, '-dir', 2, '-orient', 1, 0, 0, '-doRayleigh')
            ele_tag += 1
            mat_tag += 1

    for i in range(n_stories):
        for j in range(bm.numberOfZDirectionWoodPanels[i]):
            ops.element('twoNodeLink', ele_tag,
                        int(bm.ZDirectionWoodPanelsBotTag[i, j]), int(bm.ZDirectionWoodPanelsTopTag[i, j]),
                        '-mat', mat_tag, '-dir', 3, '-orient', 1, 0, 0, '-doRayleigh')
            ele_tag += 1
            mat_tag += 1


def define_leaning_column(bm):
    """Port of defineLeaningColumn3DModel (utils_opensees.py line 490)."""
    ele_tag = 800000
    num_leaning_col = bm.leaningColumnNodesOpenSeesTags.shape[1]

    for j in range(num_leaning_col):
        for i in range(bm.numberOfStories):
            ops.element('elasticBeamColumn', ele_tag,
                        int(bm.leaningColumnNodesOpenSeesTags[i, j]) + 1,
                        int(bm.leaningColumnNodesOpenSeesTags[i + 1, j]) + 2,
                        LARGE_NUMBER, 1, 1, LARGE_NUMBER, LARGE_NUMBER, LARGE_NUMBER,
                        PDELTA_TRANSF)
            ele_tag += 1


def define_leaning_column_flexural_springs(bm):
    """Port of defineLeaningColumnFlexuralSprings3DModel (utils_opensees.py line 515),
    which itself calls the Tcl procs CreatePinJointRXRYRZ/CreatePinJointRXRZ (ported
    directly here rather than as separate helper procs, since openseespy has no
    Tcl-proc equivalent to define once and reuse)."""
    ele_tag = 900000
    num_leaning_col = bm.leaningcolumnLoads.shape[1]

    for j in range(num_leaning_col):
        for i in range(bm.numberOfStories):
            node_r = int(bm.leaningColumnNodesOpenSeesTags[i, j])
            node_c = node_r + 1
            # CreatePinJointRXRYRZ: releases RX, RY, RZ (translations rigid)
            ops.element('zeroLength', ele_tag, node_r, node_c,
                        '-mat', STIFF_MAT, STIFF_MAT, STIFF_MAT, SOFT_MAT, SOFT_MAT, SOFT_MAT,
                        '-dir', 1, 2, 3, 4, 5, 6)
            ele_tag += 1

        for i in range(1, bm.numberOfStories + 1):
            node_r = int(bm.leaningColumnNodesOpenSeesTags[i, j])
            node_c = node_r + 2
            # CreatePinJointRXRZ: releases RX, RZ only (RY stiff)
            ops.element('zeroLength', ele_tag, node_r, node_c,
                        '-mat', STIFF_MAT, STIFF_MAT, STIFF_MAT, SOFT_MAT, STIFF_MAT, SOFT_MAT,
                        '-dir', 1, 2, 3, 4, 5, 6)
            ele_tag += 1


def define_masses(bm):
    """Port of defineMasses3DModel (utils_opensees.py line 1047)."""
    num_leaning_col = bm.leaningColumnNodesOpenSeesTags.shape[1]

    for j in range(num_leaning_col):
        for i in range(bm.numberOfStories):
            m = bm.leaningcolumnLoads[i, j] / GRAVITY_G
            if j != 0:
                ops.mass(int(bm.leaningColumnNodesOpenSeesTags[i + 1, j]), m, m, m, 0, 0, 0)
            else:
                mrot = m * ((bm.floorMaximumXDimension[i + 1] / 2) ** 2 +
                            (bm.floorMaximumZDimension[i + 1] / 2) ** 2)
                ops.mass(int(bm.leaningColumnNodesOpenSeesTags[i + 1, j]), m, m, m, mrot, mrot, mrot)


def define_gravity_loads(bm):
    """Port of defineGravityLoads3DModel (utils_opensees.py line 1024). Tcl's
    `pattern Plain 101 Constant {...}` implicitly creates the Constant time series;
    openseespy needs it explicit."""
    ops.timeSeries('Constant', 1)
    ops.pattern('Plain', 101, 1)
    num_leaning_col = bm.leaningColumnNodesOpenSeesTags.shape[1]
    for j in range(num_leaning_col):
        for i in range(bm.numberOfStories):
            ops.load(int(bm.leaningColumnNodesOpenSeesTags[i + 1, j]),
                     0, -bm.leaningcolumnLoads[i, j], 0, 0, 0, 0)


def build_model(bm):
    """Orchestrates the full model build, in the same order Model.tcl's `source`
    sequence used (utils_opensees.py define3DEigenValueAnalysisModel, line 1174)."""
    setup_model()
    define_nodes(bm)
    define_rigid_floor_diaphragm(bm)
    define_fixities(bm)
    define_wood_panel_materials(bm)
    define_wood_panels(bm)
    define_leaning_column(bm)
    define_leaning_column_flexural_springs(bm)
    define_masses(bm)
    define_gravity_loads(bm)
