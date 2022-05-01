"""
Template for metadata-based processing of codenet
"""

import json
from pathlib import Path
import pandas as pd
import tqdm
import sys
from joblib import Parallel, delayed
import traceback
import subprocess
import shutil
import json
from collections import defaultdict
import sys
import logging
from multiprocessing import Pool
from sklearn.utils import shuffle

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--sample_problems", type=int, help="number of problems to sample", default=4053)
parser.add_argument("--sample_from_each_lang", type=int, help="number of submissions from each language to sample from each problem")
parser.add_argument("--nproc", type=int, help="number of concurrent processes", default=1)
parser.add_argument("--shuffle", action="store_true", help="whether to shuffle the data before sampling")
args = parser.parse_args()

logging.basicConfig()
log = logging.getLogger()


filext_to_lang = {
    "c": "C",
    "cpp": "C++",
    "java": "Java",
}
lang_to_filext = {v: k for k, v in filext_to_lang.items()}

source_root_dir = Path(__file__).parent.parent.absolute()  # trace-modeling repo
base_dir = source_root_dir / "../Project_CodeNet"
metadata_dir = base_dir / "metadata"
src_dir = base_dir / "data"
input_dir = source_root_dir / "../all_input_output"

def do_one(problem_num, write=True):
    problem_name = 'p' + str(problem_num).rjust(5, "0")
    problem_csv = metadata_dir / (problem_name + '.csv')
    print(problem_name, problem_csv)

def get_problem_iterator(begin, end, fn, nproc=1):
    problems = range(begin, end+1)
    it = problems
    if nproc > 1:
        it = Pool(nproc).imap_unordered(fn, it)
    else:
        it = (fn(p) for p in it)

    return tqdm.tqdm(it, initial=begin, total=len(problems))
