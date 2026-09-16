import glob
import json
import os
import re
import shutil
import sys
import time

cwd = os.path.dirname(__file__)
code_dir = os.path.dirname(cwd)
baseDir = os.path.dirname(code_dir)

sys.path.append(os.path.join(baseDir, *['Codes', 'lossModule', 'Loss_ATC138']))
sys.path.append(os.path.join(baseDir, 'Codes', 'schema'))

from pelicun_bridge import bridge_pelicun_output, write_general_inputs, write_optional_inputs
from create_tenant_unit_list import create_tenant_unit_list
from loader import load_building_config

from atc138 import driver as atc138_driver

# Same occupancy-string -> tenant-unit occupancy_id mapping driverPelicun_E2E.py
# uses for the FEMA P-58 loss model's OccupancyType string.
occ_type_to_id_mapping = {
    'single-unit residential': 7,
    'single unit residential': 7,
    'sfd': 7,
    'multi-unit residential': 1,
    'multi unit residential': 1,
    'mfd': 1,
}


def _hazard_levels_on_disk(pelicun_output_root):
    levels = []
    for path in glob.glob(os.path.join(pelicun_output_root, 'IL_*')):
        match = re.fullmatch(r'IL_(\d+)', os.path.basename(path))
        if match:
            levels.append(int(match.group(1)))
    return sorted(levels)


def main(buildingID: str, seed: int = 985):
    """Run the ATC-138 functional-recovery assessment for every hazard level this
    archetype already has real Pelicun output for.

    Replaces the old MATLAB main_hazard_agnostic(buildingID): reads the building's
    own geometry/replacement-cost/occupancy back from the Pelicun config + schema
    files it already wrote, so it keeps the same single-argument call signature.
    """
    start = time.time()
    ID = buildingID

    lossAnalysisDir = os.path.join(baseDir, 'Results', ID, 'LossAnalysis')
    pelicunOutputRoot = os.path.join(lossAnalysisDir, 'PelicunOutput')
    atc138InputRoot = os.path.join(lossAnalysisDir, 'ATC138Input')
    atc138OutputRoot = os.path.join(lossAnalysisDir, 'ATC138Output')

    with open(os.path.join(lossAnalysisDir, 'PelicunInput', 'model_config.json')) as f:
        pelicun_config = json.load(f)
    asset_cfg = pelicun_config['DL']['Asset']
    num_stories = int(asset_cfg['NumberOfStories'])
    total_plan_area = float(asset_cfg['PlanArea'])
    occupancy_type = asset_cfg['OccupancyType']
    replacement_cost = float(pelicun_config['DL']['Losses']['BldgRepair']['ReplacementCost']['Median'])

    building_config = load_building_config(os.path.join(baseDir, 'BuildingInfo', ID))
    geometry = building_config.geometry
    per_story_area = geometry.floor_areas[0]
    story_height_ft = geometry.story_heights[0] / 12.0
    length_side_1_ft = geometry.floor_max_x_dimension[0] / 12.0
    length_side_2_ft = geometry.floor_max_z_dimension[0] / 12.0

    # Same stairs/elevators heuristic driverPelicun_E2E.py already uses -- no
    # richer source for these exists anywhere in the schema today.
    if num_stories == 1:
        stairs_per_story = 1
        num_elevators = 0
    else:
        stairs_per_story = 2
        num_elevators = 1

    occupancy_id = occ_type_to_id_mapping[occupancy_type.lower()]

    print(f'Initiating ATC-138 functional-recovery assessment of {ID}...')

    create_tenant_unit_list(
        atc138InputRoot,
        num_stories,
        [per_story_area] * num_stories,
        [per_story_area / 10] * num_stories,
        occupancyID=occupancy_id,
    )

    hazard_levels = _hazard_levels_on_disk(pelicunOutputRoot)
    if not hazard_levels:
        raise FileNotFoundError(f'No PelicunOutput/IL_* directories found under {pelicunOutputRoot}')

    cmp_marginals_fp = os.path.join(
        baseDir, 'BuildingInfo', ID, 'ComponentsList', 'components_list_marginals.csv'
    )

    for hazard_level in hazard_levels:
        pelicun_output_dir = os.path.join(pelicunOutputRoot, f'IL_{hazard_level}')
        model_dir = os.path.join(atc138InputRoot, f'IL_{hazard_level}')
        output_dir = os.path.join(atc138OutputRoot, f'IL_{hazard_level}')

        bridge_pelicun_output(pelicun_output_dir, model_dir, cmp_marginals_fp)
        write_general_inputs(
            model_dir,
            num_stories=num_stories,
            plan_area_ft2=per_story_area,
            story_height_ft=story_height_ft,
            length_side_1_ft=length_side_1_ft,
            length_side_2_ft=length_side_2_ft,
            replacement_cost=replacement_cost,
            num_elevators=num_elevators,
            stairs_per_story=stairs_per_story,
        )
        write_optional_inputs(model_dir, num_stories)
        # tenant_unit_list.csv is hazard-agnostic; copy the one shared copy into
        # this hazard level's model_dir, same as general/optional_inputs.
        shutil.copyfile(
            os.path.join(atc138InputRoot, 'tenant_unit_list.csv'),
            os.path.join(model_dir, 'tenant_unit_list.csv'),
        )

        atc138_driver.run_analysis(model_dir, output_dir, seed=seed, force_rebuild=True)
        print(f'Finished ATC-138 Loss of {ID} @ IL-{hazard_level}')

    finish = time.time()
    print('ATC-138 module for %s took %s seconds' % (ID, (finish - start)))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--buildingID', type=str, required=True)
    parser.add_argument('--seed', type=int, default=985)
    args = parser.parse_args()
    main(args.buildingID, seed=args.seed)
