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
            if isinstance(value, bool):
                return ast_nodes.Type(ast_nodes.PrimitiveType("bool"), 0)
            elif isinstance(value, int):
                return ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0)
            elif isinstance(value, float):
                return ast_nodes.Type(ast_nodes.PrimitiveType("float"), 0)
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
                except TypeError:
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
            block_env = env.copy()
            last_type = ast_nodes.Type(ast_nodes.PrimitiveType("unit"), 0)

            for stmt in statements:
                match stmt:
                    case ast_nodes.ExprStmt(expression):
                        last_type = infer_expression_type(expression, block_env)

                    case ast_nodes.Assignment(lvalue, rvalue):
                        match lvalue:
                            case ast_nodes.VarRef(name):
                                if name not in block_env:
                                    raise TypeError(f"Variable '{name}' not declared before assignment")
                                ltype = block_env[name]
                            case ast_nodes.FieldRef():
                                ltype = infer_expression_type(lvalue, block_env)
                            case _:
                                raise TypeError("Invalid assignment target")

                        rtype = infer_expression_type(rvalue, block_env)
                        if (ltype.base_type != rtype.base_type) or (ltype.dimension != rtype.dimension):
                            raise TypeError(f"Assignment mismatch: {ltype} vs {rtype}")

                        last_type = ast_nodes.Type(ast_nodes.PrimitiveType("unit"), 0)

                    case ast_nodes.DeclStmt(declaration):
                        match declaration:
                            case ast_nodes.VarDecl(name, type_, mutable, initializer):
                                init_type = infer_expression_type(initializer, block_env) if initializer else None
                                if type_ and init_type and (
                                        init_type.base_type != type_.base_type or init_type.dimension != type_.dimension
                                ):
                                    raise TypeError(f"Initializer type mismatch for '{name}': {init_type} vs {type_}")
                                var_type = type_ or init_type
                                if var_type is None:
                                    raise TypeError(f"Cannot determine type of variable '{name}'")
                                block_env[name] = var_type

                            case ast_nodes.RecordTypeDecl(name, fields):
                                for field in fields:
                                    if field.type is None:
                                        raise TypeError(f"Field '{field.name}' in record '{name}' has no type")
                                    if field.initializer:
                                        infer_expression_type(field.initializer, block_env)
                                block_env[name] = ast_nodes.Type(ast_nodes.RecordType(name), 0)

                            case ast_nodes.FunctionDef():
                                pass

                    case ast_nodes.WhileLoop(condition, body):
                        cond_type = infer_expression_type(condition, block_env)
                        if not (isinstance(cond_type.base_type, ast_nodes.PrimitiveType)
                                and cond_type.base_type.name == "bool"
                                and cond_type.dimension == 0):
                            raise TypeError(f"While condition must be bool, got {cond_type}")
                        # assume body is a Block expression node
                        infer_expression_type(body, block_env)
                        last_type = ast_nodes.Type(ast_nodes.PrimitiveType("unit"), 0)

                    case _:
                        raise TypeError(f"Unsupported statement in block: {stmt}")

            return last_type

        case ast_nodes.IfExpr(condition, then_expr, else_expr):
            condition_type = infer_expression_type(condition, env)

            if not (isinstance(condition_type.base_type, ast_nodes.PrimitiveType)
                    and condition_type.base_type.name == "bool"
                    and condition_type.dimension == 0):
                raise TypeError(f"The condition of the if-expression must be of type bool, but it is {condition_type} instead.")

            then_expr_type = infer_expression_type(then_expr, env)
            else_expr_type = infer_expression_type(else_expr, env)

            if then_expr_type.base_type != else_expr_type.base_type:
                raise TypeError(f"Branches must match types: {then_expr_type.base_type} | {else_expr_type.base_type}")
            elif else_expr_type.dimension != then_expr_type.dimension:
                raise TypeError(f"Branches must match dimensions: {then_expr_type.dimension} | {else_expr_type.dimension}")

            return ast_nodes.Type(then_expr_type.base_type, then_expr_type.dimension)

        case _:
            raise TypeError(f"Unexpected expression type: {type(expr)}")