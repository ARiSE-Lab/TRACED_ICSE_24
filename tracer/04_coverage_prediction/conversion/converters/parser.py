import itertools
import re
from dataclasses import dataclass
from typing import List, Dict

from treehouse.tree_sitter_utils import c_parser, cpp_parser
from treehouse.ast_creator import ASTCreator
from treehouse.cfg_creator import CFGCreator


@dataclass
class ParsedInfo:
    """Class for keeping track of an item in inventory."""

    dest_node_linenos: List[str]
    regardless_covered_linenos: Dict[str, str]


def get_parsed_info(src, lang):
    if lang == "c":
        parser = c_parser
    elif lang == "cpp":
        parser = cpp_parser
    else:
        raise NotImplementedError(lang)

    tree = parser.parse(bytes(src, "utf-8"))
    ast = ASTCreator.make_ast(tree.root_node)
    cfg = CFGCreator.make_cfg(ast)

    # get branch nodes
    branch_nodes = []
    for n in cfg.nodes():
        if len(cfg.adj[n]) > 1:
            branch_nodes.append(n)

    # map nodes based on source code lines to annotated linenos "// LXXX"
    def get_lineno(line):
        """Parse line of code to get lineno comment (// LXXX)"""
        m = re.search(r"// (L[0-9]+)", line)
        if m:
            return m.group(1)
        return None

    src_lines = src.splitlines()

    def get_node_lineno(n):
        """Helper to get LXXX for a CFG node"""
        attr = cfg.nodes[n]
        if "n" not in attr:
            return None  # no ast node - most often this means it's FUNC_EXIT or some other CFG node
        return get_lineno(src_lines[attr["n"].start_point[0]])

    # get destination nodes
    def get_dest_nodes(n):
        """Return dict of edge_attr -> destination node for a branch node n"""
        d = {}
        for m, m_attr in cfg.adj[n].items():
            label = ",".join(sorted([v["label"] for v in m_attr.values()]))
            d[label] = m
        return d

    dest_nodes = [get_dest_nodes(n) for n in branch_nodes]

    # map to lineno
    dest_node_linenos = [
        {k: get_node_lineno(v) for k, v in d.items()} for d in dest_nodes
    ]
    dest_node_linenos = [list(d.values()) for d in dest_node_linenos]
    dest_node_linenos = itertools.chain(*dest_node_linenos)
    dest_node_linenos = [r for r in dest_node_linenos if r is not None]
    dest_node_linenos = list(sorted(dest_node_linenos, key=lambda k: int(k[1:])))

    # cover "while (1)" nodes and such automatically if predecessor is covered
    regardless_covered_linenos = {}
    for cfg_n, attr in cfg.nodes(data=True):
        if len(cfg.adj[cfg_n]) > 1:
            if (attr["node_type"] == "number_literal" and attr["code"] == "1") or (
                attr["node_type"] == "true"
            ):
                # TODO: handle switch?
                cfg_n_lineno = get_node_lineno(cfg_n)
                dest_linenos = dest_node_linenos[branch_nodes.index(cfg_n)]["True"]
                regardless_covered_linenos[cfg_n_lineno] = dest_linenos

    return ParsedInfo(dest_node_linenos, regardless_covered_linenos)
