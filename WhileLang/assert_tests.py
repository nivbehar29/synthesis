from Synthesizer import *
import os
from contextlib import redirect_stdout
import inspect

RED = "\033[31m"
GREEN = "\033[32m"
RESET = "\033[0m"

disable_prints = True

def assert_with_color(condition, output, expected):
    if not condition:
        print(f"{RED}Assertion failed!{RESET}")
        print(f"output: {output}")
        print(f"expected: {expected}")
        return False
    else:
        print(f"{GREEN}Assertion passed!{RESET}")
        return True

def verify_program(program, P, Q, linv):
    ast = parse(program)
    result = False
    if ast is not None:
        result, _ = verify(P, ast, Q, linv=linv)
    return result

def test_basic_cases(program, P, Q, linv, to_disable_print):

    if to_disable_print:
            with open(os.devnull, 'w') as f:
                with redirect_stdout(f):
                    return verify_program(program, P, Q, linv)

    else:
        return verify_program(program, P, Q, linv)

def basic_case_1():
    program = "b := 3 ; c := 6 ; d := b + c ; assert (a = d)"

    P = lambda d: d["a"] == 9
    Q = lambda d: True
    linv = lambda d: True

    result = test_basic_cases(program, P, Q, linv, disable_prints)

    expected = True
    assertion = result == expected
    return assert_with_color(assertion, result, expected)

def basic_case_2():
    program = "b := 3 ; c := 6 ; d := b + c ; assert (a = d)"

    P = lambda d: d["a"] == 10
    Q = lambda d: True
    linv = lambda d: True

    result = test_basic_cases(program, P, Q, linv, disable_prints)

    expected = False
    assertion = result == expected
    return assert_with_color(assertion, result, expected)

def basic_case_3():
    program = "while x > 0 do ( x := x - 1 ; assert (x > 0))"

    P = lambda d: d["x"] > 0
    Q = lambda d: True
    linv = lambda d: d["x"] >= 0

    result = test_basic_cases(program, P, Q, linv, False)

    expected = False
    assertion = result == expected
    return assert_with_color(assertion, result, expected)

def basic_case_4():
    program = "while x > 0 do ( x := x - 1 ; assert (x >= 0)) ; assert (x = 0)"

    P = lambda d: d["x"] > 0
    Q = lambda d: True
    linv = lambda d: d["x"] >= 0

    result = test_basic_cases(program, P, Q, linv, False)

    expected = True
    assertion = result == expected
    return assert_with_color(assertion, result, expected)

def assert_tests():
    print("assert tests")

    # List of test case functions
    basic_cases = [
        basic_case_1,
        basic_case_2,
        basic_case_3,
        basic_case_4
    ]

    test_cases = []
    test_cases += basic_cases


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