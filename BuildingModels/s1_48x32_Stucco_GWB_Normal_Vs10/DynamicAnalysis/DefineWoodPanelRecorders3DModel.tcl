# Define wood panel force-deformation recorders 

cd $pathToResults/EQ_$folderNumber/WoodPanelShearForces 

# X-Direction wood panel element shear force recorders 
recorder	Element	-file	XWoodPanelShearForcesStory1.out	-time	-ele	700000	700001	700002	700003	700004	700005	700006	700007	700008	700009	700010	700011	700012	force

# Z-Direction wood panel element shear force recorders
recorder	Element	-file	ZWoodPanelShearForcesStory1.out	-time	-ele	700013	700014	700015	700016	700017	700018	700019	700020	force


cd $pathToResults/EQ_$folderNumber/WoodPanelDeformations 

# X-Direction wood panel element deformation recorders
recorder	Element	-file	XWoodPanelDeformationsStory1.out	-time	-ele	700000	700001	700002	700003	700004	700005	700006	700007	700008	700009	700010	700011	700012	deformation

# Z-Direction wood panel element shear force recorders
recorder	Element	-file	ZWoodPanelDeformationsStory1.out	-time	-ele	700013	700014	700015	700016	700017	700018	700019	700020	deformation


