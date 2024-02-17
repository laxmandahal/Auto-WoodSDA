#!/bin/bash
#$ -cwd
# error = Merged with joblog
#$ -o joblog.$JOB_ID
#$ -j y
## Edit the line below as needed:
#$ -l h_rt=2:00:00,h_data=4G
## Speficy CPU type
#$ -l arch=intel-gold-*
##$ -l exclusive
## Modify the parallel environment
## and the number of cores as needed:
#$ -pe shared 1

start=`date +%s.%N`

# echo job info on joblog:
echo "Job $JOB_ID started on:   " `hostname -s`
echo "Job $JOB_ID started on:   " `date `
echo " "

#environment
source /u/local/Modules/default/init/modules.sh
module load python/3.9.6



python3 -u process_PELICUN_output.py --run_on_Hoffman True 
python3 -u process_ATC138_output.py --run_on_Hoffman True

end=`date +%s`
runtime=$( echo "$end - $start" | bc -l )
echo "Duration: $runtime seconds"