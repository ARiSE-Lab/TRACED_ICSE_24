#!/usr/bin/env python
# coding: utf-8


import pandas as pd
from pathlib import Path
import tqdm as tqdm
import os
import psutil
from get_sequence import get_sequence
import json
from collections import defaultdict
from multiprocessing import Pool

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--lang')
parser.add_argument('--base_dirs', nargs='+')
parser.add_argument('--src_dirs', nargs='+')
parser.add_argument('--input_dir', default="../../all_input_output")
parser.add_argument('--begin_problem', type=int, default=0)
parser.add_argument('--end_problem', type=int, default=4052)
parser.add_argument('--limit_solutions', type=int, default=500)
parser.add_argument('--nproc', type=int, default=1)
args = parser.parse_args()

print(f"{args=}")

# get and json-ize sequences

process = psutil.Process(os.getpid())

filext_to_lang = {
    "c": "C",
    "cpp": "C++",
    "java": "Java",
}
lang_to_filext = {v: k for k, v in filext_to_lang.items()}

# src_dir = Path("../../Project_CodeNet/data")
# log_dir = Path("../../cpp/logs")
# output_dir = Path("../../cpp/outputs")
src_dirs = [Path(src_dir) for src_dir in args.src_dirs]
log_dirs = [Path(base_dir) / "logs" for base_dir in args.base_dirs]
output_dirs = [Path(base_dir) / "outputs" for base_dir in args.base_dirs]

metadata_dir = Path("../../Project_CodeNet/metadata")
input_dir = Path("../../all_input_output")

def get_sequence_all_inputs(lang, problem, solution):
    filext = lang_to_filext[lang]
    for src_dir in src_dirs:
        src_file = src_dir / problem / lang / (solution + '.' + filext)
        if src_file.exists():
            break
    
    input_files = list((input_dir / problem).glob('input_*.txt'))

    if len(input_files) == 0:
        input_files = [None]
    for input_file in input_files:
        if input_file is None:
            input_id = None
        else:
            input_id = input_file.stem
        
        for log_dir in log_dirs:
            log_file = log_dir / f'{filext}_{problem}_{solution}_{input_id}.xml'
            if log_file.exists():
                break

        for output_dir in output_dirs:
            output_file = output_dir / f'{filext}_{problem}_{solution}_{input_id}.txt'
            if output_file.exists():
                break
        
        yield get_sequence(filext, problem, solution, input_id, src_file, log_file, input_file, output_file)
        
def get_sequence_row(row):
    yield from get_sequence_all_inputs(row["language"], row["problem_id"], row["submission_id"])

sequences_filename = f"sequences_lang{args.lang}_from{args.begin_problem}_to{args.end_problem}_limit{args.limit_solutions}.jsonl"
with Pool(args.nproc) as pool, open(sequences_filename, 'w') as sf:
    for problem_num in range(args.begin_problem, args.end_problem+1):
        problem_csv = metadata_dir / f'p{str(problem_num).rjust(5, "0")}.csv'

        df = pd.read_csv(str(problem_csv))
        total = len(df)
        df = df[(df["language"] == args.lang) & (df["status"].isin(["Accepted", "Wrong Answer", "WA: Presentation Error"]))]
        filtered = len(df)
        excluded = total - filtered
        memory_mb = float(process.memory_info().rss) / 10e6

        num_sequences = 0
        break_all = False
        print(f'{problem_csv.name}, {total=}, {filtered=}, {excluded=}, {memory_mb=:.2f}')
        postfix = defaultdict(int)
        num_success = 0
        with tqdm.tqdm(df.iterrows(), total=len(df), desc=problem_csv.name) as pbar:
            for i, row in pbar:
                sequences = get_sequence_row(row)
                for sequence in sequences:
                    sequence_str = json.dumps(sequence)
                    postfix[sequence["outcome"]] += 1
                    if sequence["outcome"] == "success":
                        sf.write(sequence_str + '\n')
                        num_success += 1
                        if num_success >= args.limit_solutions:
                            break_all = True
                            break
                pbar.set_postfix(postfix)
                if break_all:
                    break
                

    df = df.reset_index().rename(columns={'index': 'original_index'})

