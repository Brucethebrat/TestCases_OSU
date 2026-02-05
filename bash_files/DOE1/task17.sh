#!/bin/bash

cd /users/PAS2414/brucecheng/DOE1

SCRIPT_PATH='run_scheduler_with1010_4OSC_grb_lic_include.py'

. DOE1_env/bin/activate
module load gurobi/12.0.0

python $SCRIPT_PATH 17 1 20 120
