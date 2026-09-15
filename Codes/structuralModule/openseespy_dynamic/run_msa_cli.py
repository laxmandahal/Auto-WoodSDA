# -*- coding: utf-8 -*-
"""
Standalone CLI for the OpenSeesPy MSA (Multiple Stripe Analysis) orchestrator
(msa_orchestrator.py). NOT wired into Codes/run_designModule.py -- same reasoning
as the other openseespy_* CLIs (see openseespy_eigen/run_eigen_cli.py's docstring).
Run this in any env with the requirements.txt dependencies installed:

    python Codes/structuralModule/openseespy_dynamic/run_msa_cli.py \
        --buildingID s1_48x32 --gmSet BoelterHall --workers 4 --hazardLevelIM 0.403

Runs every ground motion at every hazard level found under
BuildingModels/GM_sets/<gmSet>/ (pairing 1 only -- H1-in-X/H2-in-Z; see
msa_orchestrator.py's module docstring for why pairing 2 is skipped), in parallel
across --workers OS processes. Writes Results/<buildingID>/EDP_data/{SDR,RDR,PFA,
CollapseCount,CollapseFragility,edp_results,hazard_level_summary}.csv -- see
msa_orchestrator.save_msa_results's docstring for exactly what each file is -- and
prints the hazard-level summary table.
"""

import argparse
import os
import sys

cwd = os.path.dirname(os.path.abspath(__file__))                      # .../openseespy_dynamic
_structural_module_dir = os.path.dirname(cwd)                         # .../structuralModule
_codes_dir = os.path.dirname(_structural_module_dir)                  # .../Codes
_root_dir = os.path.dirname(_codes_dir)                                # repo root
schema_dir = os.path.join(_codes_dir, 'schema')
sys.path.append(cwd)
sys.path.append(schema_dir)

from msa_orchestrator import run_msa, save_msa_results, summarize_by_hazard_level  # noqa: E402
from ground_motion import list_hazard_levels  # noqa: E402
from loader import load_building_config  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--buildingID', type=str, required=True)
    parser.add_argument('--gmSet', type=str, required=True,
                         help="Name under BuildingModels/GM_sets/, e.g. BoelterHall")
    parser.add_argument('--workers', type=int, default=None,
                         help="Parallel worker processes (default: os.cpu_count())")
    parser.add_argument('--gmLimit', type=int, default=None,
                         help="Cap GM pairs used per hazard level (for smoke tests; default: all)")
    parser.add_argument('--numModes', type=int, default=4)
    parser.add_argument('--maxRunTime', type=float, default=3600)
    parser.add_argument('--hazardLevelIM', type=str, default=None,
                         help="Comma-separated Sa (g) target for each hazard level, in the same "
                              "order as the GM set's sorted hazard-level folder names (e.g. "
                              "'0.403,0.975' for levels 1,2). Needed only for CollapseFragility.csv "
                              "-- omit to skip that file and still get all the EDP data.")
    args = parser.parse_args()

    # Validate --hazardLevelIM before running anything -- no point burning analysis
    # time only to fail on a typo'd Sa list afterward.
    hazard_level_im = None
    if args.hazardLevelIM:
        gm_set_dir = os.path.join(_root_dir, 'BuildingModels', 'GM_sets', args.gmSet)
        levels = list_hazard_levels(gm_set_dir)
        im_values = [float(v) for v in args.hazardLevelIM.split(',')]
        if len(im_values) != len(levels):
            parser.error(f"--hazardLevelIM has {len(im_values)} value(s) but {args.gmSet!r} has "
                          f"{len(levels)} hazard level(s) ({levels}) -- provide one Sa value per "
                          f"level, in that order.")
        hazard_level_im = dict(zip(levels, im_values))

    df = run_msa(
        args.buildingID, args.gmSet, num_workers=args.workers,
        gm_limit=args.gmLimit, num_modes=args.numModes, max_run_time=args.maxRunTime,
    )

    base_dir = os.path.join(_root_dir, 'BuildingInfo', args.buildingID)
    num_stories = load_building_config(base_dir).geometry.number_of_stories

    paths = save_msa_results(df, args.buildingID, num_stories, hazard_level_im=hazard_level_im)

    print("\nWrote:")
    for name, path in paths.items():
        print(f"  {name}: {path}")
    print("\nHazard-level summary:")
    print(summarize_by_hazard_level(df).to_string(index=False))


if __name__ == '__main__':
    main()
