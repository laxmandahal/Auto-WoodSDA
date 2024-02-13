import numpy as np 
import pandas as pd 
import os 
import json
from pathlib import Path
import argparse

def extract_atc138_results():

    # baseDir = r'/u/home/l/laxmanda/project-hvburton/autoWoodSDA/'
    baseDir = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/woodSDA/autoWoodSDA_public'

    HAZARD_LEVEL = [0.1, 0.3, 0.5, 0.7, 0.9, 1.1, 1.3, 1.5, 1.7, 1.9, 2.1, 2.3, 2.5, 2.7, 2.9, 3.1, 3.3, 3.5] #units: g
    
    # BuildingList = np.genfromtxt(os.path.join(baseDir, 'BuildingModels', 'ID_for_NRHA',
    #                                         f'ArchetypeIDs_for_NRHA_{REGIONAL_STRATEGY}.txt'), dtype=str)
    BuildingList = ['MFD6B']
    # buildingIDs = np.genfromtxt(os.path.join(baseDir, 'Codes', 'ArchetypeIDs_for_NRHA.txt'), dtype=str)
    #print(buildingIDs[0])
    # BuildingList = ['s1_40x30_HWS_GWB_Heavy_Vs11', 's1_40x30_HWS_GWB_Heavy_Vs11_nonNormalized']

    mean_fr_time_all = []
    std_fr_time_all = []
    median_fr_time_all = []
    percentile_25_fr = []
    percentile_75_fr = []
    percentile_90_fr = []
    caseID = []
    hazard_level_arr = []
    mean_reoccup_time_all = []
    std_reoccup_time_all = []
    median_reoccup_time_all = []
    percentile_25_reoccup = []
    percentile_75_reoccup = []
    percentile_90_reoccup = []
    sa_val_arr = []


    for i in range(len(BuildingList)):
        ID = BuildingList[i]
        print(f'Extacting ATC-138 summary of {ID} (idx:{i})')
        for hazard_level in range(1, len(HAZARD_LEVEL)+1):
            outputDir = os.path.join(baseDir, 'Results', ID, 
                                    'LossAnalysis', 'ATC138Output', f'IL_{hazard_level}')

            f = open(os.path.join(outputDir, 'recovery_outputs.json'))
            recovery_data = json.load(f)
            f.close()

            functional_recovery_time = recovery_data['recovery']['functional']['building_level']['recovery_day']
            reoccupancy_time = recovery_data['recovery']['reoccupancy']['building_level']['recovery_day']

            mean_fr_time_all.append(np.mean(functional_recovery_time))
            std_fr_time_all.append(np.std(functional_recovery_time))
            median_fr_time_all.append(np.median(functional_recovery_time))
            percentile_25_fr.append(np.quantile(functional_recovery_time, q=0.25))
            percentile_75_fr.append(np.quantile(functional_recovery_time, q=0.75))
            percentile_90_fr.append(np.quantile(functional_recovery_time, q=0.90))
            caseID.append(ID)
            hazard_level_arr.append(hazard_level)
            sa_val_arr.append(HAZARD_LEVEL[hazard_level-1])
            mean_reoccup_time_all.append(np.mean(reoccupancy_time))
            std_reoccup_time_all.append(np.std(reoccupancy_time))
            median_reoccup_time_all.append(np.median(reoccupancy_time))
            percentile_25_reoccup.append(np.quantile(reoccupancy_time, q=0.25))
            percentile_75_reoccup.append(np.quantile(reoccupancy_time, q=0.75))
            percentile_90_reoccup.append(np.quantile(reoccupancy_time, q=0.90))

    d = {'BuildingID': caseID,
        'Mean Functional Recovery': mean_fr_time_all,
        'Std Functional Recovery': std_fr_time_all, 
        'Median Functional Recovery': median_fr_time_all,
        '25th percentile FR': percentile_25_fr, 
        '75th percentile FR': percentile_75_fr,
        '90th percentile FR': percentile_90_fr,
        'Mean Reoccupancy': mean_reoccup_time_all, 
        'Std Reoccupancy': std_reoccup_time_all, 
        'Median Reoccupancy': median_reoccup_time_all,
        '25th percentile Reoccupancy': percentile_25_reoccup, 
        '75th percentile Reoccupancy': percentile_75_reoccup,
        '90th percentile Reoccupancy': percentile_90_reoccup,
        'Hazard_level':hazard_level_arr,
        'SA(T1=0.3s)': sa_val_arr
    }
    df = pd.DataFrame(d)
    df.to_csv(os.path.join(baseDir, 'Results',
                            f'Loss_ATC_RecoveryTimes_{ID}.csv'))


if __name__ == '__main__':
	# parser = argparse.ArgumentParser()
	# #defining the arguments to be parsed
	# parser.add_argument('--regional_strategy', type=str, default='HiFi')
	# # #parse command-line arguments
	# args = parser.parse_args()
	extract_atc138_results()