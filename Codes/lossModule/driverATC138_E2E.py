import matlab.engine

import os
import numpy as np 
import argparse
import json
from pathlib import Path
import sys
import time
from typing import List

cwd = os.path.dirname(__file__)
code_dir = os.path.dirname(cwd)
baseDir = os.path.dirname(code_dir)
# baseDir = r'/u/home/l/laxmanda/project-hvburton/autoWoodSDA/'
# baseDir = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/woodSDA/autoWoodSDA_public'

# sys.path.append(os.path.join(baseDir, *['Codes', 'Loss_ATC138', 'PBEE-Recovery-ubc-study']))
sys.path.append(os.path.join(baseDir, *['Codes', 'lossModule', 'Loss_ATC138', 'PBEE-Recovery']))

# atcDir = os.path.join(baseDir, 'Codes', 'Loss_ATC138', 'PBEE-Recovery-ubc_study')
atcDir = os.path.join(baseDir, 'Codes', 'lossModule', 'Loss_ATC138', 'PBEE-Recovery')

def delete_files_from_directory(
    directory: str, 
    files_to_remove: List[str]
):
    cwd = os.getcwd()
    try:
        os.chdir(directory)
        for file in os.listdir():
            if file in files_to_remove:
                os.remove(file)
    finally:
        os.chdir(cwd)


# def main(
# 	bldg_idx: int

# ):
#     start = time.time()

#     bldg_idx = int(bldg_idx) - 1

#     BuildingList = np.genfromtxt(os.path.join(baseDir, 'BuildingModels', 'ID_for_NRHA',
#                                           f'ArchetypeIDs_for_NRHA_{REGIONAL_STRATEGY}.txt'), dtype=str)
#     print(f'Initiating ATC_138 Loss of {BuildingList[bldg_idx]} (idx: {bldg_idx})')
#     ID = BuildingList[bldg_idx]

#     # for hazard_level in range(1, len(HAZARD_LEVEL)+1):
#     hazard_level = 1
#     atcDir_perBldg = os.path.join(baseDir, 'Results', REGIONAL_STRATEGY, ID, 'LossAnalysis')
#     with open (os.path.join(atcDir, 'driver_convert_PELICUN_woodSDA.m'), 'r') as matfile:
#         matCode = matfile.readlines()
#     matCode[30] = 'REGIONAL_STRATEGY = "%s" ;\n'%REGIONAL_STRATEGY
#     matCode[31] = 'ID = "%s" ;\n'%ID
#     matCode[32] = 'haz_level = "IL_%s" ;\n'%hazard_level
#     matCode[33] = 'baseDirectory = "%s";\n'%baseDir
#     with open (os.path.join(atcDir_perBldg, 'driver_convert_PELICUN_woodSDA_auto.m'), 'w') as matfile:
#         matCode = matfile.writelines(matCode)

#     with open (os.path.join(atcDir, 'build_inputs_main.m'), 'r') as matfile:
#         inputs_builder = matfile.readlines()
#     inputs_builder[60] = 'REGIONAL_STRATEGY = "%s" ;\n'%REGIONAL_STRATEGY
#     inputs_builder[61] = 'ID = "%s" ;\n'%ID
#     inputs_builder[62] = 'haz_level = "IL_%s" ;\n'%hazard_level
#     inputs_builder[64] = 'baseDirectory = "%s";\n'%baseDir
#     with open (os.path.join(atcDir_perBldg, 'build_input_main_auto.m'), 'w') as matfile:
#         inputs_builder = matfile.writelines(inputs_builder)


#     os.chdir(atcDir_perBldg)
#     eng = matlab.engine.start_matlab()
#     eng.driver_convert_PELICUN_woodSDA_auto(nargout=0)
#     eng.build_input_main_auto(nargout=0)
#     eng.quit()

#     os.chdir(atcDir_perBldg)
#     eng = matlab.engine.start_matlab()
#     with open (os.path.join(atcDir, 'driver_PBEErecovery_woodSDA.m'), 'r') as matfile:
#         atc_recovery_main = matfile.readlines()
#     atc_recovery_main[18] = "REGIONAL_STRATEGY = '%s'; \n"%REGIONAL_STRATEGY
#     atc_recovery_main[19] = 'ID = "%s" ;\n'%ID
#     atc_recovery_main[20] = 'haz_level = "IL_%s" ;\n'%hazard_level
#     atc_recovery_main[21] = 'baseDirectory = "%s";\n'%baseDir
#     with open (os.path.join(atcDir_perBldg, 'driver_PBEErecovery_woodSDA_auto.m'), 'w') as matfile:
#         atc_recovery_main = matfile.writelines(atc_recovery_main)
#     eng.driver_PBEErecovery_woodSDA_auto(nargout=0)

#     finish = time.time()
#     print(f'Finished ATC-138 Loss of {BuildingList[bldg_idx]} (idx: {bldg_idx}) in {finish - start} seconds')

#     files_to_delete = ['driver_convert_PELICUN_woodSDA_auto.m', 
#                        'build_input_main_auto.m', 
#                        'driver_PBEErecovery_woodSDA_auto.m']
#     delete_files_from_directory(atcDir_perBldg, files_to_delete)



def main_hazard_agnostic(
	buildingID: int
):
    start = time.time()

    BuildingList = ['MFD6B']
    print(f'Initiating ATC_138 Loss of {buildingID}')
    # ID = buildingID
    
    atcDir_perBldg = os.path.join(baseDir, 'Results', buildingID, 'LossAnalysis')
    with open (os.path.join(atcDir, 'main_mainfile.m'), 'r') as matfile:
        matCode = matfile.readlines()
    # matCode[5] = 'REGIONAL_STRATEGY = "%s" ;\n'%REGIONAL_STRATEGY
    matCode[7] = 'ID = "%s" ;\n'%buildingID
    matCode[10] = 'baseDirectory = "%s";\n'%baseDir
    with open (os.path.join(atcDir, f'main_mainfile_auto.m'), 'w') as matfile:
        matCode = matfile.writelines(matCode)


    os.chdir(atcDir)
    eng = matlab.engine.start_matlab()
    eng.main_mainfile_auto(nargout=0)
    eng.quit()

    

    finish = time.time()
    print(f'Finished ATC-138 Loss of {buildingID} in {finish - start} seconds')

    files_to_delete = ['driver_convert_PELICUN_woodSDA_auto.m', 
                       'build_input_main_auto.m', 
                       'driver_PBEErecovery_woodSDA_auto.m']
    delete_files_from_directory(atcDir_perBldg, files_to_delete)




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
    #         main(REGIONAL_STRATEGY, bldg_idx=idx)
    # else:

    # main_hazard_agnostic(bldg_idx=0)