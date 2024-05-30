#!/bin/csh -f
#  submitJob_E2E.sh.cmd
#
#  UGE job for submitJob_E2E.sh built Sat Nov  4 16:03:13 PDT 2023
#
#  The following items pertain to this script
#  Use current working directory
#$ -cwd
#  input           = /dev/null
#  output          = /u/project/hvburton/laxmanda/Regional_study/codes/submitJob_E2E.sh.joblog.$JOB_ID.$TASK_ID
#$ -o /u/project/hvburton/laxmanda/Regional_study/codes/HiFi_run_files/submitJob_E2E.sh.joblog.$JOB_ID.$TASK_ID
#  error           = Merged with joblog
#$ -j y
#  The following items pertain to the user program
#  user program    = /u/project/hvburton/laxmanda/Regional_study/codes/submitJob_E2E.sh
#  arguments       = 
#  program input   = Specified by user program
#  program output  = Specified by user program
#  Threaded:     2-way threaded
#  Resources requested
#$ -pe shared 1
#$ -l h_data=2048M,h_rt=5:00:00
# #
#  Name of application for log
#$ -v QQAPP=job
#  Email address to notify
##$ -M laxmanda@mail
#  Notify at beginning and end of job
##$ -m a
#  Job is not rerunable
#$ -r n
#
#  Job array indexes
#$ -t 2-2:1
#
# Initialization for serial execution
#
  unalias *
  set qqversion = 
  set qqapp     = "jobarray threads"
  set qqmtasks  = 2
  set qqidir    = /u/project/hvburton/laxmanda/Regional_study/codes
  set qqjob     = submitJob_E2E.sh
  set qqodir    = /u/project/hvburton/laxmanda/Regional_study/codes/HiFi_run_files
  cd     /u/project/hvburton/laxmanda/Regional_study/codes
  source /u/local/bin/qq.sge/qr.runtime
  if ($status != 0) exit (1)
#
  echo "UGE job for submitJob_E2E.sh built Sat Nov  7 9:31:13 PDT 2023"
  echo ""
  echo "  submitJob_E2E.sh directory:"
  echo "    "/u/project/hvburton/laxmanda/Regional_study/codes
  echo "  Submitted to UGE:"
  echo "    "$qqsubmit
  echo "  SCRATCH directory:"
  echo "    "$qqscratch
  echo "  submitJob_E2E.sh 2-way threaded job configuration:"
#
  echo ""
  echo "Task $SGE_TASK_ID for submitJob_E2E.sh started on:   "` hostname -s `
  echo "Task $SGE_TASK_ID for submitJob_E2E.sh started at:   "` date `
  echo ""
#
# Run the user program
#
  # if more than 10 jobtasks, send only "a" mail.  until...
  # ... the last but 1 task so it applies to last task. then send or not per user preference.
  if( 5 > 10 && $SGE_TASK_ID == 4 ) then
    /u/local/bin/qalter -m a $JOB_ID
    sleep 2
  endif
#
  echo submitJob_E2E.sh "" \>\& submitJob_E2E.sh.output.$JOB_ID.$SGE_TASK_ID
  echo ""
  setenv OMP_NUM_THREADS 1
#
  /usr/bin/time /u/project/hvburton/laxmanda/Regional_study/codes/submitJob_E2E.sh  >& /u/project/hvburton/laxmanda/Regional_study/codes/HiFi_run_files/submitJob_E2E.sh.output.$JOB_ID.$SGE_TASK_ID
#
  echo ""
  echo "Task $SGE_TASK_ID for submitJob_E2E.sh finished at:  "` date `
#
# Cleanup after serial execution
#
  source /u/local/bin/qq.sge/qr.runtime
#
  echo "-------- /u/project/hvburton/laxmanda/Regional_study/codes/submitJob_E2E.sh.joblog.$JOB_ID.$SGE_TASK_ID --------" >> /u/local/apps/queue.logs/jobarray.log.multithread
  if (`wc -l /u/project/hvburton/laxmanda/Regional_study/codes/submitJob_E2E.sh.joblog.$JOB_ID.$SGE_TASK_ID  | awk '{print $1}'` >= 1) then
        head -50 /u/project/hvburton/laxmanda/Regional_study/codes/submitJob_E2E.sh.joblog.$JOB_ID.$SGE_TASK_ID >> /u/local/apps/queue.logs/jobarray.log.multithread
        echo " "  >> /u/local/apps/queue.logs/jobarray.log.multithread
        tail -50 /u/project/hvburton/laxmanda/Regional_study/codes/submitJob_E2E.sh.joblog.$JOB_ID.$SGE_TASK_ID >> /u/local/apps/queue.logs/jobarray.log.multithread
  else
        cat /u/project/hvburton/laxmanda/Regional_study/codes/submitJob_E2E.sh.joblog.$JOB_ID.$SGE_TASK_ID >> /u/local/apps/queue.logs/jobarray.log.multithread
  endif
  exit (0)
