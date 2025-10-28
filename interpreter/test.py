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
    else:
        return Type(RecordType(name), dim)


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

    def test_record_literal_creation(self):
        # record Point { x:int, y:int }
        rt = RecordTypeDecl(
            name="Point",
            fields=[
                VarDecl("x", make_type("int"), mutable=False),
                VarDecl("y", make_type("int"), mutable=False),
            ]
        )

        # var p:Point = Point { x:1, y:2 }
        rlit = RecordLiteral(
            type="Point",
            field_values={
                "x": PrimitiveLiteral(1),
                "y": PrimitiveLiteral(2),
            }
        )

        decl = VarDecl(name="p", type=make_type("Point"), mutable=True, initializer=rlit)

        prog = Program(declarations=[rt, decl])
        interp = Interpreter(prog)
        gf = interp.run()

        p_val = gf.lookup("p").value
        self.assertEqual(p_val, {"__record_name__": "Point", "x": 1, "y": 2})

    def test_record_constructor_call(self):
        # record Point { x:int, y:int }
        rt = RecordTypeDecl(
            name="Point",
            fields=[
                VarDecl("x", make_type("int"), False),
                VarDecl("y", make_type("int"), False),
            ]
        )
        # var p:Point = Point(3, 4)
        ctor_call = FunctionCall(function=VarRef("Point"), arguments=[PrimitiveLiteral(3), PrimitiveLiteral(4)])
        decl = VarDecl(name="p", type=make_type("Point"), mutable=True, initializer=ctor_call)

        prog = Program(declarations=[rt, decl])
        interp = Interpreter(prog)
        gf = interp.run()

        p_val = gf.lookup("p").value
        self.assertEqual(p_val, {"__record_name__": "Point", "x": 3, "y": 4})

    def test_field_access_and_assignment(self):
        # record Point { x:int, y:int }
        rt = RecordTypeDecl(
            name="Point",
            fields=[
                VarDecl("x", make_type("int"), True),
                VarDecl("y", make_type("int"), True),
            ]
        )

        # var p:Point = Point(10, 20)
        ctor_call = FunctionCall(function=VarRef("Point"), arguments=[PrimitiveLiteral(10), PrimitiveLiteral(20)])
        decl = VarDecl(name="p", type=make_type("Point"), mutable=True, initializer=ctor_call)

        prog = Program(declarations=[rt, decl])
        interp = Interpreter(prog)
        gf = interp.run()

        # Access field p.x
        fr = FieldRef(VarRef("p"), "x")
        val = interp.eval_expression(fr, gf)
        self.assertEqual(val.value, 10)

        # Assignment p.x = 42
        assign = Assignment(FieldRef(VarRef("p"), "x"), PrimitiveLiteral(42))
        interp.exec_statement(assign, gf)
        self.assertEqual(gf.lookup("p").value["x"], 42)

    def test_type_mismatch_in_field(self):
        # record Point { x:int, y:int }
        rt = RecordTypeDecl(
            name="Point",
            fields=[
                VarDecl("x", make_type("int"), False),
                VarDecl("y", make_type("int"), False),
            ]
        )

        # Wrong: x is float instead of int
        rlit = RecordLiteral(
            type="Point",
            field_values={"x": PrimitiveLiteral(3.14), "y": PrimitiveLiteral(2)}
        )
        decl = VarDecl(name="p", type=make_type("Point"), mutable=True, initializer=rlit)

        prog = Program(declarations=[rt, decl])
        with self.assertRaises(RuntimeTypeError):
            Interpreter(prog)

    def test_missing_field_raises(self):
        rt = RecordTypeDecl(
            name="Point",
            fields=[VarDecl("x", make_type("int"), False), VarDecl("y", make_type("int"), False)]
        )
        rlit = RecordLiteral(type="Point", field_values={"x": PrimitiveLiteral(1)})
        decl = VarDecl(name="p", type=make_type("Point"), mutable=True, initializer=rlit)

        prog = Program(declarations=[rt, decl])
        with self.assertRaises(RuntimeTypeError):
            Interpreter(prog)

    def test_extra_field_raises(self):
        rt = RecordTypeDecl(
            name="Point",
            fields=[VarDecl("x", make_type("int"), False)]
        )
        rlit = RecordLiteral(type="Point", field_values={"x": PrimitiveLiteral(1), "y": PrimitiveLiteral(2)})
        decl = VarDecl(name="p", type=make_type("Point"), mutable=True, initializer=rlit)
        prog = Program(declarations=[rt, decl])
        with self.assertRaises(RuntimeTypeError):
            Interpreter(prog)

    def test_separate_record_constructors(self):
        # record Point { x, y }
        point_decl = RecordTypeDecl(
            name="Point",
            fields=[
                VarDecl("x", make_type("int"), False),
                VarDecl("y", make_type("int"), False),
            ]
        )

        # record Circle { center:Point, radius:int }
        circle_decl = RecordTypeDecl(
            name="Circle",
            fields=[
                VarDecl("center", make_type("Point"), False),
                VarDecl("radius", make_type("int"), False),
            ]
        )

        # var p:Point = Point(1, 2)
        point_ctor_call = FunctionCall(VarRef("Point"), [PrimitiveLiteral(1), PrimitiveLiteral(2)])
        point_var = VarDecl(name="p", type=make_type("Point"), mutable=True, initializer=point_ctor_call)

        # var c:Circle = Circle(p, 5)
        circle_ctor_call = FunctionCall(VarRef("Circle"), [VarRef("p"), PrimitiveLiteral(5)])
        circle_var = VarDecl(name="c", type=make_type("Circle"), mutable=True, initializer=circle_ctor_call)

        prog = Program(declarations=[point_decl, circle_decl, point_var, circle_var])
        interp = Interpreter(prog)
        gf = interp.run()

        p_val = gf.lookup("p").value
        c_val = gf.lookup("c").value

        # Check that both records were created properly
        self.assertEqual(p_val, {"__record_name__": "Point", "x": 1, "y": 2})
        self.assertIsInstance(c_val["center"], dict)
        self.assertEqual(c_val["center"]["x"], 1)
        self.assertEqual(c_val["radius"], 5)

    def test_type_mismatch_between_records(self):
        # record A { val:int }
        a_decl = RecordTypeDecl(
            name="A",
            fields=[VarDecl("val", make_type("int"), False)]
        )

        # record B { val:int }
        b_decl = RecordTypeDecl(
            name="B",
            fields=[VarDecl("val", make_type("int"), False)]
        )

        # var a:A = A(42)
        a_var = VarDecl(name="a", type=make_type("A"), mutable=True, initializer=FunctionCall(VarRef("A"), [PrimitiveLiteral(42)]))

        # var b:B = a  <-- invalid: assigning A to B
        assign_b = VarDecl(name="b", type=make_type("B"), mutable=True, initializer=VarRef("a"))

        prog = Program(declarations=[a_decl, b_decl, a_var, assign_b])

        with self.assertRaises(RuntimeTypeError):
            Interpreter(prog)

    def test_nested_record_field_access_and_assignment(self):
        # record Inner { a:int, b:int }
        inner_decl = RecordTypeDecl(
            name="Inner",
            fields=[
                VarDecl("a", make_type("int"), True),
                VarDecl("b", make_type("int"), True),
            ]
        )

        # record Outer { inner:Inner, name:int }
        outer_decl = RecordTypeDecl(
            name="Outer",
            fields=[
                VarDecl("inner", make_type("Inner"), True),
                VarDecl("name", make_type("int"), True),
            ]
        )

        inner_ctor = FunctionCall(VarRef("Inner"), [PrimitiveLiteral(5), PrimitiveLiteral(6)])
        outer_ctor = FunctionCall(VarRef("Outer"), [inner_ctor, PrimitiveLiteral(7)])

        outer_var = VarDecl(name="o", type=make_type("Outer"), mutable=True, initializer=outer_ctor)

        prog = Program(declarations=[inner_decl, outer_decl, outer_var])
        interp = Interpreter(prog)
        gf = interp.run()

        # Access nested field o.inner.a
        field_ref = FieldRef(FieldRef(VarRef("o"), "inner"), "a")
        val = interp.eval_expression(field_ref, gf)
        self.assertEqual(val.value, 5)

        # Assign to nested field o.inner.b = 99
        assign = Assignment(FieldRef(FieldRef(VarRef("o"), "inner"), "b"), PrimitiveLiteral(99))
        interp.exec_statement(assign, gf)
        self.assertEqual(gf.lookup("o").value["inner"]["b"], 99)

    def test_operator_scalar_array_broadcast(self):
        # Test (scalar + array) broadcasting
        expr = OperatorCall('+', [PrimitiveLiteral(10),
                                  ArrayLiteral([PrimitiveLiteral(1), PrimitiveLiteral(2), PrimitiveLiteral(3)])])

        prog = Program(declarations=[])
        interp = Interpreter(prog)
        gf = interp.run()
        result = interp.eval_expression(expr, gf)

        self.assertTrue(np.allclose(result.value, np.array([11, 12, 13])))
        self.assertEqual(result.shape, (3,))

    def test_operator_array_array_broadcast(self):
        # Test (array + array) broadcasting (1x3 + 3x1)

        a1 = ArrayLiteral(
            [ArrayLiteral([PrimitiveLiteral(1), PrimitiveLiteral(2), PrimitiveLiteral(3)])])  # shape (1,3)

        a2 = ArrayLiteral([
            ArrayLiteral([PrimitiveLiteral(10)]),
            ArrayLiteral([PrimitiveLiteral(20)]),
            ArrayLiteral([PrimitiveLiteral(30)])
        ])  # shape (3,1)

        expr = OperatorCall('+', [a1, a2])

        prog = Program(declarations=[])
        interp = Interpreter(prog)
        gf = interp.run()
        result = interp.eval_expression(expr, gf)

        self.assertTrue(np.allclose(result.value, np.array([[11, 12, 13],
                                                            [21, 22, 23],
                                                            [31, 32, 33]])))
        self.assertEqual(result.shape, (3, 3))

    def test_function_broadcast_array_and_scalar(self):
        # Define f(x: float): float { return x * 2 }
        param = VarDecl(name="x", type=Type(PrimitiveType("array"), 0), mutable=True, initializer=None)
        body = OperatorCall('*', [VarRef("x"), PrimitiveLiteral(2)])
        f_def = FunctionDef(name="f", params=[param],
                            body=body,
                            return_type=Type(PrimitiveType("float"), 0))

        prog = Program(declarations=[f_def])
        interp = Interpreter(prog)
        gf = interp.run()

        # Call f on array — should broadcast elementwise
        call = FunctionCall(VarRef("f"), [ArrayLiteral([
            PrimitiveLiteral(1.0), PrimitiveLiteral(2.0), PrimitiveLiteral(3.0)
        ])])

        result = interp.eval_expression(call, gf)

        self.assertTrue(np.allclose(result.value, np.array([2.0, 4.0, 6.0])))
        self.assertEqual(result.shape, (3,))

    def test_function_broadcast_array_and_scalar2(self):
        # Define g(a: float, b: float): float { return a + b }
        param_a = VarDecl(name="a", type=Type(PrimitiveType("array"), 0), mutable=True, initializer=None)
        param_b = VarDecl(name="b", type=Type(PrimitiveType("int"), 0), mutable=True, initializer=None)
        body = OperatorCall('+', [VarRef("a"), VarRef("b")])
        g_def = FunctionDef(name="g", params=[param_a, param_b], body=body, return_type=Type(PrimitiveType("float"), 0))

        prog = Program(declarations=[g_def])
        interp = Interpreter(prog)
        gf = interp.run()

        # Call g([1,2,3], 10)
        call = FunctionCall(VarRef("g"), [
            ArrayLiteral([PrimitiveLiteral(1), PrimitiveLiteral(2), PrimitiveLiteral(3)]),
            PrimitiveLiteral(10)
        ])
        result = interp.eval_expression(call, interp.global_frame)

        self.assertTrue(np.allclose(result.value, np.array([11, 12, 13])))
        self.assertEqual(result.shape, (3,))

    def test_function_broadcast_array_pair(self):
        # g(a: float, b: float): float { return a * b }
        param_a = VarDecl(name="a", type=Type(PrimitiveType("array"), 0), mutable=True, initializer=None)
        param_b = VarDecl(name="b", type=Type(PrimitiveType("array"), 0), mutable=True, initializer=None)
        body = OperatorCall('*', [VarRef("a"), VarRef("b")])
        g_def = FunctionDef(name="g", params=[param_a, param_b], body=body, return_type=Type(PrimitiveType("float"), 0))

        prog = Program(declarations=[g_def])
        interp = Interpreter(prog)
        gf = interp.run()

        # Call g([1,2,3], [10,20,30])
        call = FunctionCall(VarRef("g"), [
            ArrayLiteral([PrimitiveLiteral(1), PrimitiveLiteral(2), PrimitiveLiteral(3)]),
            ArrayLiteral([PrimitiveLiteral(10), PrimitiveLiteral(20), PrimitiveLiteral(30)])
        ])
        result = interp.eval_expression(call, interp.global_frame)

        self.assertTrue(np.allclose(result.value, np.array([10, 40, 90])))
        self.assertEqual(result.shape, (3,))


if __name__ == "main":
    unittest.main()