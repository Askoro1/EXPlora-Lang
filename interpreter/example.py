from ast_nodes import *
from interpreter import Interpreter

# code:
# var a: array = zeros((2,2))
# var b: array = ones((2,2))
# var c = a + b
# print(c)

prog = Program(declarations=[
    VarDecl(name="a", type=Type(base_type=RecordType("array"), dimension=2), mutable=True,
            initializer=FunctionCall(function=VarRef("zeros"), arguments=[ArrayLiteral(value=[PrimitiveLiteral(2), PrimitiveLiteral(2)])])),
    VarDecl(name="b", type=Type(base_type=RecordType("array"), dimension=2), mutable=True,
            initializer=FunctionCall(function=VarRef("ones"), arguments=[ArrayLiteral(value=[PrimitiveLiteral(2), PrimitiveLiteral(2)])])),
    VarDecl(name="c", type=Type(base_type=RecordType("array"), dimension=2), mutable=True,
            initializer=OperatorCall(operator="+", operands=[VarRef("a"), VarRef("b")]))
])

interp = Interpreter(prog)
gf = interp.run()

# print
print_call = FunctionCall(function=VarRef("print"), arguments=[VarRef("c")])
interp.eval_expression(print_call, gf)
