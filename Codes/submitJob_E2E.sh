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

REGIONAL_STRATEGY="HiFi_high_collapse"
# REGIONAL_STRATEGY="SVaFi"
# BLDG_IDX=1
SGE_TASK_ID=1

# 11/4/2023- this works
### model creation breaks in Jobarray.q because sw pinching input file is read simultaneously by different runs
# python3 -u createModel_E2E_jobarray.py --regional_strategy $REGIONAL_STRATEGY --bldg_idx $SGE_TASK_ID
# python3 -u createModel_E2E_jobarray.py --regional_strategy $REGIONAL_STRATEGY --bldg_idx $BLDG_IDX
# python3 -u createModel_E2E_jobarray.py --regional_strategy HiFi --bldg_idx 1

# 11/4/2023- this works
# singularity run $H2_CONTAINER_LOC/opensees-3.2.0.sif OpenSees run_NRHA/RunNRHA_HiFi_MP.tcl $SGE_TASK_ID $REGIONAL_STRATEGY
# singularity run $H2_CONTAINER_LOC/opensees-3.2.0.sif OpenSees RunNRHA_HiFi_MP.tcl $BLDG_IDX $REGIONAL_STRATEGY
# singularity run $H2_CONTAINER_LOC/opensees-3.2.0.sif OpenSees RunNRHA_HiFi_MP.tcl 1 HiFi
# rm /u/project/hvburton/laxmanda/Regional_study/codes/HiFi_run_files/submitJob_E2E.sh.joblog.$JOB_ID.$SGE_TASK_ID

# 11/4/2023- this works
# python3 -u extract_EDPs/ProcessNRHA_outputs_E2E_jobarray.py --regional_strategy $REGIONAL_STRATEGY --bldg_idx $SGE_TASK_ID
# python3 -u extract_EDPs/ProcessNRHA_outputs_E2E_jobarray.py --regional_strategy $REGIONAL_STRATEGY --bldg_idx $BLDG_IDX
# python3 -u extract_EDPs/ProcessNRHA_outputs_E2E_jobarray.py --regional_strategy HiFi --bldg_idx 1

## delete the NRHA output files after the EDPs have been extracted. For HiFi, the 3000 GB memory limit exceeded
# python -u debug/deleteNRHA_E2E_jobarray.py --regional_strategy $REGIONAL_STRATEGY --bldg_idx $SGE_TASK_ID

## copy EDP data from one folder to another to perform downstream risk assessment
python3 -u debug/copy_edp_folders.py --regional_strategy_src HiFi --regional_strategy_dest $REGIONAL_STRATEGY --bldg_idx $SGE_TASK_ID

# 11/4/2023- this works
python3 -u loss_atc138/driverPelicun_E2E_jobarray.py --regional_strategy $REGIONAL_STRATEGY --bldg_idx $SGE_TASK_ID
# python3 -u loss_atc138/driverPelicun_E2E_jobarray.py --regional_strategy $REGIONAL_STRATEGY --bldg_idx $BLDG_IDX
# python3 -u loss_atc138/driverPelicun_E2E_jobarray.py --regional_strategy HiFi --bldg_idx 1

# 11/4/2023- this works
module load matlab/R2022b
python3 -u loss_atc138/driverATC138_E2E_jobarray.py --regional_strategy $REGIONAL_STRATEGY --bldg_idx $SGE_TASK_ID
# python3 -u loss_atc138/driverATC138_E2E_jobarray.py --regional_strategy $REGIONAL_STRATEGY --bldg_idx $BLDG_IDX
# python3 -u loss_atc138/driverATC138_E2E_jobarray.py --regional_strategy HiFi --bldg_idx 1

echo "Task id is $SGE_TASK_ID"
echo "Job $JOB_ID ended on:   " `date `
# echo "working dir is $cwd"
end=`date +%s`
runtime=$( echo "$end - $start" | bc -l )
echo "Duration: $runtime seconds"
 















