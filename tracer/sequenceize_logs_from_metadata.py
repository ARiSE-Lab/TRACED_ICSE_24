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
import functools

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--lang')
parser.add_argument('--base_dirs', nargs='+')
parser.add_argument('--src_dirs', nargs='+')
parser.add_argument('--input_dir', default="all_input_output")
parser.add_argument('--metadata_dir', default="Project_CodeNet/metadata")
parser.add_argument('--begin_problem', type=int, default=0)
parser.add_argument('--end_problem', type=int, default=4052)
parser.add_argument('--limit_solutions', type=int)
parser.add_argument('--limit_sequences', type=int)
parser.add_argument('--nproc', type=int, default=1)
parser.add_argument('--output', type=str)
args = parser.parse_args()

print(f"{args=}")

if args.output is not None:
    sequence_output_dir = Path(args.output)
    sequence_output_dir.mkdir(parents=True, exist_ok=True)
else:
    sequence_output_dir = Path.cwd()

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

# metadata_dir = Path("../../Project_CodeNet/metadata")
# input_dir = Path("../../all_input_output")
metadata_dir = Path(args.metadata_dir)
input_dir = Path(args.input_dir)

def get_sequence_all_inputs(lang, problem, solution):
    filext = lang_to_filext[lang]
    for src_dir in src_dirs:
        src_file = src_dir / problem / lang / (solution + '.' + filext)
        if src_file.exists():
            break
    
    input_files = list((input_dir / problem).glob('input_*.txt'))

    if len(input_files) == 0:
        input_files = [None]
    sequences_to_return = []
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
        
        # yield get_sequence(filext, problem, solution, input_id, src_file, log_file, input_file, output_file)
        sequences_to_return.append(get_sequence(filext, problem, solution, input_id, src_file, log_file, input_file, output_file))
    return sequences_to_return
        
def get_sequence_tuple(t):
    return get_sequence_all_inputs(*t)

def get_sequence_row(row):
    yield from get_sequence_all_inputs(row["language"], row["problem_id"], row["submission_id"])

def abortable_worker(func, *args):
    """"https://stackoverflow.com/a/29495039/8999671"""
    timeout = 10
    p = ThreadPool(1)
    res = p.apply_async(func, args=args)
    try:
        out = res.get(timeout)  # Wait timeout seconds for func to complete.
        return out
    except multiprocessing.TimeoutError:
        return None

sequences_filename = sequence_output_dir / f"sequences_lang{args.lang}_from{args.begin_problem}_to{args.end_problem}_limit{args.limit_solutions}.jsonl"
#with Pool(args.nproc) as pool, open(sequences_filename, 'w') as sf:
with open(sequences_filename, 'w') as sf:
    for problem_num in range(args.begin_problem, args.end_problem+1):
        problem_csv = metadata_dir / f'p{str(problem_num).rjust(5, "0")}.csv'

        df = pd.read_csv(str(problem_csv))
        total = len(df)
        # Categories are too narrow - expand to all bug types and just throw away if log is not present or not valid
        #df = df[(df["language"] == args.lang) & (df["status"].isin(["Accepted", "Wrong Answer", "WA: Presentation Error"]))]
        # Used for debug - get complement of previously too-narrow categories
        # df = df[(df["language"] == args.lang) & (~df["status"].isin(["Accepted", "Wrong Answer", "WA: Presentation Error"]))]
        df = df[df["language"] == args.lang]
        filtered = len(df)
        excluded = total - filtered
        memory_mb = float(process.memory_info().rss) / 10e6

        num_sequences = 0
        num_success_sequences = 0
        break_all = False
        print()
        print(f'{problem_csv.name}, {total=}, {filtered=}, {excluded=}, {memory_mb=:.2f}')
        postfix = defaultdict(int)
        num_success = 0
        # with tqdm.tqdm(df.iterrows(), total=len(df), desc=problem_csv.name) as pbar:
        #     for sequences in pool.imap(get_sequence_all_inputs, zip(df["language"], df["problem_id"], df["submission_id"])):
            # for i, row in pbar:
                # sequences = get_sequence_row(row)
        fn = functools.partial(abortable_worker, get_sequence_tuple)
        #with Pool(args.nproc) as pool, tqdm.tqdm(pool.imap_unordered(get_sequence_tuple, zip(df["language"], df["problem_id"], df["submission_id"])), total=len(df)) as pbar:
        with Pool(args.nproc) as pool, tqdm.tqdm(pool.imap(get_sequence_tuple, zip(df["language"], df["problem_id"], df["submission_id"])), total=len(df)) as pbar:
        #try:
        #with tqdm.tqdm(Parallel(n_jobs=args.nproc, timeout=1.0)(delayed(get_sequence_all_items)(*t) for t in zip(df["language"], df["problem_id"], df["submission_id"])), total=len(df)) as pbar:
            for i, sequences in enumerate(pbar):
                print('sequence', i)
                if sequences is None:
                    postfix["timeout"] += 1
                had_success = False
                for sequence in sequences:
                    sequence_str = json.dumps(sequence)
                    postfix[sequence["outcome"]] += 1
                    if sequence["outcome"] == "success":
                        had_success = True
                        sf.write(sequence_str + '\n')
                        num_success += 1
                        if args.limit_sequences is not None and num_success >= args.limit_sequences:
                            break_all = True
                            break
                if had_success:
                    num_success_sequences += 1
                if args.limit_solutions is not None and num_success_sequences >= args.limit_solutions:
                    break_all = True
                pbar.set_postfix(postfix)
                if break_all:
                    print('terminating')
                    pool.terminate()
                    break
                

    df = df.reset_index().rename(columns={'index': 'original_index'})

