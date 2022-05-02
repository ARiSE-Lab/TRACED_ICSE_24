import sys
import pysnooper

def trace_lines(frame, event, arg):
    co = frame.f_code
    func_name = co.co_name
    line_no = frame.f_lineno
    filename = co.co_filename
    print ('  %s line %s' % (func_name, line_no) + " " + str(frame.f_locals))

def trace_calls(frame, event, arg):
    if event != 'call':
        return
    return trace_lines

def c(_in):
    print ('input =', _in)
    print ('Leaving c()')

@pysnooper.snoop()
def b(arg):
    val = arg * 5
    c(val)
    print ('Leaving b()')

def a():
    b(2)
    b(2)
    b(3)
    b(2)
    print ('Leaving a()')
    
TRACE_INTO = ['b']

# sys.settrace(trace_calls)
a()