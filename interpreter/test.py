import unittest
import numpy as np

from ast_nodes import *
from utils import RuntimeTypeError, RuntimeValue, shape_of_array
from builtins_ import _builtin_zeros, _builtin_ones, _builtin_shape
from interpreter import Interpreter


def make_type(name: str, dim: int = 0):
    if name in ("int", "float", "bool", "unit"):
        return Type(PrimitiveType(name), dim)
    if name == "array":
        return Type(RecordType("array"), dim)
    raise ValueError(name)


class TestBuiltins(unittest.TestCase):
    def test_zeros_ones_shape(self):
        z = _builtin_zeros([RuntimeValue([2, 3])])
        self.assertEqual(z.shape, (2, 3))
        self.assertTrue(np.allclose(z.value, np.zeros((2, 3))))

        o = _builtin_ones([RuntimeValue([2, 3])])
        self.assertEqual(o.shape, (2, 3))
        self.assertTrue(np.allclose(o.value, np.ones((2, 3))))

        s = _builtin_shape([z])
        self.assertEqual(s.value, (2, 3))

    def test_zeros_wrong_args(self):
        with self.assertRaises(RuntimeTypeError):
            _builtin_zeros([])


class TestUtils(unittest.TestCase):
    def test_shape_of_array_numpy_and_list(self):
        a = np.zeros((2, 4))
        self.assertEqual(shape_of_array(a), (2, 4))
        self.assertEqual(shape_of_array([[1, 2], [3, 4]]), (2, 2))


class TestInterpreter(unittest.TestCase):
    def setUp(self):
        self.empty_prog = Program(declarations=[])
        self.interp = Interpreter(self.empty_prog)
        self.gf = self.interp.global_frame

    def test_arithmetic_literals_and_ops(self):
        lit1 = PrimitiveLiteral(3)
        lit2 = PrimitiveLiteral(4)
        op = OperatorCall("+", [lit1, lit2])
        res = self.interp.eval_expression(op, self.gf)
        self.assertEqual(res.value, 7)

        op2 = OperatorCall("*", [PrimitiveLiteral(5), PrimitiveLiteral(2)])
        self.assertEqual(self.interp.eval_expression(op2, self.gf).value, 10)

        op3 = OperatorCall("==", [PrimitiveLiteral(5), PrimitiveLiteral(5)])
        self.assertTrue(self.interp.eval_expression(op3, self.gf).value)

    def test_array_literal_and_addition(self):
        arr1 = ArrayLiteral([PrimitiveLiteral(1), PrimitiveLiteral(2)])
        arr2 = ArrayLiteral([PrimitiveLiteral(3), PrimitiveLiteral(4)])
        add = OperatorCall("+", [arr1, arr2])
        res = self.interp.eval_expression(add, self.gf)
        self.assertTrue(np.allclose(res.value, np.array([4, 6])))

    def test_var_decl_and_assignment(self):
        decl = VarDecl("x", make_type("int"), mutable=True, initializer=PrimitiveLiteral(5))
        prog = Program(declarations=[decl])
        interp = Interpreter(prog)
        gf = interp.run()
        self.assertEqual(gf.lookup("x").value, 5)
        assign = Assignment(VarRef("x"), PrimitiveLiteral(9))
        interp.exec_statement(assign, gf)
        self.assertEqual(gf.lookup("x").value, 9)

    def test_simple_function_call(self):
        fn = FunctionDef(
            name="add",
            params=[
                VarDecl("a", make_type("float"), mutable=False),
                VarDecl("b", make_type("float"), mutable=False),
            ],
            return_type=make_type("float"),
            body=OperatorCall("+", [VarRef("a"), VarRef("b")]),
        )
        prog = Program(declarations=[fn])
        interp = Interpreter(prog)
        gf = interp.run()
        call = FunctionCall(VarRef("add"), [PrimitiveLiteral(10.), PrimitiveLiteral(20.)])
        result = interp.eval_expression(call, gf)
        self.assertEqual(result.value, 30.)

    def test_lambda_literal_call(self):
        lmbd = LambdaLiteral(
            params=[VarDecl("x", make_type("int"), mutable=False)],
            body=OperatorCall("*", [VarRef("x"), PrimitiveLiteral(2)]),
        )
        call = FunctionCall(lmbd, [PrimitiveLiteral(5)])
        result = self.interp.eval_expression(call, self.gf)
        self.assertEqual(result.value, 10)

    def test_block_and_if_expr(self):
        block = Block(
            statements=[
                DeclStmt(VarDecl("x", make_type("int"), mutable=True, initializer=PrimitiveLiteral(5))),
                ExprStmt(OperatorCall("+", [VarRef("x"), PrimitiveLiteral(3)])),
            ]
        )
        res = self.interp.eval_expression(block, self.gf)
        self.assertEqual(res.value, 8)

        ifexpr = IfExpr(PrimitiveLiteral(True), PrimitiveLiteral(1), PrimitiveLiteral(2))
        self.assertEqual(self.interp.eval_expression(ifexpr, self.gf).value, 1)

        ifexpr2 = IfExpr(PrimitiveLiteral(False), PrimitiveLiteral(1), PrimitiveLiteral(2))
        self.assertEqual(self.interp.eval_expression(ifexpr2, self.gf).value, 2)

    def test_while_loop_simple(self):
        decl = VarDecl("i", make_type("int"), mutable=True, initializer=PrimitiveLiteral(0))
        cond = OperatorCall("<", [VarRef("i"), PrimitiveLiteral(3)])
        body = Assignment(VarRef("i"), OperatorCall("+", [VarRef("i"), PrimitiveLiteral(1)]))
        loop = WhileLoop(cond, body)
        prog = Program(declarations=[decl])
        interp = Interpreter(prog)
        gf = interp.run()
        interp.exec_statement(loop, gf)
        self.assertEqual(gf.lookup("i").value, 3)

    def test_type_mismatch_raises(self):
        decl = VarDecl("x", make_type("int"), mutable=True, initializer=PrimitiveLiteral(3.14))
        prog = Program(declarations=[decl])
        with self.assertRaises(RuntimeTypeError):
            Interpreter(prog)


if __name__ == "main":
    unittest.main()