"""
Print counts of valid submissions in each problem.
Used for sanity checking tracer output.
"""

import functools
import pandas as pd
from collections import defaultdict
from pathlib import Path
import tqdm
import json
from multiprocessing import Pool


def get_problem_iterator(begin, end, fn, nproc, **kwargs):
    problems = range(begin, end + 1)
    it = problems
    fn = functools.partial(fn, **kwargs)
    if nproc > 1:
        it = Pool(nproc).imap_unordered(fn, it)
    else:
        it = (fn(p) for p in it)

    return tqdm.tqdm(it, initial=begin, total=len(problems), desc="problems")


source_root_dir = Path(__file__).absolute().parent.parent  # trace-modeling repo
base_dir = source_root_dir / "../Project_CodeNet"
metadata_dir = base_dir / "metadata"


def do_one(problem_num):
    problem_name = "p" + str(problem_num).rjust(5, "0")
    problem_csv = metadata_dir / (problem_name + ".csv")
    df = pd.read_csv(str(problem_csv))
    df = df[df["language"].isin(["C", "C++"])]
    df = df[df["status"] != "Compile Error"]
    return problem_name, dict(df["language"].value_counts())


count_by_lang_total = defaultdict(int)
with get_problem_iterator(0, 4052, do_one, 1) as pbar:
    for problem_id, count_by_lang in pbar:
        pbar.set_description(f"{problem_id}: {count_by_lang}")
        for k in count_by_lang:
            count_by_lang_total[k] += int(count_by_lang[k])
print(json.dumps(count_by_lang_total, indent=2))
