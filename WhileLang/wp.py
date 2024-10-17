import typing
import operator
from z3 import Int, ForAll, Implies, Not, And, Solver, unsat, sat, Ast, Or, Exists

from syntax.tree import Tree
from syntax.while_lang import parse


Formula: typing.TypeAlias = Ast | bool
PVar: typing.TypeAlias = str
Env: typing.TypeAlias = dict[PVar, Formula]
Invariant: typing.TypeAlias = typing.Callable[[Env], Formula]


OP = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.floordiv,
    "!=": operator.ne,
    ">": operator.gt,
    "<": operator.lt,
    "<=": operator.le,
    ">=": operator.ge,
    "=": operator.eq,
}

def getPvars(ast: Tree):
    """
    Traverse the ast and for each node which is 'id', add its child root to a set. its child should be Pvar.
    returns the set.
    """
    pvars = set()
    if ast.root == "id":
        pvars.add(ast.subtrees[0].root)
    for child in ast.subtrees:
        pvars.update(getPvars(child))
    return pvars

def mk_env(pvars: set[PVar]) -> Env:
    return {v: Int(v) for v in pvars}

def mk_env_from_ast(ast: Tree):
    """
    Gets ast and return env for its vars
    """
    Pvars = getPvars(ast)
    env = mk_env(Pvars)
    return env, Pvars

def upd(d: Env, k: PVar, v: Formula) -> Env:
    d = d.copy()
    d[k] = v
    return d

class WP:

    def __init__(self, ast):

        #print(ast)
        env, vars = mk_env_from_ast(ast)
        # print("env, vars:")
        # print(env, vars)

        self.env = env
        self.vars = vars

    def eval_expr(self, expr: Tree, env) -> Formula:
        """Evaluate the expression `expr` in the environment `env`."""
        node_type = expr.root
        childrens = expr.subtrees

        if node_type == "id":
            return env[childrens[0].root]
        elif node_type == "num":
            return childrens[0].root
        elif node_type in OP:
            left = self.eval_expr(childrens[0], env)
            right = self.eval_expr(childrens[1], env)
            return OP[node_type](left, right)
        else:
            raise ValueError(f"Unknown expression type: {node_type}")


    def wp(self, ast: Tree, Q: Invariant, linv: Invariant) -> Invariant:
        """Compute the weakest precondition of statement `ast` with respect to postcondition `Q`."""
        node_type = ast.root
        subtrees = ast.subtrees

        if node_type == "skip":
            return Q
        elif node_type == ":=":
            x = subtrees[0].subtrees[0].root
            e = subtrees[1]
            return lambda env: Q(upd(env, x, self.eval_expr(e, env)))
        elif node_type == ";":
            S1 = subtrees[0]
            S2 = subtrees[1]
            return self.wp(S1, self.wp(S2, Q, linv), linv)
        elif node_type == "if":
            cond = subtrees[0]
            then_branch = subtrees[1]
            else_branch = subtrees[2]
            return lambda env: Or(
                And(self.eval_expr(cond, env), self.wp(then_branch, Q, linv)(env)),
                And(Not(self.eval_expr(cond, env)), self.wp(else_branch, Q, linv)(env))
            )
        elif node_type == "if_unrolled":
            cond = subtrees[0]
            then_branch = subtrees[1]
            else_branch = subtrees[2]
            program_vars = [*self.env.values()]

            return lambda env: And(
                linv(env),
                Or(
                    And(self.eval_expr(cond, env), self.wp(then_branch, Q, linv)(env)),
                    And(Not(self.eval_expr(cond, env)), self.wp(else_branch, Q, linv)(env))
                )
            )
        elif node_type == "while":
            cond = subtrees[0]
            body = subtrees[1]
            program_vars = [*self.env.values()]

            return lambda env: And(
                linv(env),
                ForAll(program_vars,
                       And(Implies(And(linv(self.env), self.eval_expr(cond, self.env)), self.wp(body, linv, linv)(self.env)),
                           Implies(And(linv(self.env), Not(self.eval_expr(cond, self.env))), Q(self.env)))))
            
        elif node_type == "assert":
            cond = subtrees[0]
            return lambda env: And(self.eval_expr(cond, env), Q(env))
        else:
            raise ValueError(f"Unknown statement type: {node_type}")



def verify(P: Invariant, ast: Tree, Q: Invariant, linv: Invariant):
    """Verify a Hoare triple {P} c {Q}
    Where P, Q are assertions (see below for examples)
    and ast is the AST of the command c.
    Returns `True` iff the triple is valid.
    Also prints the counterexample (model) returned from Z3 in case
    it is not.
    """
    wp = WP(ast)
    wp_stmt = wp.wp(ast, Q, linv)

    VC = Implies(P(wp.env), wp_stmt(wp.env))
    
    solver = Solver()
    solver.add(Not(VC))

    if solver.check() == unsat:
        print(">> The program is verified.")
        del solver
        return True, None
    else:
        print(">> The program is NOT verified.")
        print("Counterexample:", str(solver.model()) )
        return False, solver
    
def is_exist_input_to_satisfy(P: Invariant, ast: Tree, Q: Invariant, linv: Invariant):
    """Verify a Hoare triple {P} c {Q}
    Where P, Q are assertions (see below for examples)
    and ast is the AST of the command c.
    Returns `True` iff the triple is valid.
    Also prints the counterexample (model) returned from Z3 in case
    it is not.
    """

    wp = WP(ast)
    wp_stmt = wp.wp(ast, Q, linv)

    # VC = Implies(P(wp.env), wp_stmt(wp.env))
    VC = And(P(wp.env), wp_stmt(wp.env))
    
    solver = Solver()
    solver.add(VC)

    print("Model:", solver)

    if solver.check() == sat:
        print(">> The program has satisfying inputs.")
        print("Satisfying input:", solver.model())
        return True, solver
    else:
        print(">> No satisfying input found.")
        del solver
        return False, None

def extract_model_assignments(solver):
    model = solver.model()
    assignments = {}
    for var in model:
        assignments[str(var)] = model[var]
    
    return assignments

def main():
    # example program
    # pvars = ["a", "b", "i", "n"]
    # program = "a := b ; while i < n do ( a := a + 1 ; b := b + 1 )"
    # P = lambda _: True
    # Q = lambda d: d["a"] == d["b"]
    # linv = lambda d: d["a"] == d["b"]

    ## Program 4 - true
    pvars = ["a", "b", "z", "x"]
    program = "z := x ; a := 3 ; b := 6 ; while a != b do if a > b then a := a - b else b := b - a"
    P = lambda d: And(True, d['x'] == 1) # And(d['a'] > 0, d['b'] > 0)
    Q = lambda d: And(d['a'] > 0, d['a'] == d['b'])
    linv = lambda d: And(d['a'] > 0, d['b'] > 0)

    #
    # Following are other programs that you might want to try
    #

    ## Program 1
    # pvars = ['x', 'i', 'y']
    # program = "y := 0 ; while y < i do ( x := x + y ; if (x * y) < 10 then y := y + 1 else skip )"
    # P = lambda d: d['x'] > 0
    # Q = lambda d: d['x'] > 0
    # linv = lambda d: **figure it out!**

    ## Program 2
    # pvars = ['a', 'b']
    # program = "while a != b do if a > b then a := a - b else b := b - a"
    # P = lambda d: And(d['a'] > 0, d['b'] > 0)
    # Q = lambda d: And(d['a'] > 0, d['a'] == d['b'])
    # linv = lambda d: ???

    ast = parse(program)

    if ast is not None:
        print(">> Valid program.")
        # Your task is to implement "verify"
        verify(P, ast, Q, linv=linv)
    else:
        print(">> Invalid program.")


if __name__ == "__main__":
    main()