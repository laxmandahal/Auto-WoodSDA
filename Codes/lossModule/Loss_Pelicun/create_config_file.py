import numpy as np 
import pandas as pd 
import os 
import json



def create_performance_model(inputDir, outputDir):
    component_unit_mapping = {
                        'SF': 'ft2', 
                        'LF': 'ft', 
                        'EA': 'ea'}
    true = True
    false = False
    d_baseline = {
                "GeneralInformation": {
                    "PlanArea": 3600.0,
                    "NumberOfStories": 2,
                    "units": {
                        "force": "kip",
                        "length": "ft",
                        "temperature": "C",
                        "acceleration": "g",
                        "time": "sec"
                    }
                },
                "DamageAndLoss": {
                    "_method": "FEMA P58",
                    "ResponseModel": {
                        "ResponseDescription": {
                            "EDP_Distribution": "lognormal",
                            "BasisOfEDP_Distribution": "all results",
                            "Realizations": "1000"
                        },
                        "AdditionalUncertainty": {
                            "GroundMotion": "",
                            "Modeling": ""
                        },
                        "DetectionLimits":{
                            "PID": "0.15",
                            "PFA": ""
                        }
                        
                    },
                    "DamageModel": {
                        "IrreparableResidualDrift": {
                            "Median": "10.",
                            "Beta": "0.0001"
                        },
                        "CollapseLimits": {
                            "PID": "10.10"
                        },
                        "CollapseProbability": {
                            "Value": "estimated",
                            "BasisOfEstimate": "sampled EDP"
                        }
                    },
                    "LossModel": {
                        "ReplacementCost": "50000000",
                        "ReplacementTime": "540",
                        "DecisionVariables": {
                            "Injuries": true,
                            "ReconstructionCost": true,
                            "ReconstructionTime": true,
                            "RedTag": true
                        },
                        "Inhabitants": {
                            "OccupancyType": "Multi-Unit Residential",
                            "PeakPopulation": "10, 10",
                            "PopulationDataFile": ""
                        }
                    },
                    "Dependencies":{
                        "CostAndTime": false,
                        "Fragilities": "per ATC recommendation",
                        "Injuries": "Independent",
                        "InjurySeverities": false,
                        "Quantities": "Independent",
                        "ReconstructionCosts": "Independent",
                        "ReconstructionTimes": "Independent",
                        "RedTagProbabilities": "Independent"
                    },
                    "CollapseModes": [
                        {
                            "affected_area": "1.0",
                            "injuries": "0.1, 0.9",
                            "name": "complete",
                            "weight": "1.0"
                        }
                    ],
                    "ComponentDataFolder": "/Users/laxmandahal/Desktop/UCLA/Phd/Research/woodSDA/PELICUN/pelicun-2.0.0/pelicun/resources/FEMA P58 second edition/DL json",
                #       "ComponentDataFolder": "/Users/laxmandahal/Desktop/UCLA/Phd/Research/woodSDA/PELICUN/pelicun-2.6/pelicun/resources/FEMA_P58_2nd_ed.hdf",
                }
                }
    d_temp = {}
    d_temp['Components'] = {}
    cmp_sfd = pd.read_csv('components_list_SFD.csv')
    for i in range(len(cmp_sfd)):
        print(cmp_sfd.ID.values[i])
        d_temp['Components']["%s"%cmp_sfd.ID.values[i]] = [{
                                                    "location": cmp_sfd.Location.values[i],
                                                    "direction": cmp_sfd.Direction.values[i],
                                                    "median_quantity":'%s'%cmp_sfd.Median_Quantity.values[i],
                                                    "unit": component_unit_mapping[cmp_sfd.Unit.values[i]],
                                                    "distribution": 'N/A' if cmp_sfd.Distribution.isna()[i] else '%s'%cmp_sfd.Distribution.values[i],
                                                    "cov": '' if cmp_sfd.COV.isna()[i] else '%s'%cmp_sfd.COV.values[i]
                                                    }]
    d_baseline['DamageAndLoss'].update(d_temp)

    # os.chdir(storage_path)
    building_name = 'woodSDA_PM_SFD_automated'
    file_name = building_name + ".json"
    with open(file_name, 'w') as file:
        json.dump(d_baseline, file, indent=2)

   

# if __name__ == '__main__':
    # inputDir = r'C:\Users\Laxman\Desktop\PBEE-Recovery-ubc_study\inputs\woodSDA_2story\pelicun_results'
    # outputDir = r'C:\Users\Laxman\Desktop\PBEE-Recovery-ubc_study\inputs\woodSDA_2story'

    # df = create_comp_ds_from_DMG(inputDir, outputDir)