import copy
from .utils import trace_to_linenos


def trim(sequence):
    """
    Return sequence with all fields the same except trace is trimmed to only line numbers
    (remove variable state information).
    """
    cov_sequence = copy.deepcopy(sequence)
    cov_sequence["trace_lineno"] = trace_to_linenos(sequence["trace"])
    # remove long & unnecessary fields from output
    del cov_sequence["trace"]
    del cov_sequence["output"]
    return cov_sequence
