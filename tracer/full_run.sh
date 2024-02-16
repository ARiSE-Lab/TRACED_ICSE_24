#!/bin/bash

set -e

# Set up
mkdir -p results/trace_tree
conda activate traced
sudo apt install -y gdb
pip install -r requirements.txt
bash 01_preprocess/download_all_data.sh
python 01_preprocess/compile_all.py --begin_problem 0 --end_problem 4052

# Trace
bash 02_trace/trace_all_problems.sh results/

# Postprocess
bash 03_postprocess/postprocess_all_problems.sh
python 03_postprocess/sequenceize_logs_from_metadata.py --lang C --base_dirs results/trace_tree --src_dirs ../Project_CodeNet/data --input_dir all_input_output --metadata_dir ../Project_CodeNet/metadata --begin_problem 0 --end_problem 4052 --limit_solutions 1 --output results/trace_tree

# Calculate branch and line coverage
python -m 04_coverage_prediction.conversion --input_file trace_tree_sequences/sequences_*_full.jsonl --output_file trace_tree_sequences/sequences_BRANCH.jsonl --mode branch --lang c
python -m 04_coverage_prediction.conversion --input_file trace_tree_sequences/sequences_*_full.jsonl --output_file trace_tree_sequences/sequences_LINE.jsonl --mode separate_lines --lang c
