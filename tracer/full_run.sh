#!/bin/bash

set -e

# Set up
results="./results"
mkdir -p "$results"
conda activate traced
sudo apt install -y gdb libxml2-utils
pip install -r requirements.txt
bash 01_preprocess/download_all_data.sh
python 01_preprocess/compile_all.py --begin_problem 0 --end_problem 4052

# Trace
bash 02_trace/trace_all_problems.sh compile_output all_input_output $results

# Postprocess
bash 03_postprocess/postprocess_all_problems.sh $results

# Calculate branch and line coverage
python -m 04_coverage_prediction.conversion --input_file $results/sequences/sequences_*_full.jsonl --output_file $results/sequences/sequences_BRANCH.jsonl --mode branch --lang c
python -m 04_coverage_prediction.conversion --input_file $results/sequences/sequences_*_full.jsonl --output_file $results/sequences/sequences_LINE.jsonl --mode separate_lines --lang c
