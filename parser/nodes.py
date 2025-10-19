from dataclasses import dataclass
from typing import Optional


# Top-level container
@dataclass
class Program:
    declarations: list['Declaration']


# Declarations & Definitions
@dataclass
class VarDecl:
    name: str
    type: 'Type'
    mutable: bool
    initializer: Optional['Expression'] = None


# I thought about it some more, and you are welcome to use VarDecl + LambdaLiteral instead.
@dataclass
class FunctionDef:
    name: str
    # Parameters with initializers do not need to be supported.
    # You may choose to make all parameters immutable.
    params: list[VarDecl]
    return_type: 'Type'
    body: 'Expression'


@dataclass
class RecordTypeDecl:
    name: str
    fields: list[VarDecl]


Declaration = FunctionDef | VarDecl | RecordTypeDecl


# Types
@dataclass
class PrimitiveType:
    name: str  # unit, int, float, bool, etc.


@dataclass
class RecordType:
    name: str


@dataclass
class FunctionType:
    param_types: list['Type']
    return_type: 'Type'


BaseType = PrimitiveType | RecordType | FunctionType

@dataclass
class Type:
    base_type: BaseType
    dimension: int


# Statements
@dataclass
class Assignment:
    lvalue: 'PlaceExpression'
    rvalue: 'Expression'


@dataclass
class WhileLoop:
    condition: 'Expression'
    body: 'Statement'


@dataclass
class DeclStmt:
    # No need to support record type declarations.
    declaration: Declaration


@dataclass
class ExprStmt:
    expression: 'Expression'


Statement = Assignment | WhileLoop | DeclStmt | ExprStmt


# Place expressions
@dataclass
class VarRef:
    name: str


@dataclass
class FieldRef:
    record: 'Expression'
    field_name: str


PlaceExpression = VarRef | FieldRef


# Expressions
@dataclass
class PrimitiveLiteral:
    value: int | float | bool


@dataclass
class ArrayLiteral:
    value: list['Expression']


@dataclass
class LambdaLiteral:
    params: list[VarDecl]
    body: 'Expression'


@dataclass
class RecordLiteral:
    type: str
    field_values: dict[str, 'Expression']


Literal = PrimitiveLiteral | ArrayLiteral | LambdaLiteral | RecordLiteral


@dataclass
class FunctionCall:
    function: 'Expression'
    arguments: list['Expression']


@dataclass
class OperatorCall:
    operator: str
    operands: list['Expression']


@dataclass
class Block:
    # Final statement is the result of the block, if it is an expression statement.
    statements: list[Statement]


@dataclass
class IfExpr:
    condition: 'Expression'
    then_expr: 'Expression'
    else_expr: 'Expression'


Expression = Literal | PlaceExpression | FunctionCall | OperatorCall | Block | IfExpr