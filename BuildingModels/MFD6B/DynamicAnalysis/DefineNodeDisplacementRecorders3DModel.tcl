# Define node displacement recorders 

cd	$baseDir/$dataDir/NodeDisplacements

# Record displacements for x-direction wood panel nodes
recorder	Node	-file	XWoodPanelNodeDispLevel1.out	-time	-node	11012	11022	11032	11042	11052	11062	11072	11082	11092	11102	11112	11122	11132	11142	11152	11162	11172	11182	-dof	1	disp
recorder	Node	-file	XWoodPanelNodeDispLevel2.out	-time	-node	21012	21022	21032	21042	21052	21062	21072	21082	21092	21102	21112	21122	21132	21142	21152	21162	21172	21182	-dof	1	disp
recorder	Node	-file	XWoodPanelNodeDispLevel3.out	-time	-node	31012	31022	31032	31042	31052	31062	31072	31082	31092	31102	31112	31122	31132	31142	31152	31162	31172	31182	-dof	1	disp
recorder	Node	-file	XWoodPanelNodeDispLevel4.out	-time	-node	41012	41022	41032	41042	41052	41062	41072	41082	41092	41102	41112	41122	41132	41142	41152	41162	41172	41182	-dof	1	disp

# Record displacements for z-direction wood panel nodes
recorder	Node	-file	ZWoodPanelNodeDispLevel1.out	-time	-node	13012	13022	13032	13042	13052	13062	13072	13082	13092	13102	13112	13122	13132	13142	13152	13162	13172	13182	13192	13202	-dof	3	disp
recorder	Node	-file	ZWoodPanelNodeDispLevel2.out	-time	-node	23012	23022	23032	23042	23052	23062	23072	23082	23092	23102	23112	23122	23132	23142	23152	23162	23172	23182	23192	23202	-dof	3	disp
recorder	Node	-file	ZWoodPanelNodeDispLevel3.out	-time	-node	33012	33022	33032	33042	33052	33062	33072	33082	33092	33102	33112	33122	33132	33142	33152	33162	33172	33182	33192	33202	-dof	3	disp
recorder	Node	-file	ZWoodPanelNodeDispLevel4.out	-time	-node	43012	43022	43032	43042	43052	43062	43072	43082	43092	43102	43112	43122	43132	43142	43152	43162	43172	43182	43192	43202	-dof	3	disp

# Record displacements for leaning column nodes 
recorder	Node	-file	LeaningColumnNodeDispLevel1.out	-time	-node	2000	-dof	1	2	3	disp
recorder	Node	-file	LeaningColumnNodeDispLevel2.out	-time	-node	3000	-dof	1	2	3	disp
recorder	Node	-file	LeaningColumnNodeDispLevel3.out	-time	-node	4000	-dof	1	2	3	disp
recorder	Node	-file	LeaningColumnNodeDispLevel4.out	-time	-node	5000	-dof	1	2	3	disp
