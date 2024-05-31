#!/bin/bash
#$ -cwd
# error = Merged with joblog
#$ -o joblog.$JOB_ID
#$ -j y
## Edit the line below as needed:
#$ -l h_rt=12:00:00,h_data=4G
## Speficy CPU type
#$ -l arch=intel-gold-*
##$ -l exclusive
## Modify the parallel environment
## and the number of cores as needed:
#$ -pe shared 2
##$ -pe dc* 12
# Notify when
## $ -m ea

# echo job info on joblog:
echo "Job $JOB_ID started on:   " `hostname -s`
echo "Job $JOB_ID started on:   " `date `
echo " "

start=`date +%s.%N`

#environment
source /u/local/Modules/default/init/modules.sh
#environment
module load singularity
# module load apptainer
# module load intel
# module load openmpi

# SGE_TASK_ID=1

############## This command for OpenSees works fine
# singularity run $H2_CONTAINER_LOC/opensees-3.2.0.sif OpenSees RunIDAHoffmanXx.tcl $SGE_TASK_ID
# singularity run $H2_CONTAINER_LOC/opensees-3.2.0.sif OpenSees RunIDAHoffmanZz.tcl $SGE_TASK_ID

singularity run $H2_CONTAINER_LOC/opensees-3.2.0.sif OpenSees RunNRHAXx.tcl $SGE_TASK_ID
singularity run $H2_CONTAINER_LOC/opensees-3.2.0.sif OpenSees RunNRHAZz.tcl $SGE_TASK_ID

## using OpenSees MP in series                                                                                                                
# time apptainer exec $H2_CONTAINER_LOC/h2-opensees_3.5.0.sif OpenSeesMP RunNRHA_EA_VaFi.tcl $SGE_TASK_ID EA-VaFi                        
# time apptainer exec $H2_CONTAINER_LOC/h2-opensees_3.5.0.sif OpenSees RunNRHA_EA_VaFi.tcl $SGE_TASK_ID EA-VaFi                        

# ## using OpenSees MP in parallel
# `which mpirun` -np $NSLOTS apptainer run $H2_CONTAINER_LOC/h2-opensees_3.5.0.sif OpenSeesMP RunNRHA_EA_VaFi.tcl $SGE_TASK_ID EA-VaFi
# time  `which mpirun` singularity exec  $H2_CONTAINER_LOC/h2-opensees_3.3.0.sif OpenSeesMP RunNRHA.tcl $SGE_TASK_ID


echo "Job $JOB_ID ended on:   " `date `
# echo "working dir is $cwd"
end=`date +%s`
runtime=$( echo "$end - $start" | bc -l )
echo "Duration: $runtime seconds"
 















