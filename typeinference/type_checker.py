import ast_nodes

"""
Takes an expression as input and returns its type as output.

Args:
  expr: ast_nodes.Expression - The expression in question. 
  env: dict[str, ast_nodes.Type] - The environment where program variables are recorded. 

Returns:
  ast_nodes.Type: The type of the expression.
"""
def infer_expression_type(expr: ast_nodes.Expression, env: dict[str, ast_nodes.Type]) -> ast_nodes.Type:
    # Check which expression type we are dealing with
    match expr:
        # Primitive types are just returned
        case ast_nodes.PrimitiveLiteral(value):
            if isinstance(value, bool):
                return ast_nodes.Type(ast_nodes.PrimitiveType("bool"), 0)
            elif isinstance(value, int):
                return ast_nodes.Type(ast_nodes.PrimitiveType("int"), 0)
            elif isinstance(value, float):
                return ast_nodes.Type(ast_nodes.PrimitiveType("float"), 0)
            else:
                raise TypeError(f"Unexpected expression type: {type(expr)}")

        # Check if all array elements are the same type, then return that type
        # and dimension_size + 1 (since an array of scalars is a vector, array
        # of vectors is a matrix, etc.
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
            # Assume parameters already have typed due to the partially typed AST
            for p in params:
                if p.type is None:
                    raise TypeError(f"Lambda parameter '{p.name}' must have an explicit type")

            # Local environment for the lambda function
            lambda_env = env.copy()
            for p in params:
                lambda_env[p.name] = p.type

            # Infer the return type from the body expression
            body_type = infer_expression_type(body, lambda_env)

            # Build the return type from parameter and return types
            fn_base = ast_nodes.FunctionType(
                param_types=[p.type for p in params],
                return_type=body_type
            )

            return ast_nodes.Type(fn_base, 0)

        case ast_nodes.RecordLiteral(record_name, field_values):
            # Check that each record field type is valid
            for field_name, field_value in field_values.items():
                try:
                    infer_expression_type(field_value, env)
                except TypeError:
                    raise TypeError(f"Error inferring type of {field_name}: {field_value}")

            return ast_nodes.Type(ast_nodes.RecordType(record_name), 0)

        case ast_nodes.VarRef(name):
            if name not in env:
                raise TypeError(f"Variable name '{name}' is not in the environment.")
            return env[name]

        case ast_nodes.FieldRef(record, field_name):
            record_type = infer_expression_type(record, env)
            if not isinstance(record_type.base_type, ast_nodes.RecordType):
                raise TypeError(f"Cannot access field '{field_name}' on non-record type {record_type}")

            record_name = record_type.base_type.name
            if record_name not in env or not isinstance(env[record_name].base_type, ast_nodes.RecordType):
                raise TypeError(f"Unknown record type: {record_name}")

            # The record declaration must be in the environment
            record_decl = env[record_name]
            fields = record_decl.base_type.fields if hasattr(record_decl.base_type, "fields") else {}

            if field_name not in fields:
                raise TypeError(f"Field '{field_name}' not found in record '{record_name}'")

            field_type = fields[field_name]
            return ast_nodes.Type(field_type.base_type, field_type.dimension + record_type.dimension)

        case ast_nodes.FunctionCall(function, arguments):
            # ⊢ f : ((p1^i1, p2^i2) -> pr^j)^d     ⊢ a1 : p1^(k1 - i1)   ⊢ a2 : p2^(k2 - i2)
            # ------------------------------------------------------------------------------
            #                 ⊢ (f a1 a2) : pr^(max_l (kl + j + d))

            function_type = infer_expression_type(function, env)
            # function_type = Type(FunctionType([T(p1, i1), T(p2, i2)], T(pr, j)), d)

            if not isinstance(function_type.base_type, ast_nodes.FunctionType):
                raise TypeError(f"Trying to call non-function value of type {function_type}")

            # Assume that our arguments are typed already
            arg_types = [infer_expression_type(arg, env) for arg in arguments]
            # arg_types = [T(a1, k1 - i1), T(a2, k2 - i2)]
            param_types = function_type.base_type.param_types

            # If the number of expected parameters differs from the actually typed out ones
            if len(arg_types) != len(param_types):
                raise TypeError(f"Argument count mismatch: expected {len(param_types)}, got {len(arg_types)}")

            # Check base-type compatibility and collect dimensions
            ap_t = zip(arg_types, param_types)
            for a_t, p_t in ap_t:
                if a_t.base_type != p_t.base_type:
                    raise TypeError(f"Argument type mismatch: expected {p_t.base_type}, got {a_t.base_type}")

            # Get highest dimension there is, return that due to polymorphism
            result_dim = max(a.dimension - p.dimension for (a, p) in ap_t) + function_type.base_type.return_type.dimension + function_type.dimension

            ret_type = function_type.base_type.return_type
            return ast_nodes.Type(ret_type.base_type, ret_type.dimension + result_dim)

        case ast_nodes.OperatorCall(operator, operands):
            # Get the types of all operands
            operand_types = [infer_expression_type(op, env) for op in operands]
            first_type = operand_types[0]

            for t in operand_types[1:]:
                if t.base_type != first_type.base_type:
                    raise TypeError(f"Operand types do not match: {operand_types}")

            result_dim = max(t.dimension for t in operand_types)

            if operator in ("+", "-", "*", "/", "%"):
                return ast_nodes.Type(first_type.base_type, result_dim)
            elif operator in ("<", "<=", ">", ">=", "==", "!="):
                return ast_nodes.Type(ast_nodes.PrimitiveType("bool"), result_dim)
            else:
                raise TypeError(f"Unknown operator: {operator}")

        case ast_nodes.Block(statements):
            # To deal with a block, we need a copy environment
            block_env = env.copy()

            # Assume there will be no final statement that returns anything,
            # therefore make the type of the last statement "unit".
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
                                # Globally handled in typeinference/type_annotator.py
                                # Are nested functions like this required?
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