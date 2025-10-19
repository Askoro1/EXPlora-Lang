from typing import List, Optional
from nodes import *
from tokenizer import Token, TokenType, tokenize
from pprint import pprint

class ParserError(Exception):
    """Custom exception for parser errors."""
    pass

# ------------------------
# Parser
# ------------------------
class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    # ------------------------
    # Token utilities
    # ------------------------
    def peek(self) -> Token:
        return self.tokens[self.pos]

    def next(self) -> Token:
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def expect(self, typ: TokenType, value: str = None) -> Token:
        t = self.peek()
        if t.type != typ:
            raise ParserError(f"Expected {typ}, got {t.type} at pos {t.pos}")
        if value is not None and t.value != value:
            raise ParserError(f"Expected {value}, got {t.value} at pos {t.pos}")
        return self.next()

    def accept(self, typ: TokenType, value: str = None) -> Optional[Token]:
        t = self.peek()
        if t.type == typ and (value is None or t.value == value):
            return self.next()
        return None

    # ------------------------
    # Program / Declarations
    # ------------------------
    def parse(self) -> Program:
        decls = []
        while self.peek().type != TokenType.EOF:
            decls.append(self.parse_declaration())
        return Program(declarations=decls)

    def parse_array_literal(self):
        """Parse {1, 2, 3} style array literals."""
        self.expect(TokenType.OP, "{")
        values = []

        if not self.accept(TokenType.OP, "}"):
            while True:
                values.append(self.parse_expression())
                if self.accept(TokenType.OP, "}"):
                    break
                self.expect(TokenType.OP, ",")

        return ArrayLiteral(value=values)

    def parse_declaration(self):
        # Parse base type
        ttype = self.parse_type()
        name_token = self.expect(TokenType.ID)
        name = name_token.value

        # --- NEW: parse possible array dimensions like arr[5][10]
        array_dims = []
        while self.accept(TokenType.OP, "["):
            if self.peek().type == TokenType.NUMBER:
                size_token = self.next()
                array_dims.append(int(size_token.value))
            else:
                array_dims.append(None)
            self.expect(TokenType.OP, "]")

        # If there are dimensions, wrap the type
        if array_dims:
            ttype = Type(base_type=ttype, dimension=array_dims)

        # --- function declaration ---
        if self.accept(TokenType.OP, "("):
            params = []
            if not self.accept(TokenType.OP, ")"):
                while True:
                    param_type = self.parse_type()
                    param_name = self.expect(TokenType.ID).value
                    params.append(VarDecl(name=param_name, type=param_type, mutable=False))
                    if self.accept(TokenType.OP, ")"):
                        break
                    self.expect(TokenType.OP, ",")
            body = self.parse_block()
            return FunctionDef(return_type=ttype, name=name, params=params, body=body)

        # --- variable declaration ---
        else:
            init = None
            if self.accept(TokenType.OP, "="):
                # --- NEW: handle array initializer ---
                if self.peek().type == TokenType.OP and self.peek().value == "{":
                    init = self.parse_array_literal()
                else:
                    init = self.parse_expression()
            self.expect(TokenType.OP, ";")
            return VarDecl(name=name, type=ttype, mutable=True, initializer=init)

    def parse_type(self):
        t = self.peek()
        if t.type == TokenType.KW and t.value in {"int", "float", "bool", "char", "unit"}:
            self.next()
            base = PrimitiveType(t.value)
        elif t.type == TokenType.ID:
            name = self.next().value
            base = RecordType(name)
        else:
            raise ParserError(f"Unknown type {t.value} at pos {t.pos}")

        dim = 0
        while self.accept(TokenType.OP, "["):
            if self.peek().type == TokenType.NUMBER:
                self.next()  # skip number (you could store this size too)
            self.expect(TokenType.OP, "]")
            dim += 1

        return Type(base_type=base, dimension=dim)

    # ------------------------
    # Statements
    # ------------------------
    def parse_block(self) -> Block:
        self.expect(TokenType.OP, "{")
        stmts = []
        while not self.accept(TokenType.OP, "}"):
            if self.peek().type == TokenType.EOF:
                raise ParserError("Unterminated block")
            stmts.append(self.parse_statement())
        return Block(statements=stmts)

    def parse_statement(self):
        t = self.peek()

        if t.type == TokenType.KW:
            if t.value == "if":
                return self.parse_if()
            elif t.value == "while":
                return self.parse_while()
            elif t.value == "return":  # <- new handling
                self.next()
                expr = None
                if self.peek().type != TokenType.OP or self.peek().value != ";":
                    expr = self.parse_expression()
                self.expect(TokenType.OP, ";")
                # treat return like an expression statement
                return ExprStmt(expr)
            elif t.value in {"int", "float", "bool", "char"}:
                return self.parse_declaration()

        if t.type == TokenType.OP and t.value == "{":
            return self.parse_block()

        expr = self.parse_expression()
        self.expect(TokenType.OP, ";")
        return ExprStmt(expr)

    def parse_if(self):
        self.expect(TokenType.KW, "if")
        self.expect(TokenType.OP, "(")
        cond = self.parse_expression()
        self.expect(TokenType.OP, ")")
        then_branch = self.parse_statement()
        else_branch = None
        if self.accept(TokenType.KW, "else"):
            else_branch = self.parse_statement()
        return IfExpr(condition=cond, then_expr=then_branch, else_expr=else_branch)

    def parse_while(self):
        self.expect(TokenType.KW, "while")
        self.expect(TokenType.OP, "(")
        cond = self.parse_expression()
        self.expect(TokenType.OP, ")")
        body = self.parse_statement()
        return WhileLoop(condition=cond, body=body)

    # ------------------------
    # Expressions (recursive precedence)
    # ------------------------
    PRECEDENCE = {
        "=": 1,
        "||": 2,
        "&&": 3,
        "==": 4, "!=": 4,
        "<": 5, "<=": 5, ">": 5, ">=": 5,
        "+": 6, "-": 6,
        "*": 7, "/": 7, "%": 7,
    }
    RIGHT_ASSOC = {"="}

    def parse_expression(self, min_prec=0):
        node = self.parse_primary()

        while True:
            tok = self.peek()
            if tok.type == TokenType.OP and tok.value in self.PRECEDENCE:
                prec = self.PRECEDENCE[tok.value]
                op = tok.value
                if prec < min_prec:
                    break
                self.next()
                rhs = self.parse_expression(prec + (0 if op in self.RIGHT_ASSOC else 1))
                if op == "=":
                    node = Assignment(lvalue=node, rvalue=rhs)
                else:
                    node = OperatorCall(operator=op, operands=[node, rhs])
            else:
                break
        return node

    def parse_primary(self):
        tok = self.peek()
        if tok.type == TokenType.NUMBER:
            self.next()
            val = float(tok.value) if ('.' in tok.value or 'e' in tok.value or 'E' in tok.value) else int(tok.value)
            return PrimitiveLiteral(val)
        elif tok.type == TokenType.STRING:
            self.next()
            return PrimitiveLiteral(tok.value[1:-1])
        elif tok.type == TokenType.CHAR:
            self.next()
            return PrimitiveLiteral(tok.value[1:-1])
        elif tok.type == TokenType.KW and tok.value in {"true", "false"}:
            self.next()
            return PrimitiveLiteral(tok.value == "true")
        elif tok.type == TokenType.ID:
            self.next()
            node: Expression = VarRef(tok.value)
            while True:
                if self.accept(TokenType.OP, "("):
                    args = []
                    if not self.accept(TokenType.OP, ")"):
                        while True:
                            args.append(self.parse_expression())
                            if self.accept(TokenType.OP, ")"):
                                break
                            self.expect(TokenType.OP, ",")
                    node = FunctionCall(function=node, arguments=args)
                    continue
                if self.accept(TokenType.OP, "["):
                    index = self.parse_expression()
                    self.expect(TokenType.OP, "]")
                    node = OperatorCall(operator="[]", operands=[node, index])
                    continue
                break
            return node
        elif tok.type == TokenType.OP and tok.value == "(":
            self.next()
            expr = self.parse_expression()
            self.expect(TokenType.OP, ")")
            return expr
        raise ParserError(f"Unexpected token {tok.type.name}({tok.value}) at pos {tok.pos}")


if __name__ == "__main__":
    code = r"""
    int add(int a, int b) {
        return a + b;
    }

    int main() {
        int x = 10;
        float y = 6.2e-7;
        bool flag = true;
        int arr[5] = {1, 2, 3, 4, 5};

        if (x < 20) {
            x = x + 1;
        } else {
            x = x - 1;
        }

        while (x < 15) {
            x = x + 2;
        }

        int result = add(x, 5);
        return result;
    }
    """

    # Tokenize
    tokens = tokenize(code)

    # Parse
    parser = Parser(tokens)
    ast: Program = parser.parse()

    # Print AST
    pprint(ast)
