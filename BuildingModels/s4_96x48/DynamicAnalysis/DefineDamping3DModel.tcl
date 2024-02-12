# This file will be used to define damping 

# Define the periods to use for damping parameter calculation 
set periodForRayleighDamping_1 0.758; 
set periodForRayleighDamping_2 0.483; 
# Define damping parameters 
set omegaI [expr (2.0 * $pi) / ($periodForRayleighDamping_1)] 
set omegaJ [expr (2.0 * $pi) / ($periodForRayleighDamping_2)] 
set alpha1Coeff [expr (2.0 * $omegaI * $omegaJ) / ($omegaI + $omegaJ)] 
set alpha2Coeff [expr (2.0) / ($omegaI + $omegaJ)] 
set alpha1 [expr $alpha1Coeff*0.050] 
set alpha2 [expr $alpha2Coeff*0.050] 
# Assign damping to wood panel elements 
region 1 -eleRange	700000	700151	-rayleigh	0	$alpha2	0	0; 
# Assign damping to nodes 
region 2 -node	2000	2100	2200	2300	2400	2500	2600	2700	2800	3000	3100	3200	3300	3400	3500	3600	3700	3800	4000	4100	4200	4300	4400	4500	4600	4700	4800	5000	5100	5200	5300	5400	5500	5600	5700	5800	-rayleigh	$alpha1	0	0	0; 
puts "Damping defined"
