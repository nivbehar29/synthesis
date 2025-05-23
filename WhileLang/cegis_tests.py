from Synthesizer import *
import os
from contextlib import redirect_stdout
from wp import verify

RED = "\033[31m"
GREEN = "\033[32m"
RESET = "\033[0m"

disable_prints = True

def assert_with_color(condition, input, output, expected):
    if not condition:
        print(f"{RED}Assertion failed!{RESET}")
        print(f"output: {output}")
        print(f"expected: {expected}")
        return False
    else:
        print(f"{GREEN}Assertion passed!{RESET}")
        print(f"input: {input}")
        print(f"output: {output}")
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
    return assert_with_color(assertion, program, result, expected)

def basic_case_2():
    program = "b := 3 ; c := 6 ; d := b + c ; assert (a = d)"

    P = lambda d: d["a"] == 10
    Q = lambda d: True
    linv = lambda d: True

    result = test_basic_cases(program, P, Q, linv, disable_prints)

    expected = False
    assertion = result == expected
    return assert_with_color(assertion, program, result, expected)

def basic_case_3():
    program = "while x > 0 do ( x := x - 1 ; assert (x > 0))"

    P = lambda d: d["x"] > 0
    Q = lambda d: True
    linv = lambda d: d["x"] >= 0

    result = test_basic_cases(program, P, Q, linv, disable_prints)

    expected = False
    assertion = result == expected
    return assert_with_color(assertion, program, result, expected)

def basic_case_4():
    program = "while x > 0 do ( x := x - 1 ; assert (x >= 0)) ; assert (x = 0)"

    P = lambda d: d["x"] > 0
    Q = lambda d: True
    linv = lambda d: d["x"] >= 0

    result = test_basic_cases(program, P, Q, linv, disable_prints)

    expected = True
    assertion = result == expected
    return assert_with_color(assertion, program, result, expected)

def basic_case_5():
    program = "assert(c1 >= 3) ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; assert(a = c)"

    P = lambda d: d["c1"] >= 3
    Q = lambda d: True
    linv = lambda d: True

    result = test_basic_cases(program, P, Q, linv, disable_prints)

    expected = False
    assertion = result == expected
    return assert_with_color(assertion, program, result, expected)

def basic_case_6():
    program = "c1 := 2 ; assert(c1 >= 3) ; c2 := hole_2 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; assert(a = c)"

    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    result = test_basic_cases(program, P, Q, linv, disable_prints)

    expected = False
    assertion = result == expected
    return assert_with_color(assertion, program, result, expected)

class NoErrorExcpected(Exception):
        pass

def test_synth_program(program, P, Q, linv, expected_program, expected_error=NoErrorExcpected, to_disable_print = disable_prints, unroll_limit = 10):

    try:
        if to_disable_print:
            with open(os.devnull, 'w') as f:
                with redirect_stdout(f):
                    synth = Synthesizer(program)
                    returned_program = synth.synth_program(program, P, Q, linv, unroll_limit)
        else:
            synth = Synthesizer(program)
            returned_program = synth.synth_program(program, P, Q, linv, unroll_limit)
    except expected_error as e:
        returned_program = expected_error
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        returned_program = e

    if(expected_error is not NoErrorExcpected):
        assertion = returned_program == expected_error
        return assert_with_color(assertion, program, returned_program, expected_error)
    else:
        assertion = returned_program in expected_program
        return assert_with_color(assertion, program, returned_program, expected_program)

def holes_basic_case_1():
    program = "c1 := ?? ; assert(c1 >= 2) ; c2 := ?? ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; assert(a = c)"

    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = ["c1 := 2 ; assert(c1 >= 2) ; c2 := 1 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; assert(a = c)"]
    expected_error = NoErrorExcpected

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints)

def holes_basic_case_2():
    program = "c1 := ?? ; c2 := ?? ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; assert(a = c)"

    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = ["c1 := 2 ; c2 := 1 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; assert(a = c)"]
    expected_error = NoErrorExcpected

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints)

# excluded because it may give deifferent results so its may be hard to test. but seems it works fine.
def holes_basic_case_3():
    program = "c1 := ?? ; c2 := ?? ; a := c1 * x ; b := c2 + 2 ; a := a + b; c := x + x ; assert(a != c)"

#  c1 * x + c2 + 2 != 2x
# -x -1 +2 != 2x
    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = "c1 := -1 ; c2 := -1 ; a := c1 * x ; b := c2 + 2 ; a := a + b; c := x + x ; assert(a != c)"
    expected_error = NoErrorExcpected

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints)


def holes_basic_case_4():
    program = "x := 2 * ?? ; if x = 6 then y := 4 else skip ; assert y = 4"

    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = ["x := 2 * 3 ; if x = 6 then y := 4 else skip ; assert y = 4"]
    expected_error = NoErrorExcpected

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints)

def holes_basic_case_5():
    program = "x := 8 + ?? ; z:= x + 8;  if z = 20 then y := 8 else y := 5; assert y = 8"

    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = ["x := 8 + 4 ; z:= x + 8;  if z = 20 then y := 8 else y := 5; assert y = 8"]
    expected_error = NoErrorExcpected

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints)

def holes_basic_case_6():
    program = "x:= 2; y:= ?? ; assert (y - 1) > x; if (y - 3) = 5 then x := x + ?? else x:= x + 2 ; assert (x = 5)"

    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = ["x:= 2; y:= 8 ; assert (y - 1) > x; if (y - 3) = 5 then x := x + 3 else x:= x + 2 ; assert (x = 5)"]
    expected_error = NoErrorExcpected

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints)

def holes_basic_case_7():
    program = "x := 8 + ?? ; if z = (y + ??) then y := 20 - x else y := 5; assert y = 8"

    P = lambda d: And(d["y"] > 0 , d["z"] > 0)
    Q = lambda d: True
    linv = lambda d: True

    expected_program = ["x := 8 + 8 ; z:= x + 8;  if z = 20 then y := 8 else y := 5; assert y = 8"]
    expected_error = Synthesizer.ProgramNotVerified

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints)

def holes_basic_case_8():
    program = "x:= 3; y:= ??; assert ((y - 1) > x); if (y - 3) = 5 then x := x + ?? else x:= x + 6"

    P = lambda d: True
    Q = lambda d: And(d["x"] == 8, d["y"] == 8)
    linv = lambda d: True

    expected_program = ["x:= 3; y:= 8; assert ((y - 1) > x); if (y - 3) = 5 then x := x + 5 else x:= x + 6"]
    expected_error = NoErrorExcpected

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints)

def holes_no_sol_case_1():
    program = "y:= x + ?? ; if y = 10 then x := 5 else x := 9"

    P = lambda d: True
    Q = lambda d: d["x"] == 8
    linv = lambda d: True

    expected_program = ""
    expected_error = Synthesizer.ProgramNotVerified

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints)

def holes_no_sol_case_2():
    program = "y := ?? ; if x < 6 then ( x := y + 4 ) else skip  ; assert x = 6"

    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = ""
    expected_error = Synthesizer.ProgramNotVerified

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints)

# diverges
def holes_no_sol_case_3():
    # brutal test which can't be solved by the current CEGIS algorithm.
    # currently our algorithm runs forever for this test.
    # it is possible to bound x and the tool will manage to determine that there is no solution
    program = "y:= x + ?? ; if y = 10 then x := 5 else x := 9 ; assert x = 9"

    # bounded x program:
    # assert x > -10000000 ; assert x < 10000000 ; y:= x + ?? ; if y = 10 then x := 5 else x := 9 ; assert x = 9


    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = ""
    expected_error = Synthesizer.ProgramNotVerified

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints)

# diverges
# def holes_no_sol_case_4():
#     program = "t := ?? ; if x < t then x := 0 else x := 1 ; assert x = 0"

#     P = lambda d: True
#     Q = lambda d: True
#     linv = lambda d: True

#     expected_program = ""
#     expected_error = Synthesizer.NoInputToSatisfyProgram

#     return test_synth_program(program, P, Q, linv, expected_program, expected_error, False, -100, 100)

def holes_while_case_1():
    program = "y := 0 ; x := 0 ; t := ?? ; while x < t do ( y := y + 1 ; x := x + 1)  ; assert y = 5"
    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = ["y := 0 ; x := 0 ; t := 5 ; while x < t do ( y := y + 1 ; x := x + 1)  ; assert y = 5"]
    expected_error = NoErrorExcpected

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints, 10)

def holes_while_case_2():
    program = "x := 0 ; t := ?? ; while x < t do ( x := x + 1 ; assert t = 3) ; assert x > 0"
    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = ["x := 0 ; t := 3 ; while x < t do ( x := x + 1 ; assert t = 3) ; assert x > 0"]
    expected_error = NoErrorExcpected

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints, 10)


def holes_while_case_3():
    program = "x := 0 ; t := ?? ; while x < t do ( x := x + ?? ; assert t = 6) ; assert x > 0 ; assert x = 9"
    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True
    # And(d['x'] >= 0, d['t'] == 6)
    # d['x'] == 9


    expected_program = ["x := 0 ; t := 6 ; while x < t do ( x := x + 9 ; assert t = 6) ; assert x > 0 ; assert x = 9"]
    expected_error = NoErrorExcpected

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints, 10)

def error_case_ProgramNotValid():
    # Can't be parsed (colon at the end)
    program = "x := 0 ; t := ?? ; while x < t do ( x := x + 1 ; assert t = 6) ; assert x > 0 ; assert x = 9 ;"
    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = ""
    expected_error = Synthesizer.ProgramNotValid

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints, 10)

def error_case_ProgramHasNoHoles():
    # No holes -> nothing to synthesize
    program = "x := 0 ; t := 7 ; while x < t do ( x := x + 1 ; assert t = 6)"
    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = ""
    expected_error = Synthesizer.ProgramHasNoHoles

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints, 10)

def unroll_limit_case_1():
    # The unroll limit will affect the result of the synthesis
    program = "y := 0 ; x := 0 ; t := ?? ; while x < t do ( y := y + ?? ; x := x + ??)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6"
    unroll_limit = 7

    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = ["y := 0 ; x := 0 ; t := 1 ; while x < t do ( y := y + 6 ; x := x + 1)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 2 ; while x < t do ( y := y + 3 ; x := x + 1)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 3 ; while x < t do ( y := y + 2 ; x := x + 1)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 6 ; while x < t do ( y := y + 1 ; x := x + 1)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",

                        "y := 0 ; x := 0 ; t := 1 ; while x < t do ( y := y + 6 ; x := x + 2)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 2 ; while x < t do ( y := y + 6 ; x := x + 2)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 3 ; while x < t do ( y := y + 3 ; x := x + 2)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 4 ; while x < t do ( y := y + 3 ; x := x + 2)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 5 ; while x < t do ( y := y + 2 ; x := x + 2)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 6 ; while x < t do ( y := y + 2 ; x := x + 2)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",

                        "y := 0 ; x := 0 ; t := 1 ; while x < t do ( y := y + 6 ; x := x + 3)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 2 ; while x < t do ( y := y + 6 ; x := x + 3)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 3 ; while x < t do ( y := y + 6 ; x := x + 3)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 4 ; while x < t do ( y := y + 3 ; x := x + 3)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 5 ; while x < t do ( y := y + 3 ; x := x + 3)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 6 ; while x < t do ( y := y + 3 ; x := x + 3)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",

                        "y := 0 ; x := 0 ; t := 1 ; while x < t do ( y := y + 6 ; x := x + 4)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 2 ; while x < t do ( y := y + 6 ; x := x + 4)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 3 ; while x < t do ( y := y + 6 ; x := x + 4)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 4 ; while x < t do ( y := y + 6 ; x := x + 4)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 5 ; while x < t do ( y := y + 3 ; x := x + 4)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 6 ; while x < t do ( y := y + 3 ; x := x + 4)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",

                        "y := 0 ; x := 0 ; t := 1 ; while x < t do ( y := y + 6 ; x := x + 5)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 2 ; while x < t do ( y := y + 6 ; x := x + 5)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 3 ; while x < t do ( y := y + 6 ; x := x + 5)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 4 ; while x < t do ( y := y + 6 ; x := x + 5)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 5 ; while x < t do ( y := y + 6 ; x := x + 5)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 6 ; while x < t do ( y := y + 3 ; x := x + 5)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",

                        "y := 0 ; x := 0 ; t := 1 ; while x < t do ( y := y + 6 ; x := x + 6)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 2 ; while x < t do ( y := y + 6 ; x := x + 6)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 3 ; while x < t do ( y := y + 6 ; x := x + 6)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 4 ; while x < t do ( y := y + 6 ; x := x + 6)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 5 ; while x < t do ( y := y + 6 ; x := x + 6)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 6 ; while x < t do ( y := y + 6 ; x := x + 6)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        ]
    expected_error = NoErrorExcpected

    # res = test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints, unroll_limit)
    # while(res == True):
    #     res = test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints, unroll_limit)
    
    print(f"unroll_limit = {unroll_limit}")
    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints, unroll_limit)

def unroll_limit_case_2():
    # The unroll limit will affect the result of the synthesis
    program = "y := 0 ; x := 0 ; t := ?? ; while x < t do ( y := y + ?? ; x := x + ??)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6"
    unroll_limit = 1

    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: And(d["t"] <= 6 , d["x"] >= 0)

    expected_program = ["y := 0 ; x := 0 ; t := 1 ; while x < t do ( y := y + 6 ; x := x + 1)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",

                        "y := 0 ; x := 0 ; t := 1 ; while x < t do ( y := y + 6 ; x := x + 2)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 2 ; while x < t do ( y := y + 6 ; x := x + 2)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",

                        "y := 0 ; x := 0 ; t := 1 ; while x < t do ( y := y + 6 ; x := x + 3)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 2 ; while x < t do ( y := y + 6 ; x := x + 3)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 3 ; while x < t do ( y := y + 6 ; x := x + 3)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",

                        "y := 0 ; x := 0 ; t := 1 ; while x < t do ( y := y + 6 ; x := x + 4)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 2 ; while x < t do ( y := y + 6 ; x := x + 4)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 3 ; while x < t do ( y := y + 6 ; x := x + 4)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 4 ; while x < t do ( y := y + 6 ; x := x + 4)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",

                        "y := 0 ; x := 0 ; t := 1 ; while x < t do ( y := y + 6 ; x := x + 5)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 2 ; while x < t do ( y := y + 6 ; x := x + 5)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 3 ; while x < t do ( y := y + 6 ; x := x + 5)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 4 ; while x < t do ( y := y + 6 ; x := x + 5)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 5 ; while x < t do ( y := y + 6 ; x := x + 5)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",

                        "y := 0 ; x := 0 ; t := 1 ; while x < t do ( y := y + 6 ; x := x + 6)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 2 ; while x < t do ( y := y + 6 ; x := x + 6)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 3 ; while x < t do ( y := y + 6 ; x := x + 6)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 4 ; while x < t do ( y := y + 6 ; x := x + 6)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 5 ; while x < t do ( y := y + 6 ; x := x + 6)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        "y := 0 ; x := 0 ; t := 6 ; while x < t do ( y := y + 6 ; x := x + 6)  ; assert y = 6 ; assert x <= 6 ; assert x >= 0 ; assert t <= 6",
                        ]
    expected_error = NoErrorExcpected

    # res = test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints, unroll_limit)
    # while(res == True):
    #     res = test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints, unroll_limit)
    
    print(f"unroll_limit = {unroll_limit}")
    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints, unroll_limit)

# Just a playground for testing
def playground():
    program = "y := 0 ; x := 0 ; t := ?? ; while x < t do ( y := y + 1 ; x := x + 1)  ; assert y = 10"
    # thats a problem because currently we unroll loop 10 times, and only then the program can be satisfied
    # maybe we should unroll the loop 1, then verify, if not - unrool 2, then verify, etc
    # do it until we reach a defined maximum bounds, like 10 or something. the maximum bound can be a parameter of the function

    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    expected_program = ""
    expected_error = Synthesizer.NoInputToSatisfyProgram

    # program = "x:= 0; t := hole_0 ; while x < t do ( x :=  x + 1)  ; assert x = 10"

    # P = lambda d: And(d["x"] == 0)#, d["t"] == 10)
    # Q = lambda d: True
    # linv = lambda d: And(d["x"] <= 10)#, d["t"] == 10)
    # is_exist_input_to_satisfy(P, parse(program), Q, linv)

    return test_synth_program(program, P, Q, linv, expected_program, expected_error, disable_prints, 1)


    # program = "x := 0; x:= hole_0; a := 0 ; while a != 1 do ( a := 1 )"# ; assert x = 10"
    # program = "x := 0; x:= hole_0; a := 0 ; if a != 1 then ( a := 1 ) else skip ; assert x = 10"
    # P = lambda d: True
    # Q = lambda d: True
    # linv = lambda d: d["x"] >= 0
    # is_exist_input_to_satisfy(P, parse(program), Q, linv)

    # why does this not verifyed?!?!
    # program = "x:=10 ; y := x + 1; a := 0 ; while a != 1 do ( a := 1 )"# ; assert x = 10"
    # P = lambda d: True
    # Q = lambda d: d["x"] == 10
    # linv = lambda d: d["x"] >= 0
    # verify(P, parse(program), Q, linv)

    # program = "x:= hole_0 ; a := 0 ;assert(x >= 0); if a != 1 then ( a := 1 ) else skip ; assert(x >= 0)"
    # res = from_assert_to_list_to_verify(program)
    # print(res[0])
    # print(res[1])

    # program = "while x < t do y := y + 1 ; x := x + 1 ; assert y = 5 ; x := 0"

def cegis_tests():
    print("cegis tests")

    # assertion test (no synthesis)
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
        holes_basic_case_4,
        holes_basic_case_5,
        holes_basic_case_6,
        holes_basic_case_7,
        holes_basic_case_8,
    ]

    holes_no_sol_cases = [
        holes_no_sol_case_1,
        holes_no_sol_case_2,
        # holes_no_sol_case_3, # Can't be solved by the current CEGIS algorithm
    ]

    holes_while_cases = [
        holes_while_case_1,
        holes_while_case_2,
        holes_while_case_3,
    ]

    errors_cases = [
        error_case_ProgramNotValid,
        error_case_ProgramHasNoHoles,
        error_case_ProgramHasNoHoles,
    ]

    unroll_limit_cases = [
        unroll_limit_case_1,
        unroll_limit_case_2,
    ]

    test_cases = []
    test_cases += basic_cases
    test_cases += holes_basic_cases
    test_cases += holes_no_sol_cases
    test_cases += holes_while_cases
    test_cases += errors_cases
    test_cases += unroll_limit_cases

    # Use this for debugging
    # test_cases += [playground]

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