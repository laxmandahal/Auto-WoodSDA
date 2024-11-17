# Define story drift recorders 

cd $pathToResults/EQ_$folderNumber/StoryDrifts 
# Define x-direction story drift recorders 
recorder	Drift	-file	$pathToResults/EQ_$folderNumber/StoryDrifts/MidLeaningColumnXDrift.out	-time	-iNode	1000	1200	1700	1000	1200	1700	-jNode	2000	2200	2700	2000	2200	2700	-dof	1	-perpDirn	2
recorder	Drift	-file	$pathToResults/EQ_$folderNumber/StoryDrifts/CornerLeaningColumnXDrift.out	-time	-iNode	1100	1300	1600	1800	1100	1300	1600	1800	-jNode	2100	2300	2600	2800	2100	2300	2600	2800	-dof	1	-perpDirn	2
# Define z-direction story drift recorders 
recorder	Drift	-file	$pathToResults/EQ_$folderNumber/StoryDrifts/MidLeaningColumnZDrift.out	-time	-iNode	1000	1200	1700	1000	1200	1700	-jNode	2000	2400	2500	2000	2400	2500	-dof	3	-perpDirn	2
recorder	Drift	-file	$pathToResults/EQ_$folderNumber/StoryDrifts/CornerLeaningColumnZDrift.out	-time	-iNode	1100	1300	1600	1800	1100	1300	1600	1800	-jNode	2100	2300	2600	2800	2100	2300	2600	2800	-dof	3	-perpDirn	2
