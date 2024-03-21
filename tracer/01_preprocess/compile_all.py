"""
Compile all C/C++ programs in CodeNet
"""

from pathlib import Path
import pandas as pd
import tqdm
import traceback
import subprocess
import logging
from multiprocessing import Pool
import os
import argparse
import copy
import functools

compile_envs = copy.deepcopy(os.environ)
compile_envs["LD_LIBRARY_PATH"] = "/usr/lib/x86_64-linux-gnu/debug/"

args = None

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

filext_to_lang = {
    "c": "C",
    "cpp": "C++",
}
lang_to_filext = {v: k for k, v in filext_to_lang.items()}

source_root_dir = Path(__file__).absolute().parent.parent  # trace-modeling repo
base_dir = source_root_dir / "../Project_CodeNet"
metadata_dir = base_dir / "metadata"
src_dir = base_dir / "data"

output_dir = source_root_dir / "compile_output"
output_dir.mkdir(parents=True, exist_ok=True)
metadata_output_dir = source_root_dir / "compile_metadata"
metadata_output_dir.mkdir(parents=True, exist_ok=True)


def get_problem_iterator(begin, end, fn, nproc, **kwargs):
    problems = range(begin, end + 1)
    it = problems
    fn = functools.partial(fn, **kwargs)
    if nproc > 1:
        it = Pool(nproc).imap_unordered(fn, it)
    else:
        it = (fn(p) for p in it)

    return tqdm.tqdm(it, initial=begin, total=len(problems), desc="problems")


def compile_one(problem_id, language, submission_id, solution_file):
    try:
        exe_file = output_dir / problem_id / language / submission_id
        exe_file.parent.mkdir(parents=True, exist_ok=True)
        if language == "C":
            compiler = "gcc"
            compile_cmd_args = [
                compiler,
                "-g",
                "-O0",
                "-std=c99",
                str(solution_file),
                "-o",
                str(exe_file),
            ]
        elif language == "C++":
            compiler = "g++"
            compile_cmd_args = [
                compiler,
                "-g",
                "-O0",
                "-std=c++11",
                str(solution_file),
                "-o",
                str(exe_file),
            ]
        else:
            raise NotImplementedError(language)

        # log.debug(f"{compile_cmd_args=}")
        proc = subprocess.run(
            compile_cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=compile_envs,
        )

        try:
            stdout = proc.stdout.decode()
        except Exception:
            stdout = None

        if proc.returncode != 0:
            return {
                "outcome": "compile_error",
                "stdout": stdout,
                "returncode": 1,
            }

        return {
            "outcome": "success",
            "stdout": stdout,
        }
    except Exception as e:
        return {
            "outcome": "error",
            "exception": traceback.format_exc(),
        }


def do_one(problem_num, sample_submissions):
    problem_name = "p" + str(problem_num).rjust(5, "0")
    out_metadata_file = metadata_output_dir / (problem_name + ".csv")
    if out_metadata_file.exists():
        df = pd.read_csv(str(out_metadata_file))
        log.info(f"loading {out_metadata_file} {df.columns=}")
    else:
        problem_csv = metadata_dir / (problem_name + ".csv")
        df = pd.read_csv(str(problem_csv))
        df = df[df["language"].isin(["C", "C++"])]
        if sample_submissions:
            df = df.sample(sample_submissions, random_state=0)

        for i, row in tqdm.tqdm(df.iterrows(), total=len(df), desc="rows"):
            filext = lang_to_filext[row["language"]]
            solution_file = (
                src_dir
                / row["problem_id"]
                / row["language"]
                / (row["submission_id"] + "." + filext)
            )
            for key, value in compile_one(
                row["problem_id"], row["language"], row["submission_id"], solution_file
            ).items():
                df.at[i, key] = value
        df.to_csv(str(out_metadata_file))
    log.info(str(problem_name) + " " + str(df["outcome"].value_counts()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--begin_problem", type=int, help="first problem", default=0)
    parser.add_argument("--end_problem", type=int, help="last problem", default=4053)
    parser.add_argument(
        "--sample_submissions", type=int, help="submissions to sample per problem"
    )
    parser.add_argument(
        "--nproc", type=int, help="number of concurrent processes", default=1
    )
    args = parser.parse_args()

    args.end_problem = min(4053, args.end_problem)

    for _ in get_problem_iterator(
        args.begin_problem,
        args.end_problem,
        do_one,
        args.nproc,
        sample_submissions=args.sample_submissions,
    ):
        pass
