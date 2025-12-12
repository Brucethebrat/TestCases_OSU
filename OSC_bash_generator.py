# generate_sh.py

def generate_sh(idx, top_k, l_top, bucket, filename):
    top_k_lvls = [1,3]
    l_top_lvls = [10,20]
    bucket_lvls = [60,120]
    
    content = f"""#!/bin/bash

cd /users/PAS2414/brucecheng/DOE1

SCRIPT_PATH='run_scheduler_with1010_4OSC.py'

. DOE1_env/bin/activate
module load gurobi/12.0.0

python $SCRIPT_PATH {idx} {top_k_lvls[top_k]} {l_top_lvls[l_top]} {bucket_lvls[bucket]}
"""

    with open(filename, "w", newline="\n") as f:
        f.write(content)

    print(f"Generated {filename}")


# -----------------------------
# Example usage
# -----------------------------
if __name__ == "__main__":

    # OR produce many automatically:
    cases = [
        [0, 1, 1],
        [0, 0, 0],
        [0, 1, 0],
        [1, 0, 1],
        [1, 1, 0],
        [1, 0, 1],
        [0, 1, 1],
        [1, 1, 0],
        [1, 1, 0],
        [0, 0, 0],
        [1, 1, 1],
        [0, 1, 0],
        [0, 0, 1],
        [1, 0, 0],
        [0, 0, 1],
        [0, 0, 1],
        [0, 1, 1],
        [1, 0, 0],
        [0, 0, 1],
        [1, 1, 1],
        [0, 1, 0],
        [1, 1, 0],
        [0, 0, 0],
        [1, 0, 0],
        [1, 1, 1],
        [1, 0, 0],
        [0, 1, 0],
        [1, 1, 1],
        [0, 1, 1],
        [1, 1, 1]
    ]

    for idx, (top_k_lvl, l_top_lvl, bucket_lvl) in enumerate(cases):
        # generate_sh(idx, top_k, l_top, bucket, f"run_{idx}_{top_k}_{l_top}_{bucket}.sh")
        generate_sh(idx+1, top_k_lvl, l_top_lvl, bucket_lvl, f"./bash_files/task{idx+1}.sh")

    # for idx in range(1,31):
    #     print(f"./task{idx}.sh &",end=" ")
    #     if idx % 5 ==0:
    #         print("\n")
