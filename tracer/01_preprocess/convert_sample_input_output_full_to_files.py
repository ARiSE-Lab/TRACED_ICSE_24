"""
Read all entries from JSON-encoded inputs/expected outputs for CodeNet and echo to individual files.
Last output:

write input/output files: 100%|██████████████████| 3999/3999 [00:31<00:00, 125.36it/s]
wrote 15364 files
"""

import json
from pathlib import Path
import tqdm

if __name__ == "__main__":
    src_file = Path("all_input_output.json")
    dst_dir = Path("all_input_output")

    with src_file.open() as f:
        data = json.load(f)

    dst_dir.mkdir(exist_ok=True)

    written_problems = 0
    written_files = 0
    for problem_id, input_output in tqdm.tqdm(data.items(), desc="write input/output files"):
        problem_dir = dst_dir / problem_id
        problem_dir.mkdir(exist_ok=True)
        written_problems += 1
        for i, (_in, _out) in enumerate(zip(input_output["sample_input"], input_output["sample_output"])):
            (problem_dir / f"input_{i}.txt").write_text(_in)
            (problem_dir / f"output_{i}.txt").write_text(_out)
            written_files += 2

    print("wrote", written_problems, "problems")
    print("wrote", written_files, "files")
