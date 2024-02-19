#!/usr/bin/env python3

import subprocess
import argparse
import os
from datetime import datetime
from pathlib import Path

import logging

repo_src_dir = Path(__file__).parent.absolute()
trace_py = repo_src_dir / "trace_asm.py"

assert os.path.exists(repo_src_dir), repo_src_dir
assert os.path.exists(trace_py), trace_py


def run_gdb(exe_file, input_file, log_file, output_file):
    assert exe_file.exists(), exe_file
    assert input_file.exists(), input_file

    # construct gdb command
    tracer_args = [
        "gdb",
        str(exe_file),
        "-batch",
        "-nh",
    ]

    # enable/disable stdout and stderr from gdb
    if args.verbose < 2:
        tracer_args += [
            "-ex",
            "set logging file /dev/null",
            "-ex",
            "set logging redirect on",
            "-ex",
            "set logging on",
        ]

    # set gdb options to print arrays full value
    tracer_args += [
        "-ex",
        "set print elements unlimited",
        "-ex",
        "set print repeats unlimited",
        "-ex",
        "set max-value-size unlimited",
    ]

    # import trace script, move to start of main(), and run tracer
    trace_asm_cmd = f"trace-asm {log_file}"
    if args.verbose >= 3:
        trace_asm_cmd += " -v"  # output verbose stuff from inside the trace itself
    tracer_args += [
        "-ex",
        f"source {trace_py}",
        "-ex",
        f"start < {input_file} > {output_file}",
        "-ex",
        trace_asm_cmd,
    ]

    # run
    subprocess_env = {
        **os.environ,
        "PYTHONPATH": os.environ.get("PYTHONPATH", "") + ":" + str(repo_src_dir),
    }
    log.debug(
        f"""subprocess args={' '.join(['"' + a + '"' if any(c.isspace() for c in a) else a for a in tracer_args])}"""
    )
    try:
        (Path(args.cwd_dir) / output_file).parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.Popen(
            tracer_args,
            cwd=args.cwd_dir,
            env=subprocess_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
        )
        # Read line from stdout, break if EOF reached, print line
        while proc.poll() is None:
            line = proc.stdout.readline()
            if args.verbose >= 2:
                print(line, end="")
        proc.wait(timeout=args.timeout)
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        log.info(f"Process timed out after {args.timeout} seconds")
        proc.kill()
        exit_code = 124  # Same exit code as timeout(1) command on Linux
    return exit_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("exe_dir")
    parser.add_argument("problem_id")
    parser.add_argument("language", choices=["C", "C++"])
    parser.add_argument("submission_id")
    parser.add_argument("input_file", help="file from which to pipe standard input")
    parser.add_argument("cwd_dir", nargs="?", default=".")
    parser.add_argument("-v", "--verbose", type=int, default=0)
    parser.add_argument("--timeout", default=10, type=int)
    parser.add_argument("--format", action="store_true")
    args = parser.parse_args()

    # set up logger
    log_level = logging.INFO
    if args.verbose >= 1:
        log_level = logging.DEBUG
    logging.basicConfig(
        level=log_level,
        format=f"{args.problem_id}/{args.language}/{args.submission_id} {os.path.basename(args.input_file)} %(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    log = logging.getLogger()

    log.debug(f"args={args} trace_py={trace_py}")

    # start profiling
    begin = datetime.now()
    log.info(f"begin {args.problem_id}/{args.language}/{args.submission_id}-{os.path.basename(args.input_file)}")

    # run tracer
    exe_file = (
        Path(args.exe_dir) / args.problem_id / args.language / args.submission_id
    ).absolute()
    input_file = Path(args.input_file).absolute()
    output_dir = Path("trace")
    log_file = (
        output_dir
        / args.problem_id
        / args.language
        / args.submission_id
        / (input_file.name + "_log.xml")
    )
    output_file = (
        output_dir
        / args.problem_id
        / args.language
        / args.submission_id
        / (input_file.name + "_stdout.txt")
    )
    if args.language in ("C", "C++"):
        return_code = run_gdb(exe_file, input_file, log_file, output_file)
    else:
        raise NotImplementedError(args.language)

    # try to format the log - no sweat if it fails
    if args.format:
        log_file_fullpath = Path(args.cwd_dir) / log_file
        subprocess.call(f"xmllint --format {log_file_fullpath} --output {log_file_fullpath}", shell=True)

    # end profiling
    end = datetime.now()
    elapsed = end - begin
    log.info(f"end {args.problem_id}/{args.language}/{args.submission_id}-{os.path.basename(args.input_file)}, elapsed seconds: {elapsed.total_seconds()}, exit code: {return_code}")

    exit(return_code)
