from ..ast_nodes import *
from .tokenizer import tokenize
from .parser import Parser

class PrettyPrinter:
    def __init__(self):
        self.indent_level = 0
        self.indent_str = "    "  # 4 spaces
        self._in_vardecl = False

    def infer_array_dimensions(self, array_literal):
        """Recursively infer array dimension sizes from nested ArrayLiterals."""
        dims = []
        current = array_literal
        while isinstance(current, ArrayLiteral):
            dims.append(len(current.value))
            # Go deeper only if all elements are arrays
            if all(isinstance(v, ArrayLiteral) for v in current.value):
                current = current.value[0]
            else:
                break
        return dims

    def indent(self):
        self.indent_level += 1

    def dedent(self):
        self.indent_level = max(0, self.indent_level - 1)

    def write_indent(self) -> str:
        return self.indent_str * self.indent_level

    # ------------------------
    # Entry point
    # ------------------------
    def pprint(self, node) -> str:
        if isinstance(node, Program):
            return "\n".join(self.pprint(decl) for decl in node.declarations)

        elif isinstance(node, FunctionDef):
            ret_type = node.return_type
            if isinstance(ret_type.base_type, FunctionType):
                # Extract the true return type from the function type
                ret_type = ret_type.base_type.return_type

            params = ", ".join(f"{self.pprint(param.type)} {param.name}" for param in node.params)
            body = self.pprint(node.body)
            return f"{self.pprint(ret_type)} {node.name}({params}) {body}"


        elif isinstance(node, VarDecl):
            # Base type
            base_type_str = self.pprint(node.type.base_type)

            # Try to infer array dimensions if it's an array and has an initializer
            if node.type.dimension > 0 and isinstance(node.initializer, ArrayLiteral):
                dims = self.infer_array_dimensions(node.initializer)
                dim_str = "".join(f"[{d}]" for d in dims)
                s = f"{base_type_str}{dim_str} {node.name}"
            else:
                s = f"{self.pprint(node.type)} {node.name}"

            # Initializer
            if node.initializer:
                s += f" = {self.pprint(node.initializer)}"
            s += ";"

            return s


        elif isinstance(node, RecordTypeDecl):
            # Print as "Record Point { x, y }"
            field_names = ", ".join(f.name for f in node.fields)
            return f"Record {node.name} {{ {field_names} }}"

        elif isinstance(node, PrimitiveType):
            return node.name

        elif isinstance(node, RecordType):
            return node.name

        elif isinstance(node, Block):
            s = "{\n"
            self.indent()
            count = len(node.statements)

            for i, stmt in enumerate(node.statements):
                is_last = (i == count - 1)
                # Automatically return the last expression if it's ExprStmt
                if is_last and isinstance(stmt, ExprStmt):
                    s += self.write_indent() + "return " + self.pprint(stmt.expression) + ";\n"
                else:
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
            # Pretty-print nested arrays with indentation
            if all(isinstance(v, ArrayLiteral) for v in node.value):
                s = "{\n"
                self.indent()
                lines = []
                for v in node.value:
                    lines.append(self.write_indent() + self.pprint(v))
                s += ",\n".join(lines) + "\n"
                self.dedent()
                s += self.write_indent() + "}"
                return s
            else:
                elems = ", ".join(self.pprint(v) for v in node.value)
                return "{" + elems + "}"

        elif isinstance(node, RecordLiteral):
            fields = ", ".join(f"{k}: {self.pprint(v)}" for k, v in node.field_values.items())
            return f"{node.type} {{ {fields} }}"

        elif isinstance(node, LambdaLiteral):
            params = ", ".join(f"{self.pprint(p.type)} {p.name}" for p in node.params)
            body = self.pprint(node.body)
            return f"[]({params}) {body}"



        elif isinstance(node, VarDecl):
            self._in_vardecl = True

            # Base type
            base_type_str = self.pprint(node.type.base_type)
            if node.type.dimension > 0 and isinstance(node.initializer, ArrayLiteral):
                dims = self.infer_array_dimensions(node.initializer)
                dim_str = "".join(f"[{d}]" for d in dims)
                s = f"{base_type_str}{dim_str} {node.name}"
            else:
                s = f"{self.pprint(node.type)} {node.name}"
            if node.initializer:
                s += f" = {self.pprint(node.initializer)}"

            s += ";"
            self._in_vardecl = False

            return s



if __name__ == '__main__':
    code = """
    int add(int a, int b) {
        return a + b;
    }

    int main() {
        int x = 10;
        float y = 3.14;
        bool flag = true;
        int[2][2] arr = {{1, 2}, {3, 4}};
        auto f = [](int x, int y) { return x + y; };
        Point p = Point { x: 1, y: 2 };
        
        Record Point { x, y }
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
