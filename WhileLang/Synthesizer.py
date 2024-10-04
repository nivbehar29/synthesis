import typing
import operator
from z3 import Int, ForAll, Implies, Not, And, Solver, unsat, sat, Ast, Or

#from WhileLang import syntax

from syntax.tree import Tree
from syntax.while_lang import parse
from wp import *

class Synthesizer:
    def __init__(self, program, pvars):
        self.pvars = pvars

        self.orig_program = program
        self.holes_program = None
        self.holes = []  # List of holes collected from the AST

        self.inputs = []  # List of input examples
        self.outputs = []   # List of output examples
        
        self.P = []  # Preconditions
        self.Q = []  # Postconditions

    def process_holes(self):
        """Replaces all occurrences of '??' in the program string with unique hole variables."""
        self.holes_program = self.orig_program
        hole_counter = 0
        while '??' in self.holes_program:
            hole_var = f"hole_{hole_counter}"  # Create a unique hole variable
            self.holes_program = self.holes_program.replace('??', hole_var, 1)  # Replace only the first occurrence of '??'
            self.pvars.append(hole_var)  # Add the hole variable to pvars
            hole_counter += 1  # Increment the hole counter for uniqueness

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
    
    def synth_IO_program(self, all_IO_program):
        P = lambda d: d["all_outputs_sat"] == 1
        Q = lambda d: d["all_outputs_sat"] == 1
        linv = lambda d: True
        ast = parse(all_IO_program)
        self.find_holes(ast, P, Q, linv)

def main():

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

## end of counter example synthesis

    orig_program = "c1 := ?? ; c2 := ?? ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x * 2 ; if a != c then d := 0 else d := 1"
    # synth.add_example([("x", 0)], [("d", 1)])
    # synth.add_example([("x", 1)], [("d", 1)])
    
    # example for verifier giving d := 1 as input (additional input)
    #orig_program = "c1 := ?? ; c2 := ?? ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x * 2 ; if a != c then d := 0 else skip"
    # synth.add_example([("x", 0)], [("d", 1)])
    # synth.add_example([("x", 1)], [("d", 0)])

    # pvars = ["x, a, b, d, c1, c2"]
    # new_program = "c1 := 0 ; c2 := 2 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; if a = c then d := 1 else d := 0"
    # P = lambda d: d["x"] == 0
    # Q = lambda d: d["d"] == 1
    # linv = lambda d: True

    linv = lambda d: True
    synth = Synthesizer(orig_program, pvars)
    synth.process_holes() # Replace all occurrences of '??' with unique hole variables

    # here add examples one by one
    synth.add_example([("x", 0)], [("d", 1)])
    synth.add_example([("x", 1)], [("d", 1)])

    all_IO_program = synth.generate_IO_program()

    print("I/O Program:")
    print(all_IO_program)

    synth.synth_IO_program(all_IO_program)

    #print(synth.pvars)
    #print(synth.program)

    # ast_orig = parse(new_program)
    # print("original program: ")
    # print(str(ast_orig))

    # ast = parse(synth.program)
    # print("program with holes variables: ")
    # print(str(ast))



    #verify(ast, P, Q, linv)
    #find_holes(ast, P, Q, linv)

    # if ast is not None:
    #     wp = WP(ast)
    #     wp_stmt = wp.wp(ast, Q, linv)
    #     VC = Implies(P(wp.env), wp_stmt(wp.env))

    #     solver = Solver()
    #     #solver.add(VC)
    #     solver.add((VC))

    #     if solver.check() == unsat:
    #         print(">> The program is verified.")
    #     else:
    #         print(">> The program is NOT verified.")
    #         print("Counterexample:", solver.model())


    #for 
    #verify(P_input_i, ast, Q_input_i, linv=linv)



if __name__ == "__main__":
    main()