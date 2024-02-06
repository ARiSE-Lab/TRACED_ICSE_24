import pandas as pd
from pathlib import Path
import tqdm as tqdm
from get_sequence import get_sequence
import json
from collections import defaultdict
from multiprocessing import Pool

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--lang")
parser.add_argument("--base_dirs", nargs="+")
parser.add_argument("--src_dirs", nargs="+")
parser.add_argument("--input_dir", default="all_input_output")
parser.add_argument("--metadata_dir", default="data/Project_CodeNet/metadata")
parser.add_argument("--begin_problem", type=int, default=0)
parser.add_argument("--end_problem", type=int, default=4052)
parser.add_argument("--limit_solutions", type=int)
parser.add_argument("--limit_sequences", type=int)
parser.add_argument("--nproc", type=int, default=1)
parser.add_argument("--output", type=str)
args = parser.parse_args()

print(f"{args=}")

if args.output is not None:
    sequence_output_dir = Path(args.output)
    sequence_output_dir.mkdir(parents=True, exist_ok=True)
else:
    sequence_output_dir = Path.cwd()

# get and json-ize sequences

filext_to_lang = {
    "c": "C",
    "cpp": "C++",
}
lang_to_filext = {v: k for k, v in filext_to_lang.items()}

src_dirs = [Path(src_dir) for src_dir in args.src_dirs]
base_dirs = [Path(base_dir) for base_dir in args.base_dirs]

metadata_dir = Path(args.metadata_dir)
input_dir = Path(args.input_dir)


def get_sequence_all_inputs(lang, problem, solution):
    filext = lang_to_filext[lang]
    for src_dir in src_dirs:
        src_file = src_dir / problem / lang / (solution + "." + filext)
        if src_file.exists():
            break

    input_files = list((input_dir / problem).glob("input_*.txt"))

    if len(input_files) == 0:
        return []
    sequences_to_return = []
    for input_file in sorted(
        input_files, key=lambda f: f.stem if f is not None else None
    ):
        if input_file is None:
            input_id = None
        else:
            input_id = input_file.stem

        for base_dir in base_dirs:
            log_file = base_dir / problem / lang / solution / f"{input_id}.txt_log.xml"
            output_file = (
                base_dir / problem / lang / solution / f"{input_id}.txt_stdout.txt"
            )
            if log_file.exists() and output_file.exists():
                break

        sequences_to_return.append(
            get_sequence(
                filext,
                problem,
                solution,
                input_id,
                src_file,
                log_file,
                input_file,
                output_file,
            )
        )
    return sequences_to_return


def get_sequence_tuple(t):
    return get_sequence_all_inputs(*t)


sequences_filename = (
    sequence_output_dir
    / f"sequences_lang{args.lang}_from{args.begin_problem}_to{args.end_problem}_limit{args.limit_solutions}.jsonl"
)
full_sequences_filename = sequences_filename.parent / (
    sequences_filename.stem + "_full" + sequences_filename.suffix
)
with open(sequences_filename, "w") as sf, open(full_sequences_filename, "w") as full_sf:
    for problem_num in range(args.begin_problem, args.end_problem + 1):
        problem_csv = metadata_dir / f'p{str(problem_num).rjust(5, "0")}.csv'

        df = pd.read_csv(str(problem_csv))
        total = len(df)
        df = df[df["language"] == args.lang]
        df = df.sort_values(["language", "problem_id", "submission_id"])
        filtered = len(df)
        excluded = total - filtered

        num_sequences = 0
        num_success_sequences = 0
        break_all = False
        print()
        print(f"{problem_csv.name}, {total=}, {filtered=}, {excluded=}")
        postfix = defaultdict(int)
        num_success = 0
        with tqdm.tqdm(
            map(
                get_sequence_tuple,
                zip(df["language"], df["problem_id"], df["submission_id"]),
            ),
            total=len(df),
        ) as pbar:
            for i, sequences in enumerate(pbar):
                had_success = False
                for sequence in sequences:
                    sequence_str = json.dumps(sequence)
                    postfix[sequence["outcome"]] += 1
                    if sequence["outcome"] not in ["missing_log"]:
                        full_sf.write(sequence_str + "\n")
                    if sequence["outcome"] not in [
                        "success_short_trace",
                        "missing_log",
                        "parse_error",
                    ]:
                        sf.write(sequence_str + "\n")
                    if sequence["outcome"] == "success":
                        had_success = True
                        num_success += 1
                        if (
                            args.limit_sequences is not None
                            and num_success >= args.limit_sequences
                        ):
                            break_all = True
                            break
                if had_success:
                    num_success_sequences += 1
                pbar.set_postfix(postfix)

    df = df.reset_index().rename(columns={"index": "original_index"})
