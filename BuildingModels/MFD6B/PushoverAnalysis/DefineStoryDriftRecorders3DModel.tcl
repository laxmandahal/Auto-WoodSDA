# Define story drift recorders 

cd $baseDir/$dataDir/StoryDrifts 
# Define x-direction story drift recorders 
recorder	Drift	-file	$baseDir/$dataDir/StoryDrifts/LeaningColumnXDrift.out	-iNode	1000	1200	1700	2000	2200	2700	3000	3200	3700	4000	4200	4700	1000	1200	1700	-jNode	2000	2200	2700	3000	3200	3700	4000	4200	4700	5000	5200	5700	5000	5200	5700	-dof	1	-perpDirn	2

# Define z-direction story drift recorders
recorder	Drift	-file	$baseDir/$dataDir/StoryDrifts/LeaningColumnZDrift.out	-iNode	1000	1400	1500	2000	2400	2500	3000	3400	3500	4000	4400	4500	1000	1400	1500	-jNode	2000	2400	2500	3000	3400	3500	4000	4400	4500	5000	5400	5500	5000	5400	5500	-dof	3	-perpDirn	2
