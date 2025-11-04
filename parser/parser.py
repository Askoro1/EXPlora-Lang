from typing import List, Optional
from ..ast_nodes import *
from .tokenizer import Token, TokenType, tokenize
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
        self.record_defs = {}

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
            tok = self.peek()
            if tok.type == TokenType.KW and tok.value == "Record":
                decls.append(self.parse_record_type_decl())
            else:
                decls.append(self.parse_declaration())
        return Program(declarations=decls)

    def parse_array_literal(self):
        """Parse nested { ... } array literals for multidimensional arrays."""
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
        ttype = self.parse_type()
        name_token = self.expect(TokenType.ID)
        name = name_token.value

        # Function declaration
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
            return FunctionDef(name, params, ttype, body)

        # Variable initializer
        init = None
        if self.accept(TokenType.OP, "="):
            # --- Detect lambda initializer ---
            if (self.peek().type == TokenType.OP and self.peek().value == "[" and
                    self.pos + 1 < len(self.tokens) and
                    self.tokens[self.pos + 1].type == TokenType.OP and
                    self.tokens[self.pos + 1].value == "]"):
                init, lambda_type = self.parse_lambda_literal(declared_type=ttype)
            # Array literal
            elif self.peek().type == TokenType.OP and self.peek().value == "{":
                init = self.parse_array_literal()
            # Record literal
            elif self.peek().type == TokenType.ID and self.pos + 1 < len(self.tokens) and \
                    self.tokens[self.pos + 1].type == TokenType.OP and self.tokens[self.pos + 1].value == "{":
                typename = self.next().value
                init = self.parse_record_literal(typename)
            else:
                init = self.parse_expression()

        self.expect(TokenType.OP, ";")
        if isinstance(init, LambdaLiteral):
            var_type = lambda_type  # declared type wrapped as FunctionType
        else:
            var_type = ttype

        return VarDecl(name=name, type=var_type, mutable=True, initializer=init)

    def parse_type(self):
        t = self.peek()
        if t.type == TokenType.KW and t.value in {"int", "float", "bool", "char", "unit", "auto"}:
            self.next()
            base = PrimitiveType(t.value)
        elif t.type == TokenType.ID:
            name = self.next().value
            if name in self.record_defs:
                base = RecordType(name)
            else:
                # fallback: unknown type is still treated as RecordType
                base = RecordType(name)
        else:
            raise ParserError(f"Unknown type {t.value} at pos {t.pos}")

        # --- multi-dimensional array support ---
        dimension = []
        while self.accept(TokenType.OP, "["):
            size = None
            if self.peek().type == TokenType.NUMBER:
                size = int(self.next().value)
            self.expect(TokenType.OP, "]")
            dimension.append(size)

        if dimension:
            return Type(base_type=base, dimension=len(dimension))
        return Type(base_type=base, dimension=0)

    def parse_lambda_literal(self, declared_type: Type):
        self.expect(TokenType.OP, "[")
        self.expect(TokenType.OP, "]")

        # Parse params
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

        body = self.parse_block()

        # Use the declared type as return type
        param_types = [p.type for p in params]
        lambda_type = Type(
            base_type=FunctionType(param_types=param_types, return_type=declared_type),
            dimension=0
        )

        literal = LambdaLiteral(params=params, body=body)
        return literal, lambda_type


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

        # Handle record declarations inside functions
        if t.type == TokenType.KW and t.value == "Record":
            decl = self.parse_record_type_decl()
            return DeclStmt(declaration=decl)

        # Variable declarations
        if (t.type == TokenType.KW and t.value in {"int", "float", "bool", "char", "unit", "auto"}) \
                or (t.type == TokenType.ID):
            # Look ahead to see if this is a declaration
            i = self.pos + 1
            while i < len(self.tokens) and self.tokens[i].type == TokenType.OP and self.tokens[i].value == "[":
                i += 1
                while i < len(self.tokens) and not (
                        self.tokens[i].type == TokenType.OP and self.tokens[i].value == "]"):
                    i += 1
                i += 1
            if i < len(self.tokens) and self.tokens[i].type == TokenType.ID:
                decl = self.parse_declaration()
                return DeclStmt(declaration=decl)

        # Control flow and blocks
        if t.type == TokenType.KW:
            if t.value == "if":
                if_expr = self.parse_if()
                return ExprStmt(if_expr)  # wrap IfExpr
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
            block = self.parse_block()
            return ExprStmt(block)  # wrap Block in ExprStmt

        # Otherwise, normal expression
        expr = self.parse_expression()
        self.expect(TokenType.OP, ";")

        # wrap everything in ExprStmt except Assignment
        if isinstance(expr, Assignment):
            return expr
        else:
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
        # --- Detect lambda literal early ---
        if (self.peek().type == TokenType.OP and self.peek().value == "[" and
                self.pos + 1 < len(self.tokens) and
                self.tokens[self.pos + 1].type == TokenType.OP and
                self.tokens[self.pos + 1].value == "]"):
            return self.parse_lambda_literal()

        # --- Otherwise, normal expression parsing ---
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
            return PrimitiveLiteral(ord(tok.value[1:-1]))

        elif tok.type == TokenType.CHAR:
            self.next()
            return PrimitiveLiteral(ord(tok.value[1:-1]))

        elif tok.type == TokenType.KW and tok.value in {"true", "false"}:
            self.next()
            return PrimitiveLiteral(tok.value == "true")

        elif tok.type == TokenType.ID:
            self.next()
            node: Expression = VarRef(tok.value)
            # Record literal: Type { ... }
            if self.peek().type == TokenType.OP and self.peek().value == "{":
                return self.parse_record_literal(tok.value)
            # Function calls and indexing
            while True:
                if self.accept(TokenType.OP, "("):
                    args = []
                    if not self.accept(TokenType.OP, ")"):
                        while True:
                            args.append(self.parse_expression())
                            if self.accept(TokenType.OP, ")"):
                                break
                            self.expect(TokenType.OP, ",")

                    # ✅ Record constructor call handling
                    if isinstance(node, VarRef) and node.name in self.record_defs:
                        field_names = self.record_defs[node.name]
                        if len(args) != len(field_names):
                            raise ParserError(
                                f"Record '{node.name}' expects {len(field_names)} fields, "
                                f"got {len(args)} at pos {tok.pos}"
                            )
                        field_values = {field: arg for field, arg in zip(field_names, args)}
                        node = RecordLiteral(type=node.name, field_values=field_values)
                    else:
                        node = FunctionCall(function=node, arguments=args)
                    continue
                break
            return node

        # ✅ Handle lambdas early and clearly
        elif tok.type == TokenType.OP and tok.value == "[":
            # Make sure it’s a lambda like [](...)
            # (don’t eat tokens blindly if it’s array indexing)
            next_tok = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if next_tok and next_tok.type == TokenType.OP and next_tok.value == "]":
                return self.parse_lambda_literal()
            else:
                # Probably an array index, not a lambda
                raise ParserError(f"Unexpected '[' at pos {tok.pos}")

        elif tok.type == TokenType.OP and tok.value == "(":
            self.next()
            expr = self.parse_expression()
            self.expect(TokenType.OP, ")")
            return expr

        raise ParserError(f"Unexpected token {tok.type.name}({tok.value}) at pos {tok.pos}")

    def parse_record_type_decl(self):
        self.expect(TokenType.KW, "Record")
        name_token = self.expect(TokenType.ID)
        name = name_token.value

        self.expect(TokenType.OP, "{")
        fields = []

        if not self.accept(TokenType.OP, "}"):
            while True:
                field_name = self.expect(TokenType.ID).value

                # Check for explicit type
                if self.accept(TokenType.OP, ":"):
                    field_type = self.parse_type()
                else:
                    field_type = Type(PrimitiveType("auto"), 0)

                fields.append(VarDecl(name=field_name, type=field_type, mutable=False))

                if self.accept(TokenType.OP, "}"):
                    break
                self.expect(TokenType.OP, ",")

        self.accept(TokenType.OP, ";")  # optional semicolon

        # Store field names in registry for record literals
        self.record_defs[name] = [f.name for f in fields]

        return RecordTypeDecl(name=name, fields=fields)


if __name__ == "__main__":
    code = r"""
    int add(int a, int b) {
        return a + b;
    }
    
    Record Point { x: int, y: int }

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

    # Tokenize
    tokens = tokenize(code)

    # Parse
    parser = Parser(tokens)
    ast: Program = parser.parse()

    # Print AST
    pprint(ast)
