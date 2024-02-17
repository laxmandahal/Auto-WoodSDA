# Import packages
import sys
import numpy as np
import time
import os
import pandas as pd
from pathlib import Path
from BuildingModelDynamic import BuildingModelDynamic


start0 = time.time()

# baseDir = r'/u/home/l/laxmanda/project-hvburton/IM_study/ATC116_archetypes'
# baseDir = r'/u/home/l/laxmanda/project-hvburton/Regional_study/woodSDA/'
# absDir = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/woodSDA/autoWoodSDA_public'
absDir = r'/u/home/l/laxmanda/project-hvburton/autoWoodSDA/'
baseDir = r'/u/home/l/laxmanda/project-hvburton/autoWoodSDA/BuildingModels/'
sys.path.append(baseDir)

# Use environment variable to realize parallel computing  
# seed = int(os.getenv('SGE_TASK_ID'))

# REGIONAL_STRATEGY = 'EA-VaFi'
#with open(os.path.join(baseDir, 'Codes', 'ArchetypeIDs_fourStory.txt'), 'r') as f:
#AtchetypeIDs_sampled_N_20 contains 20 archetypes randomly sampled to determine runtime for HiFi FMA
# get node ids and size

BuildingList = np.genfromtxt(os.path.join(absDir, 'BuildingModels',
                                          f'BuildingNames_woodSDATest.txt'), dtype=str)
BuildingList = ['MFD6B']

# HazardLevel = np.array([0.1, 0.3, 0.5, 0.7, 0.9, 1.1, 1.3, 1.5, 1.7, 1.9, 2.1, 2.3, 2.5, 2.7, 2.9, 3.1, 3.3, 3.5])
# NumGM = np.array([22] * len(HazardLevel), dtype=int) * 2 #should be multiplied by 2 if GMs are flipped 

HazardLevel = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0])
NumGM = np.array([30] * len(HazardLevel), dtype=int) * 2 #should be multiplied by 2 if GMs are flipped 
# NumGM = np.array([20] * len(HazardLevel), dtype=int)

# HazardLevel = np.array([0.156])

# NumGM = np.array([20], dtype=int)
CollapseCriteria = 0.1
DemolitionCriteria = 0.02

site_agnostic_GM_fp = r'/u/home/l/laxmanda/project-hvburton/Regional_study/'
ResultsDir = os.path.join(absDir, 'Results')
# gmDir = os.path.join(baseDir, *['GM_sets', 'FEMAP695_FarFault_ATC116Model'])
gmDir = os.path.join(site_agnostic_GM_fp, *['NGAWest2_database','Processed'])
sys.path.append(gmDir)

modelDir = os.path.join(absDir, 'BuildingModels')
sys.path.append(modelDir)
Path(ResultsDir).mkdir(parents=True, exist_ok=True)

#ProjectName = 'Sampled_four_story'
# ProjectName = 'test_E2E'
# projectDir = os.path.join(ResultsDir, ProjectName)
# Path(projectDir).mkdir(parents=True, exist_ok=True)
is_gm_P695 = False

for i in range(1, len(BuildingList) + 1):
	start = time.time()
	#for i in range(1,2):
	# for i in range(seed, seed + 1):
	# Define inputs for post processing
	# Make sure to check the case name, number of story, hazard level and number of ground motions to match the current project
	ID = BuildingList[i-1]
	print(ID)
    
	NumStory = 4
	# NumStory = int(BuildingList[i-1].split('_')[1][1])

	# Perform post processing
	ModelResults = BuildingModelDynamic(CaseID=ID, 
			modelDir=modelDir,
			gm_hist_dir=gmDir,
			NumStory=NumStory, 
			HazardLevel=HazardLevel, 
			NumGM=NumGM, 
			CollapseCriteria=CollapseCriteria, 
			DemolitionCriteria=DemolitionCriteria,
			gm_FEMA_P695=False)


	# resultsDir_buildingID = os.path.join(projectDir, ID)
	resultsDir_buildingID = os.path.join(ResultsDir, ID)
	# Path(resultsDir_buildingID).mkdir(parents=True, exist_ok=True)
	Path(os.path.join(resultsDir_buildingID, 'EDP_data')).mkdir(parents=True, exist_ok=True)

	# Save results 
	ModelResults.SDR.to_csv(os.path.join(resultsDir_buildingID, 'EDP_data', 'SDR.csv'), sep=',', header = False, index = False)        
	ModelResults.RDR.to_csv(os.path.join(resultsDir_buildingID, 'EDP_data', 'RDR.csv'), sep=',', header = False, index = False)        
	ModelResults.PFA.to_csv(os.path.join(resultsDir_buildingID, 'EDP_data', 'PFA.csv'), sep=',', header = False, index = False)        

	ModelResults.CollapseCount.to_csv(os.path.join(resultsDir_buildingID, 'EDP_data','CollapseCount.csv'), sep = ',', header = False, index = False)
	# ModelResults.CollapseFragility.to_csv(os.path.join(resultsDir_buildingID, 'EDP_data','CollapseFragility.csv'), sep='\t', header = False, index = False)    
	# ModelResults.DemolitionFragility.to_csv('DemolitionFragility.csv', sep='\t', header = False, index = False)
	finish = time.time()
	print('Finished processing MSA results for %s in %s Minutes'%(ID, (finish-start)/60))    

finish = time.time()
print((finish - start0)/60, 'Minutes')



