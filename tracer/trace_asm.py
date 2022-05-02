import traceback
import sys
import re
from var_utils import *

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
        self.lines_executed = set()
        self.verbose = False

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
        self.verbose = verbose

        try:
            f.write(f'<trace>\n')
            i = 0
            while True:
                if should_stop:
                    break
                frame = gdb.selected_frame()
                sal = frame.find_sal()
                symtab = sal.symtab
                if symtab is not None:
                    path = symtab.fullname()
                    pc_line = sal.line
                    is_main_exe = path is not None and (path.startswith('/workspace') or path.startswith('/tmp') or path.startswith('/scratch') or path.startswith('/work'))
                    if is_main_exe:
                        f.write(f'<program_point filename="{escape_xml_field(path)}" line="{escape_xml_field(pc_line)}" frame="{escape_xml_field(frame.function())}">\n')
                        # f.write(f'<program_point filename="{escape_xml_field(path)}" line="{escape_xml_field(pc_line)}" frame="{escape_xml_field(frame.function())}" frametype="{escape_xml_field(frame.type())}" framelevel="{escape_xml_field(frame.level())}">\n')
                        self.log_vars(frame, f, path, pc_line)
                        f.write('</program_point>\n')
                        f.flush()
                        if verbose: print(f'iter {i} - step')
                        gdb.execute('s')  # This line steps to the next line which reduces overhead, but skips some lines compared to stepi.
                    else:
                        if verbose: print(f'iter {i} - not main exe - next')
                        gdb.execute('n')
                else:
                    if verbose: print(f'iter {i} - no symbol table - next')
                    gdb.execute('n')
                i += 1
        except Exception:
            print('Error while tracing')
            traceback.print_exc()
        finally:
            f.write('</trace>\n')
            if len(argv) > 0:
                f.close()


    def log_vars(self, frame, f, path, pc_line):
        """
        Navigating scope blocks to gather variables.
        Source: https://stackoverflow.com/a/30032690/8999671
        """
        pc_id_doublet = (path, pc_line)
        block = frame.block()
        variables = {}
        while block:
            for symbol in block:
                if (symbol.is_argument or symbol.is_variable):
                    name = symbol.name
                    if not name in variables and not name.startswith('std::'):
                        typ = symbol.type.name
                        symbol_lineno = symbol.line
                        if typ is None:
                            m = re.match(r'type = (.*)', gdb.execute('whatis ' + name, to_string=True).strip())
                            if m is not None:
                                typ = m.group(1)
                        value = str(symbol.value(frame))
                        age = 'new'
                        old_vars = self.frame_to_vars.get(str(frame), {})
                        if name in old_vars:
                            if old_vars[name] == value:
                                age = 'old'
                            else:
                                age = 'modified'
                                
                        symbol_id_doublet = (path, symbol_lineno)
                        symbol_line_executed = symbol_id_doublet in self.lines_executed
                        if self.verbose:
                            print(name, symbol_line_executed, symbol_id_doublet)

                        xml_elem = get_repr(typ, name, value, age, gdb.execute, symbol_lineno, symbol_line_executed)
                        if xml_elem is not None:
                            f.write(xml_elem)
                            variables[name] = value
            block = block.superblock
        self.frame_to_vars[str(frame)] = variables
        self.lines_executed.add(pc_id_doublet)

TraceAsm()
