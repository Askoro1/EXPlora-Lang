from . import type_checker
from .. import ast_nodes
from ..interpreter.builtins_ import *

def type_annotate_program(program, env=None):
    """
    Entry point function. Goes through all of the program declarations and calls
    the annotation function.

    Args:
      program: ast_nodes.Program - The AST to be annotated.
      env: dict[str, ast_nodes.Type] - The environment where program variables are recorded.

    Returns:
      program: The Typed AST (TAST) of the program.
    """
    if env is None:
        env = {}

    builtins_set = set()
    for name in BUILTINS.keys():
        builtins_set.add(name)

    for decl in program.declarations:
        annotate_declaration(decl, env, builtins_set)
    return program

def annotate_declaration(declaration: ast_nodes.Declaration, env: dict[str, ast_nodes.Type], builtins_set: set[str]):
    """
    For each declaration in the program, annotate its type to the AST.

    Args:
        declaration: ast_nodes.Declaration - The declaration in question.
        env: dict[str, ast_nodes.Type] - The environment where program variables are recorded.

    Returns:
        None
    """
    match declaration:
        case ast_nodes.VarDecl(name, declared_type, mutable, initializer):
            if initializer:
                # Recursively go down until leaf node level
                initializer = annotate_expression(initializer, env, builtins_set)

                # Get the type of the current expression
                inferred_type = initializer.type

                # Check if declared & inferred values agree on dimension and type
                if declared_type and inferred_type and (
                        inferred_type.base_type != declared_type.base_type or inferred_type.dimension != declared_type.dimension
                ):
                    raise TypeError(f"Initializer type mismatch for '{name}': {inferred_type} | {declared_type}")

                # Focus is placed on what is already in the AST (declared_type)
                # But if the developer did not declare a type, rely on inference
                var_type = declared_type or inferred_type
                if var_type is None:
                    raise TypeError(f"Cannot determine type of variable '{name}'")

                # Add the variable to environment
                env[name] = var_type

                # Annotate the VarDecl node itself
                setattr(declaration, "type", var_type)
            else:
                # Uninitialized variable, just store its declared type
                env[name] = declared_type
                setattr(declaration, "type", declared_type)

        case ast_nodes.FunctionDef(name, params, return_type, body):

            # Assume that the param & return types are already provided
            # by the partially typed AST
            fn_type = ast_nodes.Type(
                ast_nodes.FunctionType(
                    param_types=[p.type for p in params],
                    return_type=return_type,
                ),
                0)

            # Add the function type to the environment for recursive calls
            env[name] = fn_type

            # Create local function environment so that local variables
            # do not escape the score
            local_env = env.copy()
            for p in params:
                local_env[p.name] = p.type

            annotate_expression(body, local_env, builtins_set)

            setattr(declaration, "type", fn_type)

        case ast_nodes.RecordTypeDecl(name, fields):
            # Assume field names & types are already provided in the
            # partially typed AST
            field_dict = {f.name: f.type for f in fields}

            # Create a RecordType and attach its fields
            record_type = ast_nodes.RecordType(name)
            setattr(record_type, "fields", field_dict)

            env[name] = ast_nodes.Type(record_type, 0)

            # Attach the type to the declaration node itself
            setattr(declaration, "type", env[name])

def annotate_statement(stmt, env, builtins_set):
    """
    Traversal only function. Figures out what kind of statement it is dealing
    with, and calls either the expression annotation or itself.

    Args:
        stmt: The statement in question.
        env: The environment where program variables are recorded.
    """
    if isinstance(stmt, ast_nodes.Assignment):
        annotate_expression(stmt.lvalue, env, builtins_set)
        annotate_expression(stmt.rvalue, env, builtins_set)
    elif isinstance(stmt, ast_nodes.WhileLoop):
        annotate_expression(stmt.condition, env, builtins_set)
        annotate_statement(stmt.body, env, builtins_set)
    elif isinstance(stmt, ast_nodes.DeclStmt):
        annotate_declaration(stmt.declaration, env, builtins_set)
    elif isinstance(stmt, ast_nodes.ExprStmt):
        annotate_expression(stmt.expression, env, builtins_set)

def annotate_expression(expr, env, builtins_set):
    """
    Recursively goes to lower levels of the AST.
    Once Primitives are reached,  annotate with their types.
    Return to parent level and annotate based on children types.
    Repeat process for entire AST.

    Args:
        expr: The expression whose type is being checked.
        env: The environment where program variables are recorded.

    Returns:
        expr: The expression, now typed.
    """
    match expr:
        # Literal Cases
        case ast_nodes.ArrayLiteral(value):
            for v in value:
                annotate_expression(v, env, builtins_set)
        case ast_nodes.RecordLiteral(_, field_values):
            for v in field_values.values():
                annotate_expression(v, env, builtins_set)
        case ast_nodes.LambdaLiteral(params, body):
            local_env = env.copy()
            for p in params:
                local_env[p.name] = p.type
            annotate_expression(body, local_env, builtins_set)
        case ast_nodes.PrimitiveLiteral():
            pass
        case ast_nodes.StringLiteral():
            pass

        # PlaceExpression Case
        case ast_nodes.FieldRef(record, _):
            annotate_expression(record, env, builtins_set)
        case ast_nodes.VarRef():
            pass

        # Function & Operator Call
        case ast_nodes.FunctionCall(function, arguments):
            annotate_expression(function, env, builtins_set)
            for a in arguments:
                annotate_expression(a, env, builtins_set)
        case ast_nodes.OperatorCall(_, operands):
            for o in operands:
                annotate_expression(o, env, builtins_set)

        # Block, IfExpr Cases
        case ast_nodes.IfExpr(condition, then_expr, else_expr):
            annotate_expression(condition, env, builtins_set)
            annotate_expression(then_expr, env, builtins_set)
            annotate_expression(else_expr, env, builtins_set)
        case ast_nodes.Block(statements):
            local_env = env.copy()
            for s in statements:
                annotate_statement(s, local_env, builtins_set)
        case _:
            pass

    t = type_checker.infer_expression_type(expr, env, builtins_set)
    setattr(expr, "type", t)
    return expr