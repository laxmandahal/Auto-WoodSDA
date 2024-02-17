import pandas as pd 
import numpy as np
import argparse
import os 
import sys
import json
import time
import pickle

from pathlib import Path

import warnings
warnings.filterwarnings("ignore")



baseDir = r'/u/home/l/laxmanda/project-hvburton/autoWoodSDA/'
# baseDir = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/woodSDA/autoWoodSDA_public'


sys.path.append(os.path.join(baseDir, *['Codes', 'lossModule', 'Loss_Pelicun']))
sys.path.append(os.path.join(baseDir, *['Codes', 'lossModule', 'Loss_Pelicun', 'pelicun_3_1_master_new']))
sys.path.append(os.path.join(baseDir, *['Codes', 'lossModule', 'Loss_ATC138']))

from create_edp_df import create_demands_df_pelicun
from generateLossModel import generateConfgFile_pelicun3p1new
from Run_pelicun_v3p1_new import run_pelicun
# from Run_pelicun_v3p1 import compile_demand_data, pelicun_assessment1
# from pelicun_3_1.assessment import Assessment
# from create_comp_ds_list import create_comp_ds_from_DMG
from create_building_model_file import create_building_model
# from create_default_optional_inputs import create_optional_inputs
from create_default_optional_inputs import create_optional_inputs_updated
from create_tenant_unit_list import create_tenant_unit_list

from normalize_cmp_units import normalize_comp_units

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
	bldg_idx: int,
    norm_cmp_qty: bool = True,
    im_period: float = 0.3
):
    start = time.time()

    bldg_idx = int(bldg_idx) - 1
    # BuildingList = np.genfromtxt(os.path.join(baseDir, 'BuildingModels', 'ID_for_NRHA',
    #                                       f'ArchetypeIDs_for_NRHA_{REGIONAL_STRATEGY}.txt'), dtype=str)
    BuildingList = ['MFD6B']
    print(f'Initiating PELICUN Loss of {BuildingList[bldg_idx]} (idx: {bldg_idx})')
    ID = BuildingList[bldg_idx]
    # split_str = ID.split('_')

    # HAZARD_LEVEL = [0.1, 0.3, 0.5, 0.7, 0.9, 1.1, 1.3, 1.5, 1.7, 1.9, 2.1, 2.3, 2.5, 2.7, 2.9, 3.1, 3.3, 3.5]
    # NUM_GM = np.array([22] * len(HAZARD_LEVEL), dtype=int) * 2 #should be multiplied by 2 if GMs are flipped 
    HAZARD_LEVEL = [0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0]
    NUM_GM = np.array([30] * len(HAZARD_LEVEL), dtype=int) * 2 #should be multiplied by 2 if GMs are flipped 
    
    # siteID = split_str[0]
    # baselineID = '_'.join([split_str[0], split_str[1]])
    baselineID = ID
    num_story = 4
    # geom_str = split_str[1].split('x')
    archetype_length = 96
    archetype_width = 48
    total_plan_area = archetype_length * archetype_width

    collapse_limit = 0.1
    num_stairs_per_floor = 2
    num_elevators = 1

    if num_story == 1: 
        collapse_limit = 0.2
        num_stairs_per_floor = 1
        num_elevators = 0

    if baselineID in ['SFD1B', 'SFD2B', 'SFD3B', 'SFD4B']:
        replacement_cost = 450 * total_plan_area * num_story
        occupancy_type = 'Single-Unit Residential'
        occupancy_id = 7
    else:
        replacement_cost = 387 * total_plan_area * num_story
        occupancy_type = 'Multi-Unit Residential'
        occupancy_id = 1
    ## create loss_model_config.json file that is used as an input by pelicun 3.1 most updated version (cloned: Oct 2023)
    ## Note: loss model config file is hazard-level-agnostic 
    generateConfgFile_pelicun3p1new(baselineID, 
                            baseDir, total_plan_area, num_story, 
                                    numRealization = 5000, 
                                    collapseLimit = collapse_limit,
                                    theta_collapse_g = 2.5,
                                    occupancyType = occupancy_type, 
                                    replacementCost = replacement_cost, 
                                    replacementTime = 365*2,
                                    FEMA_residual_est = False)

    # resultDir = os.path.join(baseDir, 'Results', 'HiFi_FMA')
    resultDir = os.path.join(baseDir, 'Results')
    # specify file path for the atc 138 input files
    # ATC138Input_dir = os.path.join(baseDir, *['BuildingModels', REGIONAL_STRATEGY, ID, 'LossAnalysis', 'ATC138Input'])
    ATC138Input_dir = os.path.join(baseDir, *['Results', ID, 'LossAnalysis', 'ATC138Input'])
    static_table_fp = os.path.join(baseDir, 'Codes', 'lossModule', 'Loss_ATC138', 'PBEE-Recovery')

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

        # creating output directory for the ATC-138 to save the files
        # ATC138Output_dir = os.path.join(baseDir, *['BuildingModels', REGIONAL_STRATEGY, ID, 'LossAnalysis', 'ATC138Output',  f'IL_{hazard_level}'])
        ATC138Output_dir = os.path.join(baseDir, *['Results', ID, 'LossAnalysis', 'ATC138Output',  f'IL_{hazard_level}'])
        Path(ATC138Output_dir).mkdir(parents=True, exist_ok=True)
        Path(os.path.join(ATC138Input_dir, f'IL_{hazard_level}')).mkdir(parents=True, exist_ok=True)
        

        run_pelicun(config_path = DL_input_path,
                    edp_file_dir=edp_input_path,
                    output_fp=outputDir
                    )
        ## remove extra files from the directory
        # delete_files_from_directory(outputDir, keep=['DMG_sample.csv', 
        #                                         'DL_summary.csv', 
        #                                         'DV_bldg_repair_sample.csv',
        #                                         'DEM_sample.csv'
        #                                         ])
        if norm_cmp_qty:
            normalize_comp_units(outputDir, static_table_fp)
        print(f'Finished PELICUN Loss of {BuildingList[bldg_idx]} (idx: {bldg_idx}) @ IL-{hazard_level} ')

    # it saves building_model.json file inside the "ATC138Input" folder
    ## Note: building model .json file is hazard-level agnostic
    create_building_model(baseDir, ID, num_story, total_plan_area, 
                        area_per_story=[archetype_length * archetype_width]*num_story, 
                        height_per_story=[10]*num_story, 
                        edge_lengths=[[archetype_length, archetype_width],]*num_story,
                        struct_bay_area_per_story=[100]*num_story, 
                        stairs_per_story=[num_stairs_per_floor]*num_story, 
                        building_value = replacement_cost, 
                        num_entry_doors=2, 
                        num_elevators=num_elevators, 
                        peak_occupancy_rate = 3.1/1000)

    create_optional_inputs_updated(
        ATC138Input_dir, inspection=True, financing=True, permitting=True, engineering=True, contractor=True,
        long_lead_time=False, design_time_f=0.04, design_time_r=200, design_time_t=1.3, design_time_w=8,
        eng_design_min_days=14, eng_design_max_days=365, 
        essential_facility=False, borp_equivalent=False, engineer_on_retainer=False, 
        contractor_relationship='good', contractor_retainer_time=3, funding_source='private', 
        capital_available_ratio=0.1, impeding_factors_beta=0.6, impedance_truncation=2, 
        default_lead_time=182, include_surge=1, is_dense_urban_area=1, site_pga=1, pga_de=1,
        scaffolding_lead_time=5, scaffolding_erect_time=2,
        door_racking_repair_day=3, flooding_cleanup_day=5, flooding_repair_day=90,
        max_workers_per_sqft_story=0.001, max_workers_per_sqft_story_temp_repair=0.005,
        max_workers_per_sqft_building = 0.00025, max_workers_building_min=20, max_workers_building_max=260, 
        allow_tmp_repairs=True, allow_shoring=True,
        calculate_red_tag=True, red_tag_clear_time=7, red_tag_clear_beta=0.6, 
        include_local_stability_impact=True, flooding_impact=True, egress_threshold=0.5,fire_watch=True, 
        local_fire_damage_threshold=0.25, min_egress_paths=2, exterior_safety_threshold=0.1, interior_safety_threshold=0.25, 
        door_access_width_ft=9, heat_utility='gas', water_pressure_max_story=num_story, electrical=False, 
        water_potable=False, water_sanitary=False, hvac_ventilation=False, hvac_heating=False,
        hvac_cooling=False, hvac_exhaust=False
        )
    tenant_unit_df = create_tenant_unit_list(ATC138Input_dir, num_story, [archetype_length * archetype_width]*num_story, 
                            [archetype_length * archetype_width / 10]*num_story, 
                            occupancyID=occupancy_id
                            )
    print(f'Generated ATC-138 input files for {BuildingList[bldg_idx]} (idx: {bldg_idx})')
    finish = time.time()
    print('Loss module for %s Took %s Seconds'%(ID, (finish-start)))


if __name__ == '__main__':
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
    main(bldg_idx=0, norm_cmp_qty=True)




