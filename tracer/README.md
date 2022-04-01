# Java tracer

Uses GDB (GNU DeBugger). Outputs XML of the program trace to `logs/` and text output of the program `outputs/`.
Tested with `GNU gdb (GDB) 8.2`.

## How to generate traces

Run this command to compile and run the test program. The expected output is in `test/expected` (`analyze_output.txt` should match the console output of `./analyze`).

```bash
./analyze test/test.cpp test/input.txt --compile --infer_output_files  # Compile and run test/test.cpp with input test/input.txt; output to logs/ and outputs/
```

## How to convert traces to `.jsonl` format

We use a sequenceizer script to read the XML trace, perform preprocessing, and output `.jsonl` format.
TODO
