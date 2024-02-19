#!/bin/bash
exe_root="$1"
input_root="$2"
trace_root="$3"
shift
shift
shift
lang="C"

for i in {00000..04052}
do
    bash 02_trace/trace_problem.sh "$exe_root" "p${i}" "$lang" "$input_root" "$trace_root" $@
done
