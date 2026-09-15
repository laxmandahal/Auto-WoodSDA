# -*- coding: utf-8 -*-
"""
Standalone CLI for the OpenSeesPy MSA (Multiple Stripe Analysis) orchestrator
(msa_orchestrator.py). NOT wired into Codes/run_designModule.py -- same reasoning
as the other openseespy_* CLIs (see openseespy_eigen/run_eigen_cli.py's docstring).
Run this in any env with the requirements.txt dependencies installed:

    python Codes/structuralModule/openseespy_dynamic/run_msa_cli.py \
        --buildingID s1_48x32 --gmSet BoelterHall --workers 4

Runs every ground motion at every hazard level found under
BuildingModels/GM_sets/<gmSet>/, in both pairings by default, in parallel across
--workers OS processes. Writes Results/<buildingID>/EDP_data/{SDR,RDR,PFA,
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
from loader import load_building_config  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--buildingID', type=str, required=True)
    parser.add_argument('--gmSet', type=str, required=True,
                         help="Name under BuildingModels/GM_sets/, e.g. BoelterHall")
    parser.add_argument('--pairings', type=str, default='1,2',
                         help="Comma-separated pairing IDs to run, e.g. '1,2' (default) or '1'")
    parser.add_argument('--workers', type=int, default=None,
                         help="Parallel worker processes (default: os.cpu_count())")
    parser.add_argument('--gmLimit', type=int, default=None,
                         help="Cap GM pairs used per hazard level (for smoke tests; default: all)")
    parser.add_argument('--numModes', type=int, default=4)
    parser.add_argument('--maxRunTime', type=float, default=3600)
    args = parser.parse_args()

    pairings = tuple(int(p) for p in args.pairings.split(','))

    df = run_msa(
        args.buildingID, args.gmSet, pairings=pairings, num_workers=args.workers,
        gm_limit=args.gmLimit, num_modes=args.numModes, max_run_time=args.maxRunTime,
    )

    base_dir = os.path.join(_root_dir, 'BuildingInfo', args.buildingID)
    num_stories = load_building_config(base_dir).geometry.number_of_stories

    paths = save_msa_results(df, args.buildingID, args.gmSet, num_stories)

    print("\nWrote:")
    for name, path in paths.items():
        print(f"  {name}: {path}")
    print("\nHazard-level summary:")
    print(summarize_by_hazard_level(df).to_string(index=False))


if __name__ == '__main__':
    main()
