from Synthesizer import *
import os
from contextlib import redirect_stdout
import inspect
from wp import verify, verify2

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

    result = test_basic_cases(program, P, Q, linv, disable_prints)

    expected = False
    assertion = result == expected
    return assert_with_color(assertion, result, expected)

def basic_case_4():
    program = "while x > 0 do ( x := x - 1 ; assert (x >= 0)) ; assert (x = 0)"

    P = lambda d: d["x"] > 0
    Q = lambda d: True
    linv = lambda d: d["x"] >= 0

    result = test_basic_cases(program, P, Q, linv, disable_prints)

    expected = True
    assertion = result == expected
    return assert_with_color(assertion, result, expected)

def basic_case_5():
    program = "assert(c1 >= 3) ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; assert(a = c)"

    P = lambda d: d["c1"] >= 3
    Q = lambda d: True
    linv = lambda d: True

    result = test_basic_cases(program, P, Q, linv, disable_prints)

    expected = False
    assertion = result == expected
    return assert_with_color(assertion, result, expected)

def basic_case_6():
    program = "c1 := 2 ; assert(c1 >= 3) ; c2 := hole_2 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; assert(a = c)"

    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    result = test_basic_cases(program, P, Q, linv, disable_prints)

    expected = False
    assertion = result == expected
    return assert_with_color(assertion, result, expected)

class NoErrorExcpected(Exception):
        pass

def test_synth_program(program, P, Q, linv, expected_program, expected_error=NoErrorExcpected, to_disable_print = disable_prints, lower_bound=-100, upper_bound=100):

    synth = Synthesizer(program)
    try:
        if to_disable_print:
            with open(os.devnull, 'w') as f:
                with redirect_stdout(f):
                    returned_program = synth.synth_program(program, P, Q, linv, lower_bound, upper_bound)
        else:
            returned_program = synth.synth_program(program, P, Q, linv, lower_bound, upper_bound)
    except expected_error as e:
        returned_program = expected_error
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        returned_program = e

    if(expected_error is not NoErrorExcpected):
        assertion = returned_program == expected_error
        return assert_with_color(assertion, returned_program, expected_error)
    else:
        assertion = expected_program == returned_program
        return assert_with_color(assertion, returned_program, expected_program)

def holes_basic_case_1():
    program = "c1 := ?? ; assert(c1 >= 2) ; c2 := ?? ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; assert(a = c)"

    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = "c1 := 2 ; assert(c1 >= 2) ; c2 := 1 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; assert(a = c)"
    expected_error = NoErrorExcpected

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints, -100, 100)

def holes_basic_case_1():
    program = "c1 := ?? ; assert(c1 >= 2) ; c2 := ?? ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; assert(a = c)"

    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = "c1 := 2 ; assert(c1 >= 2) ; c2 := 1 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; assert(a = c)"
    expected_error = NoErrorExcpected

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints, -100, 100)

def holes_basic_case_2():
    program = "c1 := ?? ; c2 := ?? ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; assert(a = c)"

    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = "c1 := 2 ; c2 := 1 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; assert(a = c)"
    expected_error = NoErrorExcpected

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints, -100, 100)

# def holes_basic_not_so_basic():
#     program = "c1 := ?? ; c2 := ?? ; a := c1 * x ; b := c2 + 2 ; a := a + b; c := x + x ; assert(a != c)"

#     P = lambda d: True
#     Q = lambda d: True
#     linv = lambda d: True

#     expected_program = "c1 := 2 ; c2 := 1 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; assert(a = c)"
#     expected_error = NoErrorExcpected

def holes_basic_case_3():
    program = "x := 2 * ?? ; if x = 6 then y := 4 else skip ; assert y = 4"

    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = "x := 2 * 3 ; if x = 6 then y := 4 else skip ; assert y = 4"
    expected_error = NoErrorExcpected

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints, -100, 100)

def holes_basic_case_4():
    program = "x := 8 + ?? ; z:= x + 8;  if z = 20 then y := 8 else y := 5; assert y = 8"

    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = "x := 8 + 4 ; z:= x + 8;  if z = 20 then y := 8 else y := 5; assert y = 8"
    expected_error = NoErrorExcpected

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints, -100, 100)

def holes_basic_case_5():
    program = "x:= 2; y:= ?? ; assert (y - 1) > x; if (y - 3) = 5 then x := x + ?? else x:= x + 2 ; assert (x = 5)"

    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = "x:= 2; y:= 8 ; assert (y - 1) > x; if (y - 3) = 5 then x := x + 3 else x:= x + 2 ; assert (x = 5)"
    expected_error = NoErrorExcpected

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints, 0, 10)

def holes_basic_case_6():
    program = "x := 8 + ?? ; if z = (y + ??) then y := 20 - x else y := 5; assert y = 8"

    P = lambda d: And(d["y"] > 0 , d["z"] > 0)
    Q = lambda d: True
    linv = lambda d: True

    expected_program = "x := 8 + 8 ; z:= x + 8;  if z = 20 then y := 8 else y := 5; assert y = 8"
    expected_error = Synthesizer.ProgramNotVerified

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, False, -100, 100)

def assert_tests():
    print("assert tests")

    # List of test case functions
    basic_cases = [
        basic_case_1,
        basic_case_2,
        basic_case_3,
        basic_case_4,
        basic_case_5,
        basic_case_6,
    ]

    holes_basic_cases = [
        holes_basic_case_1,
        holes_basic_case_2,
        holes_basic_case_3,
        holes_basic_case_4,
        holes_basic_case_5,
        holes_basic_case_6,
    ]

    test_cases = []
    test_cases += basic_cases
    test_cases += holes_basic_cases

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