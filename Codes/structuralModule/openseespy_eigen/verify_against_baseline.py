# -*- coding: utf-8 -*-
"""
Verification script for the OpenSeesPy EigenValueAnalysis port. Run under the
x86_64 opensees_x86 env:

    /Users/laxmandahal/miniforge3/envs/opensees_x86/bin/python \
        Codes/structuralModule/openseespy_eigen/verify_against_baseline.py

No OpenSees Tcl binary is available on this machine (the committed .exe files
under BuildingModels/ are Windows PE binaries), so this performs the two
"weaker" local checks agreed with the user rather than a full HPC-generated
Tcl vs. openseespy comparison:

  1. Diffs freshly-generated Tcl (unmodified utils_opensees.py writer, current
     schema-driven BuildingModel) against whatever committed .tcl files exist
     under BuildingModels/<ID>/EigenValueAnalysis/ -- confirms the schema
     migration didn't silently change the model before trusting any baseline
     derived from it. Line-ending differences (the committed files were
     generated on Windows, CRLF) are normalized before comparing.
  2. Compares computed periods against whichever reference is available
     (committed periods.out, Databases/Baseline_archetype_info_w_periods.json)
     -- reported as a sanity check, NOT a pass/fail gate, since both of those
     references may themselves be stale (confirmed for MFD6B: the wood panel
     material assignment was changed by a later commit, after periods.out was
     generated, which is sufficient on its own to explain any period
     difference -- verified via `git log` on the Pinching4MaterialNumber files
     vs. the periods.out commit).

This must be confirmed against a fresh HPC-generated Tcl run before being
trusted for real research use -- that's on the user, not reproducible here.
"""

import csv
import json
import os
import sys

cwd = os.path.dirname(os.path.abspath(__file__))
structural_module_dir = os.path.dirname(cwd)
code_dir = os.path.dirname(structural_module_dir)
root_dir = os.path.dirname(code_dir)

sys.path.append(cwd)
sys.path.append(structural_module_dir)
sys.path.append(os.path.join(code_dir, 'schema'))

import numpy as np
import utils_opensees as uo
from BuildingModelClass import BuildingModel
from eigen_runner import generateModalAnalysisModel_ops


class _FakeSeries:
    def __init__(self, value):
        self.values = np.array([value])


class _FakeDF:
    def __init__(self, row):
        self._row = row

    def __getitem__(self, col):
        return _FakeSeries(self._row[col])


def _load_df_inputs(building_id):
    with open(os.path.join(root_dir, 'Buildings_input_info.csv')) as f:
        for row in csv.DictReader(f):
            if row['BuildingID'] == building_id or row['Layout Type'] == building_id:
                out = dict(row)
                for col, default in [('R', 6.5), ('Cd', 4.0), ('Ie', 1.0)]:
                    if out.get(col, '') == '':
                        out[col] = default
                return _FakeDF(out), out['Layout Type']
    raise RuntimeError(f"No row for {building_id!r} in Buildings_input_info.csv")


TCL_WRITER_FUNCS = [
    uo.defineNodes3DModel,
    uo.defineRigidFloorDiaphragm3DModel,
    uo.defineFixities3DModel,
    uo.defineWoodPanelMaterials3DModel,
    uo.defineWoodPanels3DModel,
    uo.defineLeaningColumn3DModel,
    uo.defineLeaningColumnFlexuralSprings3DModel,
    uo.defineGravityLoads3DModel,
    uo.defineMasses3DModel,
]


def check_1_tcl_diff(building_id, bm, scratch_dir):
    print(f"\n--- Check 1: Tcl-output diff for {building_id} ---")
    committed_dir = os.path.join(root_dir, 'BuildingModels', building_id, 'EigenValueAnalysis')
    if not os.path.isdir(committed_dir):
        print(f"  No committed EigenValueAnalysis/ directory for {building_id} -- nothing to diff against.")
        return

    out_dir = os.path.join(scratch_dir, building_id)
    os.makedirs(out_dir, exist_ok=True)
    for fn in TCL_WRITER_FUNCS:
        fn(out_dir, bm)

    for fname in sorted(os.listdir(out_dir)):
        committed_path = os.path.join(committed_dir, fname)
        if not os.path.isfile(committed_path):
            print(f"  {fname}: no committed counterpart, skipping")
            continue
        with open(committed_path, 'rb') as f:
            committed = f.read().replace(b'\r\n', b'\n')
        with open(os.path.join(out_dir, fname), 'rb') as f:
            fresh = f.read().replace(b'\r\n', b'\n')
        status = 'IDENTICAL' if committed == fresh else 'DIFFERS'
        print(f"  {fname}: {status}")


def check_2_periods(building_id, layout_id, periods):
    print(f"\n--- Check 2: period sanity check for {building_id} ---")
    print(f"  openseespy-computed periods: {periods}")

    periods_out_path = os.path.join(
        root_dir, 'BuildingModels', building_id, 'EigenValueAnalysis',
        'Analysis_Results', 'Modes', 'periods.out')
    if os.path.isfile(periods_out_path):
        with open(periods_out_path) as f:
            committed = [float(x) for x in f.read().split('\n') if x.strip()][:len(periods)]
        print(f"  committed periods.out (possibly stale): {committed}")
    else:
        print("  no committed periods.out for this archetype")

    json_path = os.path.join(root_dir, 'Databases', 'Baseline_archetype_info_w_periods.json')
    with open(json_path) as f:
        baseline_json = json.load(f)
    if layout_id in baseline_json:
        print(f"  Baseline_archetype_info_w_periods.json (possibly stale): "
              f"{baseline_json[layout_id].get('Periods')}")
    else:
        print(f"  no entry for layout {layout_id!r} in Baseline_archetype_info_w_periods.json")


def verify(building_id, scratch_dir, num_modes=4):
    print(f"=== Verifying {building_id} ===")
    df_inputs, layout_id = _load_df_inputs(building_id)
    base_dir = os.path.join(root_dir, 'BuildingInfo', building_id)

    bm = BuildingModel(building_id)
    bm.read_in_txt_inputs(building_id, base_dir, df_inputs=df_inputs)

    check_1_tcl_diff(building_id, bm, scratch_dir)

    periods = generateModalAnalysisModel_ops(building_id, bm, NumModes=num_modes)
    check_2_periods(building_id, layout_id, periods)


if __name__ == '__main__':
    scratch = sys.argv[1] if len(sys.argv) > 1 else '/tmp/openseespy_eigen_verify'
    for archetype in ['MFD6B', 's1_48x32']:
        verify(archetype, scratch)
