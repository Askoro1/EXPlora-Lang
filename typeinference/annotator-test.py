import unittest
import ast_nodes
import type_annotator

small_ast = ast_nodes.Program(declarations=[
    ast_nodes.VarDecl(
        name="x",
        type=None,
        mutable=False,
        initializer=ast_nodes.PrimitiveLiteral(5)
    ),
    ast_nodes.VarDecl(
        name="y",
        type=None,
        mutable=False,
        initializer=ast_nodes.OperatorCall(
            operator="+",
            operands=[
                ast_nodes.VarRef(name="x"),
                ast_nodes.PrimitiveLiteral(1)
            ]
        )
    )
])

expected_typed_ast_small = """Program(declarations=[
VarDecl(name='x', type=Type(base_type=PrimitiveType(name='int'), dimension=0), mutable=False, initializer=PrimitiveLiteral(value=5, type=Type(base_type=PrimitiveType(name='int'), dimension=0))),
VarDecl(name='y', type=Type(base_type=PrimitiveType(name='int'), dimension=0), mutable=False, initializer=OperatorCall(operator='+', operands=[VarRef(name='x', type=Type(base_type=PrimitiveType(name='int'), dimension=0)), PrimitiveLiteral(value=1, type=Type(base_type=PrimitiveType(name='int'), dimension=0))], type=Type(base_type=PrimitiveType(name='int'), dimension=0)))
])"""

class TypeCheckerTests(unittest.TestCase):
    def setUp(self):
        self.env = {}

    """
    Compares the Typed AST to the annotator's output.
    """

    def test_small_ast(self):
        type_annotator.type_annotate_program(small_ast, self.env)
        self.maxDiff = None
        result_str = repr(small_ast)
        # ignore whitespace differences
        clean_result = "".join(result_str.split())
        clean_expected = "".join(expected_typed_ast_small.split())
        self.assertEqual(clean_result, clean_expected)

if __name__ == "__main__":
    unittest.main()