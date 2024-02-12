# Define story drift recorders 

cd $pathToResults/EQ_$folderNumber/StoryDrifts 
# Define x-direction story drift recorders 
recorder	Drift	-file	$pathToResults/EQ_$folderNumber/StoryDrifts/MidLeaningColumnXDrift.out	-time	-iNode	1000	1200	1700	2000	2200	2700	3000	3200	3700	4000	4200	4700	1000	1200	1700	-jNode	2000	2200	2700	3000	3200	3700	4000	4200	4700	5000	5200	5700	5000	5200	5700	-dof	1	-perpDirn	2
recorder	Drift	-file	$pathToResults/EQ_$folderNumber/StoryDrifts/CornerLeaningColumnXDrift.out	-time	-iNode	1100	1300	1600	1800	2100	2300	2600	2800	3100	3300	3600	3800	4100	4300	4600	4800	1100	1300	1600	1800	-jNode	2100	2300	2600	2800	3100	3300	3600	3800	4100	4300	4600	4800	5100	5300	5600	5800	5100	5300	5600	5800	-dof	1	-perpDirn	2
# Define z-direction story drift recorders 
recorder	Drift	-file	$pathToResults/EQ_$folderNumber/StoryDrifts/MidLeaningColumnZDrift.out	-time	-iNode	1000	1200	1700	2000	2200	2700	3000	3200	3700	4000	4200	4700	1000	1200	1700	-jNode	2000	2400	2500	3000	3400	3500	4000	4400	4500	5000	5400	5500	5000	5400	5500	-dof	3	-perpDirn	2
recorder	Drift	-file	$pathToResults/EQ_$folderNumber/StoryDrifts/CornerLeaningColumnZDrift.out	-time	-iNode	1100	1300	1600	1800	2100	2300	2600	2800	3100	3300	3600	3800	4100	4300	4600	4800	1100	1300	1600	1800	-jNode	2100	2300	2600	2800	3100	3300	3600	3800	4100	4300	4600	4800	5100	5300	5600	5800	5100	5300	5600	5800	-dof	3	-perpDirn	2
