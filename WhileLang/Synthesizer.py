import typing
import operator
from z3 import Int, ForAll, Implies, Not, And, Solver, unsat, sat, Ast, Or

#from WhileLang import syntax

from syntax.tree import Tree
from syntax.while_lang import parse, parse_and_unroll, tree_to_program, remove_assertions_program
from wp import *

import re
import copy

class Synthesizer:
    def __init__(self, program):
        self.orig_program = program
        self.ast_orig = parse(self.orig_program)
        self.pvars = []

        if self.ast_orig is None:
            print("Error: Invalid program")
        else:
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
        
        if(self.pvars == []):
            print("Error: no vars in the program")
            return

        print("pvars: ", self.pvars)

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
        inputs_example_tuples = []

        for example_input, example_output in zip(inputs, outputs):
            p = lambda d: True
            q = lambda d: True
            inputs_tuples = []

            print("\nadding conditions to P:")
            for var, value in zip(pvars, example_input):
                if value != '_':
                    prev_p = copy.deepcopy(p)
                    p = lambda d, p = prev_p, var = var, value = value: And(p(d), d[var] == value)
                    print(f"var = {var}, value = {value}")
                    inputs_tuples.append((var, value))
                    

            print("\nadding conditions to Q:")
            for var, value in zip(pvars, example_output):
                if value != '_':
                    prev_q = copy.deepcopy(q)
                    q = lambda d, q = prev_q, var = var, value = value: And(q(d), d[var] == value)
                    print(f"var = {var}, value = {value}")

            inputs_example_tuples.append(inputs_tuples)

            print("\n")

            P.append(p)
            Q.append(q)

        return P, Q, inputs_example_tuples

    def fill_holes(self, program, sol):
        """Fills the holes in the program with the values from the solver model."""
        holes_to_fill_dict = self.extract_holes_from_dict(extract_model_assignments(sol))
        print("holes_to_fill_dict: ", holes_to_fill_dict)
    
        for key, value in holes_to_fill_dict.items():
            # Replace each occurrence of 'key' with its corresponding 'value'
            program = program.replace(key, str(value))
        return program
    
    def fill_holes_dict(self, program, holes_dict):
        """Fills the holes in the program with the values from the holes dictionary."""
        for key, value in holes_dict.items():
            # Replace each occurrence of 'key' with its corresponding 'value'
            program = program.replace(key, str(value))
        return program

    # def fill_zeros(ast: Tree):
    #     if(ast.root == "id"):
    #         if bool(re.match(r'hole_\d+$', ast.subtrees[0].root)):
    #             ast.subtrees[0].root

    def fill_holes_with_zeros(self, program, holes: list):
        """Fills the holes in the program with a '0'"""
        # print("hole to fill with zeroes: ", holes)
    
        holes_dict = {}
        for hole in holes:
            # Replace each occurrence of 'key' with its corresponding 'value'
            program = program.replace(hole, str(0))
            holes_dict[hole] = 0
        return program, holes_dict

    def extract_holes_from_dict(self, dict):
        hole_pattern = re.compile(r'hole_\d+')
        # Extract the keys and values that match the pattern
        holes_dict = {k: v for k, v in dict.items() if hole_pattern.match(k)}
        return holes_dict
    
    def extract_counter_example_from_dict(self, dict):
        hole_pattern = re.compile(r'hole_\d+')
        # Create a new dictionary excluding keys that match the pattern
        non_holes_dict = {k: v for k, v in dict.items() if not hole_pattern.match(k)}
        return non_holes_dict

    def synth_IO_program(self, orig_program, inputs, outputs, lower_bound = -100, upper_bound = 100, linv = None, unroll_limit = 8):
        """Synthesizes a program using input-output examples."""
        ast_orig = parse(orig_program)

        if(self.ast_orig is None):
            print("Error: Invalid program")
            return ""

        pvars = sorted(list(getPvars(ast_orig)))
        print("Pvars: ", pvars)

        P, Q, examples_inputs_tuples = self.generate_conditions(inputs, outputs, pvars)

        if linv is None:
            linv = lambda d: True

        holes_program, holes = self.process_holes(orig_program) # Replace all occurrences of '??' with unique hole variables, returnes program with holes vars, and holes vars list
        print("Holes:", holes)
        ast_holes_unrolled = parse_and_unroll(holes_program, unroll_limit)
        if(ast_holes_unrolled is None):
            print("Error: Invalid program")
            return ""
        
        program_holes_unrolled = tree_to_program(ast_holes_unrolled)

        
        solver = Solver()
        VC = []

        wp = WP(ast_holes_unrolled)

        for i in range(len(inputs)):            
            
            inputs_code = ""
            for input in examples_inputs_tuples[i]:
                print("add input key:", input[0], ":=", input[1])
                inputs_code += f"{input[0]} := {input[1]} ; "

            holes_program_with_inputs = inputs_code + program_holes_unrolled
            print("holes_program_with_inputs: \n", holes_program_with_inputs)
            ast_holes_inputs = parse(holes_program_with_inputs)

            # wp = WP(ast_holes_inputs)
            wp_stmt = wp.wp(ast_holes_inputs, Q[i], linv)

            P_i = lambda d: True

            VC_i = Implies(P_i(wp.env), wp_stmt(wp.env))
            VC.append(VC_i)

        VC = And(VC)
        solver.add(VC)
        
        if solver.check() == sat:
            print(">> The program is verified.")
            print("holes:", str(solver.model()) )
            filled_program = self.fill_holes(holes_program, solver)
            filled_program, _ = self.fill_holes_with_zeros(filled_program, holes)
            print("final program:")
            print(filled_program) 
            return filled_program
        else:
            print(">> The program is NOT verified.")
            return ""

    def synth_IO_program_old(self, orig_program, inputs, outputs, lower_bound = -100, upper_bound = 100, linv = None, unroll_limit = 8):
        """Synthesizes a program using input-output examples."""
        ast_orig = parse(orig_program)

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
        ast_holes_unrolled = parse_and_unroll(holes_program, unroll_limit)
        if(ast_holes_unrolled is None):
            print("Error: Invalid program")
            return ""
        # print(ast)

        pvars_holes = set(n for n in ast_holes_unrolled.terminals if isinstance(n, str) and n != 'skip')
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
                    bound_conditions[j] = lambda d, hole_key=holes[i], q=prev_q: And(q(d), And(d[hole_key] <= upper_bound, d[hole_key] >= lower_bound))

        for j in range(len(outputs)):            
            orig_p = copy.deepcopy(P[j])
            P_holes[j] = lambda d, p = orig_p, bc = bound_conditions[j]: And(bc(d), p(d))


        holes_conditions = lambda d: False


        i = 0
        while (i < len(inputs)):
            print("\n*******************************************\n")
            print("i = ", i)
            # print("ast_holes: \n", ast_holes_unrolled)
            # print("program unrolled: \n", tree_to_program(ast_holes_unrolled))

            wp = WP(ast_holes_unrolled)
            wp_stmt = wp.wp(ast_holes_unrolled, Q_holes[i], linv)

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
                is_verified, solver_for_counterexample = verify(P[j], parse_and_unroll(filled_program, unroll_limit), Q[j], linv = linv)
                if(is_verified):
                    continue
                else:
                    is_valid_for_all_ios = False
                    break

            print()

            if(is_valid_for_all_ios):
                print("The program is verified for all IO examples")
                final_program = self.fill_holes(holes_program, solver)
                final_program, _ = self.fill_holes_with_zeros(final_program, holes)
                return final_program
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
                    # Q_holes[j] = lambda d, q = orig_q, bc = bound_conditions[j]: And(bc(d), And(q(d), Not(holes_conditions(d))))
                    Q_holes[j] = lambda d, q = orig_q: And(q(d), Not(holes_conditions(d)))

                    

                # start again from IO number 0
                i = 0

        return ""
    
    def find_holes(self, ast, P, Q, linv):
        wp = WP(ast)
        wp_stmt = wp.wp(ast, Q, linv)

        VC = And(P(wp.env), wp_stmt(wp.env))
        
        solver = Solver()
        solver.add(VC)

        if solver.check() == unsat:
            del solver
            return False, None
        else:
            return True, solver

    def fill_ast_holes(self, ast: Tree, holes: dict) -> Tree:
        if(ast.root == "id"):
            # print(ast.root)
            if ast.subtrees[0].root in holes:
                # print("found hole: ", ast.subtrees[0].root)
                ast.root = "num"
                ast.subtrees[0].root = holes[ast.subtrees[0].root]
                return ast
        
        else:
            for child in ast.subtrees:
                self.fill_ast_holes(child, holes)

    class ProgramNotValid(Exception):
        """Raised when a specific program is not valid."""
        pass

    class ProgramHasNoHoles(Exception):
        """Raised when a specific program has no holes."""
        pass
    
    class ProgramNotVerified(Exception):
        """Raised when a specific program can't be verified."""
        pass

    class NoInputToSatisfyProgram(Exception):
        """Raised when a specific program can't be verified."""
        pass

    def synth_program(self, orig_program, P, Q, linv = None, lower_bound = -100, upper_bound = 100, unroll_limit = 10):

        print("******\n")

        ast_orig = parse(orig_program)
        if(self.ast_orig is None):
            raise self.ProgramNotValid("The given program can't be parsed")
        
        program_without_assertions = remove_assertions_program(orig_program)
        print("program_without_assertions: ", program_without_assertions)
        if program_without_assertions == None:
            raise self.ProgramNotValid("The given program can't be parsed")
        ast_without_assertion = parse(program_without_assertions)
        if(ast_without_assertion is None):
            raise self.ProgramNotValid("The given program can't be parsed")



        pvars = sorted(list(getPvars(ast_orig)))
        print("Pvars: ", pvars)

        if linv is None:
            linv = lambda d: True

        if P is None:
            P = lambda d: True

        if Q is None:
            Q = lambda d: True

        holes_program, holes = self.process_holes(orig_program) # Replace all occurrences of '??' with unique hole variables, returnes program with holes vars, and holes vars list

        if(holes == []):
            print("No holes found in the program. trying to verify the program")
            raise self.ProgramHasNoHoles("The given program has no holes in it")
            # is_verified, _ = verify(P, ast_orig, Q, linv=linv)
            # if(is_verified == False):
            #     raise self.ProgramNotVerified("The given program is not verified for all inputs")
            # return orig_program

        ast_holes = parse(holes_program)
        if(ast_holes is None):
            raise self.ProgramNotValid("The given program can't be parsed")
        
        # print(holes_program)
        # is_there_valid_input, _ = is_exist_input_to_satisfy(P, ast_holes, Q, linv=linv)
        # if(is_there_valid_input == False):
        #     raise self.NoInputToSatisfyProgram("The given program has no input which can satisfy the conditions")
        
        ast_holes_unrolled = parse_and_unroll(holes_program, unroll_limit)
        if(ast_holes_unrolled is None):
            raise self.ProgramNotValid("The given program can't be parsed")
        program_holes_unrolled = tree_to_program(ast_holes_unrolled)
        print(f"program_holes_unrolled: \n{program_holes_unrolled}\n")
        

        # filled_program, filled_holes_dict = self.fill_holes_with_zeros(holes_program, holes)

        # print("ast_unrolled_filled_with_zeros: ", ast_unrolled_filled_with_zeros)
        filled_program, filled_holes_dict = self.fill_holes_with_zeros(program_holes_unrolled, holes)
        

        # this is to bound the limits of the holes - maybe we will need this for complicated programs
        bound_conditions = lambda d: True
        # if(lower_bound != None and upper_bound != None):
        #     for i in range(len(holes)):
        #         prev_bound_conditions = copy.deepcopy(bound_conditions)
        #         print("hole key:", holes[i], "bound:", lower_bound, upper_bound)
        #         bound_conditions = lambda d, hole_key=holes[i], q=prev_bound_conditions: And(q(d), d[hole_key] <= upper_bound, d[hole_key] >= lower_bound)
           
        final_holes_p = copy.deepcopy(bound_conditions)

        new_holes_dict = {}

        while(True):
            print("\n*******************************************\n")
            ast_filled = parse(filled_program)
            result, solver = verify(P, ast_filled, Q, linv=linv)
            if result == True:
                print("The program is verified")
                filled_program_final = self.fill_holes_dict(holes_program, new_holes_dict)
                holes_to_fill_with_zeroes = [key for key in holes if key not in new_holes_dict.keys()]
                print("holes to fill with zeroes:", holes_to_fill_with_zeroes)
                filled_program_final, _ = self.fill_holes_with_zeros(filled_program_final, holes_to_fill_with_zeroes)
                print(f"final filled program: {filled_program_final}")
                return filled_program_final

                # check that the final filled program is verified. maybe this should be done by the user
                # final_result, _ = verify(P, parse(filled_program_final), Q, linv=linv)
                # if(final_result == True):
                #     print("The final program is verified")
                #     return filled_program_final
                # else:
                #     print("The final program is not verified")
                #     return ""
                
            
            ce = self.extract_counter_example_from_dict(extract_model_assignments(solver))
            if ce == {}:
                print("No counter example found - each input is a counter example")
                # ce = {'x': 0}

            print("counter example dict:", ce)

            del solver

            # This is dumb - Z3 has a bug when it gives a counter example with inputs which are not equal to inputs we assign in P
            # Or am I dumb? - I need to check this
            # For the time being, I will assign the inputs manually to the beginning of the program
            # inputs_p = lambda d: True
            # for input_key in ce:
            #     print("add input key:", input_key, "=", ce[input_key])
            #     input_p = lambda d: d[input_key] == ce[input_key]
            #     prev_inputs_p = copy.deepcopy(inputs_p)
            #     inputs_p = lambda d, p = prev_inputs_p, q = input_p: And(p(d), q(d))

            inputs_code = ""
            for input_key in ce:
                print("add input key:", input_key, ":=", ce[input_key])
                inputs_code += f"{input_key} := {ce[input_key]} ; "

            holes_program_with_inputs = inputs_code + program_holes_unrolled
            ast_holes_inputs = parse(holes_program_with_inputs)

            holes_p = lambda d: True
            for hole_key in filled_holes_dict:
                print("excluded hole key:", hole_key, "!=", filled_holes_dict[hole_key])
                hole_p = lambda d: d[hole_key] != filled_holes_dict[hole_key]
                prev_holes_p = copy.deepcopy(holes_p)
                holes_p = lambda d, p = prev_holes_p, q = hole_p: And(p(d), q(d))

            prev_final_holes_p = copy.deepcopy(final_holes_p)
            final_holes_p = lambda d, p = prev_final_holes_p, q = holes_p: And(p(d), q(d))

            # final_P = lambda d, p = P, q = inputs_p, h = final_holes_p: And(p(d), h(d), q(d))
            final_P = lambda d, p = P, h = final_holes_p: And(p(d), h(d))

            print("Finding holes")
            # result, solver = self.find_holes(ast_holes, final_P, Q, linv=linv)
            result, solver = self.find_holes(ast_holes_inputs, final_P, Q, linv=linv)
            if result == False:
                raise self.ProgramNotVerified("The given program can't be verified for all possible inputs")
            else:
                print("holes:", solver.model())
            
            new_holes_dict = self.extract_holes_from_dict(extract_model_assignments(solver))
            print("new holes dict:", new_holes_dict)

            if new_holes_dict == {}:
                print("No new holes found")
                return ""
            
            del solver
            
            filled_program = self.fill_holes_dict(program_holes_unrolled, new_holes_dict)
            holes_to_fill_with_zeroes = [key for key in holes if key not in new_holes_dict.keys()]
            print("holes to fill with zeroes:", holes_to_fill_with_zeroes)
            filled_program, holes_filled_with_zeroes_dict = self.fill_holes_with_zeros(filled_program, holes_to_fill_with_zeroes)
            print("new_holes_dict:", new_holes_dict)
            print("holes_filled_with_zeroes_dict:", holes_filled_with_zeroes_dict)
            filled_holes_dict = new_holes_dict
            filled_holes_dict.update(holes_filled_with_zeroes_dict)
            print("filled_holes_dict:", filled_holes_dict)
            print("new filled program:")
            print(filled_program)

            



# def find_holes(ast, P, Q, linv):
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

# def find_holes2(ast, P, Q, linv):
#     wp = WP(ast)
#     wp_stmt = wp.wp(ast, Q, linv)

#     VC = And(P(wp.env), wp_stmt(wp.env))
    
#     solver = Solver()
#     solver.add(VC)

#     if solver.check() == unsat:
#         print(">> The program is Not verified.")
#         return False, None
#     else:
#         print(">> The program is verified.")
#         print("holes:", str(solver.model()) )
#         return True, solver

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

    # synth = Synthesizer(orig_program)

    # orig_program = "c1 := 0 ; c2 := 1 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x "
    # orig_program = "c1 := hole_1 ; c2 := hole_2 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x "
    # orig_program = "c1 := 3 ; c2 := 0 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x "
    # orig_program = "c1 := hole_1 ; c2 := hole_2 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x "
    # orig_program = "c1 := 0 ; c2 := 5 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x "
    # orig_program = "c1 := hole_1 ; c2 := hole_2 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x "

    # P = lambda d: True
    # P = lambda d: And(d["x"] == 1, Not(And(d["hole_1"] == 0, d["hole_2"] == 0))) # for verification
    # P = lambda d: True
    # P = lambda d: And(d["x"] == 2, And(
    #                                     Not(And(d["hole_1"] == 3, d["hole_2"] == 0)),
    #                                     Not(And(d["hole_1"] == 0, d["hole_2"] == 0))
    #                                   )
    #                  )
    # P = lambda d: True
    # P = lambda d: And(d["x"] == 3, And(
    #                                     Not(And(d["hole_1"] == 3, d["hole_2"] == 0)),
    #                                     Not(And(d["hole_1"] == 0, d["hole_2"] == 0)),
    #                                     Not(And(d["hole_1"] == 0, d["hole_2"] == 5))
    #                                   )
    #                  )

    # Q = lambda d: d["a"] == d["c"]
    # linv = lambda d: True

    # ast = parse(orig_program)
    # result = verify(P, ast, Q, linv=linv)
    # result = find_holes2(ast, P, Q, linv=linv)


    orig_program = "c1 := ?? ; assert(c1 >= 2) ; c2 := ?? ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; assert(a = c)"
    # orig_program = "c1 := ?? ; assert(c1 >= 3) ; c2 := ?? ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; assert(a = c)"
    # orig_program = "assert(c1 >= 3) ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; assert(a = c)"
    P = lambda d: True
    Q = lambda d: True
    linv = lambda d: True

    synth = Synthesizer(orig_program)
    try:
        program = synth.synth_program(orig_program, P, Q, linv)
        print(program)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    else:
        print("GGGGGGGGGGGGGG")

## end of counter example synthesis


def main():

    # test_assertions()

    program = "x:= 3; y:= hole_0 ; assert ((y - 1) > x); if (y - 3) = 5 then x := x + hole_1 else x:= x + 6"

    ast = parse(program)
    print(ast)
    fill_ast_holes(ast, {'hole_0': 111111, 'hole_1': 22222})
    print(ast)


if __name__ == "__main__":
    main()