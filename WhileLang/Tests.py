from Synthesizer import *
import os
import sys
from contextlib import redirect_stdout
import inspect

RED = "\033[31m"
GREEN = "\033[32m"
RESET = "\033[0m"

disable_prints = True

def synthesize_io_program(orig_program, inputs_examples, output_examples, lower_bound, upper_bound):
    synth = Synthesizer(orig_program)
    for ex_in, ex_out in zip(inputs_examples, output_examples):
        synth.add_io_example(ex_in, ex_out)
    return synth.synth_IO_program(synth.orig_program, synth.inputs, synth.outputs, lower_bound, upper_bound)

def get_io_program(orig_program, inputs_examples, output_examples, to_disable_print, lower_bound, upper_bound):
    
    output_program = None

    if to_disable_print:
        with open(os.devnull, 'w') as f:
            with redirect_stdout(f):
                output_program = synthesize_io_program(orig_program, inputs_examples, output_examples, lower_bound, upper_bound)

    else:
        output_program = synthesize_io_program(orig_program, inputs_examples, output_examples, lower_bound, upper_bound)

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

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints, -4, 50)
    

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def linear_case_2():

    orig_program =     "c1 := ?? ; c2 := 4 * ?? ; a := c1 * x ; b := c2 - 10 ; a := a + b; c := x * 2 ; if a != c then d := 0 else d := 1"
    expected_program = ""

    inputs_examples = [[("x", 0)],
                       [("x", 1)]]
    
    output_examples = [[("d", 1)],
                       [("d", 1)]]

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints, -100, 100)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def multiple_ios_case_1():
    orig_program =     "c1 := 4 * x ; c2 := 4 * y ; c3 := 4 * z"
    expected_program = "c1 := 4 * x ; c2 := 4 * y ; c3 := 4 * z"

    inputs_examples = [[("x", 1), ("y", 2), ("z", 3)],
                       [("x", 2), ("y", 4), ("z", 6)]]
    
    output_examples = [[("c1", 4), ("c2", 8), ("c3", 12)],
                       [("c1", 8), ("c2", 16), ("c3", 24)]]

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints, -100, 100)

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

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints, -100, 100)

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

    output_program = get_io_program(orig_program, inputs_examples, output_examples, disable_prints, -100, 100)

    assertion = output_program == expected_program
    return assert_with_color(assertion, output_program, expected_program)

def pbe_tests():
    print("pbe tests")

    # List of test case functions
    linear_cases = [
        linear_case_1,
        linear_case_2,
    ]

    multiple_ios = [
        multiple_ios_case_1,
        multiple_ios_case_2,
        multiple_ios_case_3,

    ]

    test_cases = []
    # test_cases += linear_cases
    test_cases += multiple_ios

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

def assert_tests():
    print("assert tests")

def main(args):
    # Check if any arguments are provided
    if not args:
        print("No arguments were passed. Please provide some arguments.")
        return

    # Assume the first argument is the case
    case = args[0]

    if case == "pbe":
        pbe_tests()
    elif case == "assert":
        assert_tests()
    else:
        print("Invalid case selected.")

if __name__ == "__main__":
    arguments = sys.argv[1:]
    main(arguments)