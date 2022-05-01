


def escape_xml_field(s):
    """
    https://stackoverflow.com/a/65450788/8999671
    """
    if s is None:
        return s
    return (
        s.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', "&quot;")
        .replace("'", "&apos;")
        .replace("\n", "&#10;")
        )

    
def get_repr(typ, name, value, age, exec_fn):
    error = None
    if typ is not None:
        if typ == 'std::stringstream':
            command = f'printf "\\"%s\\"", {name}.str().c_str()'
                            
            try:
                value = exec_fn(command, to_string=True)
                value_lines = value.splitlines(keepends=True)
                value = ''.join(l for l in value_lines if not l.startswith('warning:'))
            except gdb.error as e:
                error = traceback.format_exc()
        if typ == 'std::string':
            command = f'printf "\\"%s\\"", {name}.c_str()'
                            
            try:
                value = exec_fn(command, to_string=True)
                value_lines = value.splitlines(keepends=True)
                value = ''.join(l for l in value_lines if not l.startswith('warning:'))
            except gdb.error as e:
                error = traceback.format_exc()
        if typ.startswith('std::vector<'):
            try:
                value = exec_fn(f'print *(&{name}[0])@{name}.size()', to_string=True)
                value = re.sub(r'\$[0-9]+ = (.*)\n', r'\1', value)
                if typ.startswith('std::vector<std::string') or typ.startswith('std::vector<std::basic_string'):
                    try:
                        length = int(exec_fn(f'printf "%d", {name}.size()', to_string=True))
                        try_value = '{'
                        for i in range(length):
                            if i > 0:
                                try_value += ', '
                            add_try_value = exec_fn(f'printf "%s", {name}[{i}].c_str()', to_string=True)
                            if add_try_value != '(null)':
                                add_try_value = '"' + add_try_value + '"'
                            try_value += add_try_value
                        try_value += '}'
                        value = try_value
                    except gdb.error:
                        pass
            except gdb.error as e:
                # The error "may be inlined" can happen when a template method is called without being instantiated
                # https://stackoverflow.com/a/40179152/8999671
                error = traceback.format_exc()
                try:
                    value = exec_fn(f'p {name}', to_string=True)
                    error = None
                except gdb.error as e:
                    error = traceback.format_exc()
    xml_elem = f'''<variable name="{escape_xml_field(name)}" typ="{escape_xml_field(typ)}" age="{escape_xml_field(age)}"'''
    if error is not None:
        xml_elem += f''' {escape_xml_field(error)}'''
    xml_elem += f'''>{escape_xml_field(value)}</variable>\n'''
    return xml_elem

def test_get_repr():
    print(get_repr("int", "i", "2", "new", lambda x: "foo"))
    print(get_repr("int", "i", "2", "modified", lambda x: "foo"))
