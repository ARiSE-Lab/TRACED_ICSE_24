import copy
import re
from .parser import get_parsed_info

from .utils import trace_to_linenos


def separate_lines(sequence):
    """Return sequence with source code and covered lines split by line."""
    cov_sequence = copy.deepcopy(sequence)
    cov_sequence["input"] = sequence["input"]
    cov_sequence["src_lines"] = src_lines = []
    cov_sequence["src_linenos"] = src_linenos = []
    cov_sequence["count_in_trace"] = counts_in_trace = []
    trace_linenos = [int(t[1:]) for t in trace_to_linenos(sequence["trace"])]
    code_lines = sequence["src"].splitlines(keepends=True)

    parsed_info = get_parsed_info(sequence["src"], sequence["lang"])

    for j, line in enumerate(code_lines):
        m = re.search(r"// (L[0-9]+)", line)
        line_number_token = None
        count_in_trace = 0
        if m is not None:
            line_number_token = m.group(1)
            line_number = int(line_number_token[1:])
            count_in_trace = trace_linenos.count(line_number)
            line = line[: m.start()].rstrip()
        src_lines.append(line)
        src_linenos.append(line_number_token)
        counts_in_trace.append(count_in_trace)

    cov_sequence["covered_in_trace"] = covered = [n > 0 for n in counts_in_trace]

    # handle "while (1)" and such like branch mode does
    for i, c in enumerate(covered):
        if not c and line_number_token in parsed_info.regardless_covered_linenos:
            dest_lineno = parsed_info.regardless_covered_linenos[line_number_token]
            dest_idx = src_linenos.index(dest_lineno)
            covered[i] = covered[dest_idx]

    assert len(cov_sequence["src_linenos"]) == len(cov_sequence["covered_in_trace"])
    assert len(cov_sequence["src_linenos"]) == len(cov_sequence["src_lines"])

    # remove long & unnecessary fields from output
    del cov_sequence["src"]
    del cov_sequence["trace"]
    del cov_sequence["output"]
    return cov_sequence
