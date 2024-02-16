"""
Convert sequences from tracer into "lines" format for coverage prediction

Format of each line of input:
{
    "lang": "c",
    "input_no": "input_0",
    "filepath": "p00000/C/s113530555.c",
    "src": "#include<stdio.h>// L1\nint main(){// L3\nint i,j;// L4\nfor(i=1;i<10;i++){// L6\nfor(j=1;j<10;j++){// L7...",
    "input": "",
    "output": "1x1=1\n1x2=2\n1x3=3\n1x4=4\n1x5=5\n1x6=6\n1x7=7\n1x8=8\n1x9=9\n2x1=2\n2x2=4\n2x3=6\n2x4=8\n2x5=10\n2x6...",
    "trace": "L6 new var: i = 0 new var: j = 0 L6 modified var: i = 1 L7 modified var: j = 1 L8 L7 modified var: j = ...",
    "outcome": "success"
}

Format of each line of output (separate_lines format - `python coverage_prediction/sequences_to_coverage_prediction.py --mode separate_lines`):
{
  "lang": "c",
  "input_no": "input_0",
  "filepath": "p00000/C/s113530555.c",
  "input": "",
  "outcome": "success",
  "src_lines": [
    "#include<stdio.h>",
    "int main(){",
    "int i,j;",
    "for(i=1;i<10;i++){",
    "for(j=1;j<10;j++){",
    "printf(\"%dx%d=%d\\n\",i,j,i*j);",
    "}",
    "}",
    "return 0;",
    "}"
  ],
  "src_linenos": [
    "L1",
    "L3",
    "L4",
    "L6",
    "L7",
    "L8",
    "L9",
    "L10",
    "L12",
    "L13"
  ],
  "count_in_trace": [
    0,
    0,
    0,
    11,
    90,
    81,
    0,
    0,
    1,
    1
  ],
  "covered_in_trace": [
    false,
    false,
    false,
    True,
    True,
    True,
    false,
    false,
    True,
    True
  ]
}

Format of each line of output (trim format `python coverage_prediction/sequences_to_coverage_prediction.py --mode trim`):
{
  "lang": "c",
  "input_no": "input_0",
  "filepath": "p00000/C/s113530555.c",
  "src": "#include<stdio.h>// L1\nint main(){// L3\nint i,j;// L4\nfor(i=1;i<10;i++){// L6\nfor(j=1;j<10;j++){// L7\nprintf...",
  "input": "",
  "outcome": "success",
  "trace_lineno": [
    "L6",
    "L6",
    "L7",
    ...
    "L6",
    "L12",
    "L13"
  ]
}

Branch mode.
items in "covered_in_trace" correspond to "src_lines" and "src_linenos".
how to read "covered_in_trace":
- true --> branch destination was covered
- false --> branch destination was NOT covered
- null --> this line is not a branch destination
{
  "lang": "c",
  "input_no": "input_0",
  "filepath": "p00000/C/s113530555.c",
  "input": "",
  "outcome": "success",
  "src_lines": [
    "#include<stdio.h>",
    "int main(){",
    "int i,j;",
    "for(i=1;i<10;i++){",
    "for(j=1;j<10;j++){",
    "printf(\"%dx%d=%d\\n\",i,j,i*j);",
    "}",
    "}",
    "return 0;",
    "}"
  ],
  "src_linenos": [
    "L1",
    "L3",
    "L4",
    "L6",
    "L7",
    "L8",
    "L9",
    "L10",
    "L12",
    "L13"
  ],
  "covered_in_trace": [
    null,
    null,
    null,
    true,
    true,
    true,
    null,
    null,
    true,
    null
  ]
}
"""

import argparse
import itertools
import traceback
import jsonlines
import tqdm
from .converters.branch_prediction import branch
from .converters.separate_lines import separate_lines
from .converters.trim import trim
from treehouse.ast_creator import AstErrorException


def convert_file(input_file, output_file, mode, start, stop):
    success = 0
    total = 0
    with jsonlines.open(input_file) as reader, jsonlines.open(
        output_file, "w"
    ) as writer:
        if start is not None or stop is not None:
            if start is None:
                start = 0
            print("sequencing", range(start, stop + 1))
            reader = itertools.islice(reader, start, stop + 1)
        for i, sequence in tqdm.tqdm(enumerate(reader), desc="convert sequences"):
            total += 1
            try:
                if "trace" not in sequence:
                    continue
                if mode == "separate_lines":
                    converted_sequence = separate_lines(sequence)
                elif mode == "branch":
                    converted_sequence = branch(sequence)
                elif mode == "trim":
                    converted_sequence = trim(sequence)
                else:
                    raise NotImplementedError(mode)
                writer.write(converted_sequence)
                success += 1
            except AstErrorException:
                print("AST had error on line", i)
            except Exception:
                print("error on line", i, traceback.format_exc())
                print(sequence)
                print(sequence["src"])
                print(sequence["trace"])
                continue
    print("success:", success)
    print("total:", total)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input_file",
        default="data/c_sequences.jsonl",
        help="jsonl file containing sequences from tracer.",
    )
    parser.add_argument(
        "--output_file",
        default="data/c_coverage_prediction.jsonl",
        help="Destination jsonl file",
    )
    parser.add_argument(
        "--mode",
        choices=["separate_lines", "trim", "branch"],
        default="separate_lines",
        help="Mode to convert output",
    )
    parser.add_argument(
        "--begin", type=int, default=None, help="Convert from the first N examples"
    )
    parser.add_argument(
        "--end", type=int, default=None, help="Convert to the first N examples"
    )
    parser.add_argument("--lang", type=str, default="C", help="Language to parse")
    args = parser.parse_args()

    convert_file(args.input_file, args.output_file, args.mode, args.begin, args.end)
