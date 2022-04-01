#!/usr/bin/env python
# coding: utf-8

# In[2]:


import argparse
import sys
    
def is_interactive():
    import __main__ as main
    return not hasattr(main, '__file__')
if is_interactive():
    print(f'Hardcoding args')
    cmd_args = [
        '--lang', 'c',
        '--base_dirs', 'c', 'tmp_c_missing',
        '--src_dirs', 'Project_CodeNet/data', 'tmp_c_missing/Project_CodeNet/data',
        '--test',
    ]
#    cmd_args = [
#        '--lang', 'java',
#        '--base_dirs', 'java',
#        '--src_dirs', 'Project_CodeNet/data', 'tmp/tmp_java/data',
#        '--test',
#    ]
else:
    print('Parsing cmd line args')
    cmd_args = sys.argv[1:]

parser = argparse.ArgumentParser()
parser.add_argument('--lang')
parser.add_argument('--test', action='store_true')
parser.add_argument('--base_dirs', nargs='+')
parser.add_argument('--src_dirs', nargs='+')
parser.add_argument('--input_dirs', nargs='+')
args = parser.parse_args(cmd_args)
print(f'{args=}')


# In[5]:


from pathlib import Path
import xml.etree.ElementTree as ET
import tqdm.auto as tqdm

log_files = {}
output_files = {}
for base_dir in args.base_dirs:
    base_dir = Path(base_dir)
    for log_file in tqdm.tqdm((base_dir / 'logs').glob('*.xml')):
        try:
            lang, problem, solution, input_str, input_id = log_file.stem.split('_')
            run_id = (lang, problem, solution, input_id)
            log_files[run_id] = log_file
        except ValueError:
            continue
    for output_file in tqdm.tqdm((base_dir / 'outputs').glob('*.txt')):
        try:
            lang, problem, solution, input_str, input_id = output_file.stem.split('_')
            run_id = (lang, problem, solution, input_id)
            output_files[run_id] = output_file
        except ValueError:
            continue

print(len(log_files))
print(len(output_files))


# In[6]:


import traceback

def get_real_text(val, lang, verbose=False, return_new_i=False):
    opener = '[' if lang == 'java' else '{'
    closer = ']' if lang == 'java' else '}'
    # print("get_real_text", val, opener, closer)
    items = val
    try:
        if val.startswith(opener) or (lang == 'java' and val.startswith('"') and val[1] == opener):
            items = []
            if val.startswith('"'):
                i = 2
            else:
                i = 1
            item = None
            item_start = i
            ignore_next_character = False
            inside_string = False
            while True:
                # print(i, val[i])
                if val[i] == '\\':
                    ignore_next_character = True
                    i += 1
                    continue
                if ignore_next_character:
                    ignore_next_character = False
                    continue

                if val[i] == ',':
                    if item is None:
                        items.append(val[item_start:i])
                    else:
                        items.append(item)
                        item = None
                    i += 1
                    while val[i].isspace():
                        i += 1
                    item_start = i
                elif val[i] == '"':
                    inside_string = not inside_string
                    i += 1
                elif val[i] == opener and not inside_string:
                    # raise NotImplementedError('TODO: implement nested arrays')
                    child_val, new_i = get_real_text(val[i:], lang, verbose=verbose, return_new_i=True)
                    if child_val in ('malformed', 'error'):
                        return child_val
                    else:
                        i += new_i
                        # print('got child', child_val, i, val[i:])
                        item = child_val
                elif val[i] == closer and not inside_string:
                    if item is None:
                        if item_start != i:
                            items.append(val[item_start:i])
                    else:
                        items.append(item)
                    i += 1
                    break
                else:
                    i += 1
    except IndexError:
        # if verbose:
        #     traceback.print_exc()
        if return_new_i:
            return 'malformed', i
        else:
            return 'malformed'
    except Exception:
        if verbose:
            traceback.print_exc()
        if return_new_i:
            return 'error', i
        else:
            return 'error'
    if return_new_i:
        return items, i
    else:
        return items

print(get_real_text('foo', 'c', True))
print(get_real_text('foo{, , }', 'c', True))
print(get_real_text('{}', 'c', True))
print(get_real_text('{1, 2}', 'c', True))
print(get_real_text('{"foo", "boo"}', 'c', True))
print(get_real_text('{"foo", "boo"', 'c', True))
print(get_real_text('{"foo", ""boo"}', 'c', True))
print(get_real_text('{"foo", {"boo", "goo"}}', 'c', True))
print(get_real_text('{"printed\\n", 2}', 'c', True))
print(get_real_text('[0, 0, 0]', 'java', True))
print(get_real_text('"[[0, 2], [1]]"', 'java', True))


# In[7]:


def get_delta(name, old_value, new_value):
    assert isinstance(old_value, list)
    assert isinstance(new_value, list)
    statements = []
    for i in range(max(len(old_value), len(new_value))):
        if i >= len(old_value):
            # TODO: New var?
            statements.append((
                f'{name}[{i}]', new_value[i]
            ))
            continue
        if i >= len(new_value):
            statements.append((
                f'{name}[{i}]', 'deleted'
            ))
            continue
        
        if old_value[i] != new_value[i]:
            statements.append((
                f'{name}[{i}]', new_value[i]
            ))
    return statements
print('* modify A[1]')
print(get_delta('A', ['"foo"', '"goo"'], ['"foo"', '"boo"']))
print('* add A[1]')
print(get_delta('A', ['"foo"'], ['"foo"', '"moo"']))
print('* delete A[1]')
print(get_delta('A', ['"foo"', '"hoo"'], ['"foo"']))
print('* modify A[0] AND delete A[1]')
print(get_delta('A', ['"boo"', '"hoo"'], ['"moo"']))


# In[8]:



def get_str_repr(val, max_str_len = 250):
    # May have to truncate
    print_text = '{'
    last_was_opener = True
    i = 0
    while i < len(val):
        v = val[i]
        if i > 0:
            if (isinstance(v, list) or v not in '{}') and not last_was_opener:
                print_text += ', '
        last_was_opener = v == '{'
        if isinstance(v, list):
            # print(val, i)
            val = val[:i] + ['{'] + v + ['}'] + val[i+1:]
            # print(val, i)
            continue
        else:
            if len(print_text) + len(v) > max_str_len:
                print_text += f'<{len(val) - i} truncated>'
                break
            else:
                print_text += v
        i += 1
    print_text += '}'
    print_text = str(print_text)
    return print_text

print(get_str_repr([]))
print(get_str_repr(['1', '2']))
print(get_str_repr(['1', '2', '3'], max_str_len=3))
print(get_str_repr(['"foo"', '"boo"']))
print(get_str_repr(['"foo"', ['"boo"', '"goo"']]))
print(get_str_repr(['"printed\\n"', '2']))
print(get_str_repr(['0', '0', '0']))
print(get_str_repr([['0', '2'], ['1']]))


# In[14]:


from collections import defaultdict
import xml.etree.ElementTree as ET

def get_trace(log_file, lang):
    # print("trace", log_file, lang)
    output = {}
    tree = ET.parse(log_file)
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
#                                 print(f'delta {mods=}')
                                for my_name, my_print_text in mods:
                                    current_state.append((age, my_name, my_print_text))
                            else:
                                print_text = get_str_repr(val)
#                                 print(f'new {print_text=}')
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
        if not any(states):
            continue
        if len(state_words) > 0:
            state_words += ' '
        state_words += f'L{lineno}'
        for state in states:
            age, name, text = state
            state_words += f' {age} var: {name} = {text}'
    return state_words, any_modified

# print(get_str_repr(['1', '0', '4196029', '0', '-53280', '32767', '0', '0', '4195952', '0']))
#print(get_trace('c/logs/c_p00001_s074179776_input_0.xml', 'c'))
#print()
#print(get_trace('c/logs/c_p00001_s473768977_input_0.xml', 'c'))
#print()
#print(get_trace('c/logs/c_p00001_s971701861_input_0.xml', 'c'))


# In[18]:


import xml.etree.ElementTree as ET
from pathlib import Path
import traceback
import json

lang_to_path = {
    "c": "C",
    "cpp": "C++",
    "java": "Java",
}
src_dirs = [Path(p) for p in args.src_dirs]
input_dir = Path("all_input_output")

def get_sequence(run_id):
    # print(run_id)
    sequence = {}
    try:
        lang, problem, solution, input_id = run_id
        
        # Get files
        log_file = log_files[run_id]
        output_file = output_files[run_id]
        src_file = None
        for src_dir in src_dirs:
            src_file = src_dir / problem / lang_to_path[lang] / (solution + '.' + lang)
            if src_file.exists():
                break
        if not log_file.exists() or not output_file.exists() or not src_file.exists():
            sequence["outcome"] = "missing"
            return sequence
        # print(run_id, log_file, output_file)

        sequence["lang"] = lang
        sequence["input_no"] = input_id

        # Find source file
        sequence["filepath"] = str(src_file.relative_to(src_dir))

        # Get source code
        with open(src_file, encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        lines = [' '.join(l.rstrip().split()) + f'// L{i}' for i, l in enumerate(lines, start=1) if l and not l.isspace()]
        sequence["src"] = '\n'.join(lines)

        # Add input and output
        for input_dir in args.input_dirs:
            input_file = Path(input_dir) / problem / f'input_{input_id}.txt'
            if input_file.exists():
                break
        with open(input_file, encoding='utf-8', errors='replace') as f:
            sequence["input"] = f.read()
        output_file = output_file
        with open(output_file, encoding='utf-8', errors='replace') as f:
            sequence["output"] = f.read()

        # Map line number to variables/values
        sequence["trace"], any_modified = get_trace(log_file, lang)
        
        if not any_modified:
            sequence["outcome"] = "success_short_trace"
        else:
            sequence["outcome"] = "success"
    except ET.ParseError:
        # print('Error', log_file, file=of)
        sequence["outcome"] = "parse_error"
        sequence["error_msg"] = traceback.format_exc()
    except Exception:
        # print('Error', log_file, file=of)
        sequence["outcome"] = "error"
        sequence["error_msg"] = traceback.format_exc()

    return sequence

#print(len(get_sequence(('c', 'p00000', 's096258090', '0'))))
#print(len(get_sequence(('c', 'p00000', 's000997878', '0'))))
#print(len(get_sequence(('c', 'p00001', 's666411079', '0'))))


def print_seq(seq):
    import re
    try:
        if seq["outcome"] == "error":
            print(json.dumps(seq, indent=2))
            return
        print(seq["outcome"])
        if 'success' not in seq["outcome"]:
            return
        print(seq["filepath"])
        print(seq["src"])
        print(re.sub(r'(L[0-9]+)', r'\n\1', seq["trace"]))
    except Exception:
        print('problem', json.dumps(seq, indent=2))
        raise
#print_seq(get_sequence(('c', 'p00001', 's473768977', '0')))

# Export example Java files
s = """
p00754/Java/s570323348.java
p00754/Java/s831710371.java
p01073/Java/s544886485.java
p01126/Java/s819043946.java
p01131/Java/s887615522.java
p01144/Java/s247659810.java
p01288/Java/s575961262.java
p01321/Java/s700550281.java
p01341/Java/s318278306.java
p01353/Java/s654988884.java
p01362/Java/s185302445.java
p01449/Java/s910810758.java
p01532/Java/s900434355.java
p01532/Java/s928311005.java
p01540/Java/s836491242.java
p01554/Java/s560239327.java
p01554/Java/s668203473.java
p01554/Java/s712636102.java
p01556/Java/s625587885.java
p01751/Java/s149621293.java
p01753/Java/s412768089.java
p01819/Java/s213700602.java
p01880/Java/s888544290.java
p01916/Java/s975413870.java
p01919/Java/s350795111.java
p02030/Java/s016452112.java
p02233/Java/s952249172.java
p02237/Java/s000828508.java
p02239/Java/s008177618.java
p02243/Java/s356625430.java
p02247/Java/s582909065.java
p02248/Java/s839733329.java
p02250/Java/s750349474.java
p02255/Java/s116287843.java
p02255/Java/s155389767.java
p02255/Java/s161089192.java
p02255/Java/s191486099.java
p02255/Java/s387915204.java
p02255/Java/s416557893.java
p02255/Java/s506993965.java
p02255/Java/s727227214.java
p02255/Java/s796011395.java
p02255/Java/s964501357.java
p02256/Java/s398900662.java
p02256/Java/s429306757.java
p02256/Java/s684758085.java
p02256/Java/s844943094.java
p02256/Java/s894981933.java
p02257/Java/s048942791.java
p02257/Java/s275580631.java
p02257/Java/s359039803.java
p02257/Java/s753631003.java
p02258/Java/s245611196.java
p02258/Java/s428484215.java
p02258/Java/s608785165.java
p02258/Java/s673092055.java
p02258/Java/s989902464.java
p02259/Java/s018222824.java
p02259/Java/s236955424.java
p02259/Java/s596427989.java
p02259/Java/s802877994.java
p02260/Java/s160373783.java
p02261/Java/s111155837.java
p02261/Java/s475138547.java
p02262/Java/s150248391.java
p02262/Java/s527514509.java
p02262/Java/s995786732.java
p02263/Java/s305091313.java
p02263/Java/s474710191.java
p02263/Java/s915556102.java
p02265/Java/s129213906.java
p02265/Java/s264692061.java
p02265/Java/s935576413.java
p02267/Java/s100680090.java
p02267/Java/s511213200.java
p02267/Java/s679528105.java
p02267/Java/s924692833.java
p02268/Java/s049586536.java
p02268/Java/s361180116.java
p02268/Java/s446681633.java
p02269/Java/s314785207.java
p02269/Java/s700046862.java
p02269/Java/s950023194.java
"""
#for l in s.splitlines():
#    if l:
#        problem, _, sol = l.split('/')
#        sol = sol.split('.')[0]
#        lang = 'java'
#        input_no = '0'
#        print_seq(get_sequence((lang, problem, sol, input_no)))

# Export example C files
# print_seq(get_sequence(('c', 'p00000', 's014428412', '0')))
# print_seq(get_sequence(('c', 'p00000', 's051215835', '0')))
# print_seq(get_sequence(('c', 'p00000', 's104659872', '0')))
# print_seq(get_sequence(('c', 'p00000', 's160777048', '0')))
# print_seq(get_sequence(('c', 'p00000', 's249280092', '0')))
# print_seq(get_sequence(('c', 'p00000', 's388010533', '0')))
# print_seq(get_sequence(('c', 'p00000', 's498121737', '0')))
# print_seq(get_sequence(('c', 'p00000', 's553567981', '0')))
# print_seq(get_sequence(('c', 'p00000', 's661193282', '0')))
# print_seq(get_sequence(('c', 'p00000', 's793156725', '0')))
# print_seq(get_sequence(('c', 'p00000', 's959455528', '0')))
# print_seq(get_sequence(('c', 'p00000', 's987134504', '0')))
# print_seq(get_sequence(('c', 'p00001', 's173380673', '0')))
# print_seq(get_sequence(('c', 'p00001', 's281792257', '0')))
# print_seq(get_sequence(('c', 'p00001', 's374785871', '0')))
# print_seq(get_sequence(('c', 'p00001', 's399600032', '0')))
# print_seq(get_sequence(('c', 'p00001', 's405225459', '0')))
# print_seq(get_sequence(('c', 'p00001', 's441225025', '0')))
# print_seq(get_sequence(('c', 'p00001', 's463972771', '0')))
# print_seq(get_sequence(('c', 'p00001', 's468182332', '0')))
# print_seq(get_sequence(('c', 'p00001', 's469957124', '0')))
# print_seq(get_sequence(('c', 'p00001', 's655430897', '0')))
# print_seq(get_sequence(('c', 'p00001', 's663064984', '0')))
# print_seq(get_sequence(('c', 'p00001', 's971826213', '0')))
# print_seq(get_sequence(('c', 'p00002', 's006640245', '0')))
# print_seq(get_sequence(('c', 'p00002', 's041059501', '0')))
# print_seq(get_sequence(('c', 'p00002', 's195660283', '0')))
# print_seq(get_sequence(('c', 'p00002', 's297323930', '0')))
# print_seq(get_sequence(('c', 'p00002', 's302393804', '0')))
# print_seq(get_sequence(('c', 'p00002', 's386360396', '0')))
# print_seq(get_sequence(('c', 'p00002', 's445324891', '0')))
# print_seq(get_sequence(('c', 'p00002', 's507551775', '0')))
# print_seq(get_sequence(('c', 'p00002', 's549249305', '0')))
# print_seq(get_sequence(('c', 'p00002', 's563594803', '0')))
# print_seq(get_sequence(('c', 'p00002', 's565291601', '0')))
# print_seq(get_sequence(('c', 'p00002', 's591124112', '0')))
# print_seq(get_sequence(('c', 'p00002', 's631024147', '0')))
# print_seq(get_sequence(('c', 'p00002', 's774929609', '0')))
# print_seq(get_sequence(('c', 'p00002', 's800178428', '0')))
# print_seq(get_sequence(('c', 'p00002', 's896877433', '0')))
# print_seq(get_sequence(('c', 'p00002', 's916716551', '0')))
# print_seq(get_sequence(('c', 'p00002', 's925147375', '0')))
# print_seq(get_sequence(('c', 'p00003', 's117469804', '0')))
# print_seq(get_sequence(('c', 'p00003', 's130622701', '0')))
# print_seq(get_sequence(('c', 'p00003', 's276592711', '0')))
# print_seq(get_sequence(('c', 'p00003', 's302679442', '0')))
# print_seq(get_sequence(('c', 'p00004', 's024944316', '0')))
# print_seq(get_sequence(('c', 'p00004', 's145980438', '0')))
# print_seq(get_sequence(('c', 'p00004', 's210031385', '0')))
# print_seq(get_sequence(('c', 'p00004', 's223825430', '0')))
# print_seq(get_sequence(('c', 'p00004', 's281073632', '0')))
# print_seq(get_sequence(('c', 'p00004', 's286728549', '0')))
# print_seq(get_sequence(('c', 'p00004', 's294739000', '0')))
# print_seq(get_sequence(('c', 'p00004', 's636403510', '0')))
# print_seq(get_sequence(('c', 'p00004', 's647852358', '0')))
# print_seq(get_sequence(('c', 'p00004', 's887419412', '0')))
# print_seq(get_sequence(('c', 'p00005', 's100837603', '0')))
# print_seq(get_sequence(('c', 'p00005', 's133199794', '0')))
# print_seq(get_sequence(('c', 'p00005', 's210824353', '0')))
# print_seq(get_sequence(('c', 'p00005', 's219641195', '0')))
# print_seq(get_sequence(('c', 'p00005', 's249843670', '0')))
# print_seq(get_sequence(('c', 'p00005', 's328065166', '0')))
# print_seq(get_sequence(('c', 'p00005', 's393873559', '0')))
# print_seq(get_sequence(('c', 'p00005', 's669492923', '0')))
# print_seq(get_sequence(('c', 'p00005', 's995456758', '0')))
# print_seq(get_sequence(('c', 'p00006', 's928806881', '0')))
# print_seq(get_sequence(('c', 'p00007', 's486526608', '0')))
# print_seq(get_sequence(('c', 'p00007', 's582089739', '0')))
# print_seq(get_sequence(('c', 'p00007', 's662452622', '0')))
# print_seq(get_sequence(('c', 'p00007', 's829410862', '0')))
# print_seq(get_sequence(('c', 'p00009', 's054705803', '0')))
# print_seq(get_sequence(('c', 'p00009', 's065994185', '0')))


# In[ ]:


all_runs = list(sorted(set(log_files.keys()).intersection(set(output_files.keys()))))
print(len(all_runs))
# all_runs = all_runs[:100]
print(len(all_runs))


# In[ ]:


from pathlib import Path
import traceback
import json
import tqdm.auto as tqdm
from multiprocessing import Pool

sequences_filename = Path(f'{args.lang}_sequences.jsonl')

# already_loaded_sequences = 

nproc = 31

if args.test:
    import random
    random.seed(0)
    my_all_runs = random.sample(all_runs, 1000)
else:
    my_all_runs = all_runs

printed_error = 0
lens = []
outcomes = defaultdict(int)
with Pool(nproc) as pool, open(sequences_filename, 'w') as sf:
    pbar = tqdm.tqdm(pool.imap_unordered(get_sequence, my_all_runs), total=len(my_all_runs), mininterval=1)
    for i, sequence in enumerate(pbar):
    # for run_id in tqdm.tqdm(my_all_runs[:1000]):
        sequence_str = json.dumps(sequence)
        lens.append(sequence_str)
        sf.write(sequence_str + '\n')
        outcomes[sequence["outcome"]] += 1
        if i % 1000 == 0:
            pbar.set_postfix(outcomes)
        if sequence["outcome"] == 'error' and printed_error < 10:
            print(f'Error {printed_error}:', json.dumps(sequence, indent=2))
            printed_error += 1

for outcome, count in outcomes.items():
    print(outcome, count)


# In[ ]:


import json
from collections import defaultdict
import numpy as np
import tqdm.auto as tqdm
import os

counts = defaultdict(int)
all_code_length = 0
all_trace_lengths = []
all_traces = []
all_input_length = 0
all_output_length = 0
num_sequences = 0
incomplete = 0
problems = set()
sequences = set()
sequences_inputs = set()
with open(sequences_filename) as f:
    for line in tqdm.tqdm(f.readlines()):
        try:
            sequence = json.loads(line)
            problems.add(os.path.dirname(os.path.dirname(sequence["filepath"])))
            sequences.add(os.path.basename(sequence["filepath"]))
            sequences_inputs.add(os.path.basename(sequence["filepath"]) + sequence["input_no"])
            all_trace_lengths.append(len(sequence["trace"]))
            counts[sequence["lang"]] += 1
            all_code_length += len(sequence["src"])
            all_traces.append(sequence["trace"])
            all_input_length += len(sequence["input"])
            all_output_length += len(sequence["output"])
            num_sequences += 1
        except KeyError:
            incomplete += 1

choptop_all_trace_lengths = sorted(all_trace_lengths)
choptop_all_trace_lengths = choptop_all_trace_lengths[:int(len(choptop_all_trace_lengths)*.99)]

print('incomplete', incomplete)
print('sequences:', json.dumps(counts, indent=2))
print('unique problems:', len(problems))
print('unique sequences:', len(sequences))
print('unique traces:', len(sequences_inputs))
print(f"average code length: {all_code_length/num_sequences:.4f}")
print(f"average trace length except 99th percentile: {np.average(choptop_all_trace_lengths):.4f}")
print(f"average trace length: {np.average(all_trace_lengths):.4f}")
print(f"average input length: {all_input_length/num_sequences:.4f}")
print(f"average output length: {all_output_length/num_sequences:.4f}")


# In[ ]:




