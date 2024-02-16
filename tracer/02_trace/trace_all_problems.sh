#!/bin/bash
for i in {00000..04052}
do
    bash 02_trace/trace_problem.sh compile_output/ "$1" all_input_output/ "p${i}" C "-0"
done
