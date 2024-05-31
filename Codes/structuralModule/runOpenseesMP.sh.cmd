#!/bin/csh -f
#  runOpenseesMP.sh.cmd
#
#  UGE job for runOpenseesMP.sh built Mon Feb 12 20:42:00 PST 2024
#
#  The following items pertain to this script
#  Use current working directory
#$ -cwd
#  input           = /dev/null
#  output          = /u/project/hvburton/laxmanda/autoWoodSDA/Codes/analysisModule/runOpenseesMP.sh.joblog.$JOB_ID.$TASK_ID
#$ -o /u/project/hvburton/laxmanda/autoWoodSDA/Codes/analysisModule/run_files/runOpenseesMP.sh.joblog.$JOB_ID.$TASK_ID
#  error           = Merged with joblog
#$ -j y
#  The following items pertain to the user program
#  user program    = /u/project/hvburton/laxmanda/autoWoodSDA/Codes/analysisModule/runOpenseesMP.sh
#  arguments       = 
#  program input   = Specified by user program
#  program output  = Specified by user program
#  Threaded:     2-way threaded
#  Resources requested
#$ -pe shared 2
#$ -l h_data=4096M,h_rt=12:00:00
# #
#  Name of application for log
#$ -v QQAPP=job
#  Email address to notify
#$ -M laxmanda@mail
#  Notify at beginning and end of job
#$ -m a
#  Job is not rerunable
#$ -r n
#
#  Job array indexes
#$ -t 1-4:1
#
# Initialization for serial execution
#
  unalias *
  set qqversion = 
  set qqapp     = "jobarray threads"
  set qqmtasks  = 2
  set qqidir    = /u/project/hvburton/laxmanda/autoWoodSDA/Codes/analysisModule
  set qqjob     = runOpenseesMP.sh
  set qqodir    = /u/project/hvburton/laxmanda/autoWoodSDA/Codes/analysisModule/run_files
  cd     /u/project/hvburton/laxmanda/autoWoodSDA/Codes/analysisModule
  source /u/local/bin/qq.sge/qr.runtime
  if ($status != 0) exit (1)
#
  echo "UGE job for runOpenseesMP.sh built Mon Feb 12 20:42:00 PST 2024"
  echo ""
  echo "  runOpenseesMP.sh directory:"
  echo "    "/u/project/hvburton/laxmanda/autoWoodSDA/Codes/analysisModule
  echo "  Submitted to UGE:"
  echo "    "$qqsubmit
  echo "  SCRATCH directory:"
  echo "    "$qqscratch
  echo "  runOpenseesMP.sh 2-way threaded job configuration:"
#
  echo ""
  echo "Task $SGE_TASK_ID for runOpenseesMP.sh started on:   "` hostname -s `
  echo "Task $SGE_TASK_ID for runOpenseesMP.sh started at:   "` date `
  echo ""
#
# Run the user program
#
  # if more than 10 jobtasks, send only "a" mail.  until...
  # ... the last but 1 task so it applies to last task. then send or not per user preference.
  if( 4 > 10 && $SGE_TASK_ID == 3 ) then
    /u/local/bin/qalter -m a $JOB_ID
    sleep 2
  endif
#
  echo runOpenseesMP.sh "" \>\& runOpenseesMP.sh.output.$JOB_ID.$SGE_TASK_ID
  echo ""
  setenv OMP_NUM_THREADS 2
#
  /usr/bin/time /u/project/hvburton/laxmanda/autoWoodSDA/Codes/analysisModule/runOpenseesMP.sh  >& /u/project/hvburton/laxmanda/autoWoodSDA/Codes/analysisModule/run_files/runOpenseesMP.sh.output.$JOB_ID.$SGE_TASK_ID
#
  echo ""
  echo "Task $SGE_TASK_ID for runOpenseesMP.sh finished at:  "` date `
#
# Cleanup after serial execution
#
  source /u/local/bin/qq.sge/qr.runtime
#
  echo "-------- /u/project/hvburton/laxmanda/autoWoodSDA/Codes/analysisModule/runOpenseesMP.sh.joblog.$JOB_ID.$SGE_TASK_ID --------" >> /u/local/apps/queue.logs/jobarray.log.multithread
  if (`wc -l /u/project/hvburton/laxmanda/autoWoodSDA/Codes/analysisModule/runOpenseesMP.sh.joblog.$JOB_ID.$SGE_TASK_ID  | awk '{print $1}'` >= 1000) then
        head -50 /u/project/hvburton/laxmanda/autoWoodSDA/Codes/analysisModule/runOpenseesMP.sh.joblog.$JOB_ID.$SGE_TASK_ID >> /u/local/apps/queue.logs/jobarray.log.multithread
        echo " "  >> /u/local/apps/queue.logs/jobarray.log.multithread
        tail -10 /u/project/hvburton/laxmanda/autoWoodSDA/Codes/analysisModule/runOpenseesMP.sh.joblog.$JOB_ID.$SGE_TASK_ID >> /u/local/apps/queue.logs/jobarray.log.multithread
  else
        cat /u/project/hvburton/laxmanda/autoWoodSDA/Codes/analysisModule/runOpenseesMP.sh.joblog.$JOB_ID.$SGE_TASK_ID >> /u/local/apps/queue.logs/jobarray.log.multithread
  endif
  exit (0)
