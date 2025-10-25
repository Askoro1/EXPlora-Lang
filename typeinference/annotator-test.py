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

    """
    Annotate a simple function definition.
    fn inc(Int x) -> Int { x + 1 }
    """
    def test_function_def_annotation(self):
        func_decl = ast_nodes.FunctionDef(
            name="inc",
            params=[ast_nodes.VarDecl("x", ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0), False)],
            return_type=ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0),
            body=ast_nodes.OperatorCall(
                operator="+",
                operands=[
                    ast_nodes.VarRef("x"),
                    ast_nodes.PrimitiveLiteral(1)
                ]
            )
        )
        program = ast_nodes.Program(declarations=[func_decl])
        type_annotator.type_annotate_program(program, self.env)
        result_type = func_decl.type
        expected_type = ast_nodes.Type(ast_nodes.FunctionType(
            param_types=[ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0)],
            return_type=ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0)
        ), 0)
        self.assertEqual(result_type, expected_type)

    """
    Annotate a record type declaration.
    record Point { x: Int, y: Int }
    """
    def test_record_type_decl_annotation(self):
        fields = [
            ast_nodes.VarDecl("x", ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0), False),
            ast_nodes.VarDecl("y", ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0), False)
        ]
        record_decl = ast_nodes.RecordTypeDecl("Point", fields)
        program = ast_nodes.Program(declarations=[record_decl])
        type_annotator.type_annotate_program(program, self.env)

        self.assertIn("Point", self.env)
        rec_type = self.env["Point"]
        self.assertIsInstance(rec_type.base_type, ast_nodes.RecordType)
        self.assertEqual(rec_type.base_type.fields["x"].base_type.name, "int")
        self.assertEqual(rec_type.base_type.fields["y"].base_type.name, "int")

    """
    Annotate variable declaration with explicit type.
    let z: Int = 3
    """
    def test_var_decl_with_type(self):
        decl = ast_nodes.VarDecl(
            name="z",
            type=ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0),
            mutable=False,
            initializer=ast_nodes.PrimitiveLiteral(3)
        )
        program = ast_nodes.Program(declarations=[decl])
        type_annotator.type_annotate_program(program, self.env)

        self.assertIn("z", self.env)
        inferred_type = self.env["z"]
        expected_type = ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0)
        self.assertEqual(inferred_type, expected_type)

    """
    Check that a declared type mismatch raises TypeError.
    let z: Float = 3  -> invalid
    """
    def test_var_decl_type_mismatch(self):
        decl = ast_nodes.VarDecl(
            name="z",
            type=ast_nodes.Type(ast_nodes.PrimitiveType("float"), 0),
            mutable=False,
            initializer=ast_nodes.PrimitiveLiteral(3)
        )
        program = ast_nodes.Program(declarations=[decl])
        with self.assertRaises(TypeError):
            type_annotator.type_annotate_program(program, self.env)

    """
    Annotate a block expression with local variable.
    { let a = 5; a + 1 }
    """
    def test_block_annotation(self):
        block = ast_nodes.Block([
            ast_nodes.DeclStmt(ast_nodes.VarDecl(
                name="a",
                type=None,
                mutable=False,
                initializer=ast_nodes.PrimitiveLiteral(5)
            )),
            ast_nodes.ExprStmt(ast_nodes.OperatorCall(
                operator="+",
                operands=[
                    ast_nodes.VarRef("a"),
                    ast_nodes.PrimitiveLiteral(1)
                ]
            ))
        ])
        program = ast_nodes.Program(declarations=[
            ast_nodes.VarDecl(name="x", type=None, mutable=False, initializer=block)
        ])
        type_annotator.type_annotate_program(program, self.env)
        self.assertIn("x", self.env)
        self.assertEqual(self.env["x"].base_type.name, "int")

    """
    Variables depending on previously declared variables.
    let a = 5; let b = a + 2
    """
    def test_chained_var_dependencies(self):
        program = ast_nodes.Program(declarations=[
            ast_nodes.VarDecl(
                name="a",
                type=None,
                mutable=False,
                initializer=ast_nodes.PrimitiveLiteral(5)
            ),
            ast_nodes.VarDecl(
                name="b",
                type=None,
                mutable=False,
                initializer=ast_nodes.OperatorCall(
                    operator="+",
                    operands=[
                        ast_nodes.VarRef("a"),
                        ast_nodes.PrimitiveLiteral(2)
                    ]
                )
            )
        ])
        type_annotator.type_annotate_program(program, self.env)
        self.assertEqual(self.env["a"].base_type.name, "int")
        self.assertEqual(self.env["b"].base_type.name, "int")

    """
    Function operating on a record.
    fn getX(Point p) -> Float { p.x }
    """

    def test_function_with_record_param(self):
        point_record = ast_nodes.RecordType("Point")
        point_record.fields = {
            "x": ast_nodes.Type(ast_nodes.PrimitiveType("float"), 0),
            "y": ast_nodes.Type(ast_nodes.PrimitiveType("float"), 0)
        }
        record_type = ast_nodes.Type(point_record, 0)

        func_decl = ast_nodes.FunctionDef(
            name="getX",
            params=[ast_nodes.VarDecl("p", record_type, False)],
            return_type=ast_nodes.Type(ast_nodes.PrimitiveType("float"), 0),
            body=ast_nodes.FieldRef(ast_nodes.VarRef("p"), "x")
        )

        program = ast_nodes.Program(declarations=[func_decl])

        self.env["Point"] = record_type

        type_annotator.type_annotate_program(program, self.env)

        self.assertIn("getX", self.env)
        self.assertIsInstance(self.env["getX"].base_type, ast_nodes.FunctionType)

    """
    Annotate a lambda literal.
    (lambda (x: Int) -> x + 1)
    """
    def test_lambda_literal_annotation(self):
        param = ast_nodes.VarDecl("x", ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0), False)
        node = ast_nodes.LambdaLiteral(
            params=[param],
            body=ast_nodes.OperatorCall(
                operator="+",
                operands=[
                    ast_nodes.VarRef("x"),
                    ast_nodes.PrimitiveLiteral(1)
                ]
            )
        )
        expr = type_annotator.annotate_expression(node, self.env)
        self.assertIsInstance(expr.type.base_type, ast_nodes.FunctionType)
        self.assertEqual(expr.type.base_type.return_type.base_type.name, "int")

    """
    Uninitialized variable declaration.
    let z: Int;
    """
    def test_uninitialized_var_decl(self):
        decl = ast_nodes.VarDecl(
            name="z",
            type=ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0),
            mutable=False,
            initializer=None
        )
        program = ast_nodes.Program(declarations=[decl])
        type_annotator.type_annotate_program(program, self.env)
        self.assertIn("z", self.env)
        self.assertEqual(self.env["z"].base_type.name, "int")

    """
    Nested block scope should not leak local variable.
    { let a = 5; { let b = 10; b + a }; }
    """
    def test_nested_block_scope(self):
        inner_block = ast_nodes.Block([
            ast_nodes.DeclStmt(ast_nodes.VarDecl(
                name="b",
                type=None,
                mutable=False,
                initializer=ast_nodes.PrimitiveLiteral(10)
            )),
            ast_nodes.ExprStmt(ast_nodes.OperatorCall(
                operator="+",
                operands=[ast_nodes.VarRef("b"), ast_nodes.VarRef("a")]
            ))
        ])

        outer_block = ast_nodes.Block([
            ast_nodes.DeclStmt(ast_nodes.VarDecl(
                name="a",
                type=None,
                mutable=False,
                initializer=ast_nodes.PrimitiveLiteral(5)
            )),
            ast_nodes.ExprStmt(inner_block)
        ])

        program = ast_nodes.Program(declarations=[
            ast_nodes.VarDecl(name="x", type=None, mutable=False, initializer=outer_block)
        ])

        type_annotator.type_annotate_program(program, self.env)
        self.assertIn("x", self.env)
        self.assertEqual(self.env["x"].base_type.name, "int")

if __name__ == "__main__":
    unittest.main()