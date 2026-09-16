import pandas as pd 
import numpy as np
import argparse
import os 
import sys
import json
import time
import pickle

from pathlib import Path
from typing import List
import warnings
warnings.filterwarnings("ignore")


cwd = os.path.dirname(__file__)
code_dir = os.path.dirname(cwd)
baseDir = os.path.dirname(code_dir)
# baseDir = r'/u/home/l/laxmanda/project-hvburton/autoWoodSDA/'
# baseDir = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/woodSDA/autoWoodSDA_public'


sys.path.append(os.path.join(baseDir, *['Codes', 'lossModule', 'Loss_Pelicun']))

from create_edp_df import create_demands_df_pelicun
from generateLossModel import generateConfgFile_pelicun3p1new
from pelicun.tools.DL_calculation import run_pelicun

def delete_files_from_directory(directory, keep):
    baseDir = os.getcwd()
    try:
        os.chdir(directory)
        for file in os.listdir():
            if not file in keep:
                os.remove(file)
    finally:
        os.chdir(baseDir)

def main(
	buildingID: str,
    HAZARD_LEVEL: List[float],
    NUM_GM: List[int],
    num_story:int,
    per_story_area: float,
    occupancy_type: str = 'Single-Unit Residential',
    collapse_limit: float=0.1,
    im_period: float = 0.3
):
    start = time.time()

    # bldg_idx = int(bldg_idx) - 1
    # BuildingList = np.genfromtxt(os.path.join(baseDir, 'BuildingModels', 'ID_for_NRHA',
    #                                       f'ArchetypeIDs_for_NRHA_{REGIONAL_STRATEGY}.txt'), dtype=str)
    # BuildingList = ['MFD6B']
    # BuildingList = ['MFD6B_FEMA_P695']
    print(f'Initiating PELICUN Loss of {buildingID}...')
    ID = buildingID
    # split_str = ID.split('_')

    # HAZARD_LEVEL = [0.1, 0.3, 0.5, 0.7, 0.9, 1.1, 1.3, 1.5, 1.7, 1.9, 2.1, 2.3, 2.5, 2.7, 2.9, 3.1, 3.3, 3.5]
    # NUM_GM = np.array([22] * len(HAZARD_LEVEL), dtype=int) * 2 #should be multiplied by 2 if GMs are flipped 
    # HAZARD_LEVEL = [0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0]
    # NUM_GM = np.array([30] * len(HAZARD_LEVEL), dtype=int) * 2 #should be multiplied by 2 if GMs are flipped 
    
    # siteID = split_str[0]
    # baselineID = '_'.join([split_str[0], split_str[1]])
    baselineID = ID
    # num_story = 4
    # geom_str = split_str[1].split('x')
    # archetype_length = 96
    # archetype_width = 48
    # total_plan_area = archetype_length * archetype_width
    total_plan_area = per_story_area * num_story

    # collapse_limit = 0.5
    # num_stairs_per_floor = 2
    # num_elevators = 1

    if num_story == 1:
        replacement_cost = 450 * total_plan_area * num_story
    else:
        replacement_cost = 387 * total_plan_area * num_story

    ## create loss_model_config.json file that is used as an input by pelicun 3.1 most updated version (cloned: Oct 2023)
    ## Note: loss model config file is hazard-level-agnostic 
    generateConfgFile_pelicun3p1new(baselineID, 
                            baseDir, total_plan_area, num_story, 
                                    numRealization = 5000, 
                                    collapseLimit = collapse_limit,
                                    theta_collapse_g = 2.5,
                                    demolition_limit=0.05,
                                    occupancyType = occupancy_type, 
                                    replacementCost = replacement_cost, 
                                    replacementTime = 365*2,
                                    FEMA_residual_est = False)

    # resultDir = os.path.join(baseDir, 'Results', 'HiFi_FMA')
    resultDir = os.path.join(baseDir, 'Results')

    for hazard_level in range(1, len(HAZARD_LEVEL)+1):
        # hazard_level = 1
        # creating and saving the demand_IL{hazard_level}.csv that is used as an input by pelicun 2.6/3.1
        im_arr = [HAZARD_LEVEL[hazard_level-1]] * NUM_GM[hazard_level-1]

        demands_df = create_demands_df_pelicun(resultDir, ID, hazard_level, IM_value=im_arr, keep_pfa_unit_g=False)

        # DL_input_path = os.path.join(baseDir, *['BuildingModels', REGIONAL_STRATEGY, ID, 'LossAnalysis', 'PelicunInput', 'model_config.json'])
        DL_input_path = os.path.join(baseDir, *['Results', ID, 'LossAnalysis', 'PelicunInput', 'model_config.json'])
        # edp_input_path = os.path.join(baseDir, *['Results', 'HiFi_FMA', ID, 'demands.csv'])
        edp_input_path = os.path.join(baseDir, *['Results', ID, 'LossAnalysis', 'PelicunInput', f'demands_IL{hazard_level}.csv'])
        # specify and make output file path to store the .csv outputs from Pelicun 2.6
        # outputDir = os.path.join(baseDir, *['BuildingModels', REGIONAL_STRATEGY, ID, 'LossAnalysis', 'PelicunOutput', f'IL_{hazard_level}'])
        outputDir = os.path.join(baseDir, *['Results', ID, 'LossAnalysis', 'PelicunOutput', f'IL_{hazard_level}'])
        Path(outputDir).mkdir(parents=True, exist_ok=True)

        # Matches the real CLI's (pelicun.tools.DL_calculation.main) own argparse
        # defaults exactly -- see that module's `main()` for the source of these.
        run_pelicun(
            config_path=DL_input_path,
            demand_file=edp_input_path,
            output_path=outputDir,
            realizations=None,       # falls back to the config's own DL.Demands.SampleSize
            auto_script_path=None,
            custom_model_dir=None,
            output_format=None,
            detailed_results=True,
            coupled_edp=False,
        )
        print(f'Finished PELICUN Loss of {buildingID} @ IL-{hazard_level} ')

    finish = time.time()
    print('Loss module for %s Took %s Seconds'%(ID, (finish-start)))


# if __name__ == '__main__':
    # parser = argparse.ArgumentParser()
    # #defining the arguments to be parsed
    # parser.add_argument('--regional_strategy', type=str, default='HiFi')
    # parser.add_argument('--bldg_idx', type=int, default=1)
    # parser.add_argument('--runAll', type=bool, default=False)
    # # #parse command-line arguments
    # args = parser.parse_args()

    # if args.runAll:
    #     REGIONAL_STRATEGY = args.regional_strategy
    #     BuildingList = np.genfromtxt(os.path.join(baseDir, 'BuildingModels', 'ID_for_NRHA',
    #                                             f'ArchetypeIDs_for_NRHA_{REGIONAL_STRATEGY}.txt'),
    #                                             dtype=str)
    #     for idx in range(1, len(BuildingList)+1):
    #         main(REGIONAL_STRATEGY, bldg_idx=idx, norm_cmp_qty=True)
    # else:
    # main(bldg_idx=0, norm_cmp_qty=True)




