import pandas as pd 
import numpy as np
import argparse
import os 
import sys
import warnings
import json
# from json import JSONEncoder
import time
from pathlib import Path


curr_fp = os.path.abspath(__file__)
cur_dir = os.path.dirname(curr_fp)
abs_dir = os.path.dirname(cur_dir)
cwd = os.path.dirname(abs_dir)

# cwd = r'/u/home/l/laxmanda/project-hvburton/Regional_study/woodSDPA/'
# cwd = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/RegionalStudy/woodSDPA'


sys.path.append(os.path.join(cwd, *['Codes','designModule']))
sys.path.append(os.path.join(cwd, *['Codes','modelingModule']))
# sys.path.append(os.path.join(cwd, *['Codes', 'PostProcessing']))
# from DesignTool.FinalShearWallDesign_allFloors import FinalShearWallDesign
from StiffnessBasedDesign import RDADesignIterationClass
####################### Modules required for OpenSees Modeling ##################
from BuildingModelClass import BuildingModel
from utils import *


# seed = int(os.getenv('SGE_TASK_ID'))

def design_and_generate_models(
    root_dir: str,
    bldg_idx: int,
    regional_strategy: str,
    baseline_building_info: dict,
    im_type:str = 'SA(0.3s)',
    save_design_csv=False, 
    run_on_Hoffman=True,
    check_against_HiFi = False
):
    bldg_idx = int(bldg_idx) - 1
    cwd = os.path.join(root_dir, 'woodSDPA')
    start = time.time()
    # Utility directory- contains source code to generate OpenSees Models 
    UtilDirectory = os.path.join(cwd, *['Codes','modelingModule'])
    # Model directory is where you want to store your model
    ModelDirectory = os.path.join(cwd, 'BuildingModels')
    # If there is no model directory, create one
    Path(ModelDirectory).mkdir(parents=True, exist_ok=True)
    # DB directory is where you store Database.csv (for steel section)
    DBDirectory = UtilDirectory
    #setup a directory to story results
    resultDirectory = os.path.join(cwd, 'Results')
    # create one if it already doesnot exist
    Path(resultDirectory).mkdir(parents=True, exist_ok=True)
    # buildingID = []
    # buildingID_for_NRHA = []  #length of this = num of FMA E2E runs needed
    # numRuns = len(df_designedArchetypes)

    # wt_factor_name_mapping = {0.8:'Light', 1:'Normal', 1.2:'Heavy'}
    wt_factor_name_mapping = {'Light':0.8, 'Normal':1.0, 'Heavy':1.2}

    df_designedArchetypes = pd.read_csv(os.path.join(root_dir, 'data',
                                                     'variant_assignment',
                                                     f'E2E_FMA_runs_{regional_strategy}.csv'))
    # remove redundant archetypes IDs 
    df_designedArchetypes = df_designedArchetypes.drop_duplicates(subset=['designedArchetype_site'])

    if check_against_HiFi:
        df_archetypes_HiFi = pd.read_csv(os.path.join(root_dir, 'data',
                                                     'variant_assignment',
                                                     'E2E_FMA_runs_HiFi.csv'))
        df_archetypes_HiFi = df_archetypes_HiFi.drop_duplicates(subset=[f'designedArchetype_site'])
        ## only keeping the archetype ID that hasn't already been run in HiFi FMA
        df_designedArchetypes = pd.merge(df_designedArchetypes, df_archetypes_HiFi,
                                         on=f'designedArchetype_{im_type}', how='left',
                                         indicator=True)

    design_Ss_all_sites = df_designedArchetypes['Ss(g)'].values
    design_S1_all_sites = df_designedArchetypes['S1(g)'].values

    for i in [bldg_idx]:
    # for i in range(len(df_designedArchetypes)):
        id_split = df_designedArchetypes['designedArchetype_site'].values[i].split('_')
        caseID = '_'.join([id_split[0], id_split[1]])
        baseline_info_dir = os.path.join(cwd, *['BuildingInfo', caseID])
        # numFloors = baseline_building_info[caseID]['Num Story']
        direction = baseline_building_info[caseID]['Directions']
        wall_line_name = baseline_building_info[caseID]['wall_line_names']
        num_walls_per_line = baseline_building_info[caseID]['num_walls_per_wallLine']
        counter = 0
        # print(i, '%s_%s_%s_%s_%s'%(caseID, mat_comb_all_sites[i], 
        building_design = RDADesignIterationClass(caseID, baseline_info_dir, direction, num_walls_per_line, counter, wall_line_name, 
                                                    Ss=design_Ss_all_sites[i],
                                                    S1=design_S1_all_sites[i], 
                                                    weight_factor=wt_factor_name_mapping[id_split[4]], 
                                                    seismic_design_level='High', 
                                                    mat_ext_int='_'.join([id_split[2], id_split[3]]))
        
        # directory to building information for the baseline archetype ID
        InfoDirectory = os.path.join(cwd, *['BuildingInfo', caseID])
        ModelClass = BuildingModel(caseID, InfoDirectory, Ss=design_Ss_all_sites[i], S1=design_S1_all_sites[i])
        ModelClass.read_in_txt_inputs(caseID, InfoDirectory)
        base_shear = ModelClass.SeismicDesignParameter['ELF Base Shear']
        # create directory for the archetype designed/modeled within "BuildingModel" folder
        # archetype_id = df_designedArchetypes['designedArchetype'].values[i]
        archetype_id_for_NRHA = df_designedArchetypes['designedArchetype_site'].values[i]


        # buildingID.append(archetype_id)
        # buildingID_for_NRHA.append(archetype_id_for_NRHA)
        # print(i, archetype_id)
        
        if save_design_csv:
            output_fp = os.path.join(resultDirectory, regional_strategy, 'DesignSummary')
            Path(output_fp).mkdir(parents=True, exist_ok=True)
            building_design.maindf.to_csv(os.path.join(output_fp, '%s.csv'%archetype_id_for_NRHA))
        
        archetype_dir = os.path.join(ModelDirectory, 
                                     regional_strategy,
                                     archetype_id_for_NRHA)
        Path(archetype_dir).mkdir(parents=True, exist_ok=True)
        os.chdir(archetype_dir)
        
        if run_on_Hoffman:
            # period = periods_df.loc[archetype_id,:].values
            period = baseline_building_info[caseID]['Periods']
        else:
            period = generateModalAnalysisModel(caseID, archetype_id_for_NRHA, ModelClass, cwd, DBDirectory)
        

        generateDynamicAnalysisModel(caseID, archetype_id_for_NRHA, ModelClass, cwd, regional_strategy, period,
                                        GenerateModelSwitch = True)

    finish = time.time()
    print(f'Model creation for {archetype_id_for_NRHA} took {finish - start} seconds')
    # return archetype_id_for_NRHA






if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    #defining the arguments to be parsed
    parser.add_argument('--regional_strategy', type=str, default='HiFi')
    parser.add_argument('--bldg_idx', type=int, default=1)
    # parser.add_argument('--archetype_csv', type=str, default='designedArchetypes_seed42_EA-VaFi.csv')
    # # parser.add_argument('--archetype_csv', type=str, default='designedArchetypes_seed42_SVaFi.csv')
    # #parse command-line arguments
    args = parser.parse_args()
    ## In local computer
    # baseDir = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/RegionalStudy'
    baseDir = r'/u/home/l/laxmanda/project-hvburton/Regional_study'
    dataDir = os.path.join(baseDir, 'data')
    woodSDPA_dir = os.path.join(baseDir, 'woodSDPA')

    baseline_BIM = json.load(open(os.path.join(dataDir, 'Baseline_archetype_info_w_periods.json')))


    design_and_generate_models(root_dir=baseDir,
                               bldg_idx= args.bldg_idx,
                               regional_strategy=args.regional_strategy, 
                               baseline_building_info=baseline_BIM, im_type='SA(0.3s)',
                               save_design_csv=False, run_on_Hoffman=True, check_against_HiFi=False)
    
    # design_and_generate_models(root_dir=baseDir, regional_strategy='VaFi', 
    #                            baseline_building_info=baseline_BIM, im_type='SA(0.3s)',
    #                            save_design_csv=False, run_on_Hoffman=True, check_against_HiFi=True)
    






