from nodes import *
from tokenizer import tokenize
from parser import Parser


class PrettyPrinter:
    def __init__(self):
        self.indent_level = 0
        self.indent_str = "    "  # 4 spaces

    def indent(self):
        self.indent_level += 1

    def dedent(self):
        self.indent_level -= 1
        if self.indent_level < 0:
            self.indent_level = 0

    def write_indent(self) -> str:
        return self.indent_str * self.indent_level

    # ------------------------
    # Entry point
    # ------------------------
    def pprint(self, node) -> str:
        if isinstance(node, Program):
            return "\n".join(self.pprint(decl) for decl in node.declarations)

        elif isinstance(node, FunctionDef):
            params = ", ".join(f"{self.pprint(param.type)} {param.name}" for param in node.params)
            body = self.pprint(node.body)
            return f"{self.pprint(node.return_type)} {node.name}({params}) {body}"

        elif isinstance(node, VarDecl):
            s = f"{self.pprint(node.type)} {node.name}"
            if node.initializer:
                s += f" = {self.pprint(node.initializer)}"
            s += ";"
            return s

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

        elif isinstance(node, ReturnStmt):
            if node.value:
                return f"return {self.pprint(node.value)};"
            else:
                return "return;"

        else:
            raise ValueError(f"Unknown AST node type: {type(node).__name__}")


if __name__ == '__main__':
    code = """
    int add(int a, int b) {
        return a + b;
    }
    
    int main() {
        int x = 10;
        float y = 3.14;
        bool flag = true;
    
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
