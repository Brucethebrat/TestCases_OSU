# generate_sh.py

def generate_sh(idx, top_k, l_top, bucket, pool_mult, alpha_fresh, filename):
    top_k_lvls = [1,3]              # 1 in the model
    l_top_lvls = [150,250]          # 200 in the model
    bucket_lvls = [30,60]           # 60 in the model   
    pool_mult_lvls = [50,100]       # 100 in the model
    alpha_fresh_lvls = [2.5,7.5]    # 5.0 in the model
    
    content = f"""#!/bin/bash

cd /users/PAS2414/brucecheng/DOE3

SCRIPT_PATH='run_scheduler_with1107_4OSC_grb_lic_include.py'

. DOE2_env/bin/activate
# module load gurobi/12.0.0

python $SCRIPT_PATH {idx} {top_k_lvls[top_k]} {l_top_lvls[l_top]} {bucket_lvls[bucket]} {pool_mult_lvls[pool_mult]} {alpha_fresh_lvls[alpha_fresh]}
"""

    with open(filename, "w", newline="\n") as f:
        f.write(content)

    print(f"Generated {filename}")


# -----------------------------
# Example usage
# -----------------------------
if __name__ == "__main__":

    # DOE3
    cases = [
        [1, 0, 0, 1, 1],
        [0, 0, 0, 0, 0],
        [0, 1, 0, 1, 0],
        [0, 0, 1, 0, 1],
        [0, 0, 1, 1, 0],
        [1, 1, 1, 0, 1],
        [0, 1, 0, 1, 1],
        [0, 1, 1, 1, 0],
        [1, 0, 1, 1, 0],
        [1, 1, 0, 0, 0],
        [1, 0, 1, 1, 1],
        [1, 0, 0, 1, 0],
        [0, 0, 0, 0, 1],
        [0, 1, 1, 0, 0],
        [1, 1, 0, 0, 1],
        [1, 1, 0, 0, 1],
        [1, 1, 0, 1, 1],
        [1, 0, 1, 0, 0],
        [0, 1, 0, 0, 1],
        [1, 0, 1, 1, 1],
        [0, 0, 0, 1, 0],
        [1, 1, 1, 1, 0],
        [1, 0, 0, 0, 0],
        [1, 0, 1, 0, 0],
        [0, 0, 1, 1, 1],
        [0, 1, 1, 0, 0],
        [1, 0, 0, 1, 0],
        [1, 1, 1, 1, 1],
        [1, 0, 0, 1, 1],
        [0, 1, 1, 1, 1]
    ]

    for idx, (top_k_lvl, l_top_lvl, bucket_lvl, pool_mult_lvl, alpha_fresh_lvl) in enumerate(cases):
        filename = f"./bash_files/DOE3/task{idx+1}.sh"
        # generate_sh(idx, top_k, l_top, bucket, f"run_{idx}_{top_k}_{l_top}_{bucket}.sh")
        generate_sh(idx+1, top_k_lvl, l_top_lvl, bucket_lvl, pool_mult_lvl, alpha_fresh_lvl, filename)

    # for idx in range(1,31):
    #     print(f"./task{idx}.sh &",end=" ")
    #     if idx % 5 ==0:
    #         print("\n")
