#!/bin/bash

cd /users/PAS2414/brucecheng/DOE2

SCRIPT_PATH='run_scheduler_with1107_4OSC_grb_lic_include.py'

. DOE2_env/bin/activate
# module load gurobi/12.0.0

python $SCRIPT_PATH 15 5 20 60 400 200 -40 30 -20 -60 2
