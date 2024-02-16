import json
from .parser import get_parsed_info
from .separate_lines import separate_lines


def branch(sequence):
    """
    Return trace with masks on each branch and whether the branch was taken or not.
    """

    parsed_info = get_parsed_info(sequence["src"], sequence["lang"])

    seq_separate_lines = separate_lines(sequence)
    del seq_separate_lines["count_in_trace"]

    # filter trace to dest node lines
    def result(covered, lineno):
        if lineno in parsed_info.dest_node_linenos:
            # if "while (1)" or similar is not covered but its constant destination is covered, then cover it
            if not covered and lineno in parsed_info.regardless_covered_linenos:
                dest_lineno = parsed_info.regardless_covered_linenos[lineno]
                dest_idx = seq_separate_lines["src_linenos"].index(dest_lineno)
                return seq_separate_lines["covered_in_trace"][dest_idx]
            else:
                return covered
        else:
            return None

    seq_separate_lines["covered_in_trace"] = [
        result(c, l)
        for l, c in zip(
            seq_separate_lines["src_linenos"], seq_separate_lines["covered_in_trace"]
        )
    ]

    assert len(seq_separate_lines["src_linenos"]) == len(
        seq_separate_lines["covered_in_trace"]
    )
    assert len(seq_separate_lines["src_linenos"]) == len(
        seq_separate_lines["src_lines"]
    )

    return seq_separate_lines


def test_branch():
    example = {
        "src": """int main(int argc, char **argv) // L1
{ // L2
    if (argc == 1) { // L3
        return 1; // L4
    } // L5
    else { // L6
        return 1; // L7
    } // L8
    if (argc == 2) // L9
    { // L10
        return 1; // L11
    } // L12
    argc += 1 // L13
    for (int i = 0; i < 10; i ++) { // L14
        argc += 5; // L15
    } // L16
    while (argc > 5) { // L17
        argc -= 5; // L18
    } // L19
    do { // L20
        argc -= 5; // L21
    } while (argc > 0); // L22
    switch (argc) { // L23
        case 0: // L24
            return 0; // L25
        case 1: // L26
            return 2; // L28
        case 2: // L29
            return 4; // L30
        default: // L31
            return -1; // L32
    } // L33
    return argc; // L34
} // L35""",
        "trace": "L1 L2 L3 L7 L9 L13 L14 L15 L14 L15 L17 L18 L17 L18 L21 L22 L21 L22 L23 L25",
        "input": "",
        "output": "",
        "lang": "c",
    }
    example_output = branch(example)
    print(json.dumps(example_output, indent=2))
    print(
        "\n".join(
            f"{l} {c}"
            for l, c in zip(
                example_output["src_linenos"], example_output["covered_in_trace"]
            )
        )
    )


def test_branch2():
    example = r"""{"lang": "c", "input_no": "input_0_0", "filepath": "p00001/C/s000586295.c", "src": "#include <stdio.h>// L1\nint main(void){// L2\n// Here your code !// L3\nint work;// L4\nint rank[3]={0};// L5\nint i;// L6\nfor(i=0;i<10;i++){// L7\nscanf(\"%d\\n\",&work);// L8\nif(work > rank[0]){// L9\nrank[2] = rank[1];// L10\nrank[1] = rank[0];// L11\nrank[0] = work;// L12\n}else if(work > rank[1]){// L13\nrank[2] = rank[1];// L14\nrank[1] = work;// L15\n}else if(work > rank[2]){// L16\nrank[2] = work;// L17\n}// L18\n}// L19\nfor(i=0;i<3;i++){// L20\nprintf(\"%d\\n\",rank[i]);// L21\n}// L22\nreturn 0;// L23\n}// L24", "input": "-1\n2002\n1\n2850\n1728\n-1\n-3776\n1\n1594\n-922", "output": "2850\n2002\n1728\n", "trace": "L5 new var: rank = {0, 0, 0} new var: work = 0 L7 new var: i = 0 L8 modified var: work = -1 L9 L13 L16 L7 modified var: i = 1 L8 modified var: work = 2002 L9 L10 L11 L12 modified var: rank[0] = 2002 L7 modified var: i = 2 L8 modified var: work = 1 L9 L13 L14 L15 modified var: rank[1] = 1 L7 modified var: i = 3 L8 modified var: work = 2850 L9 L10 modified var: rank[2] = 1 L11 modified var: rank[1] = 2002 L12 modified var: rank[0] = 2850 L7 modified var: i = 4 L8 modified var: work = 1728 L9 L13 L16 L17 modified var: rank[2] = 1728 L7 modified var: i = 5 L8 modified var: work = -1 L9 L13 L16 L7 modified var: i = 6 L8 modified var: work = -3776 L9 L13 L16 L7 modified var: i = 7 L8 modified var: work = 1 L9 L13 L16 L7 modified var: i = 8 L8 modified var: work = 1594 L9 L13 L16 L7 modified var: i = 9 L8 modified var: work = -922 L9 L13 L16 L7 modified var: i = 10 L20 modified var: i = 0 L21 L20 modified var: i = 1 L21 L20 modified var: i = 2 L21 L20 modified var: i = 3 L23 L24", "outcome": "success"}"""
    branch(json.loads(example))


def test_branch_while():
    example = {
        "src": """int main(int argc, char **argv) // L1
{ // L2
    if (argc > 5) { // L3
        while (1) { // L4
            argc -= 5; // L5
            break; // L6
        } // L7
    } // L8
    return argc; // L9
} // L10""",
        "trace": "L1 L3 L5 L6 L7 L8 L9 L10",
        "input": "",
        "output": "",
        "lang": "c",
    }
    example_output = branch(example)
    print(json.dumps(example_output, indent=2))
    assert all(
        c in (True, None) for c in example_output["covered_in_trace"]
    ), example_output["covered_in_trace"]

    example2 = {
        "src": """int main(int argc, char **argv) // L1
{ // L2
    if (argc > 5) { // L3
        while (1) { // L4
            argc -= 5; // L5
            break; // L6
        } // L7
    } // L8
    return argc; // L9
} // L10""",
        "trace": "L1 L3 L9 L10",
        "input": "",
        "output": "",
        "lang": "c",
    }
    example2_output = branch(example2)
    print(json.dumps(example2_output, indent=2))
    assert not all(
        c in (True, None) for c in example2_output["covered_in_trace"]
    ), example2_output["covered_in_trace"]

    example3 = {
        "src": """int main(int argc, char **argv) // L1
{ // L2
    if (argc > 5) { // L3
        while (true) { // L4
            argc -= 5; // L5
            break; // L6
        } // L7
    } // L8
    return argc; // L9
} // L10""",
        "trace": "L1 L3 L5 L6 L7 L8 L9 L10",
        "input": "",
        "output": "",
        "lang": "c",
    }
    example3_output = branch(example3)
    print(json.dumps(example3_output, indent=2))
    assert all(
        c in (True, None) for c in example3_output["covered_in_trace"]
    ), example3_output["covered_in_trace"]
