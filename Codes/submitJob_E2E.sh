#!/bin/bash
#$ -cwd
# error = Merged with joblog
#$ -o joblog.$JOB_ID
#$ -j y
## Edit the line below as needed:
#$ -l h_rt=8:00:00,h_data=4G
## Speficy CPU type
#$ -l arch=intel-gold-*
##$ -l exclusive
## Modify the parallel environment
## and the number of cores as needed:
#$ -pe shared 1
##$ -pe dc* 12
# Notify when
##$ -m ea

# echo job info on joblog:
echo "Job $JOB_ID started on:   " `hostname -s`
echo "Job $JOB_ID started on:   " `date `
echo " "

start=`date +%s.%N`

#environment
source /u/local/Modules/default/init/modules.sh
#environment
module load singularity
# module load intel
# module load apptainer
# module load openmpi
module load python/3.9.6
# source $HOME/mpi_env/mpi_env/bin/activate

# buildingID="MFD6B"
buildingID="s1_48x32_Stucco_GWB_Normal_Vs10"

python3 -u run_designModule.py --buildingID $buildingID 


singularity run $H2_CONTAINER_LOC/opensees-3.2.0.sif OpenSees structuralModule/RunNRHAXx.tcl $SGE_TASK_ID
singularity run $H2_CONTAINER_LOC/opensees-3.2.0.sif OpenSees structuralModule/RunNRHAZz.tcl $SGE_TASK_ID


python3 -u damageModule/ProcessMSAResults.py 


python3 -u lossModule/driverPelicun_E2E.py 


module load matlab/R2022b
python3 -u lossModule/driverATC138_E2E.py 


echo "Task id is $SGE_TASK_ID"
echo "Job $JOB_ID ended on:   " `date `
# echo "working dir is $cwd"
end=`date +%s`
runtime=$( echo "$end - $start" | bc -l )
echo "Duration: $runtime seconds"
 















