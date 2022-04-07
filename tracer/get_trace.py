
# # Parse XML trace

# get_trace function
from collections import defaultdict
import xml.etree.ElementTree as ET
import re
import io
from text_utils import *
from pathlib import Path
import json
import difflib

def get_trace(log_file, lang):
    # print("trace", log_file, lang)
    to_parse = log_file
    if lang == 'cpp':
        with open(log_file) as f:
            text = f.read()
        new_text = convert_all(text)
        if new_text != text:
            # print('Replacing text')
            to_parse = io.StringIO(new_text)
    tree = ET.parse(to_parse)
    output = {}
    trace = tree.getroot()
    current_lineno = None
    states = []
    current_state = []
    lineno = None
    variable_list_states = {}
    last_was_new = defaultdict(bool)
    any_modified = False
    for child in trace:
        if child.tag == 'program_point':
            filename = child.attrib["filename"]
            lineno = int(child.attrib["line"])
#             if lang in ('c', 'cpp'):
#                 lineno -= 1
            # print('lineno', lineno)
            for variable in child:
                if variable.tag == 'variable':
                    age = variable.attrib["age"]
                    name = variable.attrib["name"]

                    if age in ('new', 'modified'):
                        if age == 'modified':
                            any_modified = True
                        val = get_real_text(variable.text, lang)
                        # ATTN: Skip first occurrence of each variable
                        # TODO: how does this affect function calls?
#                         if lang in ('c', 'cpp'):
#                             if last_was_new[name]:
#                                 age = 'new'
#                                 last_was_new[name] = False
#                             elif age == 'new' and not isinstance(val, list):
# #                                 print('skipping', ET.tostring(variable), 'at L' + str(lineno))
#                                 last_was_new[name] = True
#                                 continue

#                         print(lineno, name, type(val), val)
                        print_text = val
                        if isinstance(val, list):
                            if name in variable_list_states:
                                # Print delta representation only
#                                 print('get_delta', name, variable_list_states[name], val)
                                
                                mods = get_delta(name, variable_list_states[name], val)
                                # try:
                                #     mods = get_delta(name, variable_list_states[name], val)
                                # except AssertionError:
                                #     # Debug purpose only
                                #     print(name)
                                #     print('Old value:', variable_list_states[name])
                                #     print('New value:', val)
                                #     print('New variable text:', variable.text)
                                #     raise

#                                 print(f'delta {mods=}')
                                if mods is None:
                                    print_text = get_str_repr(val)
                                    current_state.append((age, name, print_text))
                                else:
                                    for my_name, my_print_text in mods:
                                        current_state.append((age, my_name, my_print_text))
                            else:
                                print_text = get_str_repr(val)
                                current_state.append((age, name, print_text))
                        else:
                            current_state.append((age, name, print_text))
                        variable_list_states[name] = val
        if lineno != current_lineno:
            # ATTN: Log to previous lineno to put the modification on the action line
            states.append((lineno if current_lineno is None else current_lineno, current_state))
            current_state = []
        current_lineno = lineno
    if lineno is not None:
        states.append((lineno, current_state))
    state_words = ""
    for lineno, states in states:
        # NOTE: This used to remove all lines with no modified variables, but we now want to include them.
        # if not any(states):
        #     continue
        if len(state_words) > 0:
            state_words += ' '
        state_words += f'L{lineno}'
        for state in states:
            age, name, text = state
            state_words += f' {age} var: {name} = {text}'
    return state_words, any_modified


# %%
def test_debug_include_empty_lines():
    """
    Example: p00000/C++/s160425098.cpp
    Old trace:

    L6 new var: i = 0
    L6 new var: j = 4196144 modified var: i = 1  <-- new var, then same line with modified var. Should compress into one.
    L8 modified var: j = 1
    L8 modified var: j = 2
    L8 modified var: j = 3
    L8 modified var: j = 4
    L8 modified var: j = 5
    L8 modified var: j = 6
    L8 modified var: j = 7
    L8 modified var: j = 8
    L8 modified var: j = 9
    L6 new var: j = 10 modified var: i = 2
    L8 modified var: j = 1
    L8 modified var: j = 2
    L8 modified var: j = 3
    L8 modified var: j = 4
    L8 modified var: j = 5
    L8 modified var: j = 6
    L8 modified var: j = 7
    L8 modified var: j = 8
    L8 modified var: j = 9
    L6 new var: j = 10 modified var: i = 3
    L8 modified var: j = 1
    L8 modified var: j = 2
    L8 modified var: j = 3
    L8 modified var: j = 4
    L8 modified var: j = 5
    L8 modified var: j = 6
    L8 modified var: j = 7
    L8 modified var: j = 8
    L8 modified var: j = 9
    L6 new var: j = 10 modified var: i = 4
    L8 modified var: j = 1
    L8 modified var: j = 2
    L8 modified var: j = 3
    L8 modified var: j = 4
    L8 modified var: j = 5
    L8 modified var: j = 6
    L8 modified var: j = 7
    L8 modified var: j = 8
    L8 modified var: j = 9
    L6 new var: j = 10 modified var: i = 5
    L8 modified var: j = 1
    L8 modified var: j = 2
    L8 modified var: j = 3
    L8 modified var: j = 4
    L8 modified var: j = 5
    L8 modified var: j = 6
    L8 modified var: j = 7
    L8 modified var: j = 8
    L8 modified var: j = 9
    L6 new var: j = 10 modified var: i = 6
    L8 modified var: j = 1
    L8 modified var: j = 2
    L8 modified var: j = 3
    L8 modified var: j = 4
    L8 modified var: j = 5
    L8 modified var: j = 6
    L8 modified var: j = 7
    L8 modified var: j = 8
    L8 modified var: j = 9
    L6 new var: j = 10 modified var: i = 7
    L8 modified var: j = 1
    L8 modified var: j = 2
    L8 modified var: j = 3
    L8 modified var: j = 4
    L8 modified var: j = 5
    L8 modified var: j = 6
    L8 modified var: j = 7
    L8 modified var: j = 8
    L8 modified var: j = 9
    L6 new var: j = 10 modified var: i = 8
    L8 modified var: j = 1
    L8 modified var: j = 2
    L8 modified var: j = 3
    L8 modified var: j = 4
    L8 modified var: j = 5
    L8 modified var: j = 6
    L8 modified var: j = 7
    L8 modified var: j = 8
    L8 modified var: j = 9
    L6 new var: j = 10 modified var: i = 9
    L8 modified var: j = 1
    L8 modified var: j = 2
    L8 modified var: j = 3
    L8 modified var: j = 4
    L8 modified var: j = 5
    L8 modified var: j = 6
    L8 modified var: j = 7
    L8 modified var: j = 8
    L8 modified var: j = 9
    """
    print()
    trace, mod = get_trace("cpp/logs/cpp_p00000_s160425098_input_0.xml", "cpp")
    print(trace.replace(' L', '\nL'))


# %%
def test_debug_include_empty_lines_cases():
    # test_files = [
    #     # Files from p00000
    #     "p00000/C++/s667847559.cpp",
    #     "p00000/C++/s160425098.cpp",
    #     "p00000/C++/s682094990.cpp",
    #     # Files from p00001
    #     "p00001/C++/s488689018.cpp",
    #     "p00001/C++/s488689018.cpp",
    #     "p00001/C++/s109465441.cpp",
    # ]
    lang_to_path = {
        "C++": "cpp",
        "C": "c",
        "Java": "java",
    }
    def get_trace_for_data(data):
        prob, lang, sol = data["filepath"].split('/')
        langpath = lang_to_path[lang]
        sol = sol.split('.')[0]
        input_file = data["input_no"]
        if not input_file.startswith("input_"):
            input_file = "input_" + input_file
        return get_trace(f"{langpath}/logs/{langpath}_{prob}_{sol}_{input_file}.xml", langpath)

    test_data = []
    with open('cpp_sequences/all_sequences_langC++_head1000.jsonl') as f:
        for i in range(503):
            text = f.readline()
            if i in (0, 1, 2, 500, 501, 502):
                test_data.append(json.loads(text))
    with open('c_java_sequences/c_sequences_head1000.jsonl') as f:
        for i in range(10):
            text = f.readline()
            if i in (1, 2, 3, 4, 5, 6):
                test_data.append(json.loads(text))
    with open('c_java_sequences/java_sequences_head1000.jsonl') as f:
        for i in range(1000):
            text = f.readline()
            try:
                data = json.loads(text)
                get_trace_for_data(data)
                test_data.append(data)
            except (ET.ParseError, KeyError) as e:
                pass
            if len(test_data) == 18:
                break
    data_dir = Path("Project_CodeNet/data")

    print()
    for i, data in enumerate(test_data):
        trace, mod = get_trace_for_data(data)
        
        old_trace = data["trace"].replace(' L', '\nL')
        new_trace = trace.replace(' L', '\nL')
        
        print(f'Case {i}: {data["filepath"]} {data["input_no"]}')
        print('Code:')
        print(data["src"])
        print()

        print('Diff:')
        print()
        differ = difflib.Differ()
        t1 = []
        t2 = []
        for line in differ.compare(old_trace.splitlines(keepends=True), new_trace.splitlines(keepends=True)):
            marker = line[0]
            if marker == " ":
                # line is same in both
                t1.append(line)
                t2.append(line)

            elif marker == "-":
                # line is only on the left
                t1.append(line)
                t2.append("")

            elif marker == "+":
                # line is only on the right
                t1.append("")
                t2.append(line)
        max_t1 = max(len(t) for t in t1)
        max_t2 = max(len(t) for t in t2)
        for tt1, tt2 in zip(t1, t2):
            if len(tt1) == 0:
                tt1 = " " * (max_t1-1)
            else:
                tt1 = tt1.rjust(max_t1, " ")
                tt1 = tt1.rstrip()
            if len(tt2) == 0:
                tt2 = " " * (max_t2-1)
            else:
                tt2 = tt2.rjust(max_t2, " ")
                tt2 = tt2.rstrip()
            print(f'{tt1} | {tt2}')
        # print('New trace:')
        # print(new_trace)
        # print('Old trace:')
        # print(old_trace)


# In[106]:


def test_assertion_errors():
    assertion_errors = [
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s000553945_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s000553945_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s001518933_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s001518933_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s002659745_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s002659745_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s003663014_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s003663014_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s003685674_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s003685674_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s004381539_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s004381539_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s004483504_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s004483504_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s004976349_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s004976349_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s005204117_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s005204117_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s005530500_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s005530500_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s005807805_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s005807805_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s005836927_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s005836927_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s005934535_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s005934535_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s006026000_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s006026000_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s006288587_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s006288587_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s006498440_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s006498440_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s006745526_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s006745526_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s007324064_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s007324064_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s008346537_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s008346537_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s008451264_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s008451264_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s008481614_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s008481614_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s009096707_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s009096707_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s010124079_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s010124079_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s010751365_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s010751365_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s010857807_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s010857807_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s010943226_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s010943226_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s011368899_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s011368899_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s011399323_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s011399323_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s011524023_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s011524023_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s012345189_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s012345189_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s012760024_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s012760024_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s012847530_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s012847530_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s013376280_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s013376280_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s013412192_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s013412192_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s014124344_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s014124344_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s014481307_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s014481307_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s014554564_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s014554564_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s014751438_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s014751438_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s015006607_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s015006607_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s016117386_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s016117386_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s016226505_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s016226505_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s016318028_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s016318028_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s018233461_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s018233461_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s018301127_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s018301127_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s018398211_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s018398211_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s018472963_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s018472963_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s018712387_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s018712387_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s019205740_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s019205740_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s020126734_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s020126734_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s021301985_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s021301985_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s021476082_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s021476082_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s021563742_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s021563742_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s022766657_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s023372249_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s023372249_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s023590310_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s023590310_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s023893432_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s023893432_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s023943124_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s023943124_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s024156727_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s024156727_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s024386598_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s024386598_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s024781897_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s024781897_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s024784569_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s024784569_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s025066589_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s025066589_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s025652345_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s025652345_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s025662883_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s025662883_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s025778398_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s025778398_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s025786742_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s025786742_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s026357782_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s026357782_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s026904862_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s026904862_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s027058769_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s027058769_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s027598420_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s027598420_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s027743182_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s027743182_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s027750473_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s027750473_input_1.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s028695224_input_0.xml",
    "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s028695224_input_1.xml"
    ]
    assertion_errors = []

    succ = 0
    for ass in assertion_errors:
        print('XML file failed with AssertionError:', ass)
        try:
            get_trace(ass, 'cpp')
            succ += 1
        except AssertionError:
            pass
    print(succ, 'succeeded')


# In[ ]:


# test cases for problematic c traces
def test_problem_c_traces():
    print(get_str_repr(['1', '0', '4196029', '0', '-53280', '32767', '0', '0', '4195952', '0']))
    print(get_trace('c/logs/c_p00001_s074179776_input_0.xml', 'c'))
    print()
    print(get_trace('c/logs/c_p00001_s473768977_input_0.xml', 'c'))
    print()
    print(get_trace('c/logs/c_p00001_s971701861_input_0.xml', 'c'))


# In[108]:


# first few test cases from sample of 1000 cpp sequences
# These have XML parser errors because they timed out or errored
def test_problem_cpp_traces():
    print(get_trace('pronto_export/cpp_1000_logs_outputs/logs/cpp_p02572_s000121615_input_0.xml', 'cpp'))
    print(get_trace('pronto_export/cpp_1000_logs_outputs/logs/cpp_p02572_s000178919_input_0.xml', 'cpp'))
    print(get_trace('pronto_export/cpp_1000_logs_outputs/logs/cpp_p02572_s000178919_input_1.xml', 'cpp'))


# In[107]:


# Parse files with invalid XML tokens (0x10 and 0x02).
def test_invalid_xml_tokens():
    token_errors = [
        "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s000810862_input_0.xml",
        "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s000810862_input_1.xml",
        "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s002691870_input_0.xml",
        "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s002691870_input_1.xml",
        "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s015429600_input_0.xml",
        "pronto_export\\cpp_1000_logs_outputs\\logs\\cpp_p02572_s015429600_input_1.xml"
    ]
    token_errors = []
    for fname in token_errors:
        try:
            get_trace(fname, 'cpp')
        except Exception as e:
            if 'not well-formed' in str(e):
                with open(fname) as f:
                    print(''.join(f'{i} {l}' for i, l in enumerate(f.readlines())))
                print(fname)


# Testing get_trace with 1000 CPP samples (and the aftermath). May be out of sync with parising `debug_out.txt` since `debug_out.txt` was run on the server.

# In[110]:


# Run traces for all 1000 outputs to see which ones and how many failed.
def test_pronto_export():
    all_xml = list(Path("pronto_export/cpp_1000_logs_outputs/logs").glob('*.xml'))
    all_xml = []
    print(len(all_xml), 'XML files')
    success = 0
    errored = []
    for f in all_xml:
        try:
            get_trace(f, 'cpp')
            success += 1
        except Exception:
            errored.append(f)
    print(success, 'successfully parsed!')


# In[111]:


    # Run failed cases only and log the exceptions.
    import traceback
    from collections import defaultdict

    messages = defaultdict(list)
    for f in errored:
        try:
            get_trace(f, 'cpp')
        except Exception as e:
            canonicalized_e = re.sub(r'[0-9]', r'', str(e))
            messages[f'{type(e).__name__}: {canonicalized_e}'].append(str(f))
            print(f)
            print(traceback.format_exc())


# In[112]:


    import json
    with open('pronto_export/cpp_1000_logs_outputs/errored.txt', 'w') as f:
        for fname in errored:
            f.write(fname.name + '\n')
    for k, v in messages.items():
        messages[k] = list(map(str, v))
    with open('pronto_export/cpp_1000_logs_outputs/errored.json', 'w') as f:
        json.dump(messages, f, indent=2)
    print('\n'.join([f'{k}: {len(messages[k])}' for k in messages.keys()]))


    # Parse `debug_out.txt`, which we got from re-running `errored.txt` on the server. from the first run of 564 examples.
    # This was gotten by running ONLY `input_1.txt`, so may not contain all errors as desired.
    # Some cases "exited normally", in which case they probably failed in sequenceizer because of AssertionError or XML decode error.

# In[45]:


    from collections import defaultdict
    import json

    with open('pronto_export/cpp_1000_logs_outputs/1/debug_out.txt', encoding='utf-8') as f:
       lines = f.readlines()

    sequences = []
    start = 0
    for i, line in enumerate(lines):
        if 'begin:' in line:
            start = i
        if 'exit code:' in line:
            sequences.append('\n'.join(lines[start:i+1]))
    print(len(sequences), 'sequences')

    causes = defaultdict(list)
    for seq in sequences:
        if 'gdb.MemoryError' in seq:
            causes["gdb.MemoryError"].append(seq)
        elif 'Process timed out' in seq:
            causes["timeout"].append(seq)
        elif 'exited normally' in seq:
            causes["exited"].append(seq)
        elif 'UnicodeDecodeError' in seq:
            causes["UnicodeDecodeError"].append(seq)
        else:
            causes["unknown"].append(seq)
    causes = dict(causes)
    print(json.dumps({k: len(v) for k, v in causes.items()}, indent=2))
    print(sum(map(len, causes.values())), 'causes')

    with open('pronto_export/cpp_1000_logs_outputs/errorcauses.json', 'w') as f:
       json.dump(causes, f, indent=2)