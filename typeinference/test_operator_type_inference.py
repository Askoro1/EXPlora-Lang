import unittest
from .. import ast_nodes
from . import type_checker


class TestTypeCheckerNewFeatures(unittest.TestCase):
    """Additional type inference tests for new language features.

    These tests cover indexing, modulo, logical operators, and
    concatenation to ensure that the type checker produces the
    expected types or raises appropriate errors.
    """

    def test_indexing_reduces_dimension(self):
        """Indexing an array decreases its dimension by one."""
        env = {
            "arr2": ast_nodes.Type(ast_nodes.PrimitiveType("int"), 2),  # e.g. int^2
            "i": ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0),    # scalar int
        }
        node = ast_nodes.OperatorCall("[]", [ast_nodes.VarRef("arr2"), ast_nodes.VarRef("i")])
        result = type_checker.infer_expression_type(node, env)
        expected = ast_nodes.Type(ast_nodes.PrimitiveType("int"), 1)
        self.assertEqual(result, expected)

    def test_indexing_scalar_fails(self):
        """Attempting to index a scalar should result in a TypeError."""
        env = {
            "x": ast_nodes.Type(ast_nodes.PrimitiveType("float"), 0),
            "i": ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0),
        }
        node = ast_nodes.OperatorCall("[]", [ast_nodes.VarRef("x"), ast_nodes.VarRef("i")])
        with self.assertRaises(TypeError):
            type_checker.infer_expression_type(node, env)

    def test_index_type_must_be_int(self):
        """Index must be an int^0; other types should raise an error."""
        env = {
            "arr": ast_nodes.Type(ast_nodes.PrimitiveType("int"), 1),
            "idx": ast_nodes.Type(ast_nodes.PrimitiveType("float"), 0),
        }
        node = ast_nodes.OperatorCall("[]", [ast_nodes.VarRef("arr"), ast_nodes.VarRef("idx")])
        with self.assertRaises(TypeError):
            type_checker.infer_expression_type(node, env)

    def test_modulo_operator_type(self):
        """Modulo returns the same base type and dimension as its operands."""
        env = {
            "a": ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0),
            "b": ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0),
        }
        node = ast_nodes.OperatorCall("%", [ast_nodes.VarRef("a"), ast_nodes.VarRef("b")])
        result = type_checker.infer_expression_type(node, env)
        expected = ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0)
        self.assertEqual(result, expected)

        # array modulo array yields same dimension
        env2 = {
            "x": ast_nodes.Type(ast_nodes.PrimitiveType("int"), 1),
            "y": ast_nodes.Type(ast_nodes.PrimitiveType("int"), 1),
        }
        node2 = ast_nodes.OperatorCall("%", [ast_nodes.VarRef("x"), ast_nodes.VarRef("y")])
        result2 = type_checker.infer_expression_type(node2, env2)
        expected2 = ast_nodes.Type(ast_nodes.PrimitiveType("int"), 1)
        self.assertEqual(result2, expected2)

    def test_logical_operator_type(self):
        """Logical and/or operators return bool with the broadcasted dimension."""
        env = {
            "p": ast_nodes.Type(ast_nodes.PrimitiveType("bool"), 1),
            "q": ast_nodes.Type(ast_nodes.PrimitiveType("bool"), 1),
        }
        node = ast_nodes.OperatorCall("&&", [ast_nodes.VarRef("p"), ast_nodes.VarRef("q")])
        result = type_checker.infer_expression_type(node, env)
        expected = ast_nodes.Type(ast_nodes.PrimitiveType("bool"), 1)
        self.assertEqual(result, expected)

    def test_concatenation_operator_type(self):
        """Concatenation preserves base type and dimension."""
        env = {
            "a": ast_nodes.Type(ast_nodes.PrimitiveType("float"), 1),
            "b": ast_nodes.Type(ast_nodes.PrimitiveType("float"), 1),
        }
        node = ast_nodes.OperatorCall("++", [ast_nodes.VarRef("a"), ast_nodes.VarRef("b")])
        result = type_checker.infer_expression_type(node, env)
        expected = ast_nodes.Type(ast_nodes.PrimitiveType("float"), 1)
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
