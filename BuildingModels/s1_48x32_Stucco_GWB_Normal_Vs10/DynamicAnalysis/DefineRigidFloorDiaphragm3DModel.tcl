# This file will be used to define the rigid floor diaphragm properties 

 # Setting rigid floor diaphragm constraint on
set RigidDiaphragm ON; 

 # Define Rigid Diaphragm,dof 2 is normal to floor
set perpDirn 2; 

rigidDiaphragm $perpDirn	 2000	 2100	 2200	 2300	 2400	 2500	 2600	 2700	 2800	 11012	 11022	 11032	 11042	 11052	 11062	 11072	 11082	 11092	 11102	 11112	 11122	 11132	 13012	 13022	 13032	 13042	 13052	 13062	 13072	 13082

puts "rigid diaphragm constraints defined"