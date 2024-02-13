#!/bin/bash
#$ -cwd
# error = Merged with joblog
#$ -o joblog.$JOB_ID
#$ -j y
## Edit the line below as needed:
#$ -l h_rt=1:00:00,h_data=4G
## Speficy CPU type
#$ -l arch=intel-gold-*
##$ -l exclusive
## Modify the parallel environment
## and the number of cores as needed:
#$ -pe shared 1
##$ -pe dc* 12
# Notify when
##$ -m a

# echo job info on joblog:
echo "Job $JOB_ID started on:   " `hostname -s`
echo "Job $JOB_ID started on:   " `date `
echo " "

start=`date +%s.%N`

#environment
source /u/local/Modules/default/init/modules.sh
#environment
# module load singularity
# module load intel
# module load apptainer
# module load openmpi
module load python/3.9.6
# source $HOME/mpi_env/mpi_env/bin/activate

# BLDG_IDX=1
SGE_TASK_ID=1


# 11/4/2023- this works
# python3 -u driverPelicun_E2E.py 
# python3 -u loss_atc138/driverPelicun_E2E_jobarray.py --regional_strategy $REGIONAL_STRATEGY --bldg_idx $BLDG_IDX
# python3 -u loss_atc138/driverPelicun_E2E_jobarray.py --regional_strategy HiFi --bldg_idx 1

# 11/4/2023- this works
module load matlab/R2022b
python3 -u driverATC138_E2E.py
# python3 -u loss_atc138/driverATC138_E2E_jobarray.py --regional_strategy $REGIONAL_STRATEGY --bldg_idx $BLDG_IDX
# python3 -u loss_atc138/driverATC138_E2E_jobarray.py --regional_strategy HiFi --bldg_idx 1

echo "Task id is $SGE_TASK_ID"
echo "Job $JOB_ID ended on:   " `date `
# echo "working dir is $cwd"
end=`date +%s`
runtime=$( echo "$end - $start" | bc -l )
echo "Duration: $runtime seconds"
 















