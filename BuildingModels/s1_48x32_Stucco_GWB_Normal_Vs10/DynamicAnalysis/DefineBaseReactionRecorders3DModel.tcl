# Define base node reaction recorders 

cd $pathToResults/EQ_$folderNumber/BaseReactions 

# Base node vertical reactions 
recorder	Node	-file	XPanelBaseNodesVerticalReactions.out	-time	-node	11011	11021	11031	11041	11051	11061	11071	11081	11091	11101	11111	11121	11131	-dof	2	reaction
recorder	Node	-file	ZPanelBaseNodesVerticalReactions.out	-time	-node	13011	13021	13031	13041	13051	13061	13071	13081	-dof	2	reaction
recorder	Node	-file	LeaningColumnBaseNodeVerticalReactions.out	-time	-node	1000	1100	1200	1300	1400	1500	1600	1700	1800	-dof	2	reaction

# Base node horizontal reactions 
recorder	Node	-file	XPanelBaseNodesHorizontalReactions.out	-time	-node	11011	11021	11031	11041	11051	11061	11071	11081	11091	11101	11111	11121	11131	-dof	1	reaction
recorder	Node	-file	ZPanelBaseNodesHorizontalReactions.out	-time	-node	13011	13021	13031	13041	13051	13061	13071	13081	-dof	3	reaction
recorder	Node	-file	LeaningColumnBaseNodeXHorizontalReactions.out	-time	-node	1000	1100	1200	1300	1400	1500	1600	1700	1800	-dof	1	reaction
recorder	Node	-file	LeaningColumnBaseNodeZHorizontalReactions.out	-time	-node	1000	1100	1200	1300	1400	1500	1600	1700	1800	-dof	3	reaction
