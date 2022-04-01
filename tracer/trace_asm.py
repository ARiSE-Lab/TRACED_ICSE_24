import traceback
import sys
import re

should_stop = False

def exit_handler(_):
    """
    check the type of stop, the following is the common one after step/next,
    a more complex one would be a subclass (for example breakpoint or signal)
    """
    global should_stop
    should_stop = True


class TraceAsm(gdb.Command):
    """
    Source: https://stackoverflow.com/a/46661931/8999671
    """

    def __init__(self):
        super().__init__(
            'trace-asm',
            gdb.COMMAND_RUNNING,
            gdb.COMPLETE_NONE,
            False
        )
        gdb.events.exited.connect(exit_handler)
        global should_stop
        should_stop = False
        self.frame_to_vars = {}

    def invoke(self, argument, _):
        argv = gdb.string_to_argv(argument)
        
        if len(argv) > 0:
            f = open(argv[0], 'w')
        else:
            f = sys.stdout
        if len(argv) > 1 and argv[1] == '-v':
            verbose = True
        else:
            verbose = False

        try:
            f.write(f'<trace>\n')
            i = 0
            while True:
                if should_stop:
                    break
                frame = gdb.selected_frame()
                sal = frame.find_sal()
                symtab = sal.symtab
                # TODO if not symtab, then detect __libc_start_main and finish
                if symtab:
                    path = symtab.fullname()
                    line = sal.line
                    is_main_exe = path is not None and (path.startswith('/workspace') or path.startswith('/tmp') or path.startswith('/scratch') or path.startswith('/work'))
                    if is_main_exe:
                        f.write(f'<program_point filename="{path}" line="{line}">\n')
                        self.log_vars(frame, f)
                        f.write('</program_point>\n')
                        f.flush()
                        if verbose: print(f'iter {i} - step')
                        gdb.execute('s')  # This line steps to the next line which reduces overhead, but skips some lines compared to stepi.
                    else:
                        if verbose: print(f'iter {i} - not main exe - next')
                        gdb.execute('n')
                else:
                    if verbose: print(f'iter {i} - symtab is None - next')
                    gdb.execute('n')
                i += 1
        except Exception:
            print('Error while tracing')
            traceback.print_exc()
        finally:
            f.write('</trace>\n')
            if len(argv) > 0:
                f.close()
    
    def get_repr(self, frame, symbol):
        proxy = None
        value = str(symbol.value(frame))
        errored = False
        #print('symbol type', symbol.type.name)
        if symbol.type.name is None:
            return proxy, value, errored
        #if symbol.type.name == '':
        #    proxy = 'array'
        if symbol.type.name == 'std::stringstream':
            proxy = symbol.type.name
            command = f'printf "\\"%s\\"", {symbol.name}.str().c_str()'
                            
            try:
                value = gdb.execute(command, to_string=True)
                value_lines = value.splitlines(keepends=True)
                value = ''.join(l for l in value_lines if not l.startswith('warning:'))
            except gdb.error as e:
                value = f'error: {e}'
                errored = True
        if symbol.type.name == 'std::string':
            proxy = symbol.type.name
            command = f'printf "\\"%s\\"", {symbol.name}.c_str()'
                            
            try:
                value = gdb.execute(command, to_string=True)
                value_lines = value.splitlines(keepends=True)
                value = ''.join(l for l in value_lines if not l.startswith('warning:'))
            except gdb.error as e:
                value = f'error: {e}'
        if symbol.type.name.startswith('std::vector<'):
            proxy = symbol.type.name
            try:
                value = gdb.execute(f'print *(&{symbol.name}[0])@{symbol.name}.size()', to_string=True)
                value = re.sub(r'\$[0-9]+ = (.*)\n', r'\1', value)
                if symbol.type.name.startswith('std::vector<std::string') or symbol.type.name.startswith('std::vector<std::basic_string'):
                    try:
                        length = int(gdb.execute(f'printf "%d", {symbol.name}.size()', to_string=True))
                        try_value = '{'
                        for i in range(length):
                            if i > 0:
                                try_value += ', '
                            add_try_value = gdb.execute(f'printf "%s", {symbol.name}[{i}].c_str()', to_string=True)
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
                value = f'error: {e}'
                errored = True
                try:
                    value = gdb.execute(f'p {symbol.name}', to_string=True)
                    errored = False
                except gdb.error as e:
                    value = f'error: {e}'
                    errored = True
        return proxy, value, errored
        

    def log_vars(self, frame, f):
        """
        Navigating scope blocks to gather variables.
        Source: https://stackoverflow.com/a/30032690/8999671
        """
        block = frame.block()
        variables = {}
        while block:
            for symbol in block:
                if (symbol.is_argument or symbol.is_variable):
                    name = symbol.name
                    if not name in variables and not name.startswith('std::'):
                        proxy, value, errored = self.get_repr(frame, symbol)

                        value = (value
                            .replace('&', '&amp;')
                            .replace('<', '&lt;')
                            .replace('>', '&gt;')
                            )

                        age = 'new'
                        old_vars = self.frame_to_vars.get(str(frame), {})
                        if name in old_vars:
                            if old_vars[name] == value:
                                age = 'old'
                            else:
                                age = 'modified'
                        
                        proxy_str = ""
                        if proxy:
                            proxy_str = f' proxy="{proxy}"'
                        errored_str = ""
                        if errored:
                            errored_str = " errored=\"true\""
                        f.write(f'<variable name="{name}" age="{age}"{proxy_str}{errored_str}>{value}</variable>\n')
                        variables[name] = value
            block = block.superblock
        self.frame_to_vars[str(frame)] = variables

TraceAsm()
