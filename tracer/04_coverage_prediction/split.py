"""
OUTPUT

$ python coverage_prediction/split.py 
3745 104 102 102
202 202
202 202 3649
write splits: 474512it [04:25, 1788.08it/s]

$ wc -l data/splits/*
      26049 data/splits/test.jsonl
        202 data/splits/test_problems.txt
      26049 data/splits/test_submissions.txt
     423022 data/splits/train.jsonl
       3649 data/splits/train_problems.txt
     423022 data/splits/train_submissions.txt
      25441 data/splits/valid.jsonl
        202 data/splits/valid_problems.txt
      25441 data/splits/valid_submissions.txt
     953077 total
"""

#!/bin/bash

import jsonlines
import random
import numpy as np
import tqdm
from pathlib import Path
import argparse

#%% parameters
parser = argparse.ArgumentParser()
parser.add_argument(
    "--input_file",
    type=Path,
    default=Path("data/c_sequences.jsonl"),
    help="jsonl file containing sequences from tracer",
)
parser.add_argument(
    "--output_dir",
    type=Path,
    default=Path("data/splits"),
    help="Destination jsonl file",
)
parser.add_argument(
    "--clusters_file",
    type=Path,
    default=Path("data/Project_CodeNet/derived/duplicates/identical_problem_clusters"),
    help="CSV-ish file of identical problem clusters from Project CodeNet distribution",
)
args = parser.parse_args()
clusters_file = Path("data/Project_CodeNet/derived/duplicates/identical_problem_clusters")

#%% setup
num_problems = 4053
problem_nums = list(range(0, num_problems, 1))
test_problems = []
valid_problems = []
train_problems = []
sets = [test_problems, valid_problems, train_problems]

#%% add identical problem clusters evenly
with open(clusters_file) as f:
    identical_problems = [l.split(",") for l in f.readlines()]
for cluster in identical_problems:
    chosen_set = sets[np.argmin(list(map(len, sets)))]
    cluster_problem_nums = [int(problem_id[1:]) for problem_id in cluster]
    chosen_set.extend(cluster_problem_nums)
    for n in cluster_problem_nums:
        problem_nums.remove(n)
print(len(problem_nums), len(test_problems), len(valid_problems), len(train_problems))

#%% add remainder of problems to sets randomly
random.seed(0)
random.shuffle(problem_nums)
test_size = int(num_problems * 0.05)  # 5% test
valid_size = int(num_problems * 0.05)  # 5% valid
print(test_size, valid_size)
test_end = test_size - len(test_problems)
valid_end = test_end + (valid_size - len(valid_problems))
test_problems.extend(problem_nums[:test_end])
valid_problems.extend(problem_nums[test_end:valid_end])
train_problems.extend(problem_nums[valid_end:])
print(len(test_problems), len(valid_problems), len(train_problems))
assert not any(set(test_problems) & set(valid_problems))
assert not any(set(valid_problems) & set(train_problems))
assert not any(set(test_problems) & set(train_problems))

#%% write problem IDs
args.output_dir.mkdir(exist_ok=True)
test_output = args.output_dir / "test_problems.txt"
valid_output = args.output_dir / "valid_problems.txt"
train_output = args.output_dir / "train_problems.txt"
test_output.write_text("\n".join([f"p{pnum:05}" for pnum in sorted(test_problems)]) + "\n")
valid_output.write_text("\n".join([f"p{pnum:05}" for pnum in sorted(valid_problems)]) + "\n")
train_output.write_text("\n".join([f"p{pnum:05}" for pnum in sorted(train_problems)]) + "\n")

#%% write submission IDs
problem_to_split = {}
problem_to_split.update({n: "test" for n in test_problems})
problem_to_split.update({n: "valid" for n in valid_problems})
problem_to_split.update({n: "train" for n in train_problems})
split_to_submission_writer = {
    s: open(args.output_dir / f"{s}_submissions.txt", "w")
    for s in [
        "test",
        "valid",
        "train",
    ]
}
split_to_sequence_writer = {
    s: jsonlines.open(args.output_dir / f"{s}.jsonl", "w")
    for s in [
        "test",
        "valid",
        "train",
    ]
}
try:
    with jsonlines.open(args.input_file) as reader:
        for sequence in tqdm.tqdm(reader, desc="write splits"):
            problem_id, language, submission_filename = sequence["filepath"].split("/")
            submission_num = submission_filename.split(".")[0]  # keep as string please
            problem_num = int(problem_id[1:])
            split = problem_to_split[problem_num]
            split_to_submission_writer[split].write(submission_num + "\n")
            split_to_sequence_writer[split].write(sequence)
finally:
    for writer in split_to_submission_writer.values():
        writer.close()
