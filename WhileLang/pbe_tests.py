from Synthesizer import *
import os
from contextlib import redirect_stdout
import inspect

RED = "\033[31m"
GREEN = "\033[32m"
RESET = "\033[0m"

disable_prints = True

def synthesize_io_program(orig_program, inputs_examples, output_examples, P, Q, linv, unroll_limit = 8):
    synth = Synthesizer(orig_program)
    for ex_in, ex_out in zip(inputs_examples, output_examples):
        synth.add_io_example(ex_in, ex_out)
    return synth.synth_IO_program(synth.orig_program, synth.inputs, synth.outputs, P, Q, linv, unroll_limit)

def get_io_program(orig_program, inputs_examples, output_examples, to_disable_print, P = None, Q = None, linv = None, unroll_limit = 8):
    
    output_program = None

    if to_disable_print:
        with open(os.devnull, 'w') as f:
            with redirect_stdout(f):
                output_program = synthesize_io_program(orig_program, inputs_examples, output_examples, P, Q, linv, unroll_limit)

    else:
        output_program = synthesize_io_program(orig_program, inputs_examples, output_examples, P, Q, linv, unroll_limit)

    return output_program

def assert_with_color(condition, output_program, expected_program):
    if not condition:
        print(f"{RED}Assertion failed!{RESET}")
        print(f"output: {output_program}")
        print(f"expected: {expected_program}")
        return False
    else:
        print(f"{GREEN}Assertion passed!{RESET}")
        return True

def current_function_name():
    # Get the current frame
    frame = inspect.currentframe()
    # Get the name of the current function
    return frame.f_code.co_name

def linear_case_1():
    orig_program =     "c1 := ?? ; c2 := ?? ; a := c1 * x ; b := c2 - 10 ; a := a + b; c := x * 2 ; if a != c then d := 0 else d := 1"
    expected_program = "c1 := 2 ; c2 := 10 ; a := c1 * x ; b := c2 - 10 ; a := a + b; c := x * 2 ; if a != c then d := 0 else d := 1"

    inputs_examples = [[("x", 0)],
                       [("x", 1)]]
    
    output_examples = [[("d", 1)],
                       [("d", 1)]]

    output_program = get_io_program(orig_program, inputs_examples, output_examples, False)
    

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def linear_case_2():

    orig_program =     "c1 := ?? ; c2 := 4 * ?? ; a := c1 * x ; b := c2 - 10 ; a := a + b; c := x * 2 ; if a != c then d := 0 else d := 1"
    expected_program = ""

    inputs_examples = [[("x", 0)],
                       [("x", 1)]]
    
    output_examples = [[("d", 1)],
                       [("d", 1)]]

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def multiple_ios_case_1():
    orig_program =     "c1 := 4 * x ; c2 := 4 * y ; c3 := 4 * z"
    expected_program = "" # no holes => nothing to synthesize

    inputs_examples = [[("x", 1), ("y", 2), ("z", 3)],
                       [("x", 2), ("y", 4), ("z", 6)]]
    
    output_examples = [[("c1", 4), ("c2", 8), ("c3", 12)],
                       [("c1", 8), ("c2", 16), ("c3", 24)]]

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def multiple_ios_case_2():
    orig_program =     "c1 := ?? + x ; c2 := ?? + y ; c3 := ?? + z"
    expected_program = "c1 := 3 + x ; c2 := 6 + y ; c3 := 9 + z"

    inputs_examples = [[("x", 1), ("y", 2), ("z", 3)],
                       [("x", 2), ("y", 3), ("z", 4)],
                       [("x", 10), ("y", 12), ("z", 13)]]
    
    output_examples = [[("c1", 4), ("c2", 8), ("c3", 12)],
                       [("c1", 5), ("c2", 9), ("c3", 13)],
                       [("c1", 13), ("c2", 18), ("c3", 22)]]

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def multiple_ios_case_3():
    orig_program =     "c1 := ?? + x ; c2 := ?? + y ; c3 := ?? + z"
    expected_program = ""

    inputs_examples = [[("x", 1), ("y", 2), ("z", 3)],
                       [("x", 2), ("y", 3), ("z", 4)],
                       [("x", 3), ("y", 4), ("z", 5)]]
    
    output_examples = [[("c1", 4), ("c2", 8), ("c3", 12)],
                       [("c1", 5), ("c2", 9), ("c3", 13)],
                       [("c1", 7), ("c2", 11), ("c3", 15)]]

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def no_inputs_case_1():
    orig_program =     "c1 := ?? ; c2 := ?? ; c3 := ??"
    expected_program = ""

    inputs_examples = [[],
                       []]
    
    output_examples = [[("c1", 1), ("c2", 2), ("c3", 3)], [("c1", 1), ("c2", 2), ("c3", 1)]]

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def no_inputs_case_2():
    orig_program =     "c1 := ?? ; c2 := ?? ; if c1 = c2 then d := 1 else d := 0"
    expected_program = "c1 := 1253212 ; c2 := 1253212 ; if c1 = c2 then d := 1 else d := 0"

    inputs_examples = [[]]
    
    output_examples = [[("c2", 1253212), ("d", 1)]]

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def P_Q_case_1():
    orig_program =     "x := 3 ; c1 := ?? ; if c1 = c2 then d := 1 else d := 0"
    expected_program = "x := 3 ; c1 := 7 ; if c1 = c2 then d := 1 else d := 0"

    inputs_examples = [[("x",3)]]
    
    output_examples = [[]]

    P = lambda d: d["c2"] == 7
    Q = lambda d: d["d"] == 1

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints, P, Q)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)



def no_ios_case_1():
    orig_program =     "c2 := 10 ; c1 := c2"
    expected_program = "" # no holes => nothing to synthesize

    inputs_examples = [[]]
    
    output_examples = [[]]

    P = lambda d: True
    Q = lambda d: d["c1"] == 7

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints, P, Q)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def no_ios_case_2():
    orig_program =     "c2 := 10 ; c1 := c2"
    expected_program = "" # no holes => nothing to synthesize

    inputs_examples = [[]]
    
    output_examples = [[]]

    P = lambda d: d["c2"] == 10
    Q = lambda d: d["c1"] == 7

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints, P, Q)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def no_ios_case_3():
    orig_program =     "x := ?? ; c1 := c2"
    expected_program = "" # no ios => nothing to synthesize

    inputs_examples = [[]]
    
    output_examples = [[]]

    P = lambda d: d["c2"] == 10
    Q = lambda d: And(d["c1"] == 7, d["x"] == 1)

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints, P, Q)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def no_inputs_case_3():
    orig_program =     "c1 := ?? ; c2 := ?? ; if c1 = c2 then d := 1 else d := 0"
    expected_program = ""

    inputs_examples = [[],
                       []]
    
    output_examples = [[("c2", 2), ("d", 1)],
                       [("c2", 3), ("d", 1)]]

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def contradiction_case_1():
    orig_program =     "x := ?? ; c1 := c2 "
    expected_program = ""

    inputs_examples = [[]]
    
    output_examples = [[("x", 1)]]
    
    P = lambda d: d["c2"] == 5
    Q = lambda d: And(d["x"] == 14, d["c1"] == 3)

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints, P, Q)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def contradiction_case_2():
    orig_program =     "z := ?? ; x := y ; while a != b do (a := b) ; y := 123; x := y"
    expected_program = ""

    inputs_examples = [[("y", 1)]]
    
    output_examples = [[]]
    
    P = lambda d: And(d['a'] > 0, d['b'] > 0)
    Q = lambda d: And(d['a'] > 0, d['a'] == d['b'], d['x'] == 3)
    linv = lambda d: And(d['a'] > 0, d['b'] > 0)

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints, P, Q, linv)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def dont_care_case_1():
    orig_program =     "c1 := ?? ; c2 := ?? ; c3 := ?? ; c4 := ??"
    expected_program = "c1 := 0 ; c2 := 2 ; c3 := 3 ; c4 := 0" # c1 and c4 can be anything

    inputs_examples = [[("c1", 1)],
                       [("c1", 5)]]
    
    output_examples = [[("c2", 2), ("c3", 3)],
                       [("c2", 2), ("c3", 3)]]

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def while_case_1():
    orig_program =     "while a != b do if a > b then a := a - b else b := b - a"
    expected_program = "" # no holes => nothing to synthesize

    linv = None

    inputs_examples = [[("a", 3), ("b", 6)]]
    output_examples = [[("a", 3), ("b", 3)]]

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints, None, None, linv)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def while_case_2():
    orig_program =     "y := ?? ; while x < y do x := x + 1"
    expected_program = "y := 8 ; while x < y do x := x + 1"
    linv = None
    unroll_limit = 10

    inputs_examples = [[("x", 1)]]

    output_examples = [[("x", 8)]]

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints, None, None, linv, unroll_limit)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def while_case_3():
    orig_program =     "i := 0 ; while i < ?? do (x := x * 2 ; i := i + 1)"
    expected_program = "i := 0 ; while i < 5 do (x := x * 2 ; i := i + 1)"
    linv = None
    unroll_limit = 10

    inputs_examples = [[("x", 0)],
                       [("x", 1)],
                       [("x", 2)],]

    output_examples = [[("x", 0)],
                       [("x", 32)],
                       [("x", 64)]]

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints, None, None, linv, unroll_limit)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def while_case_4():
    orig_program =     "i := 0 ; while i < ?? do (x := x * 2 ; i := i + 1)"
    expected_program = ""
    linv = None
    unroll_limit = 10

    inputs_examples = [[("x", 1)],
                       [("x", 2)]]

    output_examples = [[("x", 32)],
                       [("x", 32)]]

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints, None, None, linv, unroll_limit)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def while_case_5():
    orig_program =     "i := 0 ; while i < 3 do (a := ?? ; x := x + a ; i := i + 1)"
    expected_program = "i := 0 ; while i < 3 do (a := 3 ; x := x + a ; i := i + 1)"
    linv = None
    unroll_limit = 10

    inputs_examples = [[("x", 1)],
                       [("x", 2)]]

    output_examples = [[("x", 10)],
                       [("x", 11)]]

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints, None, None, linv, unroll_limit)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def while_case_6():
    orig_program =     "i := 0 ; while i < 3 do (a := ?? ; b := ?? ; x := b + a ; i := i + 1)"
    expected_program = ["i := 0 ; while i < 3 do (a := 0 ; b := 3 ; x := b + a ; i := i + 1)",
                        "i := 0 ; while i < 3 do (a := 1 ; b := 2 ; x := b + a ; i := i + 1)",
                        "i := 0 ; while i < 3 do (a := 2 ; b := 1 ; x := b + a ; i := i + 1)",
                        "i := 0 ; while i < 3 do (a := 3 ; b := 0 ; x := b + a ; i := i + 1)"]
    linv = None
    unroll_limit = 10

    inputs_examples = [[("x", 1)],
                       [("x", 2)]]

    output_examples = [[("x", 3)],
                       [("x", 3)]]

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints, None, None, linv, unroll_limit)

    assertion = output_program in expected_program
    return assert_with_color(assertion, output_program, expected_program)

def while_case_7():
    orig_program =     "i := 0 ; while i < 3 do (a := ?? ; b := ?? ; x := b + a ; i := i + 1) ; c1 := ??"
    expected_program = ["i := 0 ; while i < 3 do (a := 0 ; b := 3 ; x := b + a ; i := i + 1) ; c1 := 2",
                        "i := 0 ; while i < 3 do (a := 1 ; b := 2 ; x := b + a ; i := i + 1) ; c1 := 2",
                        "i := 0 ; while i < 3 do (a := 2 ; b := 1 ; x := b + a ; i := i + 1) ; c1 := 2",
                        "i := 0 ; while i < 3 do (a := 3 ; b := 0 ; x := b + a ; i := i + 1) ; c1 := 2"]
    linv = None
    unroll_limit = 10

    inputs_examples = [[("x", 1)],
                       [("x", 2)]]

    output_examples = [[("x", 3), ("c1", 2)],
                       [("x", 3), ("c1", 2)]]

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints, None, None, linv, unroll_limit)

    assertion = output_program in expected_program
    return assert_with_color(assertion, output_program, expected_program)

def pbe_tests():
    print("pbe tests")

    # List of test case functions
    linear_cases = [
        linear_case_1,
        linear_case_2,
    ]

    multiple_ios_cases = [
        multiple_ios_case_1,
        multiple_ios_case_2,
        multiple_ios_case_3,
    ]

    aux_cases = [
        no_inputs_case_1,
        no_inputs_case_2,
        no_inputs_case_3,
        P_Q_case_1,
        no_ios_case_1,
        no_ios_case_2,
        no_ios_case_3,
        contradiction_case_1,
        contradiction_case_2,
    ]

    dond_care_cases = [
        dont_care_case_1,
    ]

    while_cases = [
        while_case_1,
        while_case_2,
        while_case_3,
        while_case_4,
        while_case_5,
        while_case_6,
        while_case_7,
    ]

    test_cases = []
    test_cases += linear_cases
    test_cases += multiple_ios_cases
    test_cases += aux_cases
    test_cases += dond_care_cases
    test_cases += while_cases

    results = []

    # Run each test case
    for case in test_cases:
        print(f"\n*********** {case.__name__} ***********\n")
        result = case()
        if(result == False):
            results.append(case.__name__)

    print(f"\n********************************\n")

    if results == []:
        print(f"{GREEN}All tests passed!{RESET}")
    else:
        print(f"{RED}Tests failed: {RESET} {results}")