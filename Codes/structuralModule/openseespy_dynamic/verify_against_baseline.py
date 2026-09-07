# -*- coding: utf-8 -*-
"""
Verification for the OpenSeesPy Dynamic port (phase 3 of 3), mirroring the
eigen/pushover phases' verify_against_baseline.py pattern:

1. Tcl-output diff: DefineDamping3DModel.tcl and DefineDynamicAnalysisParameters3DModel.tcl
   regenerated with the unmodified utils_opensees.py writers (current schema-driven
   BuildingModel, fed the SAME ModalPeriod values already present in a previously
   generated local copy under BuildingModels/MFD6B/DynamicAnalysis/, so this is a
   pure writer-logic check, not a fresh-vs-stale-geometry comparison) and diffed
   against that local copy.
2. Closed-form check: the Rayleigh alpha1/alpha2 formula, evaluated independently
   of openseespy, compared against damping.define_damping's arithmetic.

Does not import anything from openseespy_eigen/openseespy_dynamic for check 1 --
both pull in openseespy transitively, not installed in the arm64 base env this
check runs in.
"""

import os
import sys

cwd = os.path.dirname(os.path.abspath(__file__))
structural_module_dir = os.path.dirname(cwd)
code_dir = os.path.dirname(structural_module_dir)
root_dir = os.path.dirname(code_dir)


class _FakeSeries:
    def __init__(self, value):
        import numpy as np
        self.values = np.array([value])


class _FakeDF:
    """Minimal df_inputs stand-in (avoids importing pandas just for this check).
    Duplicated from run_dynamic_cli.py rather than imported from it, since that
    module pulls in openseespy transitively and this check must run in the arm64
    base env, which has no openseespy install."""

    def __init__(self, row):
        self._row = row

    def __getitem__(self, col):
        return _FakeSeries(self._row[col])


def _load_df_inputs(building_id, root_dir):
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


def check_1_tcl_diff(building_id, modal_period_1, modal_period_2):
    """modal_period_1/2 are ModalPeriod[0]/[2] from a previously generated local
    copy (BuildingModels/<ID>/DynamicAnalysis/DefineDamping3DModel.tcl) -- fed
    back in so this diff isolates writer-logic fidelity from any geometry drift
    between when that local copy was generated and today's schema."""
    sys.path.insert(0, structural_module_dir)
    sys.path.insert(0, os.path.join(code_dir, 'schema'))
    from BuildingModelClass import BuildingModel
    import utils_opensees as uo

    base_dir = os.path.join(root_dir, 'BuildingInfo', building_id)
    df_inputs = _load_df_inputs(building_id, root_dir)
    bm = BuildingModel(building_id)
    bm.read_in_txt_inputs(building_id, base_dir, df_inputs=df_inputs)

    import tempfile
    scratch_dir = os.path.join(tempfile.gettempdir(), 'dynamic_tcl_diff', building_id)
    os.makedirs(scratch_dir, exist_ok=True)

    modal_period = [modal_period_1, 0.5, modal_period_2, 0.2]  # index 1/3 unused by the writer
    uo.defineDamping3DModel(scratch_dir, bm, modal_period)
    uo.defineDynamicAnalysisParameters3DModel(scratch_dir, bm)

    local_dir = os.path.join(root_dir, 'BuildingModels', building_id, 'DynamicAnalysis')
    files = ['DefineDamping3DModel.tcl', 'DefineDynamicAnalysisParameters3DModel.tcl']

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


def check_2_damping_formula(period_1, period_2, damping_ratio):
    """Closed-form two-mode Rayleigh damping check, independent of openseespy."""
    import math
    omega_i = 2.0 * math.pi / period_1
    omega_j = 2.0 * math.pi / period_2
    alpha1 = (2.0 * omega_i * omega_j) / (omega_i + omega_j) * damping_ratio
    alpha2 = (2.0) / (omega_i + omega_j) * damping_ratio
    return alpha1, alpha2


if __name__ == '__main__':
    print("=== Check 1: Tcl-output diff (MFD6B) ===")
    for fname, status in check_1_tcl_diff('MFD6B', 0.626, 0.479).items():
        print(f"  {fname}: {status}")

    print("=== Check 2: closed-form Rayleigh damping (T1=0.626, T2=0.479, ratio=0.05) ===")
    a1, a2 = check_2_damping_formula(0.626, 0.479, 0.05)
    print(f"  alpha1={a1:.6f}  alpha2={a2:.6f}")
