from operator import ge
import numpy as np 
import pandas as pd 
import os 
import json

from pathlib import Path



# def generateLossAnalysisModel(baselineID,
#                               ID, BaseDirectory, planArea, numStories, numRealization = 1000, 
#                                 collapseLimit = 0.1, occupancyType= "Multi-Unit Residential", 
#                                 replacementCost = 50000000, replacementTime = 540):
#     """
#     This function is used to generate loss model for pelicun V2.6
#     """
    
#     component_unit_mapping = {
#                         'SF': 'ft2', 
#                         'LF': 'ft', 
#                         'EA': 'ea'}
#     ModelDirectory = os.path.join(BaseDirectory, *['BuildingModels', ID])
#     # create nested directory
#     Path(os.path.join(ModelDirectory, *['LossAnalysis', 'PelicunInput'])).mkdir(parents=True, exist_ok=True)
#     true, false = True, False

#     fileDir = os.path.join(BaseDirectory, *['Codes', 'Loss_Pelicun'])

#     with open('%s/config_file_default_setting.json'%fileDir, 'r') as fp:
#         d_baseline = json.load(fp)

#     # d_baseline['GeneralInformation']['PlanArea'] = sum(BuildingModel.floorAreas[:BuildingModel.numberOfStories])
#     # d_baseline['GeneralInformation']['NumberOfStories'] = BuildingModel.numberOfStories
#     d_baseline['GeneralInformation']['PlanArea'] = planArea
#     d_baseline['GeneralInformation']['NumberOfStories'] = numStories
#     d_baseline['DamageAndLoss']['ResponseModel']['Realizations'] = "%s"%numRealization
#     d_baseline['DamageAndLoss']['DamageModel']['CollapseLimits']['PID'] = "%s"%collapseLimit
#     d_baseline['DamageAndLoss']['LossModel']['Inhabitants']['OccupancyType'] = "%s"%occupancyType
#     d_baseline['DamageAndLoss']['LossModel']['ReplacementCost'] = "%s"%replacementCost
#     d_baseline['DamageAndLoss']['LossModel']['ReplacementTime'] = "%s"%replacementTime
#     d_baseline['DamageAndLoss']['LossModel']['ReplacementTime'] = "%s"%replacementTime
#     d_baseline['DamageAndLoss']['ComponentDataFolder'] = f"{os.path.join(fileDir, 'FEMA_P58_Fragility_Database_2ed')}"

#     d_temp = {}
#     d_temp['Components'] = {}
#     # cmp_sfd = pd.read_csv(os.path.join(BaseDirectory, *['BuildingInfo',
#     #                                                     baselineID, 
#     #                                                     'ComponentsList', 
#     #                                                     'components_list.csv']))
#     cmp_sfd = pd.read_csv(os.path.join(BaseDirectory, *['BuildingInfo',
#                                                         baselineID, 
#                                                         'ComponentsList', 
#                                                         'components_list_marginals.csv']))
#     for i in range(len(cmp_sfd) - 3): ## 3 is subtracted b/c the new csv contains excessiveRID, collapse, irreparable at the end
#         # d_temp['Components']["%s"%cmp_sfd.ID.values[i]] = [{
#         #                                             "location": cmp_sfd.Location.values[i],
#         #                                             "direction": cmp_sfd.Direction.values[i],
#         #                                             "median_quantity":'%s'%cmp_sfd.Median_Quantity.values[i],
#         #                                             "unit": component_unit_mapping[cmp_sfd.Unit.values[i]],
#         #                                             "distribution": 'N/A' if cmp_sfd.Distribution.isna()[i] else '%s'%cmp_sfd.Distribution.values[i],
#         #                                             "cov": '' if cmp_sfd.COV.isna()[i] else '%s'%cmp_sfd.COV.values[i]
#         #                                             }]
#         d_temp['Components']["%s"%cmp_sfd.cmpID.values[i]] = [{
#                                                     "location": cmp_sfd.Location.values[i],
#                                                     "direction": cmp_sfd.Direction.values[i],
#                                                     "median_quantity":'%s'%cmp_sfd.Theta_0_normalized.values[i],
#                                                     "unit": component_unit_mapping[cmp_sfd.Units.values[i]],
#                                                     "distribution": 'N/A' if cmp_sfd.Family.isna()[i] else '%s'%cmp_sfd.Family.values[i],
#                                                     "cov": '' if cmp_sfd.Theta_1.isna()[i] else '%s'%cmp_sfd.Theta_1.values[i]
#                                                     }]
#     d_baseline['DamageAndLoss'].update(d_temp)

#     # building_name = 'woodSDA_PM_SFD_automated'
#     # file_name = building_name + ".json"

#     output = os.path.join(ModelDirectory, *['LossAnalysis','PelicunInput', 'Loss_model_config.json'])
#     with open(output, 'w') as file:
#         json.dump(d_baseline, file, indent=2)



def generateConfgFile_pelicun3p1new(baselineID,
                    BaseDirectory, planArea, numStories, numRealization = 1000, 
                    collapseLimit = 0.1, 
                    theta_collapse_g = 3.5,
                    demolition_limit=0.05,
                    occupancyType= "Residential", 
                    replacementCost = 50000000, replacementTime = 540,
                    FEMA_residual_est = False):
    """
    This function is used to generate loss model for pelicun V3.1 to run the tool
    """
    
    component_unit_mapping = {
                        'SF': 'ft2', 
                        'LF': 'ft', 
                        'EA': 'ea'}
    
    # ModelDirectory = os.path.join(BaseDirectory, *['BuildingModels', regional_strategy, ID])
    ModelDirectory = os.path.join(BaseDirectory, *['Results', baselineID])
    # create nested directory
    Path(os.path.join(ModelDirectory, *['LossAnalysis', 'PelicunInput'])).mkdir(parents=True, exist_ok=True)
    true, false = True, False

    fileDir = os.path.join(BaseDirectory, *['Codes', 'lossModule', 'Loss_Pelicun'])

    with open(f'{fileDir}/baseline_config_pelicun_3p1new.json', 'r') as fp:
        d_baseline = json.load(fp)

    cmp_fp = os.path.join(BaseDirectory, *['BuildingInfo',
                                            baselineID, 
                                            'ComponentsList', 
                                            'components_list_marginals.csv'])
    # edp_fp = os.path.join(BaseDirectory, *['BuildingInfo',
    #                                         baselineID, 
    #                                         'ComponentsList', 
    #                                         'components_list_marginals.csv'])
    #DL-- Asset
    d_baseline['DL']['Asset']['ComponentAssignmentFile'] = cmp_fp
    d_baseline['DL']['Asset']['ComponentDatabase'] = "FEMA P-58"
    d_baseline['DL']['Asset']['PlanArea'] = "%s"%planArea
    d_baseline['DL']['Asset']['NumberOfStories'] = "%s"%numStories
    d_baseline['DL']['Asset']['OccupancyType'] = "%s"%occupancyType
    #DL-- Damage
    d_baseline['DL']['Damage']['CollapseFragility']["CapacityMedian"] = f"{theta_collapse_g * 386.088}"
    d_baseline['DL']['Damage']['CollapseFragility']["DemandType"] = "SA"
    d_baseline['DL']['Damage']['CollapseFragility']["Theta_1"] = "0.4"
    d_baseline['DL']['Damage']['IrreparableDamage']["DriftCapacityMedian"] = "%s"%demolition_limit
    d_baseline['DL']['Damage']['IrreparableDamage']["DriftCapacityLogStd"] = "0.1"
    #DL -- Demands
    # d_baseline['DL']['Demands']['Calibration']['PID']['TruncateUpper'] = "%s"%collapseLimit
    d_baseline['DL']['Demands']['Calibration']['PID']['TruncateUpper'] = ""
    d_baseline['DL']['Demands']['CollapseLimits']['PID'] = "%s"%collapseLimit
    # d_baseline['DL']['Demands']['DemandFilePath'] = "%s"%edpFilePath
    if FEMA_residual_est:
        d_baseline['DL']['Demands']['InferResidualDrift']["method"] = "FEMA P-58"
        d_baseline['DL']['Demands']['InferResidualDrift']["1"] = "0.0075"
        d_baseline['DL']['Demands']['InferResidualDrift']["method"] = "0.0075"
    else:
        d_baseline['DL']['Demands']['InferResidualDrift'] = ""
    d_baseline['DL']['Demands']['SampleSize'] = "%s"%numRealization
    d_baseline['DL']['Losses']['BldgRepair']['ReplacementCost']['Median'] = "%s"%replacementCost
    d_baseline['DL']['Losses']['BldgRepair']['ReplacementTime']['Median'] = "%s"%replacementTime
    

    output = os.path.join(ModelDirectory, *['LossAnalysis','PelicunInput', 'model_config.json'])
    with open(output, 'w') as file:
        json.dump(d_baseline, file, indent=2)



if __name__ == '__main__':
    # baselineID = 's4_96x48'
    # ID = 's4_96x48_High_Stucco_GWB'
    # baseDirectory = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/SurrogateModeling/DGP/woodSDA'
    # generateLossAnalysisModel(baselineID, ID, baseDirectory, planArea=96*48*2, numStories=2)
    baseDirectory = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/RegionalStudy/woodSDPA'
    baselineID = 's1_40x30'
    # ID = 's2_40x30_Stucco_GWB_Normal_Vs20'
    ID = 's1_40x30_HWS_GWB_Light_Vs13'
    REGIONAL_STRATEGY = 'EA-VaFi'
    generateConfgFile_pelicun3p1new(BaseDirectory=baseDirectory,
            baselineID=baselineID, regional_strategy=REGIONAL_STRATEGY,
                                    ID=ID, planArea=2*40*30, numStories=1,
                                    numRealization=1000, collapseLimit=0.12,
                                    occupancyType='Residential', replacementCost=12000000,
                                    replacementTime=540)
