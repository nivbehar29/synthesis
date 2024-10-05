import typing
import operator
from z3 import Int, ForAll, Implies, Not, And, Solver, unsat, sat, Ast, Or

#from WhileLang import syntax

from syntax.tree import Tree
from syntax.while_lang import parse, parse_and_unroll
from wp import *

import re
import copy

class Synthesizer:
    def __init__(self, program):
        self.orig_program = program
        self.ast_orig = parse_and_unroll(self.orig_program)
        self.pvars = []

        if(self.ast_orig is not None):
            self.pvars = sorted(list(getPvars(self.ast_orig)))

        self.inputs = []  # List of input examples
        self.outputs = []   # List of output examples

    def process_holes(self, orig_program):
        """Replaces all occurrences of '??' in the program string with unique hole variables."""
        holes_program = copy.deepcopy(orig_program)
        holes = []
        hole_counter = 0
        while '??' in holes_program:
            hole_var = f"hole_{hole_counter}"  # Create a unique hole variable
            holes_program = holes_program.replace('??', hole_var, 1)  # Replace only the first occurrence of '??'
            holes.append(hole_var)  # Add the hole variable to holes
            hole_counter += 1  # Increment the hole counter for uniqueness

        return holes_program, holes

    def add_example(self, input, output):
        """Adds a single input-output example pair to the synthesizer."""
        self.inputs.append(input)
        self.outputs.append(output)

    def add_io_example(self, inputs, outputs):
        """ need to implement this function
            inputs/outputs are lists of tuples (var, value)"""
        
        if(self.pvars is []):
            return

        try:
            if inputs != [] and outputs != []:

                new_example_in = ['_'] * len(self.pvars)
                new_example_out = ['_'] * len(self.pvars)
                
                for input in inputs:
                    index = self.pvars.index(input[0])
                    new_example_in[index] = input[1]

                for output in outputs:
                    index = self.pvars.index(output[0])
                    new_example_out[index] = output[1]

                self.inputs.append(new_example_in)
                self.outputs.append(new_example_out)
        except ValueError:
            print("Error: input/output variable not found in program")

    # def find_holes(self, ast, P, Q, linv):
    #     if ast is not None:
    #         wp = WP(ast)
    #         wp_stmt = wp.wp(ast, Q, linv)
    #         VC = Implies(P(wp.env), wp_stmt(wp.env))

    #         solver = Solver()
    #         solver.add(VC)

    #         if solver.check() == unsat:
    #             print(">> The program is NOT verified.")
    #         else:
    #             print(">> The program is verified.")
    #             print("holes examples: ", solver.model())

    def verify(self, ast, P, Q, linv):
        if ast is not None:
            wp = WP(ast)
            wp_stmt = wp.wp(ast, Q, linv)
            VC = Implies(P(wp.env), wp_stmt(wp.env))

            solver = Solver()
            solver.add(Not(VC))

            if solver.check() == unsat:
                print(">> The program is verified.")
            else:
                print(">> The program is Not verified.")
                print("Counterexample: ", solver.model())

    def generate_conditions(self, inputs, outputs, pvars):
        P = []
        Q = []

        for example_input, example_output in zip(inputs, outputs):
            p = lambda d: True
            q = lambda d: True

            print("\nadding conditions to P:")
            for var, value in zip(pvars, example_input):
                if value != '_':
                    prev_p = copy.deepcopy(p)
                    p = lambda d, p = prev_p, var = var, value = value: And(p(d), d[var] == value)
                    print(f"var = {var}, value = {value}")
                    

            print("\nadding conditions to Q:")
            for var, value in zip(pvars, example_output):
                if value != '_':
                    prev_q = copy.deepcopy(q)
                    q = lambda d, q = prev_q, var = var, value = value: And(q(d), d[var] == value)
                    print(f"var = {var}, value = {value}")

            print("\n")

            P.append(p)
            Q.append(q)

        return P, Q

    def fill_holes(self, program, sol):
        """Fills the holes in the program with the values from the solver model."""
        holes_to_fill_dict = self.extract_holes_from_dict(extract_model_assignments(sol))
        print("holes_to_fill_dict: ", holes_to_fill_dict)
    
        for key, value in holes_to_fill_dict.items():
            # Replace each occurrence of 'key' with its corresponding 'value'
            program = program.replace(key, str(value))
        return program
    
    def fill_holes_with_zeros(self, program, holes: list):
        """Fills the holes in the program with a '0'"""
        print("hole to fill with zeroes: ", holes)
    
        for hole in holes:
            # Replace each occurrence of 'key' with its corresponding 'value'
            program = program.replace(hole, str(0))
        return program

    def extract_holes_from_dict(self, dict):
        hole_pattern = re.compile(r'hole_\d+')
        # Extract the keys and values that match the pattern
        holes_dict = {k: v for k, v in dict.items() if hole_pattern.match(k)}
        return holes_dict

    def synth_IO_program(self, orig_program, inputs, outputs, lower_bound = -100, upper_bound = 100, linv = None):
        """Synthesizes a program using input-output examples."""
        ast_orig = parse_and_unroll(orig_program)

        if(self.ast_orig is None):
            print("Error: Invalid program")
            return ""

        pvars = sorted(list(getPvars(ast_orig)))
        print("Pvars: ", pvars)

        P, Q = self.generate_conditions(inputs, outputs, pvars)

        if linv is None:
            linv = lambda d: True
        holes_program, holes = self.process_holes(orig_program) # Replace all occurrences of '??' with unique hole variables, returnes program with holes vars, and holes vars list
        print("Holes:", holes)
        holes_program = holes_program
        ast_holes = parse_and_unroll(holes_program)
        if(ast_holes is None):
            print("Error: Invalid program")
            return ""
        # print(ast)

        pvars_holes = set(n for n in ast_holes.terminals if isinstance(n, str) and n != 'skip')
        print("Pvars with holes variables:", pvars_holes)
        # env = mk_env(pvars_holes)


        P_holes = copy.deepcopy(P)
        Q_holes = copy.deepcopy(Q)

        # this is to bound the limits of the holes - maybe we will need this for complicated programs
        bound_conditions = [lambda d: True] * len(P_holes)
        if(lower_bound != None and upper_bound != None):
            for i in range(len(holes)):
                for j in range(len(outputs)):
                    prev_q = copy.deepcopy(bound_conditions[j])
                    bound_conditions[j] = lambda d, hole_key=holes[i], q=prev_q: And(q(d), And(d[hole_key] < upper_bound, d[hole_key] > lower_bound))

        holes_conditions = lambda d: False


        i = 0
        while (i < len(inputs)):
            print("\n*******************************************\n")
            print("i = ", i)
            print("ast_holes: \n", ast_holes)

            wp = WP(ast_holes)
            wp_stmt = wp.wp(ast_holes, Q_holes[i], linv)

            formula = And(P_holes[i](wp.env), wp_stmt(wp.env))

            # prev_q = copy.deepcopy(Q_holes[i])
            # print("Q_holes[i]: ", Q_holes[i])
            # new_q = lambda d: And(d['a'] > 0, d['a'] == d['b'])
            # Q_holes[i] = lambda d, q = prev_q, new_qq = new_q: And(q(d), new_qq(d))

            # Q = Q_holes[i] # new_q

            # return verify(P_holes[i], ast_holes, Q_holes[i], linv)
            # return ""

            solver = Solver()
            solver.add(formula)
            if solver.check() == unsat:
                print(">> The program is verified with IO example ", i)

                i += 1
                continue  # Continue with the next input

            # Get the model and fill the holes in the program
            model = solver.model()
            print("model: ", model)
            filled_program = self.fill_holes(holes_program, solver)
            print("filled program:")
            print(filled_program) 

            # check if all verified
            solver_for_counterexample = None
            is_valid_for_all_ios = True
            for j in range(len(inputs)):
                is_verified, solver_for_counterexample = verify(P[j], parse_and_unroll(filled_program), Q[j], linv = linv)
                if(is_verified):
                    continue
                else:
                    is_valid_for_all_ios = False
                    break

            print()

            if(is_valid_for_all_ios):
                print("The program is verified for all IO examples")
                filled_program = self.fill_holes_with_zeros(filled_program, holes)
                return filled_program
            else:
                print("The program is not verified for all IO examples")
                # counterexample_dict = extract_model_assignments(solver)
                # print("counter example dict:", counterexample_dict)

                holes_dict = self.extract_holes_from_dict(extract_model_assignments(solver))
                counterexample_dict = {}
                if(solver_for_counterexample != None):
                    counterexample_dict = self.extract_holes_from_dict(extract_model_assignments(solver_for_counterexample))
                    print("counter example dict:", counterexample_dict)
                    holes_dict.update(counterexample_dict)
                # counterexample_dict = extract_model_assignments(solver)
                print("holes to set as not valid:", holes_dict)

                for j in range(len(inputs)):
                    addition_holes_condition = lambda d: True
                    for hole_key, hole_value in holes_dict.items():
                        prev_addition_holes_conditions = addition_holes_condition
                        addition_holes_condition = lambda d, q = prev_addition_holes_conditions, var = hole_key, value = hole_value: And(q(d), d[var] == value)

                    prev_holes_conditions = copy.deepcopy(holes_conditions)
                    holes_conditions = lambda d, q = prev_holes_conditions, q2 = addition_holes_condition: Or(q(d), q2(d))

                    # prev_q = Q_holes[j]
                    orig_q = copy.deepcopy(Q[j])
                    # Q_holes[j] = lambda d, q=orig_q: And(q(d), Not(holes_conditions(d)))
                    Q_holes[j] = lambda d, q = orig_q, bc = bound_conditions[j]: And(bc(d), And(q(d), Not(holes_conditions(d))))

                    

                # start again from IO number 0
                i = 0

        return ""

def test_assertions():
## start of counter example synthesis

    # example program
    pvars = ["x, a, b, c1, c2, hole_1, hole_2"]
    
    orig_program = "c1 := hole_1 ; c2 := hole_2 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x "

    # verify with init values for holes: hole_1 = 0, hole_2 = 0
    orig_program = "c1 := 0 ; c2 := 0 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x "
    # -> CS: [] -> every x is a counter example -> set x = 0

    # set x = 0 and find holes
    #orig_program = "x := 0 ; c1 := hole_1 ; c2 := hole_2 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x "
    # -> hole_2 = 1

    # verify with init values hole_1 = 0, and with found hole_2 = 1
    #orig_program = "c1 := 0 ; c2 := 1 ; a := c1 * x ; b := c2 - 1 ; a := a + b ; c := x + x "
    # -> CS: [x = 1]

    # copy the program with x = 0 and x = 1 and find holes
    #orig_program = "x := 0 ; c1 := hole_1 ; c2 := 1 ; a := c1 * x ; b := c2 - 1 ; a := a + b ; c := x + x "
    # -> no holes to find
    #orig_program = "x := 1 ; c1 := hole_1 ; c2 := 1 ; a := c1 * x ; b := c2 - 1 ; a := a + b ; c := x + x "
    # -> hole_1 = 2
    

    #orig_program = "x := 1 ; c1 := hole_1 ; c2 := 1 ; a := c1 * x ; b := c2 - 1 ; a := a + b ; c := x + x "



    # verify with found hole_1 = 2, hole_2 = 1
    #orig_program = "c1 := 2 ; c2 := 1 ; a := c1 * x ; b := c2 - 1 ; a := a + b ; c := x + x "

    P = lambda d: True
    Q = lambda d: d["a"] == d["c"]
    linv = lambda d: True

    synth = Synthesizer(orig_program, pvars)

## end of counter example synthesis

def main():

    program = "while a != b do if a > b then a := a - b else b := b - a ; x := 1"
    ast = parse(program)
    print(ast)

    # program_invert = ast_to_string(ast)
    # print(program_invert)

    # ast = parse(program_invert)
    # print(ast)

    ast_unrolled = parse_and_unroll(program)
    print(ast_unrolled)
    # program_invert = ast_to_string(ast_unrolled)
    # print(program_invert)

    # program = "if a > b then a := a - b else if a < b then b := b - a else skip"
    # ast = parse(program)
    # print(ast)

if __name__ == "__main__":
    main()