import xml.etree.ElementTree as ET
from collections import defaultdict
import argparse


def transform_xml(xml_file, schema):
    with open(xml_file) as f:
        tree = ET.parse(f)
    root = tree.getroot()
    root.attrib["schema"] = schema

    if schema == "tree":
        # gather XML metadata
        previous_line = None  # last <line> element seen
        line_to_siblings = defaultdict(list)  # siblings of each <line>
        call_stack = []  # stack of <call> elements

        # traverse tree with BFS
        q = [root]
        while q:
            p = q.pop()
            for ch in p:
                # add child to queue for BFS
                if len(ch) > 0:
                    q.append(ch)

                # gather siblings of line element.
                # these should become its children
                if ch.tag == "line":
                    previous_line = ch
                else:
                    if previous_line is not None:
                        line_to_siblings[previous_line].append((p, ch))

                # validate and remove call metadata
                if ch.tag == "call":
                    call_stack.append(ch)
                    md = list(ch)[-1]
                    assert md.tag == "call-metadata"
                    assert len(ch.attrib) > 0
                    ch_attrib = ch.attrib
                    md_attrib = md.attrib
                    if "callline" in ch_attrib:
                        del ch_attrib["callline"]
                    if "callline" in md_attrib:
                        del md_attrib["callline"]
                    if ch_attrib != md_attrib:
                        for k in ch_attrib:
                            if k not in md_attrib:
                                print(k, "not in", md_attrib)
                            elif ch_attrib[k] != md_attrib[k]:
                                print(f"{k}: {ch_attrib[k]} != {md_attrib[k]}")
                    ch.remove(md)

        # add implicit line children to line
        for line, siblings in line_to_siblings.items():
            for p, ch in siblings:
                p.remove(ch)
                line.append(ch)
    return tree


if __name__ == "__main__":
    # parse XML
    parser = argparse.ArgumentParser()
    parser.add_argument("xml_file", help="XML file to parse")
    parser.add_argument(
        "--schema", choices=["tree"], default="tree", help="schema to follow"
    )
    parser.add_argument(
        "--output", default="output.xml", help="path of output XML file"
    )
    args = parser.parse_args()
    tree = transform_xml(args.xml_file, args.schema)
    # output formatted XML
    ET.indent(tree, space="  ", level=0)
    tree.write(args.output)
