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
        self.lines_executed = []
        self.verbose = False
        self.last_frame_id = None

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

        last_func = None

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
                        func = frame.function()
                        if last_func is not None and func.name != last_func.name:
                            older_function = None if frame.older() is None else frame.older().function()
                            if verbose:
                                print(func, pc_line, last_func, older_function)
                            if older_function is not None and older_function.name == last_func.name:
                                f.write(f'<call caller="{escape_xml_field(older_function)}" callerline="{escape_xml_field(older_function.line)}" callee="{escape_xml_field(func)}" calleeline="{escape_xml_field(func.line)}"/>\n')
                                pass  # entering function call
                            else:
                                f.write(f'<return caller="{escape_xml_field(func)}" callerline="{escape_xml_field(func.line)}" callee="{escape_xml_field(last_func)}" calleeline="{escape_xml_field(last_func.line)}"/>\n')
                                popped_vars = self.frame_to_vars.pop(self.last_frame_id, None)
                                if verbose:
                                    print("pop", self.last_frame_id, popped_vars)
                                pass  # exiting function call
                        # f.write(f'<program_point filename="{escape_xml_field(path)}" line="{escape_xml_field(pc_line)}" frame="{escape_xml_field(frame.function())}" frametype="{escape_xml_field(frame.type())}" framelevel="{escape_xml_field(frame.level())}">\n')
                        self.log_vars(frame, f, path, frame.function().name, pc_line)
                        f.write(f'<line framefunction="{escape_xml_field(func)}" line="{escape_xml_field(pc_line)}" filename="{escape_xml_field(path)}"/>\n')
                        f.flush()
                        if verbose: print(f'iter {i} - step')
                        gdb.execute('s')  # This line steps to the next line which reduces overhead, but skips some lines compared to stepi.
                        last_func = func
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

    
    def get_block_id(self, block):
        # frame_id = (start_block.start, start_block.end)
        # frame_id = sal.symtab.static_block().start
        # frame_id = start_block.superblock.start
        return block.start


    def log_vars(self, frame, f, path, funcname, pc_line):
        """
        Navigating scope blocks to gather variables.
        Source: https://stackoverflow.com/a/30032690/8999671
        """
        pc_id_triplet = (path, funcname, pc_line)
        block = frame.block()
        frame_id = self.get_block_id(block)
        self.last_frame_id = frame_id
        if self.verbose:
            print("frame_id", block.function, frame_id, block.start, block.end)
        cur_block = block
        # while cur_block is not None and not cur_block.is_global() and not cur_block.is_static():
        old_vars = {}
        symbols = []
        while cur_block is not None:
            if self.verbose:
                print("block.start", cur_block.start, cur_block.function, cur_block.is_global, cur_block.is_static)
            block_id = self.get_block_id(cur_block)
            old_vars[block_id] = self.frame_to_vars.get(block_id, {})
            for sym in cur_block:
                if not (sym.is_argument or sym.is_variable) or sym.name.startswith('std::'):
                    continue
                if not any(s.name == sym.name for b, s in symbols):
                    symbols.append((block_id, sym))
            cur_block = cur_block.superblock
        variables_by_frame = {}
        symbols = list(sorted(symbols, key=lambda s: s[1].name))
        if self.verbose:
            print("symbol list", [s.name for b, s in symbols])
        for block_id, symbol in symbols:
            # if block_id not in variables_by_frame:
            #     continue
            name = symbol.name
            if block_id not in variables_by_frame or not name in variables_by_frame[block_id]:
                typ = symbol.type.name
                symbol_lineno = symbol.line
                if typ is None:
                    m = re.match(r'type = (.*)', gdb.execute('whatis ' + name, to_string=True).strip())
                    if m is not None:
                        typ = m.group(1)
                value = str(symbol.value(frame))
                age = 'new'
                if block_id in old_vars:
                    if name in old_vars[block_id]:
                        if old_vars[block_id][name] == value:
                            age = 'old'
                        else:
                            age = 'modified'
                        
                symbol_id_triplet = (path, funcname, symbol_lineno)
                if self.verbose:
                    print("old_vars", name, age, block_id, old_vars, self.frame_to_vars.keys(), block_id in self.frame_to_vars.keys())

                # this inclusion rule seems to work for all programs
                leif = [(p, f, l) for p, f, l in self.lines_executed if p == path and f == funcname]
                symbol_line_executed = leif[-1][2] >= symbol_lineno if len(leif) > 0 else False

                # this inclusion rule works for straight-line programs, but when variables are declared inside loops,
                # it prints the variable too early on subsequent iterations of the loop
                # symbol_line_executed = any(s[0] == path and s[1] == funcname and s[2] >= symbol_lineno for s in self.lines_executed)
                
                if self.verbose:
                    print("before get_repr", name, symbol_line_executed, symbol_id_triplet)

                xml_elem = get_repr(typ, name, value, age, gdb.execute, self.verbose, symbol_lineno, symbol_line_executed)
                if xml_elem is not None:
                    f.write(xml_elem)
                    if block_id not in variables_by_frame:
                        variables_by_frame[block_id] = {}
                    variables_by_frame[block_id][name] = value
            if block_id in variables_by_frame:
                if self.verbose:
                    print("assign variables", path, pc_line, frame_id, variables_by_frame[block_id])
                self.frame_to_vars[block_id] = variables_by_frame[block_id]
        # self.frame_to_vars[frame.code] = variables  # frame.code is not accessible field

        # this is an attempt to include variable declarations by imputing line numbers
        # from last executed line to current line. It has some issues because of jumps etc.
        # j = len(self.lines_executed) - 1
        # last_executed_line = None
        # while j >= 0:
        #     last_executed_line = self.lines_executed[j]
        #     if last_executed_line[0] == path and last_executed_line[1] == funcname:
        #         break
        #     j -= 1
        # if last_executed_line is not None:
        #     if last_executed_line[2] < pc_line:
        #         self.lines_executed += [(path, funcname, s) for s in range(last_executed_line[2], pc_line)]
        self.lines_executed.append(pc_id_triplet)

TraceAsm()
