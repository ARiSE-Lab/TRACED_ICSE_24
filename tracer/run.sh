#!/bin/bash

num_executions=1
for i in $(seq 1 "$num_executions")
do
    time ./test < testdata.txt
done
