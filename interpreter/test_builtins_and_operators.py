import unittest
import numpy as np

from ast_nodes import PrimitiveLiteral, ArrayLiteral, OperatorCall, VarRef, Program
from utils import RuntimeValue, RuntimeTypeError
from builtins_ import _builtin_size
from interpreter import Interpreter


class TestInterpreterNewFeatures(unittest.TestCase):
    """Unit tests for the new language features such as indexing, modulo,
    logical operators, concatenation and the size builtin.

    These tests ensure that the interpreter correctly evaluates expressions
    involving the newly introduced operators and built‑ins.  They operate
    directly on expression AST nodes without requiring full programs.
    """

    def setUp(self):
        # create an interpreter with an empty program so that builtins
        # are registered in the global frame
        self.empty_prog = Program(declarations=[])
        self.interp = Interpreter(self.empty_prog)
        self.gf = self.interp.global_frame

    def test_indexing_simple(self):
        """Indexing a one‑dimensional array returns the element at that index."""
        arr = ArrayLiteral([PrimitiveLiteral(10), PrimitiveLiteral(20), PrimitiveLiteral(30)])
        index = PrimitiveLiteral(1)
        node = OperatorCall("[]", [arr, index])
        result = self.interp.eval_expression(node, self.gf)
        self.assertEqual(result.value, 20)

    def test_indexing_on_scalar_raises(self):
        """Indexing a scalar should raise a RuntimeTypeError."""
        with self.assertRaises(RuntimeTypeError):
            node = OperatorCall("[]", [PrimitiveLiteral(5), PrimitiveLiteral(0)])
            self.interp.eval_expression(node, self.gf)

    def test_index_type_must_be_int(self):
        """Non‑integer indices should raise a RuntimeTypeError."""
        arr = ArrayLiteral([PrimitiveLiteral(1), PrimitiveLiteral(2)])
        # using a float as index
        with self.assertRaises(RuntimeTypeError):
            node = OperatorCall("[]", [arr, PrimitiveLiteral(1.0)])
            self.interp.eval_expression(node, self.gf)

    def test_modulo_operator(self):
        """The '%' operator performs integer modulo on scalars."""
        node = OperatorCall("%", [PrimitiveLiteral(7), PrimitiveLiteral(4)])
        result = self.interp.eval_expression(node, self.gf)
        self.assertEqual(result.value, 3)

    def test_logical_and_or(self):
        """Logical '&&' and '||' operators evaluate boolean expressions."""
        and_node = OperatorCall("&&", [PrimitiveLiteral(True), PrimitiveLiteral(False)])
        or_node = OperatorCall("||", [PrimitiveLiteral(False), PrimitiveLiteral(True)])
        res_and = self.interp.eval_expression(and_node, self.gf)
        res_or = self.interp.eval_expression(or_node, self.gf)
        self.assertFalse(res_and.value)
        self.assertTrue(res_or.value)

    def test_concatenation_operator(self):
        """The '++' operator concatenates arrays elementwise."""
        arr1 = ArrayLiteral([PrimitiveLiteral(1), PrimitiveLiteral(2)])
        arr2 = ArrayLiteral([PrimitiveLiteral(3), PrimitiveLiteral(4)])
        node = OperatorCall("++", [arr1, arr2])
        result = self.interp.eval_expression(node, self.gf)
        # Should produce a numpy array [1, 2, 3, 4]
        self.assertTrue(np.allclose(result.value, np.array([1, 2, 3, 4])))

    def test_size_builtin_numpy_and_list(self):
        """The size builtin returns the length of the outermost dimension."""
        # numpy array 2x3 -> size 2
        arr_np = RuntimeValue(np.zeros((2, 3)))
        res_np = _builtin_size([arr_np])
        self.assertEqual(res_np.value, 2)
        # nested list 3x2 -> size 3
        arr_list = RuntimeValue([[1, 2], [3, 4], [5, 6]])
        res_list = _builtin_size([arr_list])
        self.assertEqual(res_list.value, 3)
        # scalar -> error
        with self.assertRaises(RuntimeTypeError):
            _builtin_size([RuntimeValue(42)])


if __name__ == "__main__":
    unittest.main()
