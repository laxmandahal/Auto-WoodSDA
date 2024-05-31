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



cwd = os.path.dirname(__file__)
root_dir = os.path.dirname(cwd)


## importing code required by the design module
sys.path.append(os.path.join(cwd, 'designModule'))
from check_user_inputs import check_and_complete_inputs
from StiffnessBasedDesign import RDADesignIterationClass

##Modules required for OpenSees Modeling 
sys.path.append(os.path.join(cwd, 'modelingModule'))
from BuildingModelClass import BuildingModel
from utils_opensees import *





def design_and_generate_model(
    building_id: str,
    baseline_building_info: dict,
    save_design_csv=False, 
    generate_static_models=False,
    run_pushover=False,
    generate_dynamic_models=True
):
    '''
    This function creates code-compliant design as well as the 3D OpenSees model(s).
    The `Buildings_input_info.csv` needs to be defined in the parent directory. 

    Note: Opensees need to be installed to run this function.

    Args:
        building_id (str): ID of the building being analyzed. It exist in the Buildings_input_info.csv file and should match the name of the inputs foldes in "BuildingInfo" folder.
        baseline_building_info (dict): Design variant databse that consists of building information such as number of wall lines, number of walls, etc.
        save_design_csv (bool, optional): Specification to save the final design of te building. Defaults to False.
        generate_static_models (bool, optional): Flag to control Modal and Pushover model creation. Defaults to False.
        run_pushover (bool, optional): Flag to run pushover analysis.. Defaults to False.
        generate_dynamic_models (bool, optional): Flag to control opensees model to run dynamic analysis. Defaults to True.
    '''
    df_inputs = pd.read_csv(os.path.join(root_dir, 'Buildings_input_info.csv'))
    df_inputs = df_inputs[df_inputs['BuildingID']==building_id]

    # the specified inputs are checked and any missing inputs are defaulted to certain values
    df_inputs_checked = check_and_complete_inputs(input_df = df_inputs)

    start = time.time()

    # Model directory is where you want to store your model
    ModelDirectory = os.path.join(root_dir, 'BuildingModels')
    # If there is no model directory, create one
    Path(ModelDirectory).mkdir(parents=True, exist_ok=True)

    #setup a directory to story results
    resultDirectory = os.path.join(root_dir, 'Results')
    # create one if it already doesnot exist
    Path(resultDirectory).mkdir(parents=True, exist_ok=True)

    # mapping definition of seismic weight to a numeric factor
    wt_factor_name_mapping = {'Light':0.8, 'Normal':1.0, 'Heavy':1.2}

    layoutID = df_inputs_checked['Layout Type'].values[0]

    building_info_dir = os.path.join(root_dir, *['BuildingInfo', building_id])
    
    # importing BIM for the building ID
    # e.g.,  direction = ['X', 'X', 'X', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y', 'Y'], this signifies that there are 
    # three wall lines along X-axis and 7 wall lines along Y-axis
    direction = baseline_building_info[layoutID]['Directions']
    # the dimension of wall line name, number of walls per wall line should be the same as direction
    wall_line_name = baseline_building_info[layoutID]['wall_line_names']
    num_walls_per_line = baseline_building_info[layoutID]['num_walls_per_wallLine']
    # modal periods for the layout.. used to define tangent rayleigh damping for dynamic analysis
    periods = baseline_building_info[layoutID]['Periods']

    # counter to keep track of design iterations
    counter = 0
    building_design = RDADesignIterationClass(building_id, 
                                              building_info_dir, direction, num_walls_per_line, counter, wall_line_name,
                                              designScheme = 'LRFD', 
                                                # Ss=df_inputs_checked['Ss(g)'].values[0],
                                                # S1=df_inputs_checked['S1(g)'].values[0],
                                                df_inputs=df_inputs,
                                                weight_factor=wt_factor_name_mapping[df_inputs_checked['seismicWeight'].values[0]], 
                                                seismic_design_level='High', 
                                                mat_ext_int=df_inputs_checked['wallMaterial'].values[0]
                                                )
    print('Successfully generated code-compliant design!!')

    # directory to building information for the baseline archetype ID
    InfoDirectory = os.path.join(root_dir, *['BuildingInfo', building_id])
    # model class establishes some of the inputs required by the modeling module. Most of the code is redundant in this class, 
    ## needs future clean-up 
    ModelClass = BuildingModel(building_id)
    ModelClass.read_in_txt_inputs(building_id, InfoDirectory,
                                  df_inputs=df_inputs
                                  )

    
    if save_design_csv:
        output_fp = os.path.join(resultDirectory, 'DesignSummary')
        Path(output_fp).mkdir(parents=True, exist_ok=True)
        building_design.maindf.to_csv(os.path.join(output_fp, '%s.csv'%building_id))
    
    archetype_dir = os.path.join(ModelDirectory, building_id)
    Path(archetype_dir).mkdir(parents=True, exist_ok=True)
    os.chdir(archetype_dir)
    
    if generate_static_models:
        ## generate and run eigenvalue analysis
        periods = generateModalAnalysisModel(ID=building_id, 
                                            BuildingModel=ModelClass, 
                                            BaseDirectory=root_dir, 
                                            NumModes=4
                                            )
        generatePushoverAnalysisModel(ID=building_id, 
                                        BuildingModel=ModelClass, 
                                        BaseDirectory=root_dir,
                                        GenerateModelSwitch=True, 
                                        RunPushoverSwitch=run_pushover)
    # create dynamic model
    if generate_dynamic_models:
        generateDynamicAnalysisModel(ID=building_id, 
                                    BuildingModel=ModelClass, 
                                    BaseDirectory=root_dir, 
                                    ModalPeriod=periods)

    finish = time.time()
    print(f'Model creation for {building_id} took {finish - start} seconds')






if __name__ == '__main__':
    # parser = argparse.ArgumentParser()
    # #defining the arguments to be parsed
    # parser.add_argument('--regional_strategy', type=str, default='HiFi')
    # parser.add_argument('--bldg_idx', type=int, default=1)

    # # #parse command-line arguments
    # args = parser.parse_args()
    ## In local computer
    # baseDir = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/RegionalStudy'
    # baseDir = r'/u/home/l/laxmanda/project-hvburton/Regional_study'
    dataDir = os.path.join(root_dir, 'Databases')
    # woodSDPA_dir = os.path.join(baseDir, 'woodSDPA')

    baseline_BIM = json.load(open(os.path.join(dataDir, 'Baseline_archetype_info_w_periods.json')))

    design_and_generate_model(building_id='MFD6B',
                              baseline_building_info=baseline_BIM,
                              save_design_csv=False,
                              )






