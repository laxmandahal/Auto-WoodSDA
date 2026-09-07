# -*- coding: utf-8 -*-
"""
Direct port of defineDamping3DModel (Codes/structuralModule/utils_opensees.py line
550). Two-mode Rayleigh damping, split across two explicit `region`s exactly as the
Tcl does -- NOT a single domain-wide `rayleigh` command:
  - region 1 (all wood-panel/shear-wall elements, tag range 700000..700000+n-1):
    stiffness-proportional only (`alpha2` in one of the 3 betaK slots, or none at
    all if DampingModel isn't recognized -- same silent no-damping fallback as Tcl).
  - region 2 (all leaning-column mass-carrying nodes, stories 1..N -- excludes the
    fixed base): mass-proportional only (`alpha1`).
"""

import numpy as np
import openseespy.opensees as ops


def define_damping(bm, modal_periods):
    """modal_periods: list/array of periods from openseespy_eigen.eigen_analysis.run_eigen
    (needs at least 3 modes -- uses periods 1 and 3, i.e. modal_periods[0]/[2], same as
    the Tcl `ModalPeriod[0]`/`ModalPeriod[2]`)."""
    period_1 = float(modal_periods[0])
    period_2 = float(modal_periods[2])
    omega_i = 2.0 * np.pi / period_1
    omega_j = 2.0 * np.pi / period_2
    alpha1_coeff = (2.0 * omega_i * omega_j) / (omega_i + omega_j)
    alpha2_coeff = 2.0 / (omega_i + omega_j)

    damping_ratio = float(bm.DynamicParameter['DampingRatio'])
    alpha1 = alpha1_coeff * damping_ratio
    alpha2 = alpha2_coeff * damping_ratio

    n_panel_elements = int(bm.numberOfXDirectionWoodPanels.sum() + bm.numberOfZDirectionWoodPanels.sum())
    ele_tag_start = 700000
    ele_tag_end = ele_tag_start + n_panel_elements - 1

    damping_model = bm.DynamicParameter['DampingModel']
    if damping_model == 'TangentRayleigh':
        rayleigh_args = (0, alpha2, 0, 0)
    elif damping_model == 'InitialRayleigh':
        rayleigh_args = (0, 0, alpha2, 0)
    elif damping_model == 'CommittedRayleigh':
        rayleigh_args = (0, 0, 0, alpha2)
    else:
        rayleigh_args = (0, 0, 0, 0)

    ops.region(1, '-eleRange', ele_tag_start, ele_tag_end, '-rayleigh', *rayleigh_args)

    num_leaning_col = bm.leaningColumnNodesOpenSeesTags.shape[1]
    node_tags = [int(bm.leaningColumnNodesOpenSeesTags[i, j])
                 for i in range(1, bm.numberOfStories + 1)
                 for j in range(num_leaning_col)]
    ops.region(2, '-node', *node_tags, '-rayleigh', alpha1, 0, 0, 0)

    return {'alpha1': alpha1, 'alpha2': alpha2, 'period_1': period_1, 'period_2': period_2}
