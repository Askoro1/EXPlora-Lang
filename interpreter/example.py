from ..parser.tokenizer import *
from ..ast_nodes import *
from .interpreter import Interpreter
from ..parser.parser import Parser

# code:
# unit main(): {
#   a: array = zeros((2,2))
#   b: array = ones((2,2))
#   c = a + b
#   print(c)
# }
#
# main()

# main_fn = FunctionDef(name='main',
#                       params=[],
#                       return_type=Type(PrimitiveType("unit"), dimension=0),
#                       body=Block(statements=[
#                           DeclStmt(
#                               VarDecl(name="a", type=Type(base_type=RecordType("array"), dimension=2), mutable=True,
#                                       initializer=FunctionCall(function=VarRef("zeros"), arguments=[ArrayLiteral(value=[PrimitiveLiteral(2), PrimitiveLiteral(2)])]))
#                           ),
#                           DeclStmt(
#                               VarDecl(name="b", type=Type(base_type=RecordType("array"), dimension=2), mutable=True,
#                                       initializer=FunctionCall(function=VarRef("ones"), arguments=[ArrayLiteral(value=[PrimitiveLiteral(2), PrimitiveLiteral(2)])]))
#                           ),
#                           DeclStmt(
#                               VarDecl(name="c", type=Type(base_type=RecordType("array"), dimension=2), mutable=True,
#                                       initializer=OperatorCall(operator="+", operands=[VarRef("a"), VarRef("b")]))
#                           ),
#                           ExprStmt(
#                               FunctionCall(function=VarRef("print"), arguments=[VarRef("c")])
#                           )
#                       ]))
#
# prog = Program(declarations=[main_fn])

# code = r"""
#     int add(int a, int b) {
#         return a + b;
#     }
#
#     Record Point { x: int, y: int }
#
#     int main() {
#         int x = 10;
#         float y = 3.14;
#         char c = 'a';
#         string s = "Hello, world!";
#
#         Point p = Point(1, 2);
#         p.x = 10;
#
#         bool flag = true;
#         int[2][2] arr = {{1, 2}, {3, 4}};
#         arr[0][0] = 1000;
#         int f = [](int x, int y) { return x + y; };
#
#         int[4][2] arr = {
#             {1, 2},
#             {3, 4},
#             {5, 6},
#             {7, 8}
#         };
#
#         float[2][2][2] cube = {
#             {
#                 {1.0, 2.0},
#                 {3.0, 4.0}
#             },
#             {
#                 {5.0, 6.0},
#                 {7.0, 8.0}
#             }
#         };
#
#         cube = cube + 10;
#
#         if (x < y) {
#             x = x + 1;
#         } else {
#             x = x - 1;
#         }
#
#         while (x < 20) {
#             x = x + 2;
#         }
#
#         int result = add(x, 5);
#         return arr[0][0];
#     }
#     """

code = r"""
    int main() {
        int[2][2] arr = {{1, 2}, {3, 4}};
        arr[0][0] = 1000;
        return arr[0][0];
    }
"""

# Tokenize
tokens = tokenize(code)

# Parse
prog = Parser(tokens).parse()

# prog = Program(declarations=[main_fn])
interp = Interpreter(prog)
global_frame = interp.run()

call = FunctionCall(function=VarRef("main"), arguments=[])
print(interp.eval_expression(call, global_frame))
