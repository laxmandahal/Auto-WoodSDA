import numpy as np
import pandas as pd 
import os 
from pathlib import Path
import seaborn as sns
import matplotlib.pyplot as plt

from typing import List
from scipy.stats import gmean



def plot_edp_MSA_one_building(
    resultDir: str, 
    buildingID: str,
    edp_types: List[str],
    hazard_levels,
    save_fig = False
):

    pfa = pd.read_csv(os.path.join(resultDir, *[buildingID, 'EDP_data', 'PFA.csv']), header=None)
    story_drift = pd.read_csv(os.path.join(resultDir, *[buildingID, 'EDP_data', 'SDR.csv']), header=None)
    residual_drift = pd.read_csv(os.path.join(resultDir, *[buildingID, 'EDP_data', 'RDR.csv']), header=None)

    col_names_drift = ['Hazard_Level', 'Direction', 'GM_ID', 'Story_1', 'Story_2', 'Story_3', 'Story_4']
    col_names_drift_res = ['Hazard_Level', 'Direction', 'GM_ID', 'All Story']
    col_names_pfa = ['Hazard_Level', 'Direction', 'GM_ID', 'PGA', 'Story_1', 'Story_2', 'Story_3', 'Story_4']
    story_drift = story_drift.rename(columns= dict(zip(story_drift.columns, col_names_drift)))
    pfa = pfa.rename(columns = dict(zip(pfa.columns, col_names_pfa)))
    residual_drift = residual_drift.rename(columns= dict(zip(residual_drift.columns, col_names_drift_res)))

    il_and_gms = dict(story_drift['Hazard_Level'].value_counts())
    IM_val_list = []
    for haz_level, num_gm in il_and_gms.items():
        IM_val_list.append([hazard_levels[haz_level-1]] * num_gm)
    
    story_drift['SA(T=0.3s)'] = np.array(IM_val_list).flatten()
    pfa['SA(T=0.3s)'] = np.array(IM_val_list).flatten()
    residual_drift['SA(T=0.3s)'] = np.array(IM_val_list).flatten()

    sdr_long = pd.melt(story_drift, id_vars=['Hazard_Level', 'Direction', 'GM_ID', 'SA(T=0.3s)'],
                       var_name='Story', 
                       value_name='SDR')
    pfa_long = pd.melt(pfa, id_vars=['Hazard_Level', 'Direction', 'GM_ID', 'SA(T=0.3s)'],
                       var_name='Story', 
                       value_name='PFA')
    rdr_long = pd.melt(residual_drift, id_vars=['Hazard_Level', 'Direction', 'GM_ID', 'SA(T=0.3s)'],
                       var_name='Story', 
                       value_name='RDR')


    edp_naming_mapping = {
        'SDR': 'Story Drift Ratio (in/in)',
        'PFA': 'Peak Floor Acceleration (g)',
        'RDR': 'Residual Drift Ratio (in/in)'
    }
    edp_ylim_max = {
        'SDR': 0.1,
        'PFA': 2.5,
        'RDR': 0.05
    }
    # fig, ax = plt.subplots(1,1, figsize=(8,6))
    if len(edp_types) == 1:
        fig, ax = plt.subplots(1, len(edp_types), figsize=(8,6))
    else:
        fig, ax = plt.subplots(1, len(edp_types), figsize=(len(edp_types)*6,6.5))

    plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams['xtick.labelsize'] = 12
    plt.rcParams['ytick.labelsize'] = 12

    edp_dict_long = {
        'SDR': sdr_long,
        'PFA': pfa_long,
        'RDR': rdr_long
    }

    if len(edp_types) > 1:
        for i in range(len(edp_types)):

            sns.scatterplot(data=edp_dict_long[edp_types[i]],
                        x='SA(T=0.3s)', 
                        y=f'{edp_types[i]}', 
                        hue='Story', 
                        style='Story',
                        ax = ax[i],
                        legend=True
                        )
            ax[i].set_ylabel(f'{edp_naming_mapping[edp_types[i]]}', fontsize=15)
            # ax[i].set_ylim(ymin=0,
            #             ymax=np.min([edp_ylim_max[edp_types[i]], edp_dict_long[edp_types[i]][f'{edp_types[i]}'].max()])+0.05)
                        # ymax = 0.1)
            ax[i].set_ylim(ymin=0,
                            ymax=edp_ylim_max[edp_types[i]])
            ax[i].grid(linewidth =0.3)
            ax[i].set_xticks(hazard_levels)
            ax[i].set_xticklabels([f'{i}' for i in hazard_levels], rotation=(90), fontsize=12, ha='left')
            ax[i].set_xlabel('Intensity Measure, SA(T1=0.3s)', fontsize=15)
    else:
        sns.scatterplot(data=edp_dict_long[edp_types[i]],
                        x='SA(T=0.3s)', 
                        y=f'{edp_types[0]}', 
                        hue='Story', 
                        style='Story',
                        ax = ax,
                        legend=True
                        )
        ax.set_ylabel(f'{edp_naming_mapping[edp_types[0]]}', fontsize=15)
        # ax.set_ylim(ymin=0,
        #             ymax=np.min([edp_ylim_max[edp_types[i]], edp_dict_long[edp_types[i]][f'{edp_types[i]}'].max()])+0.05)
        ax[i].set_ylim(ymin=0,
                            ymax=edp_ylim_max[edp_types[i]])
        ax.grid(linewidth =0.3)
        ax.set_xticks(hazard_levels)
        ax.set_xticklabels([f'{i}' for i in hazard_levels], rotation=(90), fontsize=12, ha='left')
        ax.set_xlabel('Intensity Measure, SA(T1=0.3s)', fontsize=15)
        
    fig.suptitle(f'Max EDP {buildingID}', fontsize=20, fontweight='heavy')
    plt.tight_layout()
    
    if save_fig:
        output_fp = os.path.join(resultDir, *[buildingID, 'EDP_plots'])
        Path(output_fp).mkdir(parents=True, exist_ok=True)
        plt.savefig(os.path.join(output_fp, 
                                 f'scatterplot_{len(edp_types)}EDPs.png'))
        plt.close()
    else:
        plt.show()



if __name__ == '__main__':
    resultDir = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/RegionalStudy/woodSDPA/Results/EA-VaFi'
    hazard_levels = [0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0, 1.2, 1.5, 1.8, 2.0, 2.5] #units: g

    # ID = 's2_40x30_Stucco_GWB_Normal_Vs20'
    # plot_edp_MSA_one_building(resultDir=resultDir, buildingID=ID,
    #                                edp_types=['SDR', 'PFA', 'RDR'],
    #                                 hazard_levels=hazard_levels)
    
    REGIONAL_STRATEGY = 'EA-VaFi'
    #batch producing plots for all the archetypes
    cwd = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/RegionalStudy/woodSDPA'
    BuildingList = np.genfromtxt(os.path.join(cwd, 'BuildingModels', 'ID_for_NRHA',
                                          f'ArchetypeIDs_for_NRHA_{REGIONAL_STRATEGY}.txt'), dtype=str)
    for ID in BuildingList:
        plot_edp_MSA_one_building(resultDir=resultDir, buildingID=ID,
                                    edp_types=['SDR', 'PFA', 'RDR'],
                                        hazard_levels=hazard_levels,
                                        save_fig=True)
    
    print('done')