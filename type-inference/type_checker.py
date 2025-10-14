import ast_nodes

# Takes the Abstract Syntax Tree (AST) as input, produces a Typed Abstract Syntax Tree (TAST) as output.

"""
Takes an expression as input and returns its type as output.

Args:
  expr: ast_nodes.Expression - The expression in question. 
  env: dict[str, ast_nodes.Type] - The 

Returns:
  ast_nodes.Type: The type of the expression.
"""
def infer_expression_type(expr: ast_nodes.Expression, env: dict[str, ast_nodes.Type]) -> ast_nodes.Type:
    # Check which expression type we are dealing with
    match expr:
        case ast_nodes.PrimitiveLiteral(value):
            if isinstance(value, int):
                return ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0)
            elif isinstance(value, float):
                return ast_nodes.Type(ast_nodes.PrimitiveType("float"), 0)
            elif isinstance(value, bool):
                return ast_nodes.Type(ast_nodes.PrimitiveType("bool"), 0)
            else:
                raise TypeError(f"Unexpected expression type: {type(expr)}")

        case ast_nodes.ArrayLiteral(value):

            pass
        case ast_nodes.LambdaLiteral(params, body):

            pass
        case ast_nodes.RecordLiteral(typ, field_values):
            pass

        case ast_nodes.VarRef(name):
            if name not in env:
                raise TypeError(f"Variable name '{name}' is not in the environment.")
            return env[name]

        case ast_nodes.FieldRef(record, field_name):
            pass

        case ast_nodes.FunctionCall(function, arguments):
            pass

        case ast_nodes.OperatorCall(operator, operands):
            pass

        case ast_nodes.Block(statements):
            pass

        case ast_nodes.IfExpr(condition=condition, then_expr, else_expr):
            pass

        case _:
            raise TypeError(f"Unexpected expression type: {type(expr)}")