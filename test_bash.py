import sys
import time

if len(sys.argv) > 1:
    print(f"Running task {sys.argv[1]}")
else:
    print("No task ID provided.")

for i in range(20):
    print(f"Task {sys.argv[1]} running... {i+1}/20")
    time.sleep(1)