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

        return self.fill_holes_dict(program, holes_to_fill_dict)
    
    def fill_holes_dict(self, program, holes_dict):
        """Fills the holes in the program with the values from the holes dictionary."""
        # Regular expression to match 'hole_' followed by one or more digits
        hole_pattern = re.compile(r'\bhole_\d+\b')

        def replace_hole(match):
            hole_name = match.group(0)  # Get the matched hole (e.g., 'hole_1')
            # Replace it with the corresponding value from the dictionary, or keep the original if not found
            return str(holes_dict.get(hole_name, hole_name))

        # Substitute all matches using the replace_hole function
        return hole_pattern.sub(replace_hole, program)

    def fill_holes_with_zeros(self, program, holes: list):
        """Fills the holes in the program with a '0'"""
        print("hole to fill with zeroes: ", holes)
        print("program: ", program)
    
        holes_dict = {}
        for hole in holes:
            # Replace each occurrence of 'key' with its corresponding 'value'
            # program = program.replace(hole, str(0))
            holes_dict[hole] = 0

        new_program = self.fill_holes_dict(program, holes_dict)
        return new_program, holes_dict

    def extract_holes_from_dict(self, dict):
        hole_pattern = re.compile(r'\bhole_\d+\b')
        # Extract the keys and values that match the pattern
        holes_dict = {k: v for k, v in dict.items() if hole_pattern.match(k)}
        return holes_dict
    
    def extract_counter_example_from_dict(self, dict):
        hole_pattern = re.compile(r'\bhole_\d+\b')
        # Create a new dictionary excluding keys that match the pattern
        non_holes_dict = {k: v for k, v in dict.items() if not hole_pattern.match(k)}
        return non_holes_dict

    def check_for_hole(self, variables):
        # Regular expression to match the pattern "hole_" followed by a number
        pattern = r'\bhole_\d+\b'
        
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
        is_exist_input, solver = is_exist_input_to_satisfy(P, ast_holes_unrolled, Q, linv=linv)
        if(is_exist_input == False):
            print("Error: The given program has no input which can satisfy the conditions")
            if raise_errors:
                raise self.NoInputToSatisfyProgram("The given program has no input which can satisfy the conditions")
            return ""
        
        del solver

        
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
        
        # print(solver)

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
        #     pass
        #     # raise self.NoInputToSatisfyProgram("The given program has no input which can satisfy the conditions")
        # if solver_valid != None:
        #     del solver_valid
        
        return holes, holes_program, program_holes_unrolled, P, Q, linv
    
    def cegis_interactive(self, orig_program, P, Q, linv = None, unroll_limit = 10):
        self.abort_flag = [False]

        yield ("State_0", "Wait for initialization", orig_program)

        holes, holes_program, program_holes_unrolled, P, Q, linv = self.cegis_init_checks(orig_program, P, Q, linv, unroll_limit)

        yield ("State_1", "Replace holes with variables", holes_program)

        # First, we fill the program holes with zeros
        filled_program_unrolled, filled_holes_dict = self.fill_holes_with_zeros(program_holes_unrolled, holes)

        prev_filled_holes_dict = copy.deepcopy(filled_holes_dict)

        filled_program, _ = self.fill_holes_with_zeros(holes_program, holes)

        yield ("State_2", "Fill holes with zeroes", filled_program, filled_holes_dict)

        # Initialize the final holes predicate
        final_holes_p = lambda d: True

        # Initialize holes dictionary
        new_holes_dict = {}

        # Add bounderies for holes exploration
        curr_lower_bound = 5
        curr_upper_bound = -5
        holes_bound_p = self.get_bounds_condition(holes, curr_lower_bound, curr_upper_bound)

        # initialize iteration counter
        k = 0
        while(True):
            skip = True
            if(k == 0 or prev_filled_holes_dict != filled_holes_dict):
                skip = False
                
            if(skip == False):
                k += 1
                print("\n*******************************************\n")
                ast_filled = parse(filled_program_unrolled)
                result, solver = verify(P, ast_filled, Q, linv=linv)

                yield ("State_3_1", "Try to verify the program", result, solver)

                if result == True:
                    filled_program_final = self.fill_holes_dict(holes_program, new_holes_dict)
                    holes_to_fill_with_zeroes = [key for key in holes if key not in new_holes_dict.keys()]
                    filled_program_final, _ = self.fill_holes_with_zeros(filled_program_final, holes_to_fill_with_zeroes)

                    yield ("State_3_2", "Verification succeeded, fill program with current holes", filled_program_final)

                    return filled_program_final          
                
                ce = self.extract_counter_example_from_dict(extract_model_assignments(solver))
                if ce == {}:
                    print("No counter example found - each input is a counter example")
                    # ce = {'x': 0}

                yield ("State_3_3", "Verification failed, show counter example", ce, filled_holes_dict)

                print("counter example dict:", ce)

                del solver

                inputs_code = ""
                for input_key in ce:
                    print("add input key:", input_key, ":=", ce[input_key])
                    inputs_code += f"{input_key} := {ce[input_key]} ; "

                holes_program_with_inputs = inputs_code + program_holes_unrolled
                ast_holes_inputs = parse(holes_program_with_inputs)

                holes_p = lambda d: True
                for hole_key in filled_holes_dict:
                    val = filled_holes_dict[hole_key]
                    print("excluded hole key:", hole_key, "!=", val)
                    hole_p = lambda d, key = hole_key, value = val: d[key] == value
                    holes_p = lambda d, p = copy.deepcopy(holes_p), q = copy.deepcopy(hole_p): And(p(d), q(d))

                final_holes_p = lambda d, p = copy.deepcopy(final_holes_p), q = holes_p: And(p(d), Not(q(d)))

            final_P = lambda d, p = copy.deepcopy(P), h = copy.deepcopy(final_holes_p), q = copy.deepcopy(holes_bound_p): And(p(d), h(d), q(d))
            final_P_no_bounds = lambda d, p = copy.deepcopy(P), h = copy.deepcopy(final_holes_p): And(p(d), h(d))

            # First, try to solve without holes bounds, to see if there is no solution at all.
            if(skip == False):
                print("Finding holes without bounds")
                result, solver1 = self.find_holes(ast_holes_inputs, final_P_no_bounds, Q, linv=linv)
                if result == False:
                    print("The program can't be verified for all possible inputs")
                    print("num of iterations:", k)
                    yield ("State_4_2", "Couldn't find new holes", False)

                print("There is a solution, now try to find holes with bounds")

                del solver1


            print("Finding holes")

            if(skip == False):
                yield ("State_4_1", "Try to find new holes")
            # Now, after we know there is a solution, we can try to find holes with bounds
            result, solver2 = self.find_holes(ast_holes_inputs, final_P, Q, linv=linv)
            if result == False:
                # If we can't find holes with bounds, we need to increase the bounds.
                print("No solution within current bounds - Increasing bounds")
                curr_lower_bound = curr_lower_bound - 20
                curr_upper_bound = curr_upper_bound + 20
                print(f"new bounds: {curr_lower_bound}, {curr_upper_bound}")
                # Update the holes bounds predicate
                holes_bound_p = self.get_bounds_condition(holes, curr_lower_bound, curr_upper_bound)
                prev_filled_holes_dict = copy.deepcopy(filled_holes_dict)
                
                continue  
            
            print("holes:", solver2.model())
            


            new_holes_dict = self.extract_holes_from_dict(extract_model_assignments(solver2))
            print("new holes dict:", new_holes_dict)

            # if new_holes_dict == {}:
            #     print("No new holes found")
            #     print("num of iterations:", k)
            #     yield ("State_4_2", "Couldn't find new holes", False)
            #     return ""
            
            del solver2
            
            filled_program_unrolled = self.fill_holes_dict(program_holes_unrolled, new_holes_dict)
            holes_to_fill_with_zeroes = [key for key in holes if key not in new_holes_dict.keys()]
            filled_program_unrolled, holes_filled_with_zeroes_dict = self.fill_holes_with_zeros(filled_program_unrolled, holes_to_fill_with_zeroes)
            prev_filled_holes_dict = copy.deepcopy(filled_holes_dict)
            filled_holes_dict = new_holes_dict
            filled_holes_dict.update(holes_filled_with_zeroes_dict)

            # Only for the visualization (interactive CEGIS)
            filled_program = self.fill_holes_dict(holes_program, new_holes_dict)
            filled_program, _ = self.fill_holes_with_zeros(filled_program, holes_to_fill_with_zeroes)

            yield ("State_5", "New holes found, Fill program with the new holes", filled_program, filled_holes_dict)


    def get_bounds_condition(self, holes, lower_bound, upper_bound):
        final_holes_bound_p = lambda d : True
        for hole_key in holes:
            hole_bound_p = lambda d: And(d[hole_key] >= lower_bound, d[hole_key] <= upper_bound)
            final_holes_bound_p = lambda d, p = copy.deepcopy(final_holes_bound_p), q = copy.deepcopy(hole_bound_p): And(p(d), q(d))

        return final_holes_bound_p

    def synth_program(self, orig_program, P, Q, linv = None, unroll_limit = 10):

        # Checks if the given program can be parsed, have holes, and variables names are valid
        # Also returns the holes, holes program, and program with holes unrolled  
        holes, holes_program, program_holes_unrolled, P, Q, linv = self.cegis_init_checks(orig_program, P, Q, linv, unroll_limit)

        # First, we fill the program holes with zeros
        filled_program, filled_holes_dict = self.fill_holes_with_zeros(program_holes_unrolled, holes)
        prev_filled_holes_dict = copy.deepcopy(filled_holes_dict)

        # Initialize the final holes predicate
        final_holes_p = lambda d: True

        # Initialize holes dictionary
        new_holes_dict = {}

        # Add bounderies for holes exploration
        curr_lower_bound = 5
        curr_upper_bound = -5
        holes_bound_p = self.get_bounds_condition(holes, curr_lower_bound, curr_upper_bound)

        # initialize iteration counter
        k = 0
        while(True):
            skip = True
            if(k == 0 or prev_filled_holes_dict != filled_holes_dict):
                skip = False
                
            if(skip == False):
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
                
                print("filled_holes_dict:", filled_holes_dict)
                for hole_key in filled_holes_dict:
                    val = filled_holes_dict[hole_key]
                    print("excluded hole key:", hole_key, "!=", val)
                    hole_p = lambda d, key = hole_key, value = val: d[key] == value
                    holes_p = lambda d, p = copy.deepcopy(holes_p), q = copy.deepcopy(hole_p): And(p(d), q(d))

                final_holes_p = lambda d, p = copy.deepcopy(final_holes_p), q = copy.deepcopy(holes_p): And(p(d), Not(q(d)))

            # set the final P. also add the holes bounds to it
            final_P = lambda d, p = copy.deepcopy(P), h = copy.deepcopy(final_holes_p), q = copy.deepcopy(holes_bound_p): And(p(d), h(d), q(d))
            final_P_no_bounds = lambda d, p = copy.deepcopy(P), h = copy.deepcopy(final_holes_p): And(p(d), h(d))

            # First, try to solve without holes bounds, to see if there is no solution at all.
            if(skip == False):
                print("Finding holes without bounds")
                result, solver1 = self.find_holes(ast_holes_inputs, final_P_no_bounds, Q, linv=linv)
                if result == False:
                    print("The program can't be verified for all possible inputs")
                    print("num of iterations:", k)
                    raise self.ProgramNotVerified("The given program can't be verified for all possible inputs")

                print("There is a solution, now try to find holes with bounds")

                del solver1

            # Now, after we know there is a solution, we can try to find holes with bounds
            print("Finding holes with bounds")
            result, solver2 = self.find_holes(ast_holes_inputs, final_P, Q, linv=linv)
            if result == False:
                # If we can't find holes with bounds, we need to increase the bounds.
                print("No solution within current bounds - Increasing bounds")
                curr_lower_bound = curr_lower_bound - 20
                curr_upper_bound = curr_upper_bound + 20
                print(f"new bounds: {curr_lower_bound}, {curr_upper_bound}")

                # Update the holes bounds predicate
                holes_bound_p = self.get_bounds_condition(holes, curr_lower_bound, curr_upper_bound)

                prev_filled_holes_dict = copy.deepcopy(filled_holes_dict)
                continue
            
            print(f"\nsolver2 :\n{solver2}\n\n")
            print("holes:", solver2.model())
            
            new_holes_dict = self.extract_holes_from_dict(extract_model_assignments(solver2))
            print("new holes dict:", new_holes_dict)

            # if new_holes_dict == {}:
            #     print("No new holes found")
            #     print("num of iterations:", k)
            #     return ""
            
            del solver2
            
            filled_program = self.fill_holes_dict(program_holes_unrolled, new_holes_dict)
            holes_to_fill_with_zeroes = [key for key in holes if key not in new_holes_dict.keys()]
            print("holes to fill with zeroes:", holes_to_fill_with_zeroes)
            filled_program, holes_filled_with_zeroes_dict = self.fill_holes_with_zeros(filled_program, holes_to_fill_with_zeroes)
            print("new_holes_dict:", new_holes_dict)
            print("holes_filled_with_zeroes_dict:", holes_filled_with_zeroes_dict)
            prev_filled_holes_dict = copy.deepcopy(filled_holes_dict)
            filled_holes_dict = new_holes_dict
            filled_holes_dict.update(holes_filled_with_zeroes_dict)
            print("filled_holes_dict:", filled_holes_dict)
            print("new filled program:")
            print(filled_program)


def main():
    print("Nothing to do here :)")

if __name__ == "__main__":
    main()