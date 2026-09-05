# -*- coding: utf-8 -*-
"""
Standalone CLI for the OpenSeesPy EigenValueAnalysis port. NOT wired into
Codes/run_designModule.py -- that driver does `from utils_opensees import *` at
module scope and must keep working in the arm64 base env, which has no openseespy
installed. Run this under the x86_64 opensees_x86 env instead:

    /Users/laxmandahal/miniforge3/envs/opensees_x86/bin/python \
        Codes/structuralModule/openseespy_eigen/run_eigen_cli.py --buildingID MFD6B
"""

import argparse
import csv
import os
import sys

cwd = os.path.dirname(os.path.abspath(__file__))
structural_module_dir = os.path.dirname(cwd)
code_dir = os.path.dirname(structural_module_dir)
root_dir = os.path.dirname(code_dir)

sys.path.append(cwd)
sys.path.append(structural_module_dir)
sys.path.append(os.path.join(code_dir, 'schema'))

from eigen_runner import generateModalAnalysisModel_ops
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
    parser.add_argument('--numModes', type=int, default=4)
    args = parser.parse_args()

    base_dir = os.path.join(root_dir, 'BuildingInfo', args.buildingID)
    df_inputs = _load_df_inputs(args.buildingID)

    bm = BuildingModel(args.buildingID)
    bm.read_in_txt_inputs(args.buildingID, base_dir, df_inputs=df_inputs)

    periods = generateModalAnalysisModel_ops(args.buildingID, bm, NumModes=args.numModes)
    print(f"Periods for {args.buildingID}: {periods}")
    return periods


if __name__ == '__main__':
    main()
