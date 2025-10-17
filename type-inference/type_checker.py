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
            first_elem_type = infer_expression_type(value[0], env)

            for element in value[1:]:
                elem_type = infer_expression_type(element, env)
                if elem_type != first_elem_type:
                    raise TypeError(f"Array types are not homogeneous: {first_elem_type}")
                if elem_type.dimension != first_elem_type.dimension:
                    raise TypeError(f"Array elements must have the same dimension: {first_elem_type}")

            return ast_nodes.Type(first_elem_type.base_type, first_elem_type.dimension + 1)

        case ast_nodes.LambdaLiteral(params, body):
            pass

        case ast_nodes.RecordLiteral(typ, field_values):
            for field_name, field_value in field_values.items():
                try:
                    infer_expression_type(field_value, env)
                except:
                    raise TypeError(f"Error inferring type of {field_name}: {field_value}")

            return ast_nodes.Type(ast_nodes.RecordType(typ), 0)

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