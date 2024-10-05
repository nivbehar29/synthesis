import typing
import operator
from z3 import Int, ForAll, Implies, Not, And, Solver, unsat, sat, Ast, Or

#from WhileLang import syntax

from syntax.tree import Tree
from syntax.while_lang import parse
from wp import *

import re
import copy

class Synthesizer:
    def __init__(self, program):
        self.orig_program = program
        self.holes_program = None
        self.holes = []  # List of holes collected from the AST

        self.inputs = []  # List of input examples
        self.outputs = []   # List of output examples
        
        self.P = []  # Preconditions
        self.Q = []  # Postconditions

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

    def find_holes(self, ast, P, Q, linv):
        if ast is not None:
            wp = WP(ast)
            wp_stmt = wp.wp(ast, Q, linv)
            VC = Implies(P(wp.env), wp_stmt(wp.env))

            solver = Solver()
            solver.add(VC)

            if solver.check() == unsat:
                print(">> The program is NOT verified.")
            else:
                print(">> The program is verified.")
                print("holes examples: ", solver.model())

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

    def generate_IO_program(self):
        all_IO_program = ""
        iter = 1
        # each exampke input \ output is of the form [input_ex_1, input_ex_2, ...], [output_ex_1, output_ex_2, ...]
        for input_ex, output_ex in zip(self.inputs, self.outputs):
            ex_subprogram = ""

            # each input_ex is of the form [(var_1, value_1), (var_2, value_2), ...]
            inputs_str = ""
            for input in input_ex:
                input_str = input[0] + " := " + str(input[1]) + " ; "
                inputs_str += input_str
            
            # each output_ex is of the form [(var_1, value_1), (var_2, value_2), ...]
            outputs_str = ""
            iter_output = 1
            for output in output_ex:
                output_str = "if " + output[0] + " != " + str(output[1]) + " then all_outputs_sat := 0 else skip"
                extra_semicolon = ""
                if iter_output != len(output_ex):
                    extra_semicolon = " ; "
                outputs_str += output_str + extra_semicolon
                iter_output += 1

            extra_semicolon = ""
            if iter != len(self.inputs):
                extra_semicolon = " ; "

            ex_subprogram = inputs_str + self.holes_program + " ; " + outputs_str + extra_semicolon
            all_IO_program = all_IO_program + ex_subprogram

            iter += 1

        all_IO_program = "all_outputs_sat := 1 ; " + all_IO_program

        return all_IO_program
    
    def synth_IO_program_old(self, all_IO_program):
        P = lambda d: d["all_outputs_sat"] == 1
        Q = lambda d: d["all_outputs_sat"] == 1
        linv = lambda d: True
        ast = parse(all_IO_program)
        self.find_holes(ast, P, Q, linv)

    def create_conditions(self, examples_before, examples_after, pvars):
        P = []
        Q = []

        for example_in, example_out in zip(examples_before, examples_after):
            p = lambda d: True
            q = lambda d: True

            print("\nadding conditions to P:")
            for var, value in zip(pvars, example_in):
                if value != '_':
                    prev_p = copy.deepcopy(p)  # store the previous lambda
                    p = lambda d, p=prev_p, var=var, value=value: And(p(d), d[var] == value)
                    print(f"var = {var}, value = {value}")
                    

            print("\nadding conditions to Q:")
            for var, value in zip(pvars, example_out):
                if value != '_':
                    prev_q = copy.deepcopy(q)  # store the previous lambda
                    q = lambda d, q=prev_q, var=var, value=value: And(q(d), d[var] == value)
                    print(f"var = {var}, value = {value}")

            print("\n")

            P.append(p)
            Q.append(q)

        return P, Q

    def fill_holes(self, holes, program, model):
            filled_holes_count = 0
            program_lines = program.split(';')

            # Extract variable assignments from the model
            variable_mapping = {}
            for d in model.decls():
                if d.name() in holes:
                    filled_holes_count += 1
                    print(filled_holes_count)
                variable_mapping[d.name()] = model[d].as_long()  # Convert ExprRef to Python int

            # Function to replace variable placeholders with solution values
            def replace_variable(match):
                variable_name = match.group()
                return str(variable_mapping.get(variable_name, variable_name))

            # Iterate through each line and replace variables with solution values
            filled_program_lines = []
            for line in program_lines:
                filled_line = re.sub(r'hole_\d+', replace_variable, line)
                filled_program_lines.append(filled_line)

            # Join the lines to get the filled program
            filled_program = ';'.join(filled_program_lines)

            return filled_program

    def extract_holes_from_dict(self, dict):
        hole_pattern = re.compile(r'hole_\d+')
        # Extract the keys and values that match the pattern
        holes_dict = {k: v for k, v in dict.items() if hole_pattern.match(k)}
        return holes_dict

    def synth_IO_program(self, orig_program, inputs, outputs):
        ast_orig = parse(orig_program)
        # print(ast_orig)
        pvars = sorted(list(getPvars(ast_orig)))
        print("Pvars: ", pvars)

        P, Q = self.create_conditions(inputs, outputs, pvars)

        linv = lambda d: True
        synth = Synthesizer(orig_program)
        holes_program, holes = synth.process_holes(orig_program) # Replace all occurrences of '??' with unique hole variables, returnes program with holes vars, and holes vars list
        print("Holes:", holes)
        holes_program = holes_program
        ast_holes = parse(holes_program)
        # print(ast)

        pvars_holes = set(n for n in ast_holes.terminals if isinstance(n, str) and n != 'skip')
        print("Pvars holes:", pvars_holes)
        # env = mk_env(pvars_holes)


        P_holes = copy.deepcopy(P)
        Q_holes = copy.deepcopy(Q)

        # this is to bound the limits of the holes - maybe we will need this for complicated programs
        # for i in range(len(holes)):
        #     for j in range(len(outputs)):
        #         prev_q = copy.deepcopy(Q_holes[j])
        #         Q_holes[j] = lambda d, hole_key=holes[i], q=prev_q: And(q(d), And(d[hole_key] < 5, d[hole_key] > -5))

        holes_conditions = lambda d: False


        i = 0
        while (i < len(inputs)):
            print("\n*******************************************\n")
            print("i = ", i)
            print("ast_holes: \n", ast_holes)
            wp = WP(ast_holes)
            wp_stmt = wp.wp(ast_holes, Q_holes[i], linv)

            formula = And(P_holes[i](wp.env), wp_stmt(wp.env))

            solver = Solver()
            solver.add(formula)
            if solver.check() == unsat:
                print(">> The program is verified with IO example ", i)

                i += 1
                continue  # Continue with the next input
            # Get the model and fill the holes in the program
            sol = solver.model()
            print(sol)
            filled_program = self.fill_holes(holes, holes_program, sol)
            print("filled program:")
            print(filled_program)

            # check if all verified
            solver_for_counterexample = None
            is_valid_for_all_ios = True
            for j in range(len(inputs)):
                is_verified, solver_for_counterexample = verify(P[j], parse(filled_program), Q[j], linv = linv)
                if(is_verified):
                    continue
                else:
                    is_valid_for_all_ios = False
                    break

            # is_valid_for_all_ios = all(verify(P[j], parse(filled_program), Q[j], linv = linv)[0] for j in range(len(inputs)))
            print()

            if(is_valid_for_all_ios):
                print("The program is verified for all IO examples")
                break
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
                        addition_holes_condition = lambda d, q=prev_addition_holes_conditions, var=hole_key, value=hole_value: And(q(d), d[var] == value)

                    prev_holes_conditions = copy.deepcopy(holes_conditions)
                    holes_conditions = lambda d, q=prev_holes_conditions, q2 = addition_holes_condition: Or(q(d), q2(d))

                    # prev_q = Q_holes[j]
                    orig_q = copy.deepcopy(Q[j])
                    Q_holes[j] = lambda d, q=orig_q: And(q(d), Not(holes_conditions(d)))

                # start again from IO number 0
                i = 0

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
    #orig_program = "c1 := ?? ; c2 := ?? ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x * 2 ; if a != c then d := 0 else skip"
    # synth.add_example([("x", 0)], [("d", 1)])
    # synth.add_example([("x", 1)], [("d", 1)])
    
    # example for verifier giving d := 1 as input (additional input)
    orig_program = "c1 := ?? ; c2 := ?? ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x * 2 ; if a != c then d := 0 else d := 1"
    # synth.add_example([("x", 0)], [("d", 1)])
    # synth.add_example([("x", 1)], [("d", 0)])

    # pvars = ["x, a, b, d, c1, c2"]
    # new_program = "c1 := 0 ; c2 := 2 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; if a = c then d := 1 else d := 0"
    # P = lambda d: d["x"] == 0
    # Q = lambda d: d["d"] == 1
    # linv = lambda d: True

    # linv = lambda d: True
    # synth = Synthesizer(orig_program)
    # synth.process_holes() # Replace all occurrences of '??' with unique hole variables

    # # here add examples one by one
    # synth.add_example([("x", 0)], [("d", 0)])
    # synth.add_example([("x", 1)], [("d", 0)])




    orig_program = "c1 := ?? ; c2 := ?? ; a := c1 * x ; b := c2 - 10 ; a := a + b; c := x * 22 ; if a != c then d := 0 else d := 1"

    inputs = [
    ['_', '_', '_', '_', '_', '_', 0],
    ['_', '_', '_', '_', '_', '_', 1]
    ]

    outputs = [
    ['_', '_', '_', '_', '_', 1, '_'],
    ['_', '_', '_', '_', '_', 1, '_']
    ]

    synth = Synthesizer(orig_program)

    #Pvars:  ['a', 'b', 'c', 'c1', 'c2', 'd', 'x']
    synth.synth_IO_program(orig_program, inputs, outputs)

    # ast_orig = parse(orig_program)
    # # print(ast_orig)
    # pvars = sorted(list(getPvars(ast_orig)))
    # print("Pvars: ", pvars)

    # P, Q = create_conditions(inputs, outputs, pvars)

    # linv = lambda d: True
    # synth = Synthesizer(orig_program)
    # synth.process_holes() # Replace all occurrences of '??' with unique hole variables
    # holes = synth.holes
    # print("Holes:", holes)
    # holes_program = synth.holes_program
    # ast_holes = parse(holes_program)
    # # print(ast)

    # pvars_holes = set(n for n in ast_holes.terminals if isinstance(n, str) and n != 'skip')
    # print("Pvars holes:", pvars_holes)
    # env = mk_env(pvars_holes)


    # P_holes = copy.deepcopy(P)
    # Q_holes = copy.deepcopy(Q)

    # # this is to bound the limits of the holes - maybe we will need this for complicated programs
    # # for i in range(len(holes)):
    # #     for j in range(len(outputs)):
    # #         prev_q = copy.deepcopy(Q_holes[j])
    # #         Q_holes[j] = lambda d, hole_key=holes[i], q=prev_q: And(q(d), And(d[hole_key] < 5, d[hole_key] > -5))

    # holes_conditions = lambda d: False


    # i = 0
    # while (i < len(inputs)):
    #     print("\n*******************************************\n")
    #     print("i = ", i)
    #     print("ast_holes: \n", ast_holes)
    #     wp = WP(ast_holes)
    #     wp_stmt = wp.wp(ast_holes, Q_holes[i], linv)

    #     formula = And(P_holes[i](wp.env), wp_stmt(wp.env))

    #     solver = Solver()
    #     solver.add(formula)
    #     if solver.check() == unsat:
    #         print(">> The program is verified with IO example ", i)

    #         i += 1
    #         continue  # Continue with the next input
    #     # Get the model and fill the holes in the program
    #     sol = solver.model()
    #     print(sol)
    #     filled_program = fill_holes(holes, holes_program, sol)
    #     print("filled program:")
    #     print(filled_program)

    #     # check if all verified
    #     solver_for_counterexample = None
    #     is_valid_for_all_ios = True
    #     for j in range(len(inputs)):
    #         is_verified, solver_for_counterexample = verify(P[j], parse(filled_program), Q[j], linv = linv)
    #         if(is_verified):
    #             continue
    #         else:
    #             is_valid_for_all_ios = False
    #             break

    #     # is_valid_for_all_ios = all(verify(P[j], parse(filled_program), Q[j], linv = linv)[0] for j in range(len(inputs)))
    #     print()

    #     if(is_valid_for_all_ios):
    #         print("The program is verified for all IO examples")
    #         break
    #     else:
    #         print("The program is not verified for all IO examples")
    #         # counterexample_dict = extract_model_assignments(solver)
    #         # print("counter example dict:", counterexample_dict)

    #         holes_dict = extract_holes_from_dict(extract_model_assignments(solver))
    #         counterexample_dict = {}
    #         if(solver_for_counterexample != None):
    #             counterexample_dict = extract_holes_from_dict(extract_model_assignments(solver_for_counterexample))
    #             print("counter example dict:", counterexample_dict)
    #             holes_dict.update(counterexample_dict)
    #         # counterexample_dict = extract_model_assignments(solver)
    #         print("holes to set as not valid:", holes_dict)

    #         for j in range(len(inputs)):
    #             addition_holes_condition = lambda d: True
    #             for hole_key, hole_value in holes_dict.items():
    #                 prev_addition_holes_conditions = addition_holes_condition
    #                 addition_holes_condition = lambda d, q=prev_addition_holes_conditions, var=hole_key, value=hole_value: And(q(d), d[var] == value)

    #             prev_holes_conditions = copy.deepcopy(holes_conditions)
    #             holes_conditions = lambda d, q=prev_holes_conditions, q2 = addition_holes_condition: Or(q(d), q2(d))

    #             # prev_q = Q_holes[j]
    #             orig_q = copy.deepcopy(Q[j])
    #             Q_holes[j] = lambda d, q=orig_q: And(q(d), Not(holes_conditions(d)))

    #         # start again from IO number 0
    #         i = 0

    # example_dict = {'x': 1, 'y': 2, 'z': 10}  # Test case for evaluation

    # p0 = P[0](example_dict)
    # q0 = Q[0](example_dict)

    # print(p0)
    # print(q0)

    # for i in range(len(synth.inputs)):
    #     print("Input: ", synth.inputs[i])
    #     print("Output: ", synth.outputs[i])

    #     io_example_formula = And(self.P[i](env), aux_verify(ast, self.Q[i], self.linv, env)(env))


    # all_IO_program = synth.generate_IO_program()

    # print("I/O Program:")
    # print(all_IO_program)

    # synth.synth_IO_program(all_IO_program)






if __name__ == "__main__":
    main()