#!/bin/bash
# trace submissions in a problem
# example:
# bash trace_collection_c_cpp/trace_problem.sh data/compiled/data/Project_CodeNet/data data/trace data/sample_input_output_full p00001 C -0

if [ "$#" -ne 6 ]; then
    echo "Incorrect Usage: $0 $@"
    exit 1
fi

# arguments
exe_dir="$1"
trace_root="$2"
input_root="$3"
problem_id="$4"
lang="$5"
head_n="$6"  # -n argument to head. Supply "-0" to take all. default -0
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

input_dir="$input_root/$problem_id"
if [ ! -d "$input_dir" ]
then
    echo "no input dir $input_dir"
    exit 1
fi

# log files
dst_dir="$trace_root/trace/$problem_id/$lang"
error_log="$dst_dir/error.log"
trace_log="$dst_dir/trace.log"
exitcode_log="$dst_dir/exitcodes.log"
mkdir -p $dst_dir
rm -f "$error_log" "$trace_log"
seed=42

while read src_filename
do
    for input_filepath in $input_dir/input_*.txt
    do
        timeout_duration="10s"
        (timeout $timeout_duration $script $exe_dir $problem_id $lang $src_filename $input_filepath $trace_root -v 2) >> $trace_log 2>> "$error_log"
        exitcode="$?"
        echo $src_filename $input_filepath $exitcode >> $exitcode_log
        # patch up log after timeout
        if [ "$exitcode" == 124 ]
        then
            echo $src_filename $input_filepath $exitcode timed out >> $error_log
            log_file="$dst_dir/$(basename $src_filename)/$(basename $input_filepath)_log.xml"
            echo "<timeout amount=\"$timeout_duration\"/>" >> $log_file
            echo "</trace>" >> $log_file
        fi
    done
    echo $src_filename
done < <(ls "$lang_dir" | grep -v -e .log -e .touch | shuf --random-source=<(yes $seed) | head -n $head_n) | tqdm --total $(ls "$lang_dir" | grep -v -e .log -e .touch | shuf --random-source=<(yes $seed) | head -n $head_n | wc -l) >> "$trace_log"
