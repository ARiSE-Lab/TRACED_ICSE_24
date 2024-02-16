import re


def trace_to_linenos(trace):
    """Convert trace text to list of line numbers"""
    return re.findall(r"\b(L[0-9]+)\b", trace)
