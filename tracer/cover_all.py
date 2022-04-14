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


filext_to_lang = {
    "c": "C",
    "cpp": "C++",
    "java": "Java",
}
lang_to_filext = {v: k for k, v in filext_to_lang.items()}

base_dir = Path("../Project_CodeNet")
input_dir = Path("../all_input_output")
metadata_dir = base_dir / "metadata"
out_dir = Path("instrumented_output")
new_src_dir = Path("../Project_CodeNet_full2/Project_CodeNet/data")

enabled_languages = "C C++".split()

def do_one(problem_num):
    problem_name = 'p' + str(problem_num).rjust(5, "0")
    problem_csv = metadata_dir / (problem_name + '.csv')

    df = pd.read_csv(str(problem_csv))
    total = len(df)
    df = df[df["language"].isin(enabled_languages)]

    df = pd.concat((group.head(1) for lang, group in df.groupby("language"))) # NOTE: for debug, get 1 from each eligible language

    for i, row in df.iterrows():
        try:
            src_file = new_src_dir / row["problem_id"] / row["language"] / (row["submission_id"] + '.' + lang_to_filext[row["language"]])
            print("covering", src_file)
            assert src_file.exists(), src_file
            input_file = sorted((input_dir / row["problem_id"]).glob("input_*.txt"))[0]
            # Measure coverage
            cmd = f"./gcov_generate {src_file} {input_file}"
            print(cmd)
            proc = subprocess.run(cmd, shell=True, timeout=10)
            if proc.returncode == 0:
                yield "success"
            elif proc.returncode == 1:
                yield "bad arguments"
            elif proc.returncode == 2:
                yield "clean error"
            elif proc.returncode == 3:
                yield "compile error"
            elif proc.returncode == 4:
                yield "gcov error"
            sub_out_dir = out_dir / row["problem_id"] / row["language"] / row["submission_id"]
            sub_out_dir.mkdir(exist_ok=True, parents=True)
            for of in Path.cwd().glob("*.gc*"):
                shutil.move(of, sub_out_dir / of.name)
        except Exception:
            traceback.print_exc()

# problems = range(4053)
problems = range(5)
# problems = range(1)
it = tqdm.tqdm(problems, "problems")
# it = Parallel(n_jobs=8)(delayed(do_one)(p) for p in it)  # parallel
it = (do_one(p) for p in it)  # sequential

outcomes = defaultdict(int)
for outcome_set in it:
    for outcome in outcome_set:
        outcomes[outcome] += 1
print(json.dumps(outcomes, indent=2))
