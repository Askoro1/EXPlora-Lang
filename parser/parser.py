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
        """Parse nested { ... } array literals for multi-dimensional arrays."""
        self.expect(TokenType.OP, "{")
        values = []

        if not self.accept(TokenType.OP, "}"):
            while True:
                if self.peek().type == TokenType.OP and self.peek().value == "{":
                    # Nested array literal
                    values.append(self.parse_array_literal())
                else:
                    # Regular element (number, variable, etc.)
                    values.append(self.parse_expression())
                if self.accept(TokenType.OP, "}"):
                    break
                self.expect(TokenType.OP, ",")

        return ArrayLiteral(value=values)

    def parse_declaration(self):
        # --- parse base type ---
        ttype = self.parse_type()
        name_token = self.expect(TokenType.ID)
        name = name_token.value

        # --- parse array dimensions after variable name ---
        array_dims = []
        while self.accept(TokenType.OP, "["):
            if self.peek().type == TokenType.NUMBER:
                size_token = self.next()
                array_dims.append(int(size_token.value))
            else:
                array_dims.append(None)
            self.expect(TokenType.OP, "]")

        # attach dimensions if any
        if array_dims:
            # If type already has dimensions (e.g. int[3] arr[4][5]), combine them
            if isinstance(ttype.dimension, list):
                ttype.dimension.extend(array_dims)
            else:
                ttype.dimension = array_dims

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

        # --- variable initializer ---
        init = None
        if self.accept(TokenType.OP, "="):
            # Check for record literal: Type { ... }
            if self.peek().type == TokenType.ID and self.pos + 1 < len(self.tokens) and \
                    self.tokens[self.pos + 1].type == TokenType.OP and self.tokens[self.pos + 1].value == "{":
                typename = self.next().value
                init = self.parse_record_literal(typename)
            elif self.peek().type == TokenType.OP and self.peek().value == "{":
                init = self.parse_array_literal()
            else:
                init = self.parse_expression()

        self.expect(TokenType.OP, ";")

        # --- handle 'auto' ---
        if isinstance(ttype.base_type, PrimitiveType) and ttype.base_type.name == "auto":
            if init is None:
                raise ParserError(f"'auto' variable '{name}' must have an initializer at pos {name_token.pos}")
            ttype = Type(PrimitiveType("auto"), 0)

        return VarDecl(name=name, type=ttype, mutable=True, initializer=init)

    def parse_type(self):
        t = self.peek()
        if t.type == TokenType.KW and t.value in {"int", "float", "bool", "char", "unit", "auto"}:
            self.next()
            base = PrimitiveType(t.value)
        elif t.type == TokenType.ID:
            name = self.next().value
            base = RecordType(name)
        else:
            raise ParserError(f"Unknown type {t.value} at pos {t.pos}")

        # --- multi-dimensional array support ---
        dims = []
        while self.accept(TokenType.OP, "["):
            if self.peek().type == TokenType.NUMBER:
                size = int(self.next().value)
                dims.append(size)
            else:
                dims.append(None)  # e.g. int arr[][5];
            self.expect(TokenType.OP, "]")

        if dims:
            return Type(base_type=base, dimension=dims)
        return Type(base_type=base, dimension=[])

    def parse_lambda_literal(self):
        # Parse [] (...) -> type { ... }
        self.expect(TokenType.OP, "[")
        self.expect(TokenType.OP, "]")

        self.expect(TokenType.OP, "(")
        params = []
        if not self.accept(TokenType.OP, ")"):
            while True:
                ptype = self.parse_type()
                pname = self.expect(TokenType.ID).value
                params.append(VarDecl(name=pname, type=ptype, mutable=False))
                if self.accept(TokenType.OP, ")"):
                    break
                self.expect(TokenType.OP, ",")

        rettype = Type(PrimitiveType("unit"), 0)
        if self.accept(TokenType.OP, "->"):
            rettype = self.parse_type()

        body = self.parse_block()
        return LambdaLiteral(params=params, body=body)


    def parse_record_literal(self, typename: str):
        # Parse Type { field: value, ... }
        self.expect(TokenType.OP, "{")
        fields = {}
        if not self.accept(TokenType.OP, "}"):
            while True:
                field_name = self.expect(TokenType.ID).value
                self.expect(TokenType.OP, ":")
                field_val = self.parse_expression()
                fields[field_name] = field_val
                if self.accept(TokenType.OP, "}"):
                    break
                self.expect(TokenType.OP, ",")

        return RecordLiteral(type=typename, field_values=fields)

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

        # Handle declarations: primitive or user-defined types
        if (t.type == TokenType.KW and t.value in {"int", "float", "bool", "char", "unit", "auto"}) \
                or (t.type == TokenType.ID):
            # Peek ahead: if next token is ID, this is a declaration
            if self.tokens[self.pos + 1].type == TokenType.ID:
                return self.parse_declaration()

        # Handle control flow
        if t.type == TokenType.KW:
            if t.value == "if":
                return self.parse_if()
            elif t.value == "while":
                return self.parse_while()
            elif t.value == "return":
                self.next()
                expr = None
                if self.peek().type != TokenType.OP or self.peek().value != ";":
                    expr = self.parse_expression()
                self.expect(TokenType.OP, ";")
                return ExprStmt(expr)

        # Block
        if t.type == TokenType.OP and t.value == "{":
            return self.parse_block()

        # Otherwise, expression statement
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
        if tok.type == TokenType.KW and tok.value == "auto":
            raise ParserError(f"Unexpected 'auto' at pos {tok.pos} — it should only appear at start of a declaration")
        elif tok.type == TokenType.NUMBER:
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
            # Record literal: Type { ... }
            if self.peek().type == TokenType.OP and self.peek().value == "{":
                record = self.parse_record_literal(tok.value)
                return record
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
        elif tok.type == TokenType.OP and tok.value == "[":
            return self.parse_lambda_literal()
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
        
        int matrix[3][3] = {
            {1, 2, 3},
            {4, 5, 6},
            {7, 8, 9}
        };
        
        float cube[2][2][2] = {
            {
                {1.0, 2.0},
                {3.0, 4.0}
            },
            {
                {5.0, 6.0},
                {7.0, 8.0}
            }
        };
                
        auto f = [](int x, int y) {
            return x + y;
        };
        
        Point p = Point { x: 1, y: 2 };

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
