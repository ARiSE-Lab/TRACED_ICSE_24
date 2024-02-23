#!/bin/bash
log_dir="$1"
tree_dir="$log_dir/tree"
sequence_dir="$log_dir/sequences"
codenet_dir="$(dirname $0)/../Project_CodeNet"
mkdir -p "$tree_dir" "$sequence_dir"

# Convert to tree-format XML
for i in {00000..04052}
do
    for logfile in $(find $1/trace/"p$i"/C -name '*_log.xml')
    do
        dstfile="$tree_dir/$(realpath --relative-to "$log_dir/trace" "$logfile")"
        mkdir -p "$(dirname $dstfile)"
        python 03_postprocess/transform_xml.py "$logfile" --schema tree --output "$dstfile"
        cp "$(dirname $logfile)"/*_stdout.txt "$(dirname $dstfile)/"
    done
done

# Convert to JSONL
python 03_postprocess/sequenceize_logs_from_metadata.py --lang C --base_dirs "$tree_dir" --src_dirs "$codenet_dir/data" --input_dir all_input_output --metadata_dir "$codenet_dir/metadata" --begin_problem 0 --end_problem 4052 --output "$sequence_dir"
