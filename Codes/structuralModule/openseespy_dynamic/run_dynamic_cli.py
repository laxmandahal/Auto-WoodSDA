# -*- coding: utf-8 -*-
"""
Standalone CLI for the OpenSeesPy Dynamic/NRHA port (phase 3 of 3). NOT wired
into Codes/run_designModule.py -- see openseespy_eigen/run_eigen_cli.py's
docstring for why. Run this under the x86_64 opensees_x86 env:

    /Users/laxmandahal/miniforge3/envs/opensees_x86/bin/python \
        Codes/structuralModule/openseespy_dynamic/run_dynamic_cli.py \
        --buildingID s1_48x32 --gmSet BoelterHall --hazardLevel 1 --gmIndex 0 --pairing 1

--globalCounter is also accepted as an alternative to --hazardLevel/--gmIndex,
replicating the old $SGE_TASK_ID bucketing (see ground_motion.bucket_global_counter).
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

from dynamic_runner import generateDynamicAnalysisModel_ops
from postprocess import summarize_dynamic
from ground_motion import bucket_global_counter
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
    parser.add_argument('--gmSet', type=str, required=True,
                         help="Name under BuildingModels/GM_sets/, e.g. BoelterHall")
    parser.add_argument('--hazardLevel', type=str, default=None)
    parser.add_argument('--gmIndex', type=int, default=None,
                         help="0-based GM pair index within --hazardLevel")
    parser.add_argument('--globalCounter', type=int, default=None,
                         help="Alternative to --hazardLevel/--gmIndex: old $SGE_TASK_ID "
                              "semantics, 1-based across all hazard levels")
    parser.add_argument('--pairing', type=int, choices=[1, 2], default=1)
    parser.add_argument('--numModes', type=int, default=4)
    parser.add_argument('--driftLimit', type=float, default=0.1)
    parser.add_argument('--maxRunTime', type=float, default=3600)
    args = parser.parse_args()

    gm_set_dir = os.path.join(root_dir, 'BuildingModels', 'GM_sets', args.gmSet)

    if args.globalCounter is not None:
        hazard_level, gm_index = bucket_global_counter(gm_set_dir, args.globalCounter)
    elif args.hazardLevel is not None and args.gmIndex is not None:
        hazard_level, gm_index = args.hazardLevel, args.gmIndex
    else:
        parser.error("Provide either --globalCounter or both --hazardLevel and --gmIndex")

    base_dir = os.path.join(root_dir, 'BuildingInfo', args.buildingID)
    df_inputs = _load_df_inputs(args.buildingID)

    bm = BuildingModel(args.buildingID)
    bm.read_in_txt_inputs(args.buildingID, base_dir, df_inputs=df_inputs)

    result = generateDynamicAnalysisModel_ops(
        args.buildingID, bm, gm_set_dir, hazard_level, gm_index, args.pairing,
        num_modes=args.numModes, drift_limit=args.driftLimit, max_run_time=args.maxRunTime,
    )
    summary = summarize_dynamic(result, bm.storyHeights)

    print(f"{args.buildingID}: hazard level {hazard_level}, GM index {gm_index}, "
          f"pairing {args.pairing}")
    print(f"  GM files: X={result['ground_motion']['gm_x_file']}")
    print(f"            Z={result['ground_motion']['gm_z_file']}")
    print(f"  Scale factor (incl. g): {result['ground_motion']['scale_factor']:.3f}")
    print(f"  Modal periods used for damping: {result['modal_periods']}")
    print(f"  Analysis status: {'ACCOMPLISHED' if summary['ok'] == 0 else 'FAILED'} "
          f"({summary['final_time']:.3f}/{summary['gm_time']:.3f} s)")
    print(f"  Collapse flag: {summary['collapse_flag']} (dof={summary['collapse_dof']})")
    print(f"  Peak SDR X per story: {['%.4f' % v for v in summary['peak_sdr_x']]}")
    print(f"  Peak SDR Z per story: {['%.4f' % v for v in summary['peak_sdr_z']]}")
    print(f"  Peak PFA X per floor (g): {['%.4f' % v for v in summary['peak_pfa_x_g']]}")
    print(f"  Peak PFA Z per floor (g): {['%.4f' % v for v in summary['peak_pfa_z_g']]}")
    return result, summary


if __name__ == '__main__':
    main()
