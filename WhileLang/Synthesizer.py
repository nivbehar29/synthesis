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

    class ProgramNotValid(Exception):
        """Raised when a specific program is not valid."""
        pass

    class ProgramHasNoHoles(Exception):
        """Raised when a specific program has no holes."""
        pass

    class NoExamplesProvided(Exception):
        """Raised when a specific program is not valid."""
        pass
    
    class ProgramNotVerified(Exception):
        """Raised when a specific program can't be verified."""
        pass

    class NoInputToSatisfyProgram(Exception):
        """Raised when a specific program can't be verified."""
        pass

    class ProgramHasInvalidVarName(Exception):
        """Raised when a specific program is not valid."""
        pass

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

        # Interactive CEGIS variables
        self.abort_flag = [False]

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
            if inputs != [] or outputs != []:

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
        output_example_tuples = []

        for example_input, example_output in zip(inputs, outputs):
            p = lambda d: True
            q = lambda d: True
            inputs_tuples = []
            output_tuples = []

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
                    output_tuples.append((var, value))

            inputs_example_tuples.append(inputs_tuples)
            output_example_tuples.append(output_tuples)

            print("\n")

            P.append(p)
            Q.append(q)

        return P, Q, inputs_example_tuples, output_example_tuples

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

    def check_for_hole(self, variables):
        # Regular expression to match the pattern "hole_" followed by a number
        pattern = r'hole_\d+'
        
        for var in variables:
            if re.match(pattern, var):
                return var
        return None


    def synth_IO_program(self, orig_program, inputs, outputs, P = None, Q = None, linv = None, unroll_limit = 8, raise_errors = False):
        """Synthesizes a program using input-output examples."""
        
        if P is None:
            P = lambda d: True
        if Q is None:
            Q = lambda d: True
        if linv is None:
            linv = lambda d: True

        ast_orig = parse(orig_program)

        if(self.ast_orig is None):
            print("Error: Invalid program")
            if(raise_errors):
                raise self.ProgramNotValid("The given program can't be parsed")
            return ""

        pvars = sorted(list(getPvars(ast_orig)))
        print("Pvars: ", pvars)

        holes_vars_check = self.check_for_hole(pvars)
        if holes_vars_check is not None:
            print("Error: Invalid variable name: {holes_vars_check}")
            if(raise_errors):
                raise self.ProgramHasInvalidVarName(f"{holes_vars_check}")
            return ""

        print("generating conditions")
        P_inputs, Q_outputs, examples_inputs_tuples, output_example_tuples = self.generate_conditions(inputs, outputs, pvars)

        # Add Q conditions for each output example
        for i in range(len(Q_outputs)):
            prev_Q_i = copy.deepcopy(Q_outputs[i])
            Q_add = copy.deepcopy(Q)
            Q_outputs[i] = lambda d, q_cond = prev_Q_i, q = Q_add: And(q(d), q_cond(d))

        # Add P conditions for each input example
        # for i in range(len(P_inputs)):
        #     prev_P_i = copy.deepcopy(P_inputs[i])
        #     P_add = copy.deepcopy(P)
        #     P_inputs[i] = lambda d, p_cond = prev_P_i, p = P_add: And(p(d), p_cond(d))


        holes_program, holes = self.process_holes(orig_program) # Replace all occurrences of '??' with unique hole variables, returnes program with holes vars, and holes vars list
        
        if(holes == []):
            print("Error: The given program has no holes in it")
            if raise_errors:
                raise self.ProgramHasNoHoles("The given program has no holes in it")
            return ""
        
        # Checks for the existence of an input that satisfies the conditions
        # Currently unused because we can't get it write for program which has while loops.
        # But - when unrolling the loops, it does work, so we can use it for the unrolled program
        # print("holes program: ", holes_program)
        # ast_holes = parse(holes_program)
        # is_exist_input, _ = is_exist_input_to_satisfy(P, ast_holes, Q, linv=linv)
        # if(is_exist_input == False):
        #     print("Error: The given program has no input which can satisfy the conditions")
        #     if raise_errors:
        #         raise self.NoInputToSatisfyProgram("The given program has no input which can satisfy the conditions")
        #     return ""


        print("Holes:", holes)
        ast_holes_unrolled = parse_and_unroll(holes_program, unroll_limit)
        if(ast_holes_unrolled is None):
            print("Error: Invalid program")
            if(raise_errors):
                raise self.ProgramNotValid("The given program can't be parsed")
            return ""
        
        program_holes_unrolled = tree_to_program(ast_holes_unrolled)

        # Checks for the existence of an input that satisfies the conditions
        print("program holes unrolled: ", program_holes_unrolled)
        is_exist_input, _ = is_exist_input_to_satisfy(P, ast_holes_unrolled, Q, linv=linv)
        if(is_exist_input == False):
            print("Error: The given program has no input which can satisfy the conditions")
            if raise_errors:
                raise self.NoInputToSatisfyProgram("The given program has no input which can satisfy the conditions")
            return ""

        
        solver = Solver()
        VC = []

        wp = WP(ast_holes_unrolled)

        print("inputs: ", inputs)
        print("outputs: ", outputs)

        if(len(inputs) == 0 and len(outputs) == 0):
            print("Error: No input-output examples has been provided")
            if(raise_errors):
                raise self.NoExamplesProvided("No input-output examples has been provided")
            return ""
            # wp_stmt = wp.wp(ast_holes_unrolled, Q, linv)
            # VC.append(Implies(P(wp.env), wp_stmt(wp.env)))
        else:
            for i in range(len(inputs)):            
                
                P_i = copy.deepcopy(P)
                # P_i = P_inputs[i]


                inputs_code = ""
                for input in examples_inputs_tuples[i]:
                    print("add input key:", input[0], ":=", input[1])
                    inputs_code += f"{input[0]} := {input[1]} ; "

                outputs_code = ""
                # for output in output_example_tuples[i]:
                #     print("add output key:", output[0], ":=", output[1])
                #     outputs_code += f"; assert {output[0]} = {output[1]} "


                holes_program_with_inputs = inputs_code + program_holes_unrolled + outputs_code
                print("holes_program_with_inputs: \n", holes_program_with_inputs)
                ast_holes_inputs = parse(holes_program_with_inputs)

                # wp = WP(ast_holes_inputs)
                wp_stmt = wp.wp(ast_holes_inputs, Q_outputs[i], linv)

                VC_i = Implies(P_i(wp.env), wp_stmt(wp.env))
                VC.append(VC_i)

        VC_final = And(VC)
        solver.add(VC_final)
        
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
            if(raise_errors):
                raise self.ProgramNotVerified("The given program can't be verified for the given input-output examples")
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

    
    def cegis_init_checks(self, orig_program, P, Q, linv, unroll_limit):
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

        holes_vars_check = self.check_for_hole(pvars)
        if holes_vars_check is not None:
            print("Error: Invalid variable name: {holes_vars_check}")
            raise self.ProgramHasInvalidVarName(f"{holes_vars_check}")

        if linv is None:
            linv = lambda d: True

        if P is None:
            P = lambda d: True

        if Q is None:
            Q = lambda d: True

        holes_program, holes = self.process_holes(orig_program) # Replace all occurrences of '??' with unique hole variables, returnes program with holes vars, and holes vars list

        print("holessss: ", holes)

        if(holes == []):
            raise self.ProgramHasNoHoles("The given program has no holes in it")

        ast_holes = parse(holes_program)
        if(ast_holes is None):
            raise self.ProgramNotValid("The given program can't be parsed")
        
        ast_holes_unrolled = parse_and_unroll(holes_program, unroll_limit)
        if(ast_holes_unrolled is None):
            raise self.ProgramNotValid("The given program can't be parsed")
        program_holes_unrolled = tree_to_program(ast_holes_unrolled)
        print(f"program_holes_unrolled: \n{program_holes_unrolled}\n")

        # Checks for the existence of an input that satisfies the conditions
        # print(holes_program)
        # is_there_valid_input, solver_valid = is_exist_input_to_satisfy(P, ast_holes_unrolled, Q, linv)
        # print("is_there_valid_input: ", is_there_valid_input)
        # if(is_there_valid_input == False):
        #     raise self.NoInputToSatisfyProgram("The given program has no input which can satisfy the conditions")
        # if solver_valid != None:
        #     del solver_valid
        
        return holes, holes_program, program_holes_unrolled, P, Q, linv
    
    def cegis_interactive(self, orig_program, P, Q, linv = None, unroll_limit = 10):
        self.abort_flag = [False]

        holes, holes_program, program_holes_unrolled, P, Q, linv = self.cegis_init_checks(orig_program, P, Q, linv, unroll_limit)

        yield ("State_0", "Wait for initialization")


        yield ("State_1", "Replace holes with variables", program_holes_unrolled)

        # First, we fill the program holes with zeros
        filled_program, filled_holes_dict = self.fill_holes_with_zeros(program_holes_unrolled, holes)


        yield ("State_2", "Fill holes with zeroes", filled_program)


        # Initialize the final holes predicate
        final_holes_p = lambda d: True

        # Initialize holes dictionary
        new_holes_dict = {}

        # initialize iteration counter
        k = 0
        while(True):
            k += 1
            print("\n*******************************************\n")
            ast_filled = parse(filled_program)
            result, solver = verify(P, ast_filled, Q, linv=linv)

            yield ("State_3_1", "Try to verify the program", result, solver)

            if result == True:
                print("The program is verified")
                filled_program_final = self.fill_holes_dict(holes_program, new_holes_dict)
                holes_to_fill_with_zeroes = [key for key in holes if key not in new_holes_dict.keys()]
                print("holes to fill with zeroes:", holes_to_fill_with_zeroes)
                filled_program_final, _ = self.fill_holes_with_zeros(filled_program_final, holes_to_fill_with_zeroes)
                print(f"final filled program: {filled_program_final}")
                print("num of iterations:", k)

                yield ("State_3_2", "Verification succeeded, fill program with current holes", filled_program_final)

                return filled_program_final          
            
            ce = self.extract_counter_example_from_dict(extract_model_assignments(solver))
            if ce == {}:
                print("No counter example found - each input is a counter example")
                # ce = {'x': 0}

            yield ("State_3_3", "Verification failed, show counter example", ce)

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

            yield ("State_4_1", "Try to find new holes")
            result, solver = self.find_holes(ast_holes_inputs, final_P, Q, linv=linv)
            if result == False:
                print("num of iterations:", k)
                yield ("State_4_2", "Couldn't find new holes", False)
                return
            else:
                print("holes:", solver.model())
            


            new_holes_dict = self.extract_holes_from_dict(extract_model_assignments(solver))
            print("new holes dict:", new_holes_dict)

            if new_holes_dict == {}:
                print("No new holes found")
                print("num of iterations:", k)
                yield ("State_4_2", "Couldn't find new holes", False)
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

            yield ("State_5", "New holes found, Fill program with the new holes", True, filled_program)



        yield "cegis_interactive: 3rd yield"

        # raise StopIteration("cegis_interactive finished")

    def synth_program(self, orig_program, P, Q, linv = None, unroll_limit = 10):

        # Checks if the given program can be parsed, have holes, and variables names are valid
        # Also returns the holes, holes program, and program with holes unrolled  
        holes, holes_program, program_holes_unrolled, P, Q, linv = self.cegis_init_checks(orig_program, P, Q, linv, unroll_limit)

        # First, we fill the program holes with zeros
        filled_program, filled_holes_dict = self.fill_holes_with_zeros(program_holes_unrolled, holes)

        # Initialize the final holes predicate
        final_holes_p = lambda d: True

        # Initialize holes dictionary
        new_holes_dict = {}

        # initialize iteration counter
        k = 0
        while(True):
            k += 1
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
                print("num of iterations:", k)
                return filled_program_final          
            
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
            result, solver = self.find_holes(ast_holes_inputs, final_P, Q, linv=linv)
            if result == False:
                print("num of iterations:", k)
                raise self.ProgramNotVerified("The given program can't be verified for all possible inputs")
            else:
                print("holes:", solver.model())
            
            new_holes_dict = self.extract_holes_from_dict(extract_model_assignments(solver))
            print("new holes dict:", new_holes_dict)

            if new_holes_dict == {}:
                print("No new holes found")
                print("num of iterations:", k)
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

    test_assertions()


if __name__ == "__main__":
    main()