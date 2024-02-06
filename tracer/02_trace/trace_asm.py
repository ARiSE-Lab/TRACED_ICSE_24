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


def is_user_path(path):
    return path.startswith('/workspace') or path.startswith('/tmp') or path.startswith('/scratch') or path.startswith('/work') or re.match(r".*p[0-9]{5}/(C|C\+\+)/s[0-9]{9}\.c$", path)


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
        self.lines_executed = [[]]
        self.verbose = False
        self.errored = False

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

        if verbose:
            print("python version", sys.version)

        last_func = None

        functions_info = gdb.execute("info functions", to_string=True)
        current_file = None
        breakpoints = []
        for l in functions_info.splitlines():
            m = re.match(r"^File (.*):$", l)
            if m:
                current_file = m.group(1)
            if not m or not is_user_path(current_file):
                if verbose: print(f"{current_file} is not main file - skip breakpoint")
                continue
            m = re.match(r"^([0-9]+):\s+(.*)$", l)
            if m:
                lineno = int(m.group(1))
                funcname = m.group(2)
                if verbose:
                    print("setting breakpoint at", lineno, "for function", funcname)
                myself = self
                class MyReturnBreakpoint(gdb.FinishBreakpoint):
                    """https://sourceware.org/gdb/onlinedocs/gdb/Finish-Breakpoints-in-Python.html"""
                    def __init__(self, frame, **kwargs):
                        super().__init__(frame)
                        self.callee_frame_id = myself.get_block_id(frame.block())
                        self.tag_fields = kwargs

                    def stop(self):
                        try:
                            fields = " ".join(f'{k}="{escape_xml_field(v)}"' for k, v in self.tag_fields.items())
                            f.write(f'<call-metadata {fields}/>\n</call>\n')

                            popped_lines_executed = myself.lines_executed.pop()
                            popped_vars = myself.frame_to_vars.pop(self.callee_frame_id, None)
                            if verbose:
                                print("pop", self.callee_frame_id, popped_vars, popped_lines_executed)
                        except Exception as ex:
                            print(f"breakpoint exception {current_file}:{lineno}", traceback.format_exc())
                            self.errored = True
                        return False
                    def out_of_scope(self):
                        raise NotImplementedError("OUT OF SCOPE")

                class MyCallBreakpoint(gdb.Breakpoint):
                    """https://sourceware.org/gdb/onlinedocs/gdb/Breakpoints-In-Python.html"""
                    def stop(self):
                        try:
                            frame = gdb.selected_frame()
                            try:
                                calleefilename = frame.find_sal().symtab.fullname()
                            except Exception:
                                calleefilename = "<error>"
                            try:
                                callee = frame.function()
                            except Exception:
                                callee = "<error>"

                            try:
                                older = frame.older()
                            except Exception:
                                older = "<error>"
                            try:
                                older_sal = older.find_sal()
                            except Exception:
                                older_sal = "<error>"
                            try:
                                callfilename = older_sal.symtab.fullname()
                            except Exception:
                                callfilename = "<error>"
                            try:
                                caller = None if older is None else older.function()
                            except Exception:
                                caller = "<error>"
                            try:
                                callline = older_sal.line
                            except Exception:
                                callline = "<error>"
                            if is_user_path(calleefilename) and is_user_path(callfilename):
                                f.write(f'<call callline="{escape_xml_field(callline)}" callfilename="{escape_xml_field(callfilename)}" caller="{escape_xml_field(caller)}" callerline="{escape_xml_field(caller.line)}" callee="{escape_xml_field(callee)}" calleeline="{escape_xml_field(callee.line)}" calleefilename="{escape_xml_field(calleefilename)}">\n')
                                MyReturnBreakpoint(frame, callline=callline, callfilename=callfilename, caller=caller, callerline=caller.line, callee=callee, calleeline=callee.line, calleefilename=calleefilename)

                                myself.lines_executed.append([])
                                return False
                            else:
                                print("skip", frame, caller, callee)
                                return True
                        except Exception as ex:
                            print(f"breakpoint exception {current_file}:{lineno}", traceback.format_exc())
                            self.errored = True
                MyCallBreakpoint(f"{current_file}:{lineno}")

        try:
            f.write(f'<trace lang="C/C++">\n')
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
                    is_main_exe = path is not None and is_user_path(path)
                    if is_main_exe:
                        func = frame.function()
                        self.log_vars(frame, f, path, frame.function().name, pc_line)
                        f.write(f'<line framefunction="{escape_xml_field(func)}" line="{escape_xml_field(pc_line)}" filename="{escape_xml_field(path)}"/>\n')
                        f.flush()
                        if verbose: print(f'iter {i} - step')
                        gdb.execute('s')  # This line steps to the next line which reduces overhead, but skips some lines compared to stepi.
                        last_func = func
                    else:
                        if verbose: print(f'iter {i} - {path} is not main exe - next')
                        gdb.execute('n')
                else:
                    if verbose: print(f'iter {i} - no symbol table - next')
                    gdb.execute('n')
                i += 1
        except Exception:
            print('Error while tracing')
            traceback.print_exc()
            self.errored = True
        finally:
            f.write('</trace>\n')
            if len(argv) > 0:
                f.close()
        if self.errored:
            print("WARNING: error occurred in execution")

    
    def get_block_id(self, block):
        return block.start


    def log_vars(self, frame, f, path, funcname, pc_line):
        """
        Navigating scope blocks to gather variables.
        Source: https://stackoverflow.com/a/30032690/8999671
        """
        try:
            pc_id_triplet = (path, funcname, pc_line)
            block = frame.block()
            frame_id = self.get_block_id(block)
            if self.verbose:
                print("frame_id", block.function, frame_id, block.start, block.end)
            cur_block = block
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
                try:
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
                        leif = [(p, f, l) for p, f, l in self.lines_executed[-1] if p == path and f == funcname]
                        symbol_line_executed = leif[-1][2] >= symbol_lineno if len(leif) > 0 else False
                        
                        if self.verbose:
                            print("before get_repr", name, symbol_line_executed, symbol_id_triplet)

                        block_cmd = gdb.find_pc_line(block_id)
                        block_path = block_cmd.symtab.fullname()
                        block_line = block_cmd.line
                        xml_elem = get_repr(typ, name, value, age, gdb.execute, self.verbose, symbol_lineno, symbol_line_executed, block_id, block_path, block_line)
                        if xml_elem is not None:
                            f.write(xml_elem)
                            if block_id not in variables_by_frame:
                                variables_by_frame[block_id] = {}
                            variables_by_frame[block_id][name] = value
                    if block_id in variables_by_frame:
                        if self.verbose:
                            print("assign variables", path, pc_line, frame_id, variables_by_frame[block_id])
                        self.frame_to_vars[block_id] = variables_by_frame[block_id]
                except Exception:
                    if self.verbose:
                        print("exception for symbol", block_id, symbol, traceback.format_exc())
                    self.errored = True
            self.lines_executed[-1].append(pc_id_triplet)
        except Exception:
            if self.verbose:
                print("exception for frame", frame, f, path, funcname, pc_line, traceback.format_exc())
            self.errored = True

TraceAsm()
