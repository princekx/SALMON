#!/bin/bash
#SBATCH --time=5:00
#SBATCH --mem=60gb
#SBATCH --cpus-per-task=16
/data/apps/sss/environments/default-2024_11_26/bin/python ./paths_test.py -d 2025-01-04 -t 00 -a eqwaves -m mogreps