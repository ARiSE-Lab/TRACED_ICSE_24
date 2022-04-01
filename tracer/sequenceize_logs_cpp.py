#!/usr/bin/env python
# coding: utf-8

# In[5]:


#import os
#os.chdir('..')


# In[6]:


import argparse
import sys
    
def is_interactive():
    import __main__ as main
    return not hasattr(main, '__file__')
if is_interactive():
    print(f'Hardcoding args')
    # C
    #     cmd_args = [
    #         '--lang', 'c',
    #         '--base_dirs', 'c', 'tmp_c_missing',
    #         '--src_dirs', 'Project_CodeNet/data', 'tmp_c_missing/Project_CodeNet/data',
    #         '--test',
    #     ]
    # Java
    # cmd_args = [
    #     '--lang', 'java_1000',
    #     '--base_dirs', 'java',
    #     '--src_dirs', 'Project_CodeNet/data', 'tmp/tmp_java/data',
    #     '--test',
    # ]
    cmd_args = [
        '--lang', 'cpp',
        '--base_dirs', 'pronto_export/cpp_1000_logs_outputs',
        # '--src_dirs', 'Project_CodeNet/data', 'tmp/tmp_java/data',
        '--test',
    ]
else:
    print('Parsing cmd line args')
    cmd_args = sys.argv[1:]

parser = argparse.ArgumentParser()
parser.add_argument('--lang')
parser.add_argument('--test', action='store_true')
parser.add_argument('--root_dir', default='/work/LAS/weile-lab/benjis/weile-lab/tracing')
parser.add_argument('--base_dirs', nargs='+')
parser.add_argument('--src_dirs', nargs='+')
parser.add_argument('--begin', type=int)
parser.add_argument('--end', type=int)
parser.add_argument('--limit_solutions', type=int)
args = parser.parse_args(cmd_args)
print(f'{args=}')

if args.begin is not None:
   assert args.end is not None

# In[7]:


from pathlib import Path
import xml.etree.ElementTree as ET
import tqdm.auto as tqdm
import joblib

#mem = joblib.Memory('sequenceize_cache', verbose=0)

if args.begin is not None or args.end is not None:
    assert args.begin is not None
    assert args.end is not None
    assert args.begin < args.end
    cut_to_problems = [('p' + str(i).rjust(5, '0')) for i in range(args.begin, args.end+1)]
    print('cut to', len(cut_to_problems), 'problems: ', list(sorted(cut_to_problems)))

def get_files(path):
    i = 0
    for problem_id in cut_to_problems:
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

log_files = {}
output_files = {}
for base_dir in args.base_dirs:
    base_dir = Path(base_dir)
    for log_file in tqdm.tqdm(get_files(base_dir / 'logs')):
        if args.test: assert log_file.exists(), log_file
        try:
            lang, problem, solution, input_str, input_id = log_file.stem.split('_')
            run_id = (lang, problem, solution, input_id)
            log_files[run_id] = log_file
        except ValueError:
            continue
    for output_file in tqdm.tqdm(get_files(base_dir / 'outputs')):
        if args.test: assert output_file.exists(), log_file
        try:
            lang, problem, solution, input_str, input_id = output_file.stem.split('_')
            run_id = (lang, problem, solution, input_id)
            output_files[run_id] = output_file
        except ValueError:
            continue

def test_get_files():
    print(len(log_files), 'log files')
    print('first 5:', list(log_files)[:5])
    print(len(output_files), 'output files')
    print('first 5:', list(output_files.items())[:5])

"""
if args.begin is not None:
   cut_to_problems = set()
   for i in range(args.begin, args.end+1):
       problem_seek = 'p' + str(i).rjust(5, '0')
       cut_to_problems.add(problem_seek)
   for run_id in list(log_files.keys()):
       if run_id[1] not in cut_to_problems:
           del log_files[run_id]
   for run_id in list(output_files.keys()):
       if run_id[1] not in cut_to_problems:
           del output_files[run_id]
   print('cut to', len(cut_to_problems), 'problems: ', list(sorted(cut_to_problems)))
   print(len(log_files), 'log files')
   print(len(output_files), 'output files')
"""

# # Parse XML trace

# In[83]:


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
                elif val[i] == '=' and not inside_string:
                    # we are in a dict object - return the original string
                    return val
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

def test_get_real_text():
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
    print(get_real_text('{"x = 0"}', 'cpp', True))
    print(get_real_text('{x = 0}', 'cpp', True))


# In[101]:


def get_delta(name, old_value, new_value):
    # assert isinstance(old_value, list)
    # assert isinstance(new_value, list)
    if not isinstance(old_value, list) and isinstance(new_value, list):
        return None
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
    
def test_get_delta():
    print('* modify A[1]')
    print(get_delta('A', ['"foo"', '"goo"'], ['"foo"', '"boo"']))
    print('* add A[1]')
    print(get_delta('A', ['"foo"'], ['"foo"', '"moo"']))
    print('* delete A[1]')
    print(get_delta('A', ['"foo"', '"hoo"'], ['"foo"']))
    print('* modify A[0] AND delete A[1]')
    print(get_delta('A', ['"boo"', '"hoo"'], ['"moo"']))


# In[102]:



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

def test_get_str_repr():
    print(get_str_repr([]))
    print(get_str_repr(['1', '2']))
    print(get_str_repr(['1', '2', '3'], max_str_len=3))
    print(get_str_repr(['"foo"', '"boo"']))
    print(get_str_repr(['"foo"', ['"boo"', '"goo"']]))
    print(get_str_repr(['"printed\\n"', '2']))
    print(get_str_repr(['0', '0', '0']))
    print(get_str_repr([['0', '2'], ['1']]))


# In[103]:


import re

def convert_proxy(matchobj):
    """https://stackoverflow.com/a/60343277/8999671"""
    innertext = matchobj.group(1)
    innertext = innertext.replace('&', '&amp;')
    innertext = innertext.replace('<', '&lt;')
    innertext = innertext.replace('>', '&gt;')
    innertext = innertext.replace('\'', '&apos;')
    innertext = innertext.replace('"', '&quot;')
    return f'proxy="{innertext}"'

def convert_all_proxy(text):
    return re.sub(r'proxy="([^"]+)"', convert_proxy, text)

def convert_all_disallowedunicode(text):
    """
    https://www.w3.org/TR/xml/#charsets
    Char ::= #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
    """
    return re.sub(r'[^\u0009\u000A\u000D\u0020-\uD7FF\uE000-\uFFFD\u10000-\u10FFFF]', '', text)

def convert_all(text):
    text = convert_all_proxy(text)
    text = convert_all_disallowedunicode(text)
    return text

def test_convert_all_proxy():
    print(convert_all_proxy("foo"))
    print(convert_all_proxy("proxy=\"foo\""))
    print(convert_all_proxy("proxy=\"<foo&>\""))
    print(convert_all("""<variable name="h" age="new" proxy="std::string">""</variable>"""))
    print(convert_all("""<variable name="s3" age="new" proxy="std::string">"
    @"</variable>"""))


# In[104]:


# get_trace function
from collections import defaultdict
import xml.etree.ElementTree as ET
import re
import io

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
        if not any(states):
            continue
        if len(state_words) > 0:
            state_words += ' '
        state_words += f'L{lineno}'
        for state in states:
            age, name, text = state
            state_words += f' {age} var: {name} = {text}'
    return state_words, any_modified


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


# # Putting sequence together

# In[33]:


# get_sequence parses the entire sequence from various files: input, output, XML log, source code...
# Check it out as some files may be commented out for debuggnig purpose.
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
print(f'{src_dirs=}')
for p in src_dirs:
    assert p.exists(), p
input_dir = Path(args.root_dir, "all_input_output")
print(f'{input_dir=}')

sequences_got = 0

def get_sequence(run_id):
    global sequences_got
    verbose = sequences_got < 5
    sequences_got += 1
    # print(run_id)
    sequence = {}
    try:
        lang, problem, solution, input_id = run_id
        if verbose:
            print(run_id, lang, problem, solution, input_id)
        
        # Get files
        log_file = log_files[run_id]
        output_file = output_files[run_id]
        src_file = None
        for src_dir in src_dirs:
            src_file = src_dir / problem / lang_to_path[lang] / (solution + '.' + lang)
            if src_file.exists():
                break
        if verbose:
            print(log_file)
            print(output_file)
            print(src_file)
        #if not log_file.exists() or not output_file.exists():
        if not log_file.exists():
            sequence["outcome"] = "missing_log"
            return sequence
        if not output_file.exists():
            sequence["outcome"] = "missing_output"
            return sequence
        if not src_file.exists():
            sequence["outcome"] = "missing_src"
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
        input_file = input_dir / problem / f'input_{input_id}.txt'
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
        #raise 
        sequence["outcome"] = "parse_error"
        sequence["error_msg"] = traceback.format_exc()
    except Exception:
        # print('Error', log_file, file=of)
        sequence["outcome"] = "error"
        sequence["error_msg"] = traceback.format_exc()

    return sequence

print(len(get_sequence(('c', 'p00000', 's096258090', '0'))))
print(len(get_sequence(('c', 'p00000', 's000997878', '0'))))
print(len(get_sequence(('c', 'p00001', 's666411079', '0'))))


# In[ ]:


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
# print_seq(get_sequence(('c', 'p00001', 's473768977', '0')))



print_seq(get_sequence(('cpp', 'p02572', 's000178919', '0')))
print_seq(get_sequence(('cpp', 'p02572', 's000178919', '1')))


# # Test cases

# In[ ]:



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



# Export example Java files
# s = """
# p00754/Java/s570323348.java
# p00754/Java/s831710371.java
# p01073/Java/s544886485.java
# p01126/Java/s819043946.java
# p01131/Java/s887615522.java
# p01144/Java/s247659810.java
# p01288/Java/s575961262.java
# p01321/Java/s700550281.java
# p01341/Java/s318278306.java
# p01353/Java/s654988884.java
# p01362/Java/s185302445.java
# p01449/Java/s910810758.java
# p01532/Java/s900434355.java
# p01532/Java/s928311005.java
# p01540/Java/s836491242.java
# p01554/Java/s560239327.java
# p01554/Java/s668203473.java
# p01554/Java/s712636102.java
# p01556/Java/s625587885.java
# p01751/Java/s149621293.java
# p01753/Java/s412768089.java
# p01819/Java/s213700602.java
# p01880/Java/s888544290.java
# p01916/Java/s975413870.java
# p01919/Java/s350795111.java
# p02030/Java/s016452112.java
# p02233/Java/s952249172.java
# p02237/Java/s000828508.java
# p02239/Java/s008177618.java
# p02243/Java/s356625430.java
# p02247/Java/s582909065.java
# p02248/Java/s839733329.java
# p02250/Java/s750349474.java
# p02255/Java/s116287843.java
# p02255/Java/s155389767.java
# p02255/Java/s161089192.java
# p02255/Java/s191486099.java
# p02255/Java/s387915204.java
# p02255/Java/s416557893.java
# p02255/Java/s506993965.java
# p02255/Java/s727227214.java
# p02255/Java/s796011395.java
# p02255/Java/s964501357.java
# p02256/Java/s398900662.java
# p02256/Java/s429306757.java
# p02256/Java/s684758085.java
# p02256/Java/s844943094.java
# p02256/Java/s894981933.java
# p02257/Java/s048942791.java
# p02257/Java/s275580631.java
# p02257/Java/s359039803.java
# p02257/Java/s753631003.java
# p02258/Java/s245611196.java
# p02258/Java/s428484215.java
# p02258/Java/s608785165.java
# p02258/Java/s673092055.java
# p02258/Java/s989902464.java
# p02259/Java/s018222824.java
# p02259/Java/s236955424.java
# p02259/Java/s596427989.java
# p02259/Java/s802877994.java
# p02260/Java/s160373783.java
# p02261/Java/s111155837.java
# p02261/Java/s475138547.java
# p02262/Java/s150248391.java
# p02262/Java/s527514509.java
# p02262/Java/s995786732.java
# p02263/Java/s305091313.java
# p02263/Java/s474710191.java
# p02263/Java/s915556102.java
# p02265/Java/s129213906.java
# p02265/Java/s264692061.java
# p02265/Java/s935576413.java
# p02267/Java/s100680090.java
# p02267/Java/s511213200.java
# p02267/Java/s679528105.java
# p02267/Java/s924692833.java
# p02268/Java/s049586536.java
# p02268/Java/s361180116.java
# p02268/Java/s446681633.java
# p02269/Java/s314785207.java
# p02269/Java/s700046862.java
# p02269/Java/s950023194.java
# """
# for l in s.splitlines():
#     if l:
#         problem, _, sol = l.split('/')
#         sol = sol.split('.')[0]
#         lang = 'java'
#         input_no = '0'
#         print_seq(get_sequence((lang, problem, sol, input_no)))


# # Other

# In[16]:


all_runs = list(sorted(set(log_files.keys()).intersection(set(output_files.keys()))))
print(len(all_runs))
# all_runs = all_runs[:100]
print(len(all_runs))


# In[17]:


from pathlib import Path
import traceback
import json
import tqdm.auto as tqdm
from multiprocessing import Pool

sequences_filename = Path(f'{args.lang}_sequences_{args.begin}_{args.end}.jsonl')

# already_loaded_sequences = 

nproc = 31

if False:
    import random
    random.seed(0)
    my_all_runs = random.sample(all_runs, 1000)
else:
    my_all_runs = all_runs

num_errors = 0
printed_error = 0
lens = []
outcomes = defaultdict(int)
with Pool(nproc) as pool, open(sequences_filename, 'w') as sf:
    pbar = tqdm.tqdm(pool.imap_unordered(get_sequence, my_all_runs), total=len(my_all_runs), mininterval=1)
    for i, sequence in enumerate(pbar):
        try:
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
        except Exception:
            num_errors += 1
            print(num_errors, 'error outside multiprocess. Skipping...')
            traceback.print_exc()

for outcome, count in outcomes.items():
    print(outcome, count)


# In[28]:


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




