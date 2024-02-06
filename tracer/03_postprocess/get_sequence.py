"""
Putting sequence together
get_sequence parses the entire sequence from various files: input, output, XML log, source code...
Check it out as some files may be commented out for debuggnig purpose.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import traceback
import json
import os

from get_trace import *


def get_sequence(
    lang,
    problem,
    solution,
    input_id,
    src_file,
    log_file,
    input_file,
    output_file,
    verbose=False,
):
    src_file = Path(src_file)
    log_file = Path(log_file)
    if input_file is not None:
        input_file = Path(input_file)
    output_file = Path(output_file)
    sequence = {}
    try:
        sequence["lang"] = lang
        sequence["input_no"] = input_id

        # Find source filepath
        sequence["filepath"] = str(src_file.relative_to(src_file.parent.parent.parent))

        if verbose:
            print(lang, problem, solution, input_id)
            print(log_file)
            print(output_file)
            print(src_file)

        # handle error states
        if not log_file.exists():
            sequence["outcome"] = "missing_log"
            return sequence
        if not output_file.exists():
            sequence["outcome"] = "missing_output"
            return sequence
        if not src_file.exists():
            sequence["outcome"] = "missing_src"
            return sequence
        if os.path.getsize(log_file) > 1e9:
            sequence["outcome"] = "toobig_log"
            return sequence
        if os.path.getsize(src_file) > 1e9:
            sequence["outcome"] = "missing_src"
            return sequence
        if os.path.getsize(output_file) > 1e9:
            sequence["outcome"] = "missing_output"
            return sequence

        # Get source code
        with open(src_file, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        lines = [
            " ".join(l.rstrip().split()) + f"// L{i}"
            for i, l in enumerate(lines, start=1)
            if l and not l.isspace()
        ]
        sequence["src"] = "\n".join(lines)

        # Get input and output
        if input_file is not None:
            with open(input_file, encoding="utf-8", errors="replace") as f:
                sequence["input"] = f.read()
        with open(output_file, encoding="utf-8", errors="replace") as f:
            sequence["output"] = f.read()

        # Map line number to variables/values
        sequence["trace"], any_modified, timed_out = get_trace(log_file, lang)

        outcome = "success"
        if not any_modified:
            outcome += "_short_trace"
        if timed_out:
            outcome += "_timed_out"
        sequence["outcome"] = outcome
    except ET.ParseError:
        sequence["outcome"] = "parse_error"
        sequence["error_msg"] = traceback.format_exc()
    except Exception:
        sequence["outcome"] = "error"
        sequence["error_msg"] = traceback.format_exc()

    return sequence


def print_seq(seq):
    import re

    try:
        if seq["outcome"] == "error":
            print(json.dumps(seq, indent=2))
            return
        print(seq["outcome"])
        if "success" not in seq["outcome"]:
            return
        print(seq["filepath"])
        print(seq["src"])
        print(re.sub(r"(L[0-9]+)", r"\n\1", seq["trace"]))
    except Exception:
        print("problem", json.dumps(seq, indent=2))
        raise
