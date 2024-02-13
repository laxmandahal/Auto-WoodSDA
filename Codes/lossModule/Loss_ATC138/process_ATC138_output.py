import numpy as np 
import pandas as pd 
import os 
import json
from pathlib import Path


baseDir = r'/u/home/l/laxmanda/project-hvburton/Regional_study/woodSDPA/'
# baseDir = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/RegionalStudy/Codes/woodSDPA'

buildingIDs = np.genfromtxt(os.path.join(baseDir, 'Codes', 'ArchetypeIDs_for_NRHA.txt'), dtype=str)
#print(buildingIDs[0])


mean_fr_time_all = []
std_fr_time_all = []
median_fr_time_all = []
percentile_25_fr = []
percentile_75_fr = []
percentile_90_fr = []
caseID = []
mean_reoccup_time_all = []
std_reoccup_time_all = []
median_reoccup_time_all = []
percentile_25_reoccup = []
percentile_75_reoccup = []
percentile_90_reoccup = []


for i in range(len(buildingIDs)):
    ID = buildingIDs[i]
    print(ID)
    outputDir = os.path.join(baseDir, 'BuildingModels', ID, 'LossAnalysis', 'ATC138Output')

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
    mean_reoccup_time_all.append(np.mean(reoccupancy_time))
    std_reoccup_time_all.append(np.std(reoccupancy_time))
    median_reoccup_time_all.append(np.median(reoccupancy_time))
    percentile_25_reoccup.append(np.quantile(reoccupancy_time, q=0.25))
    percentile_75_reoccup.append(np.quantile(reoccupancy_time, q=0.75))
    percentile_90_reoccup.append(np.quantile(reoccupancy_time, q=0.90))

d = {'ID': caseID,
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
     '90th percentile Reoccupancy': percentile_90_reoccup
}
df = pd.DataFrame(d)
df.to_csv(os.path.join(baseDir, 'Codes', 'ATC_Times_HiFi_N200.csv'))
