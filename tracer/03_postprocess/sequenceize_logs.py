#!/usr/bin/env python
# coding: utf-8

# %% parse args
import json
from collections import defaultdict
import numpy as np
import tqdm.auto as tqdm
import os

import argparse
import sys

import functools
from multiprocessing import Pool
from text_utils import *
from get_sequence import *
from get_trace import *
from file_utils import *

def parse_args():
    import __main__ as main
    is_jupyter = not hasattr(main, '__file__')

    if is_jupyter:
        print(f'Hardcoding args')
    else:
        print('Parsing cmd line args')
        cmd_args = sys.argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument('--lang')
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--root_dir', default='/work/LAS/weile-lab/benjis/weile-lab/tracing')
    parser.add_argument('--base_dirs', nargs='+')
    parser.add_argument('--src_dirs', nargs='+')
    parser.add_argument('--input_dirs', nargs='+')
    parser.add_argument('--begin', type=int)
    parser.add_argument('--end', type=int)
    parser.add_argument('--limit_solutions', type=int)
    parser.add_argument('--nproc', type=int, default=31)
    return parser.parse_args(cmd_args)

args = parse_args()
print(f'{args=}')

log_files, output_files = get_log_files(args)
print(len(log_files), 'log files')
print('first 5:', list(log_files)[:5])
print(len(output_files), 'output files')
print('first 5:', list(output_files.items())[:5])

sequences_filename = Path(f'{args.lang}_sequences_{args.begin}_{args.end}.jsonl')
if sequences_filename.exists():
    sequences_filename.unlink()


# %% get all sequences multithreaded


lang_to_path = {
    "c": "C",
    "cpp": "C++",
}
src_dir = Path(args.src_dirs[0])
input_dir = Path(args.input_dirs[0])

nproc = args.nproc

import pandas as pd
all_runs = list(sorted(set(log_files.keys()).intersection(set(output_files.keys()))))
print(len(all_runs))
df = pd.DataFrame(all_runs, columns=["lang", "problem", "solution", "input_id"])
df["log_file"] = df.apply(lambda row: log_files[(row["lang"], row["problem"], row["solution"], row["input_id"])], axis=1)
df["output_file"] = df.apply(lambda row: output_files[(row["lang"], row["problem"], row["solution"], row["input_id"])], axis=1)
df["input_file"] = df.apply(lambda row: input_dir / row["problem"] / f'input_{row["input_id"]}.txt', axis=1)
df["src_file"] = df.apply(lambda row: src_dir / row["problem"] / lang_to_path[row["lang"]] / (row["solution"] + '.' + row["lang"]), axis=1)
df["src_file_relative"] = df["src_file"].apply(lambda sf: sf.relative_to(src_dir))
print(df.head())

num_errors = 0
printed_error = 0
lens = []
outcomes = defaultdict(int)
with Pool(nproc) as pool, open(sequences_filename, 'w') as sf:
    pbar = tqdm.tqdm(pool.starmap(get_sequence,
    zip(df["lang"], df["problem"], df["solution"], df["input_id"], df["src_file"], df["src_file_relative"], df["log_file"], df["input_file"], df["output_file"])),
    total=len(all_runs), mininterval=1)
    for i, sequence in enumerate(pbar):
        try:
            sequence_str = json.dumps(sequence)
            lens.append(sequence_str)
            sf.write(sequence_str + '\n')
            outcomes[sequence["outcome"]] += 1
            if i % 100 == 0:
                pbar.set_postfix(outcomes)
            if sequence["outcome"] == 'error' and printed_error < 10:
                print(f'Error {printed_error}:', json.dumps(sequence, indent=2))
                printed_error += 1
        except Exception:
            num_errors += 1
            print(num_errors, 'error outside multiprocess. Skipping...')
            traceback.print_exc()
for outcome, count in outcomes.items():
    print(outcome, count)


# %% report results

counts = defaultdict(int)
all_code_length = 0
all_trace_lengths = []
all_traces = []
all_input_length = 0
all_output_length = 0
num_sequences = 0
incomplete = 0
problems = set()
sequences = set()
sequences_inputs = set()
with open(sequences_filename) as f:
    for line in tqdm.tqdm(f.readlines()):
        try:
            sequence = json.loads(line)
            problems.add(os.path.dirname(os.path.dirname(sequence["filepath"])))
            sequences.add(os.path.basename(sequence["filepath"]))
            sequences_inputs.add(os.path.basename(sequence["filepath"]) + sequence["input_no"])
            all_trace_lengths.append(len(sequence["trace"]))
            counts[sequence["lang"]] += 1
            all_code_length += len(sequence["src"])
            all_traces.append(sequence["trace"])
            all_input_length += len(sequence["input"])
            all_output_length += len(sequence["output"])
            num_sequences += 1
        except KeyError:
            incomplete += 1
assert num_sequences > 0, 'no complete sequences, check for errors'

choptop_all_trace_lengths = sorted(all_trace_lengths)
choptop_all_trace_lengths = choptop_all_trace_lengths[:int(len(choptop_all_trace_lengths)*.99)]

print('incomplete', incomplete)
print('sequences:', json.dumps(counts, indent=2))
print('unique problems:', len(problems))
print('unique sequences:', len(sequences))
print('unique traces:', len(sequences_inputs))
print(f"average code length: {all_code_length/num_sequences:.4f}")
print(f"average trace length except 99th percentile: {np.average(choptop_all_trace_lengths):.4f}")
print(f"average trace length: {np.average(all_trace_lengths):.4f}")
print(f"average input length: {all_input_length/num_sequences:.4f}")
print(f"average output length: {all_output_length/num_sequences:.4f}")
