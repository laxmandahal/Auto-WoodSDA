# This file is used to run PELICUN v3.1. The woodSDA is made compatible with versions 2.6 and 3.1 of Pelicun
# Version 2.6 is used to generate required input data files for ATC-138
# Version 3.1 is much more modularized and is used to compute loss

#author: Laxman Dahal

import os
import sys
import pandas as pd
idx = pd.IndexSlice
import numpy as np 

from pelicun_3_1.base import convert_to_MultiIndex
from pelicun_3_1.assessment import Assessment

edp_name_mapping = {'SDR':'PID',
                    'PFA':'PFA', 
                    'RDR':'RID'}

def compile_demand_data(edp_list, edp_name):

    index_name = []
    median = []
    log_std = []
    for i in range(len(edp_list)):
        baseline_num = 3 if edp_name[i]=='PFA' else 2
        edp = edp_list[i]
        ## filter out collpase casese
        collapse_limit = 3 if edp_name[i]=='PFA' else 1
        
        for stripe in edp[0].unique():
            churn_df = edp[edp[0]==stripe]
            story_name = 0 
            for story in churn_df.columns:
                for uniq_dir in edp[1].unique():
                    edp = edp_list[i][(edp_list[i][story]<= collapse_limit)]
                    if story >=3:
                        story_name = story - baseline_num
                        index_name.append('%s-%s-%s-%s'%(stripe, edp_name_mapping[edp_name[i]], story_name, uniq_dir))
                        median.append(edp[(edp[0]==stripe) & (edp[1]==uniq_dir)][story].median())
                        log_std.append(edp[(edp[0]==stripe) & (edp[1]==uniq_dir)][story].std())
    d = {
        'idx': index_name, 
        'Theta_0': median, 
        'Theta_1': log_std
    }
    df_edp = pd.DataFrame(d)
    df_edp = df_edp.set_index('idx')

    df_edp = convert_to_MultiIndex(df_edp, axis=0)
    df_edp.index.names = ['stripe','type','loc','dir']
    df_edp.insert(0, 'Family',"")
    df_edp['Family'] = 'lognormal'
    return df_edp


def pelicun_assessment1(PAL, baseDir, baselineID, raw_demands, stripe, delta_y=0.0075, sample_size=1000,
                        estimate_RID=True):
    # PAL = Assessment({"PrintLog": False, "Seed": 415,})

    # prepare the demand input for pelicun
    stripe_demands = raw_demands.loc[str(stripe),:]
    
    # units - - - - - - - - - - - - - - - - - - - - - - - -  
    stripe_demands.insert(0, 'Units',"")
    stripe_demands.loc['PFA','Units'] = 'g'
    stripe_demands.loc['PID','Units'] = 'rad'
    if not estimate_RID:
        stripe_demands.loc['RID','Units'] = 'rad'

    temp_theta1 = list(stripe_demands.loc['PID', 'Theta_1'])
    temp_theta0 = list(stripe_demands.loc['PID', 'Theta_0'])
    ## pelicun 3.1 did not perform loss analysis (i.e. it didn't create DV variables).
    ## it turns out, it the SDR demand is too little, 0 DVs are created, to avoid that
    ## lower limit is set for SDR/PID
    for i in range (len(temp_theta1)):
        if temp_theta1[i] <= 0.0002:
            temp_theta1[i] = 0.0002
        if temp_theta0[i]<= 0.0004:
            temp_theta0[i] = 0.0004
    stripe_demands.loc['PID', 'Theta_1'] = temp_theta1
    stripe_demands.loc['PID', 'Theta_0'] = temp_theta0
    
    # prepare a correlation matrix that represents perfect correlation
    ndims = stripe_demands.shape[0]
    demand_types = stripe_demands.index 

    perfect_CORR = pd.DataFrame(
        np.ones((ndims, ndims)),
        columns = demand_types,
        index = demand_types)
    # prepare additional fragility and consequence data ahead of time
    # cmp_marginals = pd.read_csv('CMP_marginals.csv', index_col=0)
    # print(stripe_demands)
    cmp_marginals = pd.read_csv(os.path.join(baseDir, *['BuildingInfo',
                                                        baselineID,
                                                        'ComponentsList',
                                                        'components_list_marginals.csv']), index_col=1)

    # add missing data to P58 damage model
    P58_data = PAL.get_default_data('fragility_DB_FEMA_P58_2nd')
    cmp_list = cmp_marginals.index.unique().values[:-3]

    # now take those components that are incomplete, and add the missing information
    additional_fragility_db = P58_data.loc[cmp_list,:].loc[P58_data.loc[cmp_list,'Incomplete'] == 1].sort_index()

    # prepare the extra damage models for collapse and irreparable damage
    additional_fragility_db.loc[
        'excessiveRID', [('Demand','Directional'),
                        ('Demand','Offset'),
                        ('Demand','Type'), 
                        ('Demand','Unit')]] = [1, 0, 'Residual Interstory Drift Ratio', 'rad']   

    additional_fragility_db.loc[
        'excessiveRID', [('LS1','Family'),
                        ('LS1','Theta_0'),
                        ('LS1','Theta_1')]] = ['lognormal', 0.01, 0.3]   

    additional_fragility_db.loc[
        'irreparable', [('Demand','Directional'),
                        ('Demand','Offset'),
                        ('Demand','Type'), 
                        ('Demand','Unit')]] = [1, 0, 'Peak Spectral Acceleration|1.13', 'g']   

    additional_fragility_db.loc[
        'irreparable', ('LS1','Theta_0')] = 1e10

    additional_fragility_db.loc[
        'collapse', [('Demand','Directional'),
                     ('Demand','Offset'),
                     ('Demand','Type'), 
                     ('Demand','Unit')]] = [1, 0, 'Peak Spectral Acceleration|1.13', 'g']   

    additional_fragility_db.loc[
        'collapse', [('LS1','Family'),
                     ('LS1','Theta_0'),
                     ('LS1','Theta_1')]] = ['lognormal', 1.35, 0.5]  

    # Now we can set the incomplete flag to 0 for these components
    additional_fragility_db['Incomplete'] = 0

    # create the additional consequence models
    additional_consequences = pd.DataFrame(
        columns = pd.MultiIndex.from_tuples([
            ('Incomplete',''), ('Quantity','Unit'), ('DV', 'Unit'), ('DS1', 'Theta_0')]),
        index=pd.MultiIndex.from_tuples([
            ('replacement','Cost'), ('replacement','Time')])
    )

    additional_consequences.loc[('replacement', 'Cost')] = [0, '1 EA', 'USD_2011', 21600000]
    additional_consequences.loc[('replacement', 'Time')] = [0, '1 EA', 'worker_day', 12500]

    # load the demand model
    PAL.demand.load_model({'marginals': stripe_demands,
                           'correlation': perfect_CORR})

    # generate samples
    PAL.demand.generate_sample({"SampleSize": sample_size})

    # add residual drift and Sa
    demand_sample = PAL.demand.save_sample()

    if estimate_RID:
        
        RID = PAL.demand.estimate_RID(demand_sample['PID'], {'yield_drift': delta_y})
        demand_sample_ext = pd.concat([demand_sample, RID], axis=1)

    # Sa_vals = [0.158, 0.387, 0.615, 0.843, 1.071, 1.299, 1.528, 1.756]
    Sa_vals = [0.156, 0.37, 0.628, 0.852, 1.095, 1.34, 1.633, 1.874, 2.111, 2.383]
    demand_sample_ext[('SA_1.13',0,1)] = Sa_vals[stripe-1]

    # add units to the data 
    demand_sample_ext.T.insert(0, 'Units',"")

    # PFA and SA are in "g" in this example, while PID and RID are "rad"
    demand_sample_ext.loc['Units', ['PFA', 'SA_1.13']] = 'g'
    demand_sample_ext.loc['Units',['PID', 'RID']] = 'rad'

    PAL.demand.load_sample(demand_sample_ext)

    # specify number of stories
    # PAL.stories = 4
    PAL.stories = int(baselineID.split('_')[0][1])

    # load component definitions
    # cmp_marginals = pd.read_csv('CMP_marginals.csv', index_col=0)
    PAL.asset.load_cmp_model({'marginals': cmp_marginals})

    # generate sample
    PAL.asset.generate_cmp_sample(sample_size)

    # load the models into pelicun
    PAL.damage.load_damage_model([
        additional_fragility_db,  # This is the extra fragility data we've just created
        'PelicunDefault/fragility_DB_FEMA_P58_2nd.csv' # and this is a table with the default P58 data    
    ])

    # prescribe the damage process
    dmg_process = {
        "1_collapse": {
            "DS1": "ALL_NA"
        },
        "2_excessiveRID": {
            "DS1": "irreparable_DS1"
        }
    }

    # calculate damages
    PAL.damage.calculate(dmg_process=dmg_process)

    # create the loss map
    drivers = [f'DMG-{cmp}' for cmp in cmp_marginals.index.unique()]
    drivers = drivers[:-3]+drivers[-2:]

    loss_models = cmp_marginals.index.unique().tolist()[:-3] +['replacement',]*2

    loss_map = pd.DataFrame(loss_models, columns=['BldgRepair'], index=drivers)

    # load the loss model
    PAL.bldg_repair.load_model(
        [additional_consequences,
         "PelicunDefault/bldg_repair_DB_FEMA_P58_2nd.csv"], 
        loss_map)

    # perform the calculation
    PAL.bldg_repair.calculate()

    # get the aggregate losses
    agg_DF = PAL.bldg_repair.aggregate_losses()
    return agg_DF

if __name__ == '__main__':
    # ID = 's4_96x48_High_Stucco_GWB'
    # baselineID = 's4_96x48'
    # ID = 's3_96x48_Moderate_HWS_GWB_Light'
    # baselineID = 's3_96x48'
    # ID = 's1_40x30_High_Stucco_GWB_Heavy'
    # baselineID = 's1_40x30'
    ID = 'site0_s1_96x48_Stucco_GWB_Normal_Vs32'
    id_str_split = ID.split('_')
    baselineID = '_'.join([id_str_split[1], id_str_split[2]])
    baseDir = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/RegionalStudy/woodSDPA'

    pfa = pd.read_csv(os.path.join(baseDir, *['Results', 'HiFi_FMA', ID, 'EDP_data', 'PFA.csv']), header=None)
    sdr = pd.read_csv(os.path.join(baseDir, *['Results', 'HiFi_FMA', ID, 'EDP_data', 'SDR.csv']), header=None)
    rdr = pd.read_csv(os.path.join(baseDir, *['Results', 'HiFi_FMA', ID, 'EDP_data', 'RDR.csv']), header=None)

    # raw_demands = compile_demand_data([sdr, pfa, rdr], ['SDR', 'PFA', 'RDR'])
    raw_demands = compile_demand_data([sdr, pfa], ['SDR', 'PFA'])
    stripe=1
    PAL = Assessment({"PrintLog": False, "Seed": 415})
    ndf = pelicun_assessment1(PAL, baseDir, baselineID, raw_demands, stripe, delta_y=0.0075, sample_size=1000)
    # print(raw_demands)
    print(ndf.describe())
