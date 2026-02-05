#!/bin/bash

cd /users/PAS2414/brucecheng/DOE2

SCRIPT_PATH='run_scheduler_with1107_4OSC_grb_lic_include.py'

. DOE2_env/bin/activate
# module load gurobi/12.0.0

python $SCRIPT_PATH 24 5 10 30 400 400 -40 30 -40 -120 1
