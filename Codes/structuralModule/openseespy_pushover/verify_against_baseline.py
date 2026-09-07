# -*- coding: utf-8 -*-
"""
Verification for the OpenSeesPy Pushover port (phase 2 of 3), mirroring
openseespy_eigen/verify_against_baseline.py's two-pronged approach:

1. Tcl-output diff: the *new* pieces this phase adds (pushover loading pattern,
   RunXPushoverAnalysis.tcl/RunZPushoverAnalysis.tcl parameters) are re-generated
   with the current schema-driven BuildingModel via the unmodified
   utils_opensees.py writers, then diffed against the committed baseline .tcl
   files. Model-definition files (nodes, panels, etc.) were already covered by
   the eigen phase's diff check and are unchanged here.
2. Summary-metric comparison: base strength (Vmax/W), drift at 80% Vmax, and
   FEMA P-695 ductility demand from a fresh OpenSeesPy run, compared against
   FEMA P-2139-2's Table 2 (hardcoded below, MFD6B is the only row that matches
   an archetype in this repo -- s1_48x32 has no published-table counterpart).

No OpenSees Tcl binary runs on this Mac, so there is no fresh Tcl pushover curve
to diff numerically -- only the loading/analysis-setup Tcl files (deterministic
text, no solve needed) can be diffed. A local, untracked (gitignored)
Static-Pushover-Output-Model3D-XPushoverDirection/ directory exists for MFD6B
under BuildingModels/ but was found to predate the same geometry-affecting
commit already identified as stale in the eigen phase (16 vs the current 18
X-direction panels at story 1) -- it is deliberately NOT used as ground truth
here, same reasoning as the stale periods.out baseline in phase 1.
"""

import os
import subprocess
import sys

cwd = os.path.dirname(os.path.abspath(__file__))
structural_module_dir = os.path.dirname(cwd)
code_dir = os.path.dirname(structural_module_dir)
root_dir = os.path.dirname(code_dir)

# FEMA P-2139-2 Table 2: "Comparison of eigenvalue and pushover analysis results
# between FEMA P-2139-2 and the current study." OpenSees columns only (the
# FEMA P-2139 columns are that report's own independent model, not reproduced
# here). Provided by the user (2026-09-07), not derived from repo data.
TABLE_2_OPENSEES = {
    'SFD1B': {'period': 0.13, 'base_strength': 2.28, 'drift_80pct': 3.54, 'ductility': 0.22},
    'SFD3B': {'period': 0.13, 'base_strength': 2.53, 'drift_80pct': 3.52, 'ductility': 0.16},
    'SFD2B': {'period': 0.22, 'base_strength': 1.04, 'drift_80pct': 1.89, 'ductility': 0.26},
    'SFD4B': {'period': 0.22, 'base_strength': 1.14, 'drift_80pct': 1.94, 'ductility': 0.28},
    'MFD1B': {'period': 0.16, 'base_strength': 1.51, 'drift_80pct': 3.08, 'ductility': 0.99},
    'MFD4B': {'period': 0.16, 'base_strength': 1.75, 'drift_80pct': 3.51, 'ductility': 0.69},
    'MFD2B': {'period': 0.26, 'base_strength': 0.67, 'drift_80pct': 1.99, 'ductility': 1.22},
    'MFD5B': {'period': 0.26, 'base_strength': 0.72, 'drift_80pct': 2.21, 'ductility': 1.14},
    'MFD3B': {'period': 0.49, 'base_strength': 0.39, 'drift_80pct': 1.31, 'ductility': 2.28},
    'MFD6B': {'period': 0.49, 'base_strength': 0.48, 'drift_80pct': 1.41, 'ductility': 1.74},
}


class _FakeSeries:
    def __init__(self, value):
        import numpy as np
        self.values = np.array([value])


class _FakeDF:
    """Minimal df_inputs stand-in (avoids importing pandas just for this check).
    Duplicated from run_pushover_cli.py rather than imported from it, since that
    module pulls in openseespy transitively (via pushover_runner ->
    model_builders) and this check must also run in the arm64 base env, which
    has no openseespy install."""

    def __init__(self, row):
        self._row = row

    def __getitem__(self, col):
        return _FakeSeries(self._row[col])


def _load_df_inputs(building_id):
    import csv
    with open(os.path.join(root_dir, 'Buildings_input_info.csv')) as f:
        for row in csv.DictReader(f):
            if row['BuildingID'] == building_id or row['Layout Type'] == building_id:
                out = dict(row)
                for col, default in [('R', 6.5), ('Cd', 4.0), ('Ie', 1.0)]:
                    if out.get(col, '') == '':
                        out[col] = default
                return _FakeDF(out)
    raise RuntimeError(f"No row for {building_id!r} in Buildings_input_info.csv")


def check_1_tcl_diff(building_id):
    """Regenerates the pushover-specific Tcl files with the unmodified
    utils_opensees.py writers (current schema-driven BuildingModel) and diffs
    them against BuildingModels/<ID>/PushoverAnalysis/*.tcl -- a previously
    generated (but gitignored/untracked, so possibly stale) local copy. Unlike
    the eigen phase, BuildingInfo/<ID>/BaselineTclFiles/.../PushoverAnalysis/
    (git-tracked) does NOT include these per-archetype loading/run files at all
    -- only the archetype-independent template files (RunStaticPushover.tcl
    etc.) are committed there, so there is no git-tracked ground truth for this
    specific diff. Deliberately does not import anything from the
    openseespy_eigen/openseespy_pushover packages -- both pull in openseespy
    transitively, which isn't installed in the arm64 base env this check runs
    in."""
    sys.path.insert(0, structural_module_dir)
    sys.path.insert(0, os.path.join(code_dir, 'schema'))
    from BuildingModelClass import BuildingModel
    import utils_opensees as uo

    base_dir = os.path.join(root_dir, 'BuildingInfo', building_id)
    df_inputs = _load_df_inputs(building_id)
    bm = BuildingModel(building_id)
    bm.read_in_txt_inputs(building_id, base_dir, df_inputs=df_inputs)

    import tempfile
    scratch_dir = os.path.join(tempfile.gettempdir(), 'pushover_tcl_diff', building_id)
    os.makedirs(scratch_dir, exist_ok=True)
    uo.definePushoverLoading3DModel(scratch_dir, bm)
    uo.setupPushoverAnalysis(scratch_dir, bm)

    local_dir = os.path.join(root_dir, 'BuildingModels', building_id, 'PushoverAnalysis')
    files = ['DefinePushoverXLoading3DModel.tcl', 'DefinePushoverZLoading3DModel.tcl',
             'RunXPushoverAnalysis.tcl', 'RunZPushoverAnalysis.tcl']

    results = {}
    for fname in files:
        new_path = os.path.join(scratch_dir, fname)
        local_path = os.path.join(local_dir, fname)
        if not os.path.exists(local_path):
            results[fname] = 'no local comparison file'
            continue
        with open(new_path, 'rb') as f:
            new_bytes = f.read().replace(b'\r\n', b'\n')
        with open(local_path, 'rb') as f:
            local_bytes = f.read().replace(b'\r\n', b'\n')
        results[fname] = 'IDENTICAL' if new_bytes == local_bytes else 'DIFFERS'
    return results


def check_2_table2(building_id, direction, summary):
    """Compares a fresh OpenSeesPy pushover run's summary metrics against
    Table 2 (MFD6B only has a published counterpart in this repo)."""
    ref = TABLE_2_OPENSEES.get(building_id)
    if ref is None:
        return f"No Table 2 row for {building_id} -- nothing to compare."

    lines = [f"{building_id} {direction}-direction vs. FEMA P-2139-2 Table 2 (OpenSees column):"]
    lines.append(f"  Base strength (Vmax/W): ours={summary['base_strength_ratio']:.3f}  "
                 f"table={ref['base_strength']:.3f}")
    lines.append(f"  Drift @ 80% Vmax (%):   ours={summary['drift_at_80pct_vmax_pct']:.2f}  "
                 f"table={ref['drift_80pct']:.2f}")
    lines.append(f"  Ductility demand:       ours={summary['ductility_demand']:.2f}  "
                 f"table={ref['ductility']:.2f}")
    lines.append("  (Table 2's own model is FEMA P-2139-2's independent build, not this "
                 "repo's -- reasonable agreement is a positive signal, not an exact-match "
                 "requirement.)")
    return '\n'.join(lines)


if __name__ == '__main__':
    print("=== Check 1: Tcl-output diff (MFD6B) ===")
    for fname, status in check_1_tcl_diff('MFD6B').items():
        print(f"  {fname}: {status}")
