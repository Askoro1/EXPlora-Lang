from typeinference import type_checker, ast_nodes

def type_annotate_program(program, env=None):
    if env is None:
        env = {}
    for decl in program.declarations:
        annotate_declaration(decl, env)
    return program

def annotate_declaration(declaration: ast_nodes.Declaration, env: dict[str, ast_nodes.Type]) -> ast_nodes.Program:
    match declaration:
        case ast_nodes.VarDecl(name, ttype, mutable, initializer):
            if initializer:
                # Recursively go as deep as possible
                annotate_expression(initializer, env)

                # Get the type of the current expression
                expression_type = type_checker.infer_expression_type(initializer, env)

                # Check if there are any mismatches between type & dimension
                if ttype and expression_type and (
                        expression_type.base_type != ttype.base_type or expression_type.dimension != ttype.dimension
                ):
                    raise TypeError(f"Initializer type mismatch for '{name}': {expression_type} | {ttype}")

                var_type = ttype or expression_type
                if var_type is None:
                    raise TypeError(f"Cannot determine type of variable '{name}'")

                # Add the variable to environment
                env[name] = var_type

                # Annotate the VarDecl node itself
                setattr(declaration, "type", var_type)
            else:
                # Uninitialized variable, just store its declared type
                env[name] = ttype
                setattr(declaration, "type", ttype)

        case ast_nodes.FunctionDef(name, params, return_type, body):
            # Register function type for recursion support
            fn_type = ast_nodes.Type(
                ast_nodes.FunctionType(
                    param_types=[p.type for p in params],
                    return_type=return_type,
                ),
                0)
            env[name] = fn_type

            # Create local function environment
            local_env = env.copy()
            for p in params:
                local_env[p.name] = p.type

            annotate_expression(body, local_env)

            setattr(declaration, "type", fn_type)

        case ast_nodes.RecordTypeDecl(name, fields):
            # Collect field types into a dict
            field_dict = {f.name: f.type for f in fields}

            # Create a RecordType and attach its fields
            record_type = ast_nodes.RecordType(name)
            setattr(record_type, "fields", field_dict)

            env[name] = ast_nodes.Type(record_type, 0)

            # Attach the type to the declaration node itself
            setattr(declaration, "type", env[name])

def annotate_statement(stmt, env):
    if isinstance(stmt, ast_nodes.Assignment):
        annotate_expression(stmt.lvalue, env)
        annotate_expression(stmt.rvalue, env)
    elif isinstance(stmt, ast_nodes.WhileLoop):
        annotate_expression(stmt.condition, env)
        annotate_statement(stmt.body, env)
    elif isinstance(stmt, ast_nodes.DeclStmt):
        annotate_declaration(stmt.declaration, env)
    elif isinstance(stmt, ast_nodes.ExprStmt):
        annotate_expression(stmt.expression, env)

def annotate_expression(expr, env):
    match expr:
        # Literal Cases
        case ast_nodes.ArrayLiteral(value):
            for v in value:
                annotate_expression(v, env)
        case ast_nodes.RecordLiteral(_, field_values):
            for v in field_values.values():
                annotate_expression(v, env)
        case ast_nodes.LambdaLiteral(params, body):
            local_env = env.copy()
            for p in params:
                local_env[p.name] = p.type
            annotate_expression(body, local_env)
        case ast_nodes.PrimitiveLiteral():
            pass

        # PlaceExpression Case
        case ast_nodes.FieldRef(record, _):
            annotate_expression(record, env)
        case ast_nodes.VarRef():
            pass

        # Function & Operator Call
        case ast_nodes.FunctionCall(function, arguments):
            annotate_expression(function, env)
            for a in arguments:
                annotate_expression(a, env)
        case ast_nodes.OperatorCall(_, operands):
            for o in operands:
                annotate_expression(o, env)

        # Block, IfExpr Cases
        case ast_nodes.IfExpr(condition, then_expr, else_expr):
            annotate_expression(condition, env)
            annotate_expression(then_expr, env)
            annotate_expression(else_expr, env)
        case ast_nodes.Block(statements):
            local_env = env.copy()
            for s in statements:
                annotate_statement(s, local_env)
        case _:
            pass

    t = type_checker.infer_expression_type(expr, env)
    setattr(expr, "type", t)
    return expr