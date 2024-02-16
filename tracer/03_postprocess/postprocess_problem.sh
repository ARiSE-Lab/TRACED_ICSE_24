#!/bin/bash
for f in $(ls "trace/p${$1}/C/*/*_log.xml")
do
    dst_f="trace_tree/$(realpath --relative-to trace $(dirname $f))"
    python 03_postprocess/transform_xml.py "$f" --schema tree --output "$dst_f"
done
