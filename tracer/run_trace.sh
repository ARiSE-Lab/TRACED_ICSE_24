#!/bin/bash

num_executions=1
for i in $(seq 1 "$num_executions")
do
    time gdb -batch -nh -x trace.gdb test
done
