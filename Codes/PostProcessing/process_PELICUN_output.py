import numpy as np 
import pandas as pd 
import os 
import argparse
from pathlib import Path
import time
import json

start = time.time()


def extract_pelicun_results(
    run_on_Hoffman: bool = False
):

    if run_on_Hoffman:
        baseDir = r'/u/home/l/laxmanda/project-hvburton/autoWoodSDA/'
    else:
        baseDir = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/woodSDA/autoWoodSDA_public'


    HAZARD_LEVEL = [0.1, 0.3, 0.5, 0.7, 0.9, 1.1, 1.3, 1.5, 1.7, 1.9, 2.1, 2.3, 2.5, 2.7, 2.9, 3.1, 3.3, 3.5] #units: g
    # HAZARD_LEVEL = [0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0]

    # BuildingList = np.genfromtxt(os.path.join(baseDir, 'BuildingModels', 'ID_for_NRHA',
    #                                         f'ArchetypeIDs_for_NRHA_{REGIONAL_STRATEGY}.txt'), dtype=str)
    BuildingList = ['MFD6B']
    g = 386.04 #in/sec2

    archetypeID = []
    bldg_value = []
    mean_repair_cost = []
    median_repair_cost = []
    repair_cost_10th_percentile = []
    repair_cost_25th_percentile = []
    repair_cost_75th_percentile = []
    repair_cost_90th_percentile = []
    repair_cost_std = []
    hazard_level_arr = []
    sa_val_arr = []
    ## extracting structural responses
    max_sdr = []
    max_pfa = []
    max_rdr = []
    max_pga = []
    max_sdr_profile = []
    max_pfa_profile = []
    max_rdr_profile = []
    max_pga_profile = []

    for i in range(len(BuildingList)):
        ID = BuildingList[i]
        print(f'Extacting Pelicun and EDP summary of {ID} (idx:{i})')
        pelicun_fp = os.path.join(baseDir, 'Results', ID, 
                                    'LossAnalysis', 'PelicunInput')
        f = open(os.path.join(pelicun_fp, 'model_config.json'))
        modelConfig = json.load(f)
        f.close()
        
        for hazard_level in range(1, len(HAZARD_LEVEL)+1):
            bldg_value.append(modelConfig['DL']['Losses']['BldgRepair']['ReplacementCost']['Median'])
            
            outputDir = os.path.join(baseDir, 'Results', ID, 
                                    'LossAnalysis', 'PelicunOutput', f'IL_{hazard_level}')

            df_pelicun = pd.read_csv(os.path.join(outputDir, 'DL_summary.csv'))
            archetypeID.append(ID)
            mean_repair_cost.append(np.mean(df_pelicun['repair_cost-'].values))
            median_repair_cost.append(np.quantile(df_pelicun['repair_cost-'].values, q=0.5))
            repair_cost_10th_percentile.append(np.quantile(df_pelicun['repair_cost-'].values, q=0.1))
            repair_cost_25th_percentile.append(np.quantile(df_pelicun['repair_cost-'].values, q=0.25))
            repair_cost_75th_percentile.append(np.quantile(df_pelicun['repair_cost-'].values, q=0.75))
            repair_cost_90th_percentile.append(np.quantile(df_pelicun['repair_cost-'].values, q=0.9))
            repair_cost_std.append(np.std(df_pelicun['repair_cost-'].values))
            hazard_level_arr.append(hazard_level)
            sa_val_arr.append(HAZARD_LEVEL[hazard_level - 1])

            edp_df = pd.read_csv(os.path.join(baseDir, 'Results', ID, 'LossAnalysis', 'PelicunInput',
                                            f'demands_IL{hazard_level}.csv'), index_col=0)
            
            pga_columns = ['1-PFA-0-1', '1-PFA-0-2']
            sdr_columns = [col for col in edp_df.columns if 'PID' in col]
            pfa_columns_all = [col for col in edp_df.columns if 'PFA' in col]
            pfa_columns = [x for x in pfa_columns_all if x not in pga_columns]
            rdr_columns = [col for col in edp_df.columns if 'RID' in col]

            max_sdr_profile.append(edp_df[sdr_columns].max().tolist())
            max_pfa_profile.append(list(edp_df[pfa_columns].max() / g))
            max_rdr_profile.append(edp_df[rdr_columns].max().tolist())
            max_pga_profile.append(list(edp_df[pga_columns].max() / g))

            max_sdr.append(max(edp_df[sdr_columns].max().tolist()))
            max_pfa.append(max(list(edp_df[pfa_columns].max() / g)))
            max_rdr.append(max(edp_df[rdr_columns].max().tolist()))
            max_pga.append(max(list(edp_df[pga_columns].max() / g)))

    d = {
        'BuildingID':archetypeID,
        'Replacement_Cost': bldg_value,
        'Mean_Repair_Cost':mean_repair_cost,
        'Median_Repair_Cost':median_repair_cost,
        'RepairCost_10th_percentile':repair_cost_10th_percentile,
        'RepairCost_25th_percentile':repair_cost_25th_percentile,
        'RepairCost_75th_percentile':repair_cost_75th_percentile,
        'RepairCost_90th_percentile':repair_cost_90th_percentile,
        'RepairCost_std':repair_cost_std,
        'Hazard_level':hazard_level_arr,
        'SA(T1=0.3s)': sa_val_arr,
        'Max SDR': max_sdr,
        'Max PFA': max_pfa,
        'Max RDR': max_rdr,
        'Max PGA': max_pga
    }
    d_edp_profile = {
        'BuildingID':archetypeID,
        'Hazard_level':hazard_level_arr,
        'SA(T1=0.3s)': sa_val_arr,
        'Max SDR Profile': max_sdr_profile,
        'Max PFA Profile': max_pfa_profile,
        'Max RDR Profile': max_rdr_profile,
        'Max PGA': max_pga_profile
    }
    df = pd.DataFrame(d)
    df_edp = pd.DataFrame(d_edp_profile)
    finish = time.time()
    print(f'Finished exacting pelicun results in {(finish - start)/60} minutes')
    df.to_csv(os.path.join(baseDir, 'Results', BuildingList[0], f'Loss_pelicun_{ID}.csv'))
    df_edp.to_csv(os.path.join(baseDir, 'Results', BuildingList[0], f'EDP_Profile_{ID}.csv'))


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	# #defining the arguments to be parsed
	parser.add_argument('--run_on_Hoffman', type=bool, default=False)
	# # #parse command-line arguments
	args = parser.parse_args()
	extract_pelicun_results(run_on_Hoffman=args.run_on_Hoffman)