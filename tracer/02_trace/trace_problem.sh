#!/bin/bash
exe_root="$1"
problem="$2"
lang="$3"
input_root="$4"
trace_root="$5"
shift
shift
shift
shift
shift

set -e

for solution in $(find $exe_root/$problem/$lang -executable -type f -name 's*' | xargs -n1 basename)
do
    for input_file in $(find $input_root/$problem -type f -name 'input_*.txt')
    do
        python 02_trace/analyze.py "$exe_root" "$problem" "$lang" "$solution" "$input_file" "$trace_root" --verbose 1 $@
    done
done
