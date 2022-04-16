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

## params
sample_problems = 5
sample_from_each_lang = 50
## params

logging.basicConfig(level=logging.DEBUG if sample_problems <= 5 and sample_from_each_lang <= 5 else logging.INFO)
log = logging.getLogger()


filext_to_lang = {
    "c": "C",
    "cpp": "C++",
    "java": "Java",
}
lang_to_filext = {v: k for k, v in filext_to_lang.items()}

base_dir = Path("../Project_CodeNet")
input_dir = Path("../all_input_output")
metadata_dir = base_dir / "metadata"
new_src_dir = Path("../Project_CodeNet_full2/Project_CodeNet/data")
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
    proc = subprocess.run(f"./{exe_filepath}", stdin=infile, stdout=outfile, stderr=subprocess.PIPE, text=True, timeout=10)
    if proc.stderr:
        log.debug(f"run {exe_filepath} stderr: {proc.stderr}")
    return proc

def run_gcov(src_filename, outfile=sys.stdout):
    proc = subprocess.run(f"gcov -b -c {src_filename}", shell=True, check=True, stdout=outfile, stderr=subprocess.PIPE, text=True)
    if proc.stderr:
        log.debug(f"gcov {src_filename} stderr: {proc.stderr}")
    return proc

def do_one(problem_num):
    problem_name = 'p' + str(problem_num).rjust(5, "0")
    problem_csv = metadata_dir / (problem_name + '.csv')

    df = pd.read_csv(str(problem_csv))
    total = len(df)
    df = df[df["language"].isin(enabled_languages)]

    df = pd.concat((group.head(sample_from_each_lang) for lang, group in df.groupby("language"))) # NOTE: for debug, get 1 from each eligible language
    df["outcome"] = "unknown"
    log.info(f"covering {problem_name} {len(df)=}")

    for i, row in df.iterrows():
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
                df.at[i, "outcome"] = "compile_error"
                continue

            sub_out_dir = out_dir / row["problem_id"] / row["language"] / row["submission_id"]
            sub_out_dir.mkdir(exist_ok=True, parents=True)

            for input_filepath in sorted((input_dir / row["problem_id"]).glob("input_*.txt")):
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
                    df.at[i, "outcome"] = "run_error"
                    continue
                except subprocess.TimeoutExpired as e:
                    log.debug(f"outcome: timeout\n{traceback.format_exc()}")
                    df.at[i, "outcome"] = "timeout"
                    continue
                
                try:
                    with open(get_output_filepath(".gcov_stdout"), "w") as outfile:
                        run_gcov(src_filepath.name, outfile=outfile)
                except subprocess.CalledProcessError as e:
                    log.debug(f"outcome: gcov error\n{traceback.format_exc()}")
                    df.at[i, "outcome"] = "gcov_error"
                    continue
                gcov_filepath = Path(src_filepath.name + ".gcov")
                if gcov_filepath.exists():
                    shutil.move(gcov_filepath, get_output_filepath(".gcov"))

            # move extra gcov files to another directory
            clean_coverage(row["submission_id"])
            log.debug(f"outcome: success")
            df.at[i, "outcome"] = "success"
        except Exception:
            log.exception("unhandled error")
            df.at[i, "outcome"] = "error"

    df.to_csv(str(out_metadata_dir / (problem_name + "_coverage.csv")))
    return list(df["outcome"])

# problems = range(4053)
problems = range(sample_problems)
# problems = range(1)
it = problems
it = Pool(3).imap_unordered(do_one, it)
# it = Parallel(n_jobs=3)(delayed(do_one)(p) for p in it)  # parallel
# it = (do_one(p) for p in it)  # sequential

outcomes = defaultdict(int)
for outcome_set in tqdm.tqdm(it, total=len(problems), desc="running coverage"):
    for outcome in outcome_set:
        outcomes[outcome] += 1
print(json.dumps(outcomes, indent=2))
