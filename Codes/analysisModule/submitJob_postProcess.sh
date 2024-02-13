#!/bin/bash
#$ -cwd
# error = Merged with joblog
#$ -o joblog.$JOB_ID
#$ -j y
## Edit the line below as needed:
#$ -l h_rt=4:00:00,h_data=4G
## Speficy CPU type
#$ -l arch=intel-gold-*
##$ -l exclusive
## Modify the parallel environment
## and the number of cores as needed:
#$ -pe shared 2
##$ -pe dc* 1
# Notify when
#$ -m a

# echo job info on joblog:
echo "Job $JOB_ID started on:   " `hostname -s`
echo "Job $JOB_ID started on:   " `date `
echo " "

start=`date +%s.%N`

#environment
source /u/local/Modules/default/init/modules.sh
# module load python/3.7.3
module load python/3.9.6
# module load openmpi
# source $HOME/mpi_env/mpi_env/bin/activate



# python3 ProcessMSAResults.py $SGE_TASK_ID
python3 -u ProcessMSAResults.py 
#python3 extractSDRonly.py $SGE_TASK_ID


echo "Job $JOB_ID ended on:   " `date `
# echo "working dir is $cwd"
end=`date +%s`
runtime=$( echo "$end - $start" | bc -l )
echo "Duration: $runtime seconds"
 