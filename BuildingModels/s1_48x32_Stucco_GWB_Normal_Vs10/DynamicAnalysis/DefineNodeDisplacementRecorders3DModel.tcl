# Define node displacement recorders 

cd	$baseDir/$dataDir/NodeDisplacements

# Record displacements for x-direction wood panel nodes
recorder	Node	-file	XWoodPanelNodeDispLevel1.out	-time	-node	11012	11022	11032	11042	11052	11062	11072	11082	11092	11102	11112	11122	11132	-dof	1	disp

# Record displacements for z-direction wood panel nodes
recorder	Node	-file	ZWoodPanelNodeDispLevel1.out	-time	-node	13012	13022	13032	13042	13052	13062	13072	13082	-dof	3	disp

# Record displacements for leaning column nodes 
recorder	Node	-file	LeaningColumnNodeDispLevel1.out	-time	-node	2000	-dof	1	2	3	disp
