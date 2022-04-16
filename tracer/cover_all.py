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

logging.basicConfig(level=logging.DEBUG if (args.sample_problems <= 5 and args.sample_from_each_lang is not None and args.sample_from_each_lang <= 5) else logging.INFO)
log = logging.getLogger()


filext_to_lang = {
    "c": "C",
    "cpp": "C++",
    "java": "Java",
}
lang_to_filext = {v: k for k, v in filext_to_lang.items()}

base_dir = Path("../../Project_CodeNet")
input_dir = Path("../../all_input_output")
metadata_dir = base_dir / "metadata"
new_src_dir = Path("../../Project_CodeNet_full2/Project_CodeNet/data")
out_dir = Path("instrumented_output")
exe_dir = Path("instrumented_exes")
out_metadata_dir = Path("instrumented_metadata")
out_metadata_dir.mkdir(exist_ok=True, parents=True)

enabled_languages = "C C++".split()

def clean_coverage(submission_id, all_files=True):
    if all_files:
        g = f"{submission_id}*.gc*"
    else:
        g = f"{submission_id}*.gcda"
    for of in Path.cwd().glob(g):
        of.unlink()

def compile_coverage(src_filepath, exe_filepath):
    if src_filepath.name.endswith(".c"):
        cc = "gcc"
    if src_filepath.name.endswith(".cpp"):
        cc = "g++"
    proc = subprocess.run(f"{cc} --coverage {src_filepath} -o {exe_filepath}", shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.stdout:
        log.debug(f"compile {src_filepath} -> {exe_filepath} stdout: {proc.stderr}")
    if proc.stderr:
        log.debug(f"compile {src_filepath} -> {exe_filepath} stderr: {proc.stderr}")

def run_input(exe_filepath, infile, outfile=sys.stdout):
    proc = subprocess.run(f"./{exe_filepath}", stdin=infile, stdout=outfile, stderr=subprocess.PIPE, text=True, timeout=3)
    if proc.stderr:
        log.debug(f"run {exe_filepath} stderr: {proc.stderr}")
    return proc

def run_gcov(src_filename, outfile=sys.stdout):
    proc = subprocess.run(f"gcov -b -c {src_filename}", shell=True, check=True, stdout=outfile, stderr=subprocess.PIPE, text=True)
    if proc.stderr:
        log.debug(f"gcov {src_filename} stderr: {proc.stderr}")
    return proc

def do_one(problem_num, write=True):
    problem_name = 'p' + str(problem_num).rjust(5, "0")
    out_metadata_file = out_metadata_dir / (problem_name + "_coverage.csv")
    if out_metadata_file.exists():
        log.debug(f"{problem_name} done")
        df = pd.read_csv(str(out_metadata_file))
        return list(df["outcome"])

    try:
        problem_csv = metadata_dir / (problem_name + '.csv')

        df = pd.read_csv(str(problem_csv))
        total = len(df)
        df = df[df["language"].isin(enabled_languages)]
        if args.sample_from_each_lang:
            groups = []
            for lang, group in df.groupby("language"):
                group_cut = group.head(min(args.sample_from_each_lang, len(group)))
                if len(group_cut) > 0:
                    groups.append(group_cut)
            df = pd.concat(groups)
        if args.shuffle:
            df = shuffle(df, random_state=0)
        df["outcome"] = "unknown"
        log.info(f"covering {problem_name} {len(df)=}")
    except Exception:
        log.exception(f"error processing {problem_name}, skipping")
        return [f"{problem_name}_error"]

    for i, row in df.iterrows():
        def set_outcome(status):
            if df.at[i, "outcome"] == "unknown":
                df.at[i, "outcome"] = status
            else:
                df.at[i, "outcome"] = df.at[i, "outcome"] + "," + status

        try:
            src_filepath = new_src_dir / row["problem_id"] / row["language"] / (row["submission_id"] + '.' + lang_to_filext[row["language"]])
            log.debug(f"covering {src_filepath}")
            assert src_filepath.exists(), src_filepath

            exe_filepath = exe_dir / row["problem_id"] / row["language"] / row["submission_id"]
            exe_filepath.parent.mkdir(exist_ok=True, parents=True)
            try:
                compile_coverage(src_filepath, exe_filepath)
            except subprocess.CalledProcessError as e:
                log.debug(f"outcome: compile error\n{traceback.format_exc()}")
                set_outcome("compile_error")
                continue

            sub_out_dir = out_dir / row["problem_id"] / row["language"] / row["submission_id"]
            sub_out_dir.mkdir(exist_ok=True, parents=True)

            for input_filepath in sorted((input_dir / row["problem_id"]).glob("input_*.txt")):
                clean_coverage(row["submission_id"], all_files=False)
                def get_output_filepath(suffix):
                    return sub_out_dir / (input_filepath.stem + suffix)

                try:
                    with (
                        open(input_filepath, "r") as infile,
                        open(get_output_filepath(".stdout"), "w") as outfile,
                        open(get_output_filepath(".exitcode"), "w") as exitcodefile
                        ):
                        proc = run_input(exe_filepath, infile, outfile)
                        exitcodefile.write(str(proc.returncode))
                except subprocess.CalledProcessError as e:
                    log.debug(f"outcome: run error\n{traceback.format_exc()}")
                    set_outcome("run_error")
                    continue
                except subprocess.TimeoutExpired as e:
                    log.debug(f"outcome: timeout\n{traceback.format_exc()}")
                    set_outcome("timeout")
                    continue
                
                try:
                    with open(get_output_filepath(".gcov_stdout"), "w") as outfile:
                        run_gcov(src_filepath.name, outfile=outfile)
                except subprocess.CalledProcessError as e:
                    log.debug(f"outcome: gcov error\n{traceback.format_exc()}")
                    set_outcome("gcov_error")
                    continue
                gcov_filepath = Path(src_filepath.name + ".gcov")
                if gcov_filepath.exists():
                    shutil.move(gcov_filepath, get_output_filepath(".gcov"))

            # move extra gcov files to another directory
            clean_coverage(row["submission_id"])
            log.debug(f"outcome: success")
            set_outcome("success")
        except Exception:
            log.exception("unhandled error")
            set_outcome("error")
            clean_coverage(row["submission_id"])

    if write:
        df.to_csv(str(out_metadata_file))

def test_do_one():
    do_one(1000, write=False)

problems = range(args.sample_problems)
it = problems
if args.nproc > 1:
    it = Pool(args.nproc).imap_unordered(do_one, it)
else:
    it = (do_one(p) for p in it)

for _ in tqdm.tqdm(it, total=len(problems), desc="running coverage"):
    pass
