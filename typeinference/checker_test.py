import unittest
import ast_nodes
import type_checker

class TypeCheckerTests(unittest.TestCase):
    def setUp(self):
        self.env = {}

    """
    Check if int literal & inference match.
    """
    def test_primitive_literal(self):
        node = ast_nodes.PrimitiveLiteral(5)
        result = type_checker.infer_expression_type(node, self.env)
        expected = ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0)
        self.assertEqual(result, expected)

    """
    Check if array literal & inference match.
    """
    def test_array_literal(self):
        node = ast_nodes.ArrayLiteral([
            ast_nodes.PrimitiveLiteral(1),
            ast_nodes.PrimitiveLiteral(2)
        ])

        result = type_checker.infer_expression_type(node, self.env)
        expected = ast_nodes.Type(ast_nodes.PrimitiveType("int"), 1)
        self.assertEqual(result, expected)

    """
    Check if operator call case has expected output.
    """
    def test_operator_call(self):
        env = {"x": ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0),
               "y": ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0)}
        node = ast_nodes.OperatorCall("+", [
            ast_nodes.VarRef("x"),
            ast_nodes.VarRef("y")
        ])

        result = type_checker.infer_expression_type(node, env)
        expected = ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0)
        self.assertEqual(result, expected)

    """
    Check if the record literal case has expected output.
    """
    def test_record_literal(self):
        point_record = ast_nodes.RecordType("Point")
        point_record.fields = {
            "x": ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0),
            "y": ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0)
        }

        env = {"Coord" : ast_nodes.Type(point_record, 0)}

        node = ast_nodes.RecordLiteral("Point", {
            "x": ast_nodes.PrimitiveLiteral(1.0),
            "y": ast_nodes.PrimitiveLiteral(3.14)})

        result = type_checker.infer_expression_type(node, env)
        expected = ast_nodes.Type(ast_nodes.RecordType("Point"), 0)
        self.assertEqual(result, expected)

    def test_field_ref(self):
        point_record = ast_nodes.RecordType("Point")
        point_record.fields = {
            "x": ast_nodes.Type(ast_nodes.PrimitiveType("float"), 0),
            "y": ast_nodes.Type(ast_nodes.PrimitiveType("float"), 0)
        }

        env = {"Point": ast_nodes.Type(point_record, 0),
               "p": ast_nodes.Type(ast_nodes.RecordType("Point"), 0)}

        field_ref = ast_nodes.FieldRef(
            record=ast_nodes.VarRef("p"),
            field_name="x"
        )

        result = type_checker.infer_expression_type(field_ref, env)
        expected = ast_nodes.Type(ast_nodes.PrimitiveType("float"), 0)
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()