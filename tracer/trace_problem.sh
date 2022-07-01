#!/bin/bash
# trace submissions in a problem
# example:
# bash trace_collection_c_cpp/trace_problem.sh data/compiled/data/Project_CodeNet/data data/trace p00001 C -0

if [ "$#" -ne 4 ]; then
    echo "Incorrect Usage: $0 $@"
    exit 1
fi

# arguments
exe_dir="$1"
trace_root="$2"
problem_id="$3"
lang="$4"
head_n="$5"  # -n argument to head. Supply "-0" to take all. default -0
if [ -z "$head_n" ]
then
    head_n="-0"
fi

script="$(dirname $0)/analyze"
ls $script || exit 1
gcc --version || exit 1
g++ --version || exit 1

# input dir
problem_dir="$exe_dir/$problem_id"
lang_dir="$problem_dir/$lang"
# output dir - prefix dst_dir with lang_dir
mkdir -p "$trace_root"

# log files
dst_dir="$trace_root/trace/$problem_id/$lang"
error_log="$dst_dir/error.log"
trace_log="$dst_dir/trace.log"
mkdir -p $dst_dir
rm -f "$error_log" "$trace_log"

while read src_filename
do
    for input_filepath in data/sample_input_output_full/$problem_id/input_*.txt
    do
        $script $exe_dir $problem_id $lang $src_filename $input_filepath $trace_root -v 2 >> $trace_log 2>> "$error_log"
    done
    echo $src_filename
done < <(ls "$lang_dir" | grep -v -e .log -e .touch | head -n $head_n) | tqdm --total $(ls $lang_dir | wc -l) >> "$trace_log"
