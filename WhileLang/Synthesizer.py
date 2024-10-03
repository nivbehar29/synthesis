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
        self.program = program
        self.inputs = []  # List of input examples
        self.outputs = []   # List of output examples
        self.holes = []  # List of holes collected from the AST
        self.P = []  # Preconditions
        self.Q = []  # Postconditions

    def process_holes(self):
        """Replaces all occurrences of '??' in the program string with unique hole variables."""
        hole_counter = 0
        while '??' in self.program:
            hole_var = f"hole_{hole_counter}"  # Create a unique hole variable
            self.program = self.program.replace('??', hole_var, 1)  # Replace only the first occurrence of '??'
            self.pvars.append(hole_var)  # Add the hole variable to pvars
            hole_counter += 1  # Increment the hole counter for uniqueness

    def add_example(self, input, output):
        """Adds a single input-output example pair to the synthesizer."""
        self.inputs.append(input)
        self.outputs.append(output)


    def verify(self, preconditions, postconditions, sketch_program):
        """Verifies the correctness of the sketch program using Z3 based on preconditions and postconditions."""
        s = Solver()
        
        # Create a fresh state for each example
        for precond, postcond in zip(preconditions, postconditions):
            state_before = {var: Int(var) for var in self.pvars}
            state_after = {var: Int(var + '_after') for var in self.pvars}

            # Add precondition to the solver
            s.add(precond(state_before))

            # Apply the sketch (simulated or real)
            # NOTE: sketch_program is expected to modify state_before in place to simulate execution
            sketch_program(state_before)

            # Add postcondition to the solver
            s.add(Not(postcond(state_before)))  # Looking for a counterexample

        if s.check() == sat:
            print("Verification failed, counterexample found.")
            return False
        else:
            print("Program verified successfully.")
            return True

    def synthesize_holes(self, ast, sketch_program):
        """Synthesizes hole values for the given program sketch using input-output examples."""
        self.collect_holes(ast)  # Collect the holes in the AST
        preconditions, postconditions = self.create_conditions(self.inputs, self.outputs)
        return self.verify(preconditions, postconditions, sketch_program)

def find_holes(ast, P, Q, linv):
    if ast is not None:
        wp = WP(ast)
        wp_stmt = wp.wp(ast, Q, linv)
        VC = Implies(P(wp.env), wp_stmt(wp.env))

        solver = Solver()
        #solver.add(VC)
        solver.add((VC))

        if solver.check() == unsat:
            print(">> The program is NOT verified.")
        else:
            print(">> The program is verified.")
            print("holes examples: ", solver.model())

def verify(ast, P, Q, linv):
    if ast is not None:
        wp = WP(ast)
        wp_stmt = wp.wp(ast, Q, linv)
        VC = Implies(P(wp.env), wp_stmt(wp.env))

        solver = Solver()
        #solver.add(VC)
        solver.add(Not(VC))

        if solver.check() == unsat:
            print(">> The program is verified.")
        else:
            print(">> The program is Not verified.")
            print("Counterexample: ", solver.model())

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

    pvars = ["x, a, b, d, c1, c2, hole_1, hole_2, all_outputs_sat"]
    orig_program = "c1 := ?? ; c2 := ?? ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x * c1 "
    new_program = "all_outputs_sat := 1 ; " \
                  "x := 0 ; c1 := hole_1 ; c2 := hole_2 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x * 2 ; if a != c then all_outputs_sat := 0 else skip ; " \
                  "x := 1 ; c1 := hole_1 ; c2 := hole_2 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x * 2 ; if a != c then all_outputs_sat := 0 else skip"
    print(new_program)
    P = lambda d: d["all_outputs_sat"] == 1
    Q = lambda d: d["all_outputs_sat"] == 1
    linv = lambda d: True

    # pvars = ["x, a, b, d, c1, c2"]
    # new_program = "c1 := 0 ; c2 := 2 ; a := c1 * x ; b := c2 - 1 ; a := a + b; c := x + x ; if a = c then d := 1 else d := 0"
    # P = lambda d: d["x"] == 0
    # Q = lambda d: d["d"] == 1
    # linv = lambda d: True

    linv = lambda d: True
    synth = Synthesizer(new_program, pvars)

    #print(synth.program)

    synth.process_holes()

    #print(synth.pvars)
    #print(synth.program)

    ast_orig = parse(new_program)
    print("original program: ")
    print(str(ast_orig))

    ast = parse(synth.program)
    print("program with holes variables: ")
    print(str(ast))

    verify(ast, P, Q, linv)
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