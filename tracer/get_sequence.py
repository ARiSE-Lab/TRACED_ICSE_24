
# # Putting sequence together

# In[33]:


# get_sequence parses the entire sequence from various files: input, output, XML log, source code...
# Check it out as some files may be commented out for debuggnig purpose.
import xml.etree.ElementTree as ET
from pathlib import Path
import traceback
import json
import os

from get_trace import *

# sequences_got = 0

def get_sequence(lang, problem, solution, input_id, src_file, log_file, input_file, output_file, verbose = False):
    src_file = Path(src_file)
    log_file = Path(log_file)
    if input_file is not None:
        input_file = Path(input_file)
    output_file = Path(output_file)
    sequence = {}
    try:
        sequence["lang"] = lang
        sequence["input_no"] = input_id

        # Find source filepath
        sequence["filepath"] = str(src_file.relative_to(src_file.parent.parent.parent))

        if verbose:
            print(lang, problem, solution, input_id)
            print(log_file)
            print(output_file)
            print(src_file)

        # handle error states
        if not log_file.exists():
            sequence["outcome"] = "missing_log"
            return sequence
        if not output_file.exists():
            sequence["outcome"] = "missing_output"
            return sequence
        if not src_file.exists():
            sequence["outcome"] = "missing_src"
            return sequence
        if os.path.getsize(log_file) > 1e9:
            sequence["outcome"] = "toobig_log"
            return sequence
        if os.path.getsize(src_file) > 1e9:
            sequence["outcome"] = "missing_src"
            return sequence
        if os.path.getsize(output_file) > 1e9:
            sequence["outcome"] = "missing_output"
            return sequence

        # Get source code
        with open(src_file, encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        lines = [' '.join(l.rstrip().split()) + f'// L{i}' for i, l in enumerate(lines, start=1) if l and not l.isspace()]
        sequence["src"] = '\n'.join(lines)

        # Get input and output
        if input_file is not None:
            with open(input_file, encoding='utf-8', errors='replace') as f:
                sequence["input"] = f.read()
        with open(output_file, encoding='utf-8', errors='replace') as f:
            sequence["output"] = f.read()
        
        # Map line number to variables/values
        sequence["trace"], any_modified, timed_out = get_trace(log_file, lang)
        
        outcome = "success"
        if not any_modified:
            outcome += "_short_trace"
        if timed_out:
            outcome += "_timed_out"
        sequence["outcome"] = outcome
    except ET.ParseError:
        sequence["outcome"] = "parse_error"
        sequence["error_msg"] = traceback.format_exc()
    except Exception:
        sequence["outcome"] = "error"
        sequence["error_msg"] = traceback.format_exc()

    return sequence

def test_case():
    """Test entry used for debugging"""
    print("trace:", get_trace("data/trace_mutated/trace/p00001/C/s000149616/input_0_0.txt_log.xml", "c"))
    print("sequence:", get_sequence("c", "p00001", "s000149616", "input_0_0", "data/Project_CodeNet/data/p00001/C/s000149616.c", "data/trace_mutated/trace/p00001/C/s000149616/input_0_0.txt_log.xml", "data/mutated_input/p00001/input_0_0.txt", "data/trace_mutated/trace/p00001/C/s000149616/input_0_0.txt_stdout.txt"))

def test_get_sequence():
    print(len(get_sequence(('c', 'p00000', 's096258090', '0'))))
    print(len(get_sequence(('c', 'p00000', 's000997878', '0'))))
    print(len(get_sequence(('c', 'p00001', 's666411079', '0'))))


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


def test_print_seq():
    print_seq(get_sequence(('cpp', 'p02572', 's000178919', '0')))
    print_seq(get_sequence(('cpp', 'p02572', 's000178919', '1')))

def test_c_cases():
    # Export example C files
    print_seq(get_sequence(('c', 'p00000', 's014428412', '0')))
    print_seq(get_sequence(('c', 'p00000', 's051215835', '0')))
    print_seq(get_sequence(('c', 'p00000', 's104659872', '0')))
    print_seq(get_sequence(('c', 'p00000', 's160777048', '0')))
    print_seq(get_sequence(('c', 'p00000', 's249280092', '0')))
    print_seq(get_sequence(('c', 'p00000', 's388010533', '0')))
    print_seq(get_sequence(('c', 'p00000', 's498121737', '0')))
    print_seq(get_sequence(('c', 'p00000', 's553567981', '0')))
    print_seq(get_sequence(('c', 'p00000', 's661193282', '0')))
    print_seq(get_sequence(('c', 'p00000', 's793156725', '0')))
    print_seq(get_sequence(('c', 'p00000', 's959455528', '0')))
    print_seq(get_sequence(('c', 'p00000', 's987134504', '0')))
    print_seq(get_sequence(('c', 'p00001', 's173380673', '0')))
    print_seq(get_sequence(('c', 'p00001', 's281792257', '0')))
    print_seq(get_sequence(('c', 'p00001', 's374785871', '0')))
    print_seq(get_sequence(('c', 'p00001', 's399600032', '0')))
    print_seq(get_sequence(('c', 'p00001', 's405225459', '0')))
    print_seq(get_sequence(('c', 'p00001', 's441225025', '0')))
    print_seq(get_sequence(('c', 'p00001', 's463972771', '0')))
    print_seq(get_sequence(('c', 'p00001', 's468182332', '0')))
    print_seq(get_sequence(('c', 'p00001', 's469957124', '0')))
    print_seq(get_sequence(('c', 'p00001', 's655430897', '0')))
    print_seq(get_sequence(('c', 'p00001', 's663064984', '0')))
    print_seq(get_sequence(('c', 'p00001', 's971826213', '0')))
    print_seq(get_sequence(('c', 'p00002', 's006640245', '0')))
    print_seq(get_sequence(('c', 'p00002', 's041059501', '0')))
    print_seq(get_sequence(('c', 'p00002', 's195660283', '0')))
    print_seq(get_sequence(('c', 'p00002', 's297323930', '0')))
    print_seq(get_sequence(('c', 'p00002', 's302393804', '0')))
    print_seq(get_sequence(('c', 'p00002', 's386360396', '0')))
    print_seq(get_sequence(('c', 'p00002', 's445324891', '0')))
    print_seq(get_sequence(('c', 'p00002', 's507551775', '0')))
    print_seq(get_sequence(('c', 'p00002', 's549249305', '0')))
    print_seq(get_sequence(('c', 'p00002', 's563594803', '0')))
    print_seq(get_sequence(('c', 'p00002', 's565291601', '0')))
    print_seq(get_sequence(('c', 'p00002', 's591124112', '0')))
    print_seq(get_sequence(('c', 'p00002', 's631024147', '0')))
    print_seq(get_sequence(('c', 'p00002', 's774929609', '0')))
    print_seq(get_sequence(('c', 'p00002', 's800178428', '0')))
    print_seq(get_sequence(('c', 'p00002', 's896877433', '0')))
    print_seq(get_sequence(('c', 'p00002', 's916716551', '0')))
    print_seq(get_sequence(('c', 'p00002', 's925147375', '0')))
    print_seq(get_sequence(('c', 'p00003', 's117469804', '0')))
    print_seq(get_sequence(('c', 'p00003', 's130622701', '0')))
    print_seq(get_sequence(('c', 'p00003', 's276592711', '0')))
    print_seq(get_sequence(('c', 'p00003', 's302679442', '0')))
    print_seq(get_sequence(('c', 'p00004', 's024944316', '0')))
    print_seq(get_sequence(('c', 'p00004', 's145980438', '0')))
    print_seq(get_sequence(('c', 'p00004', 's210031385', '0')))
    print_seq(get_sequence(('c', 'p00004', 's223825430', '0')))
    print_seq(get_sequence(('c', 'p00004', 's281073632', '0')))
    print_seq(get_sequence(('c', 'p00004', 's286728549', '0')))
    print_seq(get_sequence(('c', 'p00004', 's294739000', '0')))
    print_seq(get_sequence(('c', 'p00004', 's636403510', '0')))
    print_seq(get_sequence(('c', 'p00004', 's647852358', '0')))
    print_seq(get_sequence(('c', 'p00004', 's887419412', '0')))
    print_seq(get_sequence(('c', 'p00005', 's100837603', '0')))
    print_seq(get_sequence(('c', 'p00005', 's133199794', '0')))
    print_seq(get_sequence(('c', 'p00005', 's210824353', '0')))
    print_seq(get_sequence(('c', 'p00005', 's219641195', '0')))
    print_seq(get_sequence(('c', 'p00005', 's249843670', '0')))
    print_seq(get_sequence(('c', 'p00005', 's328065166', '0')))
    print_seq(get_sequence(('c', 'p00005', 's393873559', '0')))
    print_seq(get_sequence(('c', 'p00005', 's669492923', '0')))
    print_seq(get_sequence(('c', 'p00005', 's995456758', '0')))
    print_seq(get_sequence(('c', 'p00006', 's928806881', '0')))
    print_seq(get_sequence(('c', 'p00007', 's486526608', '0')))
    print_seq(get_sequence(('c', 'p00007', 's582089739', '0')))
    print_seq(get_sequence(('c', 'p00007', 's662452622', '0')))
    print_seq(get_sequence(('c', 'p00007', 's829410862', '0')))
    print_seq(get_sequence(('c', 'p00009', 's054705803', '0')))
    print_seq(get_sequence(('c', 'p00009', 's065994185', '0')))


# In[ ]:



def test_java_cases():
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
    for l in s.splitlines():
        if l:
            problem, _, sol = l.split('/')
            sol = sol.split('.')[0]
            lang = 'java'
            input_no = '0'
            print_seq(get_sequence((lang, problem, sol, input_no)))
