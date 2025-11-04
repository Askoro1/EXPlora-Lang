from ..ast_nodes import *
from .tokenizer import tokenize
from .parser import Parser

class PrettyPrinter:
    def __init__(self):
        self.indent_level = 0
        self.indent_str = "    "  # 4 spaces

    def indent(self):
        self.indent_level += 1

    def dedent(self):
        self.indent_level = max(0, self.indent_level - 1)

    def write_indent(self) -> str:
        return self.indent_str * self.indent_level

    def infer_array_dimensions(self, array_literal):
        dims = []
        current = array_literal
        while isinstance(current, ArrayLiteral):
            dims.append(len(current.value))
            if all(isinstance(v, ArrayLiteral) for v in current.value):
                current = current.value[0]
            else:
                break
        return dims

    def pprint(self, node) -> str:
        if isinstance(node, Program):
            return "\n".join(self.pprint(decl) for decl in node.declarations)

        elif isinstance(node, FunctionDef):
            ret_type = self.pprint(node.return_type)
            params = ", ".join(f"{self.pprint(param.type)} {param.name}" for param in node.params)
            body = self.pprint(node.body)
            return f"{ret_type} {node.name}({params}) {body}"

        elif isinstance(node, VarDecl):
            # Lambdas: print declared type, not full function type
            if isinstance(node.initializer, LambdaLiteral) and isinstance(node.type.base_type, FunctionType):
                declared_type = self.pprint(node.type.base_type.return_type)
                s = f"{declared_type} {node.name}"
            else:
                base_type_str = self.pprint(node.type.base_type)
                # Arrays
                if node.type.dimension > 0 and isinstance(node.initializer, ArrayLiteral):
                    dims = self.infer_array_dimensions(node.initializer)
                    dim_str = "".join(f"[{d}]" for d in dims)
                    s = f"{base_type_str}{dim_str} {node.name}"
                else:
                    s = f"{self.pprint(node.type)} {node.name}"

            if node.initializer:
                s += f" = {self.pprint(node.initializer)}"
            s += ";"
            return s

        elif isinstance(node, RecordTypeDecl):
            # Print field names with types
            fields_str = ", ".join(f"{f.name}: {self.pprint(f.type)}" for f in node.fields)
            return f"Record {node.name} {{ {fields_str} }}"

        elif isinstance(node, PrimitiveType):
            return node.name

        elif isinstance(node, RecordType):
            return node.name

        elif isinstance(node, Block):
            s = "{\n"
            self.indent()
            for stmt in node.statements:
                s += self.write_indent() + self.pprint(stmt) + "\n"
            self.dedent()
            s += self.write_indent() + "}"
            return s

        elif isinstance(node, ExprStmt):
            return self.pprint(node.expression) + ";"

        elif isinstance(node, DeclStmt):
            return self.pprint(node.declaration)

        elif isinstance(node, Assignment):
            return f"{self.pprint(node.lvalue)} = {self.pprint(node.rvalue)}"

        elif isinstance(node, OperatorCall):
            if node.operator == "[]":
                return f"{self.pprint(node.operands[0])}[{self.pprint(node.operands[1])}]"
            elif len(node.operands) == 2:
                return f"{self.pprint(node.operands[0])} {node.operator} {self.pprint(node.operands[1])}"
            else:
                return f"{node.operator}({', '.join(self.pprint(op) for op in node.operands)})"

        elif isinstance(node, FunctionCall):
            args = ", ".join(self.pprint(arg) for arg in node.arguments)
            return f"{self.pprint(node.function)}({args})"

        elif isinstance(node, VarRef):
            return node.name

        elif isinstance(node, IfExpr):
            s = f"if ({self.pprint(node.condition)}) {self.pprint(node.then_expr)}"
            if node.else_expr:
                s += f" else {self.pprint(node.else_expr)}"
            return s

        elif isinstance(node, WhileLoop):
            return f"while ({self.pprint(node.condition)}) {self.pprint(node.body)}"

        elif isinstance(node, PrimitiveLiteral):
            if isinstance(node.value, str):
                return f'"{node.value}"'
            elif isinstance(node.value, bool):
                return "true" if node.value else "false"
            else:
                return str(node.value)

        elif isinstance(node, ArrayLiteral):
            if all(isinstance(v, ArrayLiteral) for v in node.value):
                s = "{\n"
                self.indent()
                lines = [self.write_indent() + self.pprint(v) for v in node.value]
                s += ",\n".join(lines) + "\n"
                self.dedent()
                s += self.write_indent() + "}"
                return s
            else:
                return "{" + ", ".join(self.pprint(v) for v in node.value) + "}"

        elif isinstance(node, RecordLiteral):
            fields = ", ".join(f"{k}: {self.pprint(v)}" for k, v in node.field_values.items())
            return f"{node.type} {{ {fields} }}"

        elif isinstance(node, LambdaLiteral):
            params = ", ".join(f"{self.pprint(p.type)} {p.name}" for p in node.params)
            body = self.pprint(node.body)
            return f"[]({params}) {body}"

        elif isinstance(node, Type):
            if isinstance(node.base_type, FunctionType):
                ret_type_str = self.pprint(node.base_type.return_type)
                param_strs = [self.pprint(t) for t in node.base_type.param_types]
                s = f"{ret_type_str}({', '.join(param_strs)})"
            else:
                s = self.pprint(node.base_type)

            if isinstance(node.dimension, int) and node.dimension > 0:
                s += "[]" * node.dimension
            return s

        else:
            raise ValueError(f"Unknown AST node type: {type(node).__name__}")



if __name__ == '__main__':
    code = """
    int add(int a, int b) {
        return a + b;
    }
    
    Record Point { x: int, y: int };

    int main() {
        int x = 10;
        float y = 3.14;
        bool flag = true;
        int[2][2] arr = {{1, 2}, {3, 4}};
        int f = [](int x, int y) { return x + y; };
    
        Point p = Point(1, 2);
        
        int[4][2] arr = {
            {1, 2},
            {3, 4},
            {5, 6},
            {7, 8}
        };
        
        float[2][2][2] cube = {
            {
                {1.0, 2.0},
                {3.0, 4.0}
            },
            {
                {5.0, 6.0},
                {7.0, 8.0}
            }
        };

        if (x < y) {
            x = x + 1;
        } else {
            x = x - 1;
        }

        while (x < 20) {
            x = x + 2;
        }

        int result = add(x, 5);
        return result;
    }
    """

    tokens = tokenize(code)
    parser = Parser(tokens)
    ast = parser.parse()

    printer = PrettyPrinter()
    pretty_code = printer.pprint(ast)
    print(pretty_code)
