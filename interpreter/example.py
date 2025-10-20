from ast_nodes import *
from interpreter import Interpreter

# code:
# unit main(): {
#   a: array = zeros((2,2))
#   b: array = ones((2,2))
#   c = a + b
#   print(c)
# }
#
# main()

main_fn = FunctionDef(name='main',
                      params=[],
                      return_type=Type(PrimitiveType("unit"), dimension=0),
                      body=Block(statements=[
                          DeclStmt(
                              VarDecl(name="a", type=Type(base_type=RecordType("array"), dimension=2), mutable=True,
                                      initializer=FunctionCall(function=VarRef("zeros"), arguments=[ArrayLiteral(value=[PrimitiveLiteral(2), PrimitiveLiteral(2)])]))
                          ),
                          DeclStmt(
                              VarDecl(name="b", type=Type(base_type=RecordType("array"), dimension=2), mutable=True,
                                      initializer=FunctionCall(function=VarRef("ones"), arguments=[ArrayLiteral(value=[PrimitiveLiteral(2), PrimitiveLiteral(2)])]))
                          ),
                          DeclStmt(
                              VarDecl(name="c", type=Type(base_type=RecordType("array"), dimension=2), mutable=True,
                                      initializer=OperatorCall(operator="+", operands=[VarRef("a"), VarRef("b")]))
                          ),
                          ExprStmt(
                              FunctionCall(function=VarRef("print"), arguments=[VarRef("c")])
                          )
                      ]))

prog = Program(declarations=[main_fn])
interp = Interpreter(prog)
global_frame = interp.run()

call = FunctionCall(function=VarRef("main"), arguments=[])
interp.eval_expression(call, global_frame)
