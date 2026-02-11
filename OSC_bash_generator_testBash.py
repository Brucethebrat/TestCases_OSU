# generate_sh.py

def generate_sh(idx, top_k, l_top, bucket, same_airport_bonus, domicile_bonus, pair_loc_adj, tour_pair_bonus, enforce_diversity, filename):
    top_k_lvls = [3,5]
    l_top_lvls = [10,20]
    bucket_lvls = [30,60]
    SAME_AIRPORT_BONUS_lvls = [400, 800]
    DOMICILE_BONUS_lvls = [200, 400]
    PAIR_LOC_ADJ_SAME_lvls = [-20, -40]
    PAIR_LOC_ADJ_DIFF_lvls = [15, 30]
    TOUR_PAIR_BONUS_1_lvls = [-20, -40]
    TOUR_PAIR_BONUS_2_lvls = [-60, -120]
    ENFORCE_DIVERSITY_lvls = [1, 2]
    
    content = f"""#!/bin/bash
echo "Starting task {idx}..."
    
cd /users/PAS2414/brucecheng/DOE2

SCRIPT_PATH='./test_bash.py'

. DOE2_env/bin/activate
# module load gurobi/12.0.0
python $SCRIPT_PATH {idx}

echo "Finished task {idx}"
"""
# SCRIPT_PATH='run_scheduler_with1107_4OSC_grb_lic_include.py'
# python $SCRIPT_PATH {idx} {top_k_lvls[top_k]} {l_top_lvls[l_top]} {bucket_lvls[bucket]} {SAME_AIRPORT_BONUS_lvls[same_airport_bonus]} {DOMICILE_BONUS_lvls[domicile_bonus]} {PAIR_LOC_ADJ_SAME_lvls[pair_loc_adj]} {PAIR_LOC_ADJ_DIFF_lvls[pair_loc_adj]} {TOUR_PAIR_BONUS_1_lvls[tour_pair_bonus]} {TOUR_PAIR_BONUS_2_lvls[tour_pair_bonus]} {ENFORCE_DIVERSITY_lvls[enforce_diversity]}

    with open(filename, "w", newline="\n") as f:
        f.write(content)

    print(f"Generated {filename}")


# -----------------------------
# Example usage
# -----------------------------
if __name__ == "__main__":

    # DOE1
    '''cases = [
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
    ]'''

    '''for idx, (top_k_lvl, l_top_lvl, bucket_lvl) in enumerate(cases):
        # generate_sh(idx, top_k, l_top, bucket, f"run_{idx}_{top_k}_{l_top}_{bucket}.sh")
        generate_sh(idx+1, top_k_lvl, l_top_lvl, bucket_lvl, f"./bash_files/task{idx+1}.sh")'''

    # DOE2
    cases = [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0, 0],
        [1, 0, 0, 1, 0, 0, 1, 0],
        [0, 1, 0, 1, 1, 1, 0, 1],
        [1, 1, 1, 1, 1, 0, 1, 1],
        [1, 0, 0, 0, 0, 1, 1, 1],
        [0, 0, 1, 1, 0, 1, 0, 1],
        [1, 0, 1, 0, 0, 0, 0, 1],
        [0, 1, 1, 0, 1, 0, 1, 0],
        [0, 1, 0, 0, 1, 1, 0, 0],
        [1, 1, 1, 1, 0, 1, 1, 0],
        [1, 1, 0, 1, 1, 1, 0, 0],
        [0, 0, 0, 1, 1, 0, 0, 0],
        [0, 0, 1, 0, 1, 0, 1, 0],
        [1, 1, 1, 0, 0, 1, 0, 1],
        [0, 1, 0, 0, 0, 0, 1, 1],
        [0, 0, 0, 1, 0, 0, 1, 0],
        [1, 1, 1, 0, 0, 1, 1, 1],
        [1, 1, 0, 0, 0, 1, 0, 0],
        [0, 1, 0, 0, 1, 1, 1, 0],
        [0, 1, 0, 1, 1, 0, 1, 1],
        [1, 0, 0, 0, 1, 0, 0, 1],
        [1, 0, 0, 1, 1, 0, 0, 1],
        [1, 0, 0, 0, 1, 1, 1, 0],
        [1, 1, 1, 0, 0, 1, 0, 1],
        [0, 1, 0, 1, 0, 1, 0, 0],
        [0, 1, 0, 1, 0, 0, 1, 1],
        [1, 1, 1, 1, 1, 0, 0, 0],
        [0, 1, 0, 0, 0, 1, 1, 1],
        [1, 0, 0, 1, 0, 1, 1, 1],
        [1, 1, 0, 0, 0, 0, 1, 0],
        [0, 1, 0, 0, 0, 0, 0, 1],
        [0, 0, 1, 1, 0, 0, 1, 0],
        [1, 0, 0, 0, 1, 1, 1, 1],
        [0, 0, 1, 0, 1, 1, 0, 1],
        [1, 0, 1, 1, 0, 1, 0, 0],
        [0, 0, 1, 1, 0, 1, 1, 1],
        [1, 1, 1, 1, 0, 0, 1, 0],
        [0, 1, 1, 0, 1, 0, 0, 0],
        [1, 0, 0, 1, 1, 1, 0, 1]
    ]

    for idx, (top_k_lvl, l_top_lvl, bucket_lvl, same_airport_bonus, domicile_bonus, pair_loc_adj, tour_pair_bonus, enforce_diversity) in enumerate(cases):
        # filename = f"./bash_files/DOE2/task{idx+1}.sh"
        filename = f"./bash_files/TestBash/task{idx+1}.sh"
        # generate_sh(idx, top_k, l_top, bucket, f"run_{idx}_{top_k}_{l_top}_{bucket}.sh")
        generate_sh(idx+1, top_k_lvl, l_top_lvl, bucket_lvl, same_airport_bonus, domicile_bonus, pair_loc_adj, tour_pair_bonus, enforce_diversity, filename)

    # for idx in range(1,31):
    #     print(f"./task{idx}.sh &",end=" ")
    #     if idx % 5 ==0:
    #         print("\n")
