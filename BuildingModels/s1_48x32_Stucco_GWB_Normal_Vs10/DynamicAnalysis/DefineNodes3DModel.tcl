# This file will be used to define all nodes 
# Units: inch


# Define x-direction wood panel nodes
# Story 1 
node 	 11011 	 24.000 	 0.000 	 0.000; 
node 	 11012 	 24.000 	 120.000 	 0.000; 
node 	 11021 	 144.000 	 0.000 	 0.000; 
node 	 11022 	 144.000 	 120.000 	 0.000; 
node 	 11031 	 288.000 	 0.000 	 0.000; 
node 	 11032 	 288.000 	 120.000 	 0.000; 
node 	 11041 	 432.000 	 0.000 	 0.000; 
node 	 11042 	 432.000 	 120.000 	 0.000; 
node 	 11051 	 552.000 	 0.000 	 0.000; 
node 	 11052 	 552.000 	 120.000 	 0.000; 
node 	 11061 	 48.000 	 0.000 	 192.000; 
node 	 11062 	 48.000 	 120.000 	 192.000; 
node 	 11071 	 288.000 	 0.000 	 192.000; 
node 	 11072 	 288.000 	 120.000 	 192.000; 
node 	 11081 	 528.000 	 0.000 	 192.000; 
node 	 11082 	 528.000 	 120.000 	 192.000; 
node 	 11091 	 24.000 	 0.000 	 384.000; 
node 	 11092 	 24.000 	 120.000 	 384.000; 
node 	 11101 	 144.000 	 0.000 	 384.000; 
node 	 11102 	 144.000 	 120.000 	 384.000; 
node 	 11111 	 288.000 	 0.000 	 384.000; 
node 	 11112 	 288.000 	 120.000 	 384.000; 
node 	 11121 	 432.000 	 0.000 	 384.000; 
node 	 11122 	 432.000 	 120.000 	 384.000; 
node 	 11131 	 552.000 	 0.000 	 384.000; 
node 	 11132 	 552.000 	 120.000 	 384.000; 
puts "x-direction wood panel nodes defined"

# Define z-direction wood panel nodes 
# Story 1 
node 	 13011 	 0.000 	 0.000 	 24.000; 
node 	 13012 	 0.000 	 120.000 	 24.000; 
node 	 13021 	 0.000 	 0.000 	 192.000; 
node 	 13022 	 0.000 	 120.000 	 192.000; 
node 	 13031 	 0.000 	 0.000 	 360.000; 
node 	 13032 	 0.000 	 120.000 	 360.000; 
node 	 13041 	 288.000 	 0.000 	 48.000; 
node 	 13042 	 288.000 	 120.000 	 48.000; 
node 	 13051 	 288.000 	 0.000 	 336.000; 
node 	 13052 	 288.000 	 120.000 	 336.000; 
node 	 13061 	 576.000 	 0.000 	 24.000; 
node 	 13062 	 576.000 	 120.000 	 24.000; 
node 	 13071 	 576.000 	 0.000 	 192.000; 
node 	 13072 	 576.000 	 120.000 	 192.000; 
node 	 13081 	 576.000 	 0.000 	 360.000; 
node 	 13082 	 576.000 	 120.000 	 360.000; 
puts "z-direction wood panel nodes defined" 

# Define main leaning column nodes 
node 	 1000 	 288.000 	 0.000 	 192.000; 
node 	 2000 	 288.000 	 120.000 	 192.000; 

node 	 1100 	 0.000 	 0.000 	 0.000; 
node 	 2100 	 0.000 	 120.000 	 0.000; 

node 	 1200 	 288.000 	 0.000 	 0.000; 
node 	 2200 	 288.000 	 120.000 	 0.000; 

node 	 1300 	 576.000 	 0.000 	 0.000; 
node 	 2300 	 576.000 	 120.000 	 0.000; 

node 	 1400 	 0.000 	 0.000 	 192.000; 
node 	 2400 	 0.000 	 120.000 	 192.000; 

node 	 1500 	 0.000 	 0.000 	 384.000; 
node 	 2500 	 0.000 	 120.000 	 384.000; 

node 	 1600 	 288.000 	 0.000 	 384.000; 
node 	 2600 	 288.000 	 120.000 	 384.000; 

node 	 1700 	 576.000 	 0.000 	 384.000; 
node 	 2700 	 576.000 	 120.000 	 384.000; 

node 	 1800 	 576.000 	 0.000 	 192.000; 
node 	 2800 	 576.000 	 120.000 	 192.000; 

puts "main leaning column nodes defined" 

# Define leaning column top nodes for zero length springs 
node 	 1001 	 288.000 	 0.000 	 192.000; 

node 	 1101 	 0.000 	 0.000 	 0.000; 

node 	 1201 	 288.000 	 0.000 	 0.000; 

node 	 1301 	 576.000 	 0.000 	 0.000; 

node 	 1401 	 0.000 	 0.000 	 192.000; 

node 	 1501 	 0.000 	 0.000 	 384.000; 

node 	 1601 	 288.000 	 0.000 	 384.000; 

node 	 1701 	 576.000 	 0.000 	 384.000; 

node 	 1801 	 576.000 	 0.000 	 192.000; 

# Define leaning column bottom nodes for zero length springs 
node 	 2002 	 288.000 	 120.000 	 192.000; 

node 	 2102 	 0.000 	 120.000 	 0.000; 

node 	 2202 	 288.000 	 120.000 	 0.000; 

node 	 2302 	 576.000 	 120.000 	 0.000; 

node 	 2402 	 0.000 	 120.000 	 192.000; 

node 	 2502 	 0.000 	 120.000 	 384.000; 

node 	 2602 	 288.000 	 120.000 	 384.000; 

node 	 2702 	 576.000 	 120.000 	 384.000; 

node 	 2802 	 576.000 	 120.000 	 192.000; 

puts "Leaning column nodes for zero length spring defined"