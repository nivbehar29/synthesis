import typing

from syntax.tree import Tree
from syntax.parsing.earley.earley import Grammar, Parser, ParseTrees
from syntax.parsing.silly import SillyLexer

__all__ = ["parse"]


class WhileParser:

    TOKENS = (
        r"(if|if_unrolled|then|else|while|do|skip|assert)(?![\w\d_]) "
        r"(?P<id>[^\W\d]\w*) "
        r"(?P<num>[+\-]?\d+) "
        r"(?P<op>[!<>]=|([+\-*/<>=])) "
        r"(?P<hole>\?\?) "
        r"[();]  :=".split()
    )
    GRAMMAR = r"""
    S   ->   S1     |   S1 ; S
    S1  ->   skip   |   id := E   |   if E then S else S1   |   if_unrolled E then S else S1    |   while E do S1  |   assert E
    S1  ->   ( S )
    E   ->   E0   |   E0 op E0
    E0  ->   id   |   num   |   hole
    E0  ->   ( E )
    """

    def __init__(self) -> None:
        self.tokenizer = SillyLexer(self.TOKENS)
        self.grammar = Grammar.from_string(self.GRAMMAR)

    def __call__(self, program_text: str) -> typing.Optional[Tree]:
        tokens = list(self.tokenizer(program_text))

        earley = Parser(grammar=self.grammar, sentence=tokens, debug=False)
        earley.parse()

        if earley.is_valid_sentence():
            trees = ParseTrees(earley)
            assert len(trees) == 1
            return self.postprocess(trees.nodes[0])
        else:
            return None

    def postprocess(self, t: Tree) -> Tree:
        if t.root in ["γ", "S", "S1", "E", "E0"] and len(t.subtrees) == 1:
            return self.postprocess(t.subtrees[0])
        elif (
            t.root in ["S", "S1", "E"]
            and len(t.subtrees) == 3
            and t.subtrees[1].root in [":=", ";", "op"]
        ):
            return Tree(
                t.subtrees[1].subtrees[0].root,
                [self.postprocess(s) for s in [t.subtrees[0], t.subtrees[2]]],
            )
        elif len(t.subtrees) == 3 and t.subtrees[0].root == "(":
            return self.postprocess(t.subtrees[1])
        elif t.root == "S1" and t.subtrees[0].root in ["if", "if_unrolled", "while", 'assert']:
            return self.postprocess(Tree(t.subtrees[0].root, t.subtrees[1::2]))
        elif t.root == "num":
            return Tree(t.root, [Tree(int(t.subtrees[0].root))])  # parse ints
        elif t.root == "hole":
            return Tree(t.root, [Tree(t.subtrees[0].root)])

        return Tree(t.root, [self.postprocess(s) for s in t.subtrees])


def parse(program_text: str) -> typing.Optional[Tree]:
    return WhileParser()(program_text)

def unroll_while(tree: Tree, unroll_bound: int) -> Tree:
    """
    Unrolls a `while` loop in the AST by replacing it with repeated `if cond then body else skip`
    statements without nesting, but as a sequence of separate condition checks.
    
    Args:
        tree (Tree): The abstract syntax tree containing a `while` loop.
        unroll_bound (int): The number of times to unroll the loop.
    
    Returns:
        Tree: The new unrolled tree.
    """
    if tree.root == "while":
        cond = tree.subtrees[0]
        body = tree.subtrees[1]
        
        # Start with the first `if cond then body else skip`
        unrolled = Tree("if_unrolled", [cond, body, Tree("skip", [])])  # First unrolled iteration
        
        # Create a sequence of `if cond then body else skip` statements
        for _ in range(unroll_bound - 1):
            next_unroll = Tree("if_unrolled", [cond, body, Tree("skip", [])])
            unrolled = Tree(";", [unrolled, next_unroll])  # Sequence them with `;`
        
        return unrolled
    
    # Recursively unroll any other while loops inside the tree
    return Tree(tree.root, [unroll_while(subtree, unroll_bound) for subtree in tree.subtrees])


def parse_and_unroll(program: str, unroll_limit: int = 8) -> Tree:
    """
    Parses the program string and unrolls all 'while' loops up to a set limit.
    
    Args:
        program (str): The program code as a string.
        unroll_limit (int): The number of times to unroll the 'while' loops.

    Returns:
        Tree: The modified AST with unrolled 'while' loops.
    """
    ast = parse(program)
    if ast:
        res = unroll_while(ast, unroll_limit)
        print(res)
        return res
    else:
        return None

def tree_to_program(tree: Tree) -> str:
    """
    Converts an AST (Tree) back into a While-language program as a string.

    Args:
        tree (Tree): The abstract syntax tree of the program.

    Returns:
        str: The program in string format.
    """
    if tree.root == ":=":  # Assignment
        left = tree_to_program(tree.subtrees[0])
        right = tree_to_program(tree.subtrees[1])
        return f"{left} := {right}"
    
    elif tree.root == "if" or tree.root == "if_unrolled":  # If-then-else statement
        cond = tree_to_program(tree.subtrees[0])
        then_part = tree_to_program(tree.subtrees[1])
        else_part = tree_to_program(tree.subtrees[2])
        return f"{tree.root} {cond} then ({then_part}) else ({else_part})"
    
    elif tree.root == "while":  # While loop
        cond = tree_to_program(tree.subtrees[0])
        body = tree_to_program(tree.subtrees[1])
        return f"while {cond} do ({body})"
    
    elif tree.root == "assert":  # Assert statement
        cond = tree_to_program(tree.subtrees[0])
        return f"assert {cond}"
    
    elif tree.root in ["+", "-", "*", "/", ">", "<", ">=", "<=", "==", "!=", "op", "="]:  # Binary operation
        left = tree_to_program(tree.subtrees[0])
        operator = tree.root  # Use the operator directly from the tree root
        right = tree_to_program(tree.subtrees[1])
        return f"({left} {operator} {right})"
    
    elif tree.root == "id":  # Identifier (variable)
        return tree.subtrees[0].root
    
    elif tree.root == "num":  # Number (constant)
        return str(tree.subtrees[0].root)
    
    elif tree.root == "skip":  # Skip statement
        return "skip"
    
    elif tree.root == "hole":  # Hole (??)
        return "??"
    
    elif tree.root == ";":  # Sequence of statements (S; S)
        left = tree_to_program(tree.subtrees[0])
        right = tree_to_program(tree.subtrees[1])
        return f"{left} ; {right}"
    
    else:
        # For any other unhandled case (e.g., grouping expressions)
        return " ".join(tree_to_program(subtree) for subtree in tree.subtrees)


def ast_to_string(ast: Tree) -> str:
    """
    Wrapper function that takes an AST and returns the corresponding program string.

    Args:
        ast (Tree): The abstract syntax tree of the program.

    Returns:
        str: The program as a string.
    """
    return tree_to_program(ast)

def remove_assertions_ast(ast):
    if(ast is None):
        return None

    if ast.root == "assert":
        return None
    else:
        new_subtrees = []
        for subtree in ast.subtrees:
            new_subtree = remove_assertions_ast(subtree)
            if new_subtree is not None:
                new_subtrees.append(new_subtree)
        ast.subtrees = new_subtrees

        if ast.root == ';' and len(ast.subtrees) == 1:
            ast = ast.subtrees[0]
        elif ast.root == ';' and len(ast.subtrees) == 0:
            ast = None

    return ast

def remove_assertions_program(program):
    ast = parse(program)
    if ast is None:
        return None
    print(f"ast_old: {ast}")
    ast_new = remove_assertions_ast(ast)
    print(f"ast_new: {ast_new}")

    if(ast_new is None):
        return None
    
    program_new = tree_to_program(ast_new)
    return program_new
