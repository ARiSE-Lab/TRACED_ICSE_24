# C tracer

Uses GDB (GNU DeBugger). Outputs XML of the program trace to `logs/` and text output of the program `outputs/`.
Tested with `GNU gdb (GDB) 8.2`.

## How to generate traces

Run this command to compile and run the test program. The expected output is in `test/expected` (`test/expected/analyze_output.txt` should match the console output of `./analyze`).

```bash
./analyze test/p00001/C/s000149616.c test/p00001/input_0.txt --compile --infer_output_files -v  # Compile and run s000149616.c with input input_0.txt; output to logs/ and outputs/
```

## How to convert traces to `.jsonl` format

We use a sequenceizer script to read the XML trace, perform preprocessing, and output `.jsonl` format.
You should get console output matching `test/expected/sequenceize_logs_c_output.txt`.

```bash
python sequenceize_logs_c.py --base_dirs . --lang c --src_dirs test --input_dirs test
```
