"""Parse XML trace"""

from transform_xml import transform_xml
from text_utils import *


def get_trace(log_file, lang, remove_empty_lines=False):
    tree = transform_xml(log_file, "tree")
    timed_out = False
    trace = tree.getroot()
    current_lineno = None
    states = []
    current_state = []
    lineno = None
    variable_list_states = {}
    any_modified = False
    # TODO: handle calls within line
    for child in trace:
        assert child.tag == "line", f"'{child.tag}' should be 'line'"
        lineno = int(child.attrib["line"])
        for variable in child:
            if variable.tag == "variable":
                age = variable.attrib["age"]
                name = variable.attrib["name"]

                if age in ("new", "modified"):
                    if age == "modified":
                        any_modified = True
                    val = get_real_text(variable.text, lang)
                    val_text = val
                    # handle lists specially
                    if isinstance(val, list):
                        if name in variable_list_states:
                            mods = get_delta(name, variable_list_states[name], val)
                            if mods is None:
                                val_text = get_str_repr(val)
                                current_state.append((age, name, val_text))
                            else:
                                for mod_name, mod_val_text in mods:
                                    current_state.append((age, mod_name, mod_val_text))
                        else:
                            val_text = get_str_repr(val)
                            current_state.append((age, name, val_text))
                    else:
                        current_state.append((age, name, val_text))
                    variable_list_states[name] = val
            elif variable.tag == "timeout":
                timed_out = True
        if lineno != current_lineno:
            states.append((lineno, current_state))
            current_state = []

    # accumulate string representation of trace
    state_words = ""
    for lineno, states in states:
        if remove_empty_lines:
            # remove all lines with no new/modified variables
            if not any(states):
                continue
        if len(state_words) > 0:
            state_words += " "
        state_words += f"L{lineno}"
        for state in states:
            age, name, text = state
            state_words += f" {age} var: {name} = {text}"

    return state_words, any_modified, timed_out
