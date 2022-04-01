
from pathlib import Path
import xml.etree.ElementTree as ET
import tqdm.auto as tqdm
import joblib

def get_files(args, path, problem_list):
    """Yield files in a directory based on an index"""
    i = 0
    for problem_id in problem_list:
        problem_index = path / f'sorted_input_{problem_id}.txt'
        if not problem_index.exists():
            continue
        num_solutions = 0
        with open(problem_index) as f:
            line = f.readline().strip()

            i += 1
            num_solutions += 1
            yield path / line
            while line:
                line = f.readline().strip()
                i += 1
                num_solutions += 1
                yield path / line
                if args.test and i >= 1000:
                    return
                if args.limit_solutions is not None and num_solutions >= args.limit_solutions:
                    break

        #return [path / p for p in sorted(f.readlines())]

def get_log_files(args):
    """Get dicts of all log files and all output files"""

    if args.begin is not None or args.end is not None:
        assert args.begin is not None
        assert args.end is not None
        assert args.begin < args.end
        problem_list = [('p' + str(i).rjust(5, '0')) for i in range(args.begin, args.end+1)]
        print('cut to', len(problem_list), 'problems: ', list(sorted(problem_list)))

    log_files = {}
    output_files = {}
    for base_dir in args.base_dirs:
        base_dir = Path(base_dir)
        for log_file in tqdm.tqdm(get_files(args, base_dir / 'logs', problem_list)):
            if args.test: assert log_file.exists(), log_file
            try:
                lang, problem, solution, input_str, input_id = log_file.stem.split('_')
                run_id = (lang, problem, solution, input_id)
                log_files[run_id] = log_file
            except ValueError:
                continue
        for output_file in tqdm.tqdm(get_files(args, base_dir / 'outputs', problem_list)):
            if args.test: assert output_file.exists(), log_file
            try:
                lang, problem, solution, input_str, input_id = output_file.stem.split('_')
                run_id = (lang, problem, solution, input_id)
                output_files[run_id] = output_file
            except ValueError:
                continue
    return log_files, output_files