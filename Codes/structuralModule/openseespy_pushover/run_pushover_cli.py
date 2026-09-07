# -*- coding: utf-8 -*-
"""
Standalone CLI for the OpenSeesPy Pushover port (phase 2 of 3). NOT wired into
Codes/run_designModule.py -- see openseespy_eigen/run_eigen_cli.py's docstring
for why. Run this under the x86_64 opensees_x86 env:

    /Users/laxmandahal/miniforge3/envs/opensees_x86/bin/python \
        Codes/structuralModule/openseespy_pushover/run_pushover_cli.py \
        --buildingID MFD6B --direction X
"""

import argparse
import csv
import os
import sys

cwd = os.path.dirname(os.path.abspath(__file__))
structural_module_dir = os.path.dirname(cwd)
code_dir = os.path.dirname(structural_module_dir)
root_dir = os.path.dirname(code_dir)
eigen_pkg_dir = os.path.join(structural_module_dir, 'openseespy_eigen')

sys.path.append(cwd)
sys.path.append(eigen_pkg_dir)
sys.path.append(structural_module_dir)
sys.path.append(os.path.join(code_dir, 'schema'))

from pushover_runner import generatePushoverAnalysisModel_ops
from postprocess import summarize_pushover
from BuildingModelClass import BuildingModel


class _FakeSeries:
    def __init__(self, value):
        import numpy as np
        self.values = np.array([value])


class _FakeDF:
    """Minimal df_inputs stand-in (avoids importing pandas just for this CLI)."""

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
                return _FakeDF(out)
    raise RuntimeError(f"No row for {building_id!r} in Buildings_input_info.csv")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--buildingID', type=str, required=True)
    parser.add_argument('--direction', type=str, choices=['X', 'Z'], default='X')
    parser.add_argument('--curveOut', type=str, default=None,
                         help='Optional path to write the raw (roof_drift_pct, base_shear) '
                              'curve as CSV.')
    args = parser.parse_args()

    base_dir = os.path.join(root_dir, 'BuildingInfo', args.buildingID)
    df_inputs = _load_df_inputs(args.buildingID)

    bm = BuildingModel(args.buildingID)
    bm.read_in_txt_inputs(args.buildingID, base_dir, df_inputs=df_inputs)

    result = generatePushoverAnalysisModel_ops(args.buildingID, bm, args.direction)

    total_weight = float(sum(bm.floorWeights))
    summary = summarize_pushover(result['roof_drift_pct'], result['base_shear'], total_weight)

    print(f"{args.buildingID} {args.direction}-direction pushover (ok={result['ok']}, "
          f"{len(result['roof_drift_pct'])} steps):")
    print(f"  W (total seismic weight)     = {total_weight:.1f} kips")
    print(f"  Vmax                          = {summary['Vmax']:.3f} kips")
    print(f"  Base strength (Vmax/W)        = {summary['base_strength_ratio']:.3f}")
    print(f"  Drift @ 80% Vmax (post-peak)  = {summary['drift_at_80pct_vmax_pct']:.2f} %")
    print(f"  Ductility demand (FEMA P-695) = {summary['ductility_demand']:.2f}")

    if args.curveOut:
        import numpy as np
        os.makedirs(os.path.dirname(args.curveOut) or '.', exist_ok=True)
        np.savetxt(args.curveOut,
                   np.column_stack([result['roof_drift_pct'], result['base_shear']]),
                   delimiter=',', header='roof_drift_pct,base_shear_kips', comments='')
        print(f"  Curve written to {args.curveOut}")

    return result, summary


if __name__ == '__main__':
    main()
