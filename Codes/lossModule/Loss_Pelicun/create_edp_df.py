import pandas as pd
import os



def create_demands_df_pelicun(resultDir, buildingID, hazard_level, IM_value,
                              keep_pfa_unit_g=False):
    '''This function generates EDP demands dataframe that is compatible with Pelicun.
    
    Args:
        resultDir (str): Directory to the results folder where outputs from different modules are saved
                        for each archetype
        buildingID (str): archetype of building ID
        hazardLevel (int): hazard level at which loss analysis is to be performed. Pelicun call this "stripe"
    
    Note: This function only works for four-story building or shorter
    '''

    g = 386.088 ## unit: in/s^2
    pfa = pd.read_csv(os.path.join(resultDir, *[buildingID, 'EDP_data', 'PFA.csv']), header=None)
    if not keep_pfa_unit_g:
        # for i in range(3, pfa.shape[1]):
        pfa.iloc[:,3:] = pfa.iloc[:,3:] * g #converting the unit to in/s2
    sdr = pd.read_csv(os.path.join(resultDir, *[buildingID, 'EDP_data', 'SDR.csv']), header=None)
    rdr = pd.read_csv(os.path.join(resultDir, *[buildingID, 'EDP_data', 'RDR.csv']), header=None)
    # pfa = pd.read_csv(os.path.join(resultDir, *['edp_outputs', buildingID, 'PFA.csv']), header=None)
    # sdr = pd.read_csv(os.path.join(resultDir, *['edp_outputs', buildingID, 'SDR.csv']), header=None)
    # rdr = pd.read_csv(os.path.join(resultDir, *['edp_outputs', buildingID, 'RDR.csv']), header=None)
    col_names_drift = ['IM', 'Direction', 'GM_ID', 'Story_1', 'Story_2', 'Story_3', 'Story_4']
    col_names_pfa = ['IM', 'Direction', 'GM_ID', 'Story_0', 'Story_1', 'Story_2', 'Story_3', 'Story_4']
    sdr = sdr.rename(columns= dict(zip(sdr.columns, col_names_drift)))
    pfa = pfa.rename(columns = dict(zip(pfa.columns, col_names_pfa)))
    rdr = rdr.rename(columns= dict(zip(rdr.columns, col_names_drift)))

    edp_list = [sdr, pfa, rdr]
    edp_name = ['PID', 'PFA', 'RID']
    # hazard_level = 3
    # hazard_level = hazardLevel
    d = {}
    for i in range(len(edp_list)):
        for j in range(len(edp_list[i].columns) - 3):
            for k in edp_list[i].Direction.unique():
                if edp_name[i] == "PFA":
                    collapse_trigger = 4 * g
                    col_name = '1-%s-%s-%s'%(edp_name[i], j, k)
                    level = j
                else:
                    collapse_trigger = 1
                    col_name = '1-%s-%s-%s'%(edp_name[i], (j+1), k)
                    level = j + 1
                ### replacing the cases that have excessively high edp values with 90th percentile
                edp_list[i].loc[(edp_list[i]['Direction']==k) & 
                                (edp_list[i]['Story_%s'%level] > collapse_trigger), 'Story_%s'%level] = edp_list[i]['Story_%s'%level].quantile(q=0.9)
                d[col_name] = edp_list[i][(edp_list[i]['IM']==hazard_level) 
                                        & (edp_list[i]['Direction']==k)]['Story_%s'%level].values
            
    df = pd.DataFrame(d)
    df['1-SA-0-1'] = IM_value
    df.to_csv(os.path.join(resultDir, *[buildingID, f'demands_IL{hazard_level}.csv']))

    return df

if __name__ == '__main__':
    # resultDir = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/RegionalStudy/Codes/woodSDPA/Results/HiFi_FMA'
    # ID = 'site0_s1_96x48_Stucco_GWB_Normal_Vs32'
    resultDir = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/RegionalStudy/woodSDPA/Results/EA-VaFi'
    ID = 's2_40x30_Stucco_GWB_Normal_Vs20'
    aa = create_demands_df_pelicun( resultDir=resultDir, buildingID=ID, hazard_level=1, IM_value=[0.1]*20)
    print(aa.head())
    