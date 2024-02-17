import os
import numpy as np 
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List
from pathlib import Path
import json

HAZARD_LEVELS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0] #units: g
HAZARD_LEVEL = [0.1, 0.3, 0.5, 0.7, 0.9, 1.1, 1.3, 1.5, 1.7, 1.9, 2.1, 2.3, 2.5, 2.7, 2.9, 3.1, 3.3, 3.5] #units: g

from smoothing_function import smooth_list_mean, smooth_list


def plot_pelicun_loss_all_bldg(
    df_fp: str, 
    loss_type: str='Median_Repair_Cost',
    summary_stats: str = 'Mean', 
    save_fig:bool = False,
    file_name:str = 'all_bldg'
):
    

    df = pd.read_csv(os.path.join(df_fp, f'Loss_pelicun_{regional_strategy}_N609.csv'))
    hazard_vals = [0.1, 0.3, 0.5, 0.7, 0.9, 1.1, 1.3, 1.5, 1.7, 1.9, 2.1, 2.3, 2.5, 2.7, 2.9, 3.1, 3.3, 3.5] #units: g
    
    layoutID = []
    numStory = []
    typ_floor_area = []
    occup_type = []
    replacement_cost = []
    for i in range(len(df)):    
        split_str = df['BuildingID'].values[i].split('_')
        baselineID = '_'.join([split_str[0], split_str[1]])
        layoutID.append(baselineID)
        num_story = int(split_str[0][1])
        numStory.append(num_story)
        geom_str = split_str[1].split('x')
        floor_area = int(geom_str[0]) * int(geom_str[1])
        typ_floor_area.append(floor_area)
        if baselineID in ['s1_40x30', 's1_48x32', 's2_40x30', 's2_40x30']:
            replacement_cost.append(450 * floor_area * num_story)
            occup_type.append('Single-Unit Residential')
        else:
            replacement_cost.append(387 * floor_area * num_story)
            occup_type.append('Multi-Unit Residential')
    df['Layout ID'] = layoutID
    df['Num Story'] = numStory
    df['Typ Floor Area'] = typ_floor_area
    df['Occupancy Type'] = occup_type
    df['Replacement Cost'] = replacement_cost
    df['Median Loss Ratio'] = df['Median_Repair_Cost'] / df['Replacement Cost']

    ylabel_mapping = {
        'Median_Repair_Cost': 'Median Repair Loss (in USD)',
        'Median Loss Ratio': 'Median Loss Ratio (SEL)'
    }

    fig, ax = plt.subplots(figsize=(8,6))
    plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams['xtick.labelsize'] = 12
    plt.rcParams['ytick.labelsize'] = 12

    sns.lineplot(data=df, x='Hazard_level', y=loss_type,
                errorbar=None, hue=None,
                markers=False, dashes=False, lw = 0.5, units='BuildingID', estimator=None, color='grey',
                ax=ax)

    if summary_stats.lower() in ['mean', 'average', 'avg']:
        ax.plot(df['Hazard_level'].unique(), df.groupby('Hazard_level').mean(numeric_only=True)[loss_type].values, 
                linewidth = 2, color='r', label='Mean')
    elif summary_stats.lower() in ['median', '50th percentile']:
        ax.plot(df['Hazard_level'].unique(), df.groupby('Hazard_level').median(numeric_only=True)[loss_type].values, 
                linewidth = 2, color='r', label='Median')
    else:
        raise ValueError('The entered Summary Statistics is currently not supported. Valid options are: [Mean, Median]')
    
    ax.set_ylabel(ylabel_mapping[loss_type], fontsize=15)
    ax.set_xticks(df['Hazard_level'].unique())
    ax.set_xticklabels([f'{i}' for i in hazard_vals], rotation=(90), fontsize=12, ha='left')

    ax.set_xlabel('Intensity Measure, SA(T1=0.3s)', fontsize=15)
    ax.grid(linewidth=0.3)
    plt.legend(fontsize=13)
    fig.suptitle('Expected Repair Cost of 609 EA-VaFi Archetypes',
                fontsize = 18, fontweight='heavy')
    plt.tight_layout()
    
    if save_fig:
        output_fp = os.path.join(df_fp, *[regional_strategy, '_summary', 'Loss_pelicun'])
        Path(output_fp).mkdir(parents=True, exist_ok=True)
        plt.savefig(os.path.join(output_fp, 
                                 f'lineplot_{loss_type}_{file_name}with{summary_stats}.png'))
        plt.close()
    else:
        plt.show()


def plot_act138_loss_all_bldg(
    df_fp: str,
    plot_recovery_time: List[str]=['Reoccupancy', 'Functional Recovery'],
    filter_by: str=None,
    smooth_values:bool = True,
    input_statistics = 'Median',
    regional_strategy: str='EA-VaFi',
    summary_stats: str = 'Mean', 
    save_fig:bool = False,
    file_name:str = 'all_bldg'
):
    
    df = pd.read_csv(os.path.join(df_fp, f'ATC_Times_{regional_strategy}_N609_30GMs.csv'))
    # df = pd.read_csv(os.path.join(df_fp, f'ATC_Times_{regional_strategy}_N609_normalized.csv'))
    if smooth_values:
        fr_smooth = []
        ro_smooth = []
        for bldg_id in df['BuildingID'].unique():
            ro_smooth.append(smooth_list(df[df['BuildingID']==bldg_id]['Median Reoccupancy'].values))
            fr_smooth.append(smooth_list(df[df['BuildingID']==bldg_id]['Median Functional Recovery'].values))
            # ro_smooth.append(smooth_list_mean(df[df['BuildingID']==bldg_id]['Median Reoccupancy'].values))
            # fr_smooth.append(smooth_list_mean(df[df['BuildingID']==bldg_id]['Median Functional Recovery'].values))
        df['Smooth Median Functional Recovery'] = np.array(fr_smooth).flatten()
        df['Smooth Median Reoccupancy'] = np.array(ro_smooth).flatten()
    
    if len(plot_recovery_time) == 1:
        fig, ax = plt.subplots(1, len(plot_recovery_time), figsize=(8,6))
    else:
        fig, ax = plt.subplots(1, len(plot_recovery_time), figsize=(len(plot_recovery_time)*7,6))
    plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams['xtick.labelsize'] = 12
    plt.rcParams['ytick.labelsize'] = 12

    hazard_levels = list(df['Hazard_level'].unique())
    hazard_vals = [0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0] #units: g
    if len(plot_recovery_time) > 1:
        for i in range(len(plot_recovery_time)):
            if smooth_values:
                sns.lineplot(data = df, x = 'Hazard_level', 
                            #  y = f'{input_statistics} {plot_recovery_time[i]}',
                            y=f'Smooth {input_statistics} {plot_recovery_time[i]}',
                            hue=None, markers=False, dashes=False, lw = 0.5,
                            units='BuildingID', estimator=None, color='grey',
                            errorbar=None, ax=ax[i])
            else:
                sns.lineplot(data = df, x = 'Hazard_level', 
                             y = f'{input_statistics} {plot_recovery_time[i]}',
                            hue=None, markers=False, dashes=False, lw = 0.5,
                            units='BuildingID', estimator=None, color='grey',
                            errorbar=None, ax=ax[i])

            ax[i].set_ylabel(f'{input_statistics} {plot_recovery_time[i]} (days)', fontsize=14)
            # ax[i].set_ylim(ymin=min(df['Median Functional Recovery'].min()) - 10,
            #             ymax=max(df['Median Functional Recovery'].max())+10)
                        # ymax = 350)
            ax[i].grid(linewidth =0.3)
            ax[i].set_xticks(hazard_levels)
            ax[i].set_xticklabels([f'{i}' for i in hazard_vals], rotation=(90), fontsize=10, ha='left')
            ax[i].set_xlabel('Intensity Measure, SA(T1=0.3s)', fontsize=14, labelpad=15)
            # plt.setp(ax[i].get_legend().get_title(), fontsize='14')
            # ax[i].get_legend().remove()
            if summary_stats.lower() in ['mean', 'average', 'avg']:
                ax[i].plot(df['Hazard_level'].unique(), df.groupby('Hazard_level').mean(numeric_only=True)[f'{input_statistics} {plot_recovery_time[i]}'].values, 
                        linewidth = 2, color='r', label='Mean')
            elif summary_stats.lower() in ['median', '50th percentile']:
                ax[i].plot(df['Hazard_level'].unique(), df.groupby('Hazard_level').median(numeric_only=True)[f'{input_statistics} {plot_recovery_time[i]}'].values, 
                        linewidth = 2, color='r', label='Median')
            else:
                raise ValueError('The entered Summary Statistics is currently not supported. Valid options are: [Mean, Median]')

    else:
        sns.lineplot(data = df, x = 'Hazard_level', y = 'Median %s'%plot_recovery_time[0], 
                    hue=None, markers=False, dashes=False, lw = 0.5,
                    units='ID', estimator=None, color='grey',
                    errorbar=None, ax=ax)

        ax.set_ylabel(f'{input_statistics} {plot_recovery_time[i]} (days)', fontsize=14)
        # ax[0][0].set_xlabel('Return Periods (years)', fontsize=17)
        # ax.set_ylim(ymin=min(df['Median Functional Recovery'].min()) - 10,
        #             ymax=max(df['Median Functional Recovery'].max())+10)
        ax.grid(linewidth =0.5)
        ax.set_xticks(hazard_levels)
        ax.set_xticklabels([f'{i}' for i in hazard_levels], rotation=(90), fontsize=12, ha='left')
        ax.set_xlabel('Intensity Measure, SA(T1=0.3s)', fontsize=15)
        plt.setp(ax.get_legend().get_title(), fontsize='14')
        ax.get_legend().remove()

   
    fig.suptitle('Expected Recovery Time of 609 EA-VaFi Archetypes',
                 fontsize = 18, fontweight='heavy')
    
    plt.legend(bbox_to_anchor=(1.02, 1), fontsize=14, borderaxespad=0.)
    plt.tight_layout()
    
    if save_fig:
        output_fp = os.path.join(df_fp, *[regional_strategy, '_summary', 'Loss_atc138'])
        Path(output_fp).mkdir(parents=True, exist_ok=True)
        plt.savefig(os.path.join(output_fp, 
                                 f'lineplot_{file_name}with{summary_stats}.png'))
        plt.close()
    else:
        plt.show()


def plot_components_breakdown(
    result_dir: str,
    regional_strategy: str,
    buildingID: str,
    hazard_level: int,
    recovery_time_type: str,
    plot_type: str = 'boxplot',
    save_fig: bool = False
):
    
    recovery = json.load(open(os.path.join(result_dir, 
                                           regional_strategy,
                                           buildingID, 'LossAnalysis',
                                           'ATC138Output',
                                           f'IL_{hazard_level}',
                                           'recovery_outputs.json')))
    comp_ds_df = pd.read_csv(os.path.join(result_dir, regional_strategy,
                                           buildingID, 'LossAnalysis',
                                           'ATC138Input',
                                           f'IL_{hazard_level}',
                                           'comp_ds_list.csv'))
    comp_name_ds = [f"{comp_ds_df['comp_id'].values[i]}_{comp_ds_df['ds_seq_id'].values[i]}_{comp_ds_df['ds_sub_id'].values[i]}" for i in range(len(comp_ds_df))]
    comp_breakdown = recovery['recovery'][recovery_time_type.lower()]['breakdowns']['component_breakdowns_all_reals']
    # comp_names = recovery['recovery'][recovery_time_type.lower()]['breakdowns']['comp_names']
    bldg_level_days_ = recovery['recovery'][recovery_time_type.lower()]['building_level']['recovery_day']

    fig, ax = plt.subplots(figsize=(8,6))
    plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams['xtick.labelsize'] = 12
    plt.rcParams['ytick.labelsize'] = 12

    if plot_type.lower() in ['boxplot', 'box plot']:
        sns.boxplot(data=np.array(comp_breakdown), ax=ax)
    elif plot_type.lower() in ['barplot', 'bar plot']:
        sns.barplot(data=np.array(comp_breakdown), ax=ax, estimator=np.median)
    else:
        raise ValueError('Invaldi plot type. Valid options: [boxplot, barplot]')

    ax.set_xticklabels(comp_name_ds, rotation=(90), fontsize=8, ha='left')
    ax.set_xlabel('Component IDs', labelpad=15, fontsize=12)
    ax.set_ylabel(f'Realizations of {recovery_time_type} days', fontsize=12)
    plt.title(f"ID: {buildingID} @ SA = {HAZARD_LEVELS[hazard_level-1]}g - Output Median days: {np.median(bldg_level_days_)}")
    plt.tight_layout()
    plt.show()


def components_breakdown_table(
    result_dir: str,
    regional_strategy: str,
    buildingID: str,
    hazard_level: int,
    recovery_time_type: str,
    save_fig: bool = False
):
    
    recovery = json.load(open(os.path.join(result_dir, 
                                           regional_strategy,
                                           buildingID, 'LossAnalysis',
                                           'ATC138Output',
                                           f'IL_{hazard_level}',
                                           'recovery_outputs.json')))
    # comp_ds_df = pd.read_csv(os.path.join(result_dir, regional_strategy,
    #                                        buildingID, 'LossAnalysis',
    #                                        'ATC138Input',
    #                                        f'IL_{hazard_level}',
    #                                        'comp_ds_list.csv'))
    # comp_name_ds = [f"{comp_ds_df['comp_id'].values[i]}_{comp_ds_df['ds_seq_id'].values[i]}_{comp_ds_df['ds_sub_id'].values[i]}" for i in range(len(comp_ds_df))]
    comp_breakdown = recovery['recovery'][recovery_time_type.lower()]['breakdowns']['component_breakdowns']
    comp_names = recovery['recovery'][recovery_time_type.lower()]['breakdowns']['comp_names']
    targ_days = recovery['recovery'][recovery_time_type.lower()]['breakdowns']['perform_targ_days']
    bldg_level_days_ = recovery['recovery'][recovery_time_type.lower()]['building_level']['recovery_day']
    df = pd.DataFrame(data=comp_breakdown, index= comp_names, columns=targ_days)
    fig, ax = plt.subplots(figsize=(8,6))
    plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams['xtick.labelsize'] = 12
    plt.rcParams['ytick.labelsize'] = 12
    sns.heatmap(df, annot=True, cmap='Reds', linewidths=0.5, 
                    fmt=".2f", cbar=False, ax=ax)
    ax.set_xticklabels(ax.get_xticklabels(), weight='bold')
    ax.set_yticklabels(ax.get_yticklabels(), weight='bold')
    ax.set_xlabel(f'Percent of Realizations affecting building {recovery_time_type}', fontsize=14)
    # ax.xaxis.tick_top()  # X-axis labels on top
    # ax.set_ylabel('FEMA Component ID', fontsize=16)

    fig.suptitle(f"ID: {buildingID} @ SA = {HAZARD_LEVELS[hazard_level-1]}g - Output Median days: {np.median(bldg_level_days_)}",
                 fontweight='heavy', fontsize=14)
    plt.tight_layout()
    plt.show()



if __name__ == '__main__':
    result_dir = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/RegionalStudy/woodSDPA/Results'
    # plot_pelicun_loss_all_bldg(result_dir, save_fig=False, summary_stats='Mean', loss_type='Median Loss Ratio')
    plot_act138_loss_all_bldg(result_dir, input_statistics='Median', save_fig=False, summary_stats='Mean',
                              smooth_values=False)
    # ID = 's1_40x30_HWS_GWB_Heavy_Vs11'
    # plot_components_breakdown(result_dir, 'EA-VaFi', ID, hazard_level=13, recovery_time_type='Functional',
    #                           plot_type='boxplot')
    # components_breakdown_table(result_dir, 'EA-VaFi', ID, hazard_level=11, recovery_time_type='Reoccupancy')
