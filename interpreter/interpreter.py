from typing import Any, Dict, List, Tuple
from ..ast_nodes import *
from .utils import (_np, NUMPY_ENABLED, RuntimeTypeError, RuntimeValue, shape_of_array, broadcast_shapes)
from .builtins_ import BUILTINS


class Frame:
    def __init__(self, parent: Optional['Frame'] = None):
        self.vars: Dict[str, RuntimeValue] = {}
        self.parent = parent

    def define(self, name: str, rv: RuntimeValue):
        self.vars[name] = rv

    def lookup(self, name: str) -> RuntimeValue:
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.lookup(name)
        raise RuntimeTypeError(f"NameError: '{name}' not found in environment")


class Interpreter:
    def __init__(self, program: Program):
        self.program = program
        self.global_frame = Frame()
        # register builtins in global scope as funcs
        for name, fn in BUILTINS.items():
            # wrap builtin into RuntimeValue as callable
            rv = RuntimeValue(fn, static_type=None, is_function=True, func_meta={'builtin': True, 'pyfunc': fn})
            self.global_frame.define(name, rv)
        # table of user-defined functions: name -> FunctionDef node
        self.functions: Dict[str, FunctionDef] = {}
        # Registry for record types: name -> { field_name: VarDecl }
        self.type_registry: Dict[str, Dict[str, VarDecl]] = {}
        # init: read declarations and register them
        self._register_declarations(program.declarations)

    def _register_declarations(self, decls: List[Any]):
        for d in decls:
            if isinstance(d, FunctionDef):
                self.functions[d.name] = d

            elif isinstance(d, VarDecl):
                if d.initializer is None:
                    rv = RuntimeValue(None, static_type=d.type)
                else:
                    rv = self.eval_expression(d.initializer, self.global_frame)
                    # type check
                    self._check_type_match(d.type, rv)
                self.global_frame.define(d.name, rv)

            elif isinstance(d, RecordTypeDecl):
                # store layout: { field_name: VarDecl }
                layout = {v.name: v for v in d.fields}
                self.type_registry[d.name] = layout

                field_list = list(d.fields)
                record_name = d.name

                def make_record_constructor(args_rv_list, _layout=layout, _field_list=field_list, _record_name=record_name):
                    # allow either positional args in declared order or a single dict-like arg
                    if len(args_rv_list) == 1 and isinstance(args_rv_list[0].value, dict):
                        vals = args_rv_list[0].value
                    else:
                        # map positional args to fields by order as in _field_list
                        if len(args_rv_list) != len(_field_list):
                            raise RuntimeTypeError(f"{d.name} constructor expects {len(_field_list)} args")
                        vals = {f.name: arg.value for f, arg in zip(_field_list, args_rv_list)}

                    # validate and return python dict
                    rec = {}
                    for fname, vdecl in _layout.items():
                        if fname not in vals:
                            raise RuntimeTypeError(f"Missing field {fname} for {_record_name}")
                        # type-check
                        rv = RuntimeValue(vals[fname], static_type=vdecl.type)
                        self._check_type_match(vdecl.type, rv)
                        rec[fname] = vals[fname]

                    # Tag with record name
                    rec["__record_name__"] = _record_name

                    return RuntimeValue(rec, static_type=Type(base_type=RecordType(d.name), dimension=0))

                # register constructor as builtin-like callable
                rv_ctor = RuntimeValue(None,
                                       static_type=Type(base_type=FunctionType(param_types=[v.type for v in d.fields],
                                                                               return_type=Type(
                                                                                   base_type=RecordType(d.name),
                                                                                   dimension=0)),
                                                        dimension=0),
                                       is_function=True,
                                       func_meta={'builtin': True, 'pyfunc': make_record_constructor})
                self.global_frame.define(d.name, rv_ctor)

            else:
                raise RuntimeTypeError(f"Unsupported top-level declaration: {d}")

    def _check_type_match(self, expected: Optional[Type], actual: RuntimeValue):
        if expected is None:
            return
        # if actual.static_type is set - we just check directly
        if actual.static_type is not None:
            if self._type_eq(expected, actual.static_type):
                return
        # in case `static_type` is not set in runtime, fall through to value inference
        v = actual.value
        if v is None:
            inferred = PrimitiveType("unit")
        elif isinstance(v, bool):
            inferred = PrimitiveType("bool")
        elif isinstance(v, int):
            inferred = PrimitiveType("int")
        elif isinstance(v, float):
            inferred = PrimitiveType("float")
        elif isinstance(v, str):
            if len(v) == 1:
                inferred = PrimitiveType("char")
            else:
                inferred = PrimitiveType("string")

        elif NUMPY_ENABLED and isinstance(v, _np.ndarray):
            shape = shape_of_array(v)
            dim = len(shape)

            if dim > 0:
                type_ = v.dtype
            else:
                type_ = None

            if type_ == int:
                base_type = PrimitiveType("int")
            elif type_ == float:
                base_type = PrimitiveType("float")
            elif type_ == bool:
                base_type = PrimitiveType("bool")
            elif type_ is None:
                base_type = PrimitiveType("unit")
            else:
                raise RuntimeTypeError(f"Unsupported type: {type_}")

            inferred = Type(base_type=base_type, dimension=dim)

        elif isinstance(v, list):
            shape = shape_of_array(v)
            dim = len(shape)

            if dim > 0:
                elem = v[0]
                for it in range(dim - 1):
                    elem = elem[0]
                type_ = type(elem)
            else:
                type_ = None

            if type_ == int:
                base_type = PrimitiveType("int")
            elif type_ == float:
                base_type = PrimitiveType("float")
            elif type_ == bool:
                base_type = PrimitiveType("bool")
            elif type_ is None:
                base_type = PrimitiveType("unit")
            else:
                raise RuntimeTypeError(f"Unsupported type: {type_}")

            inferred = Type(base_type=base_type, dimension=dim)

        elif isinstance(v, dict):
            rec_name = v.get("__record_name__")
            inferred = RecordType(rec_name if rec_name else "record")
        elif actual.is_function:
            # build function type from func_meta if present
            fm = actual.func_meta
            if fm and 'params_type' in fm and 'return_type' in fm:
                inferred = FunctionType(param_types=fm['params_type'], return_type=fm['return_type'])
            elif fm and 'params_type' in fm and 'return_type' not in fm:
                inferred = FunctionType(param_types=fm['params_type'], return_type=Type(PrimitiveType("unit"), dimension=0))
            elif fm and 'params_type' not in fm and 'return_type' in fm:
                inferred = FunctionType(param_types=[], return_type=fm['return_type'])
            else:
                inferred = FunctionType(param_types=[], return_type=Type(PrimitiveType("unit"), dimension=0))
        else:
            raise RuntimeTypeError(f"Unsupported type: {type(v)}")

        # expected.base_type may be PrimitiveType | RecordType | FunctionType
        if (isinstance(expected.base_type, PrimitiveType) or isinstance(expected.base_type, RecordType)) and expected.dimension == 0:
            if isinstance(expected.base_type, RecordType) and isinstance(v, dict):
                rec_name = v.get("__record_name__")
                if rec_name is None:
                    raise RuntimeTypeError(f"Expected record '{expected.base_type.name}', got plain record")

                # Strict record name match
                if rec_name != expected.base_type.name:
                    raise RuntimeTypeError(f"Type mismatch: expected record '{expected.base_type.name}', got '{rec_name}'")

                # Ensure record name exists in registry
                if expected.base_type.name in self.type_registry:
                    # ensure all required fields exist
                    layout = self.type_registry[expected.base_type.name]
                    for fname, vdecl in layout.items():
                        if fname not in v:
                            raise RuntimeTypeError(f"Missing field '{fname}' in record '{expected.base_type.name}'")
                        # Validate field type recursively
                        field_val = RuntimeValue(v[fname])
                        self._check_type_match(vdecl.type, field_val)
                    return
                else:
                    raise RuntimeTypeError(f"Unsupported RecordType: '{expected.base_type.name}'")
            if inferred.name == expected.base_type.name:
                return
            raise RuntimeTypeError(f"Type mismatch: expected {expected.base_type.name}, got {inferred.name}.")
        if isinstance(expected.base_type, FunctionType):
            if not actual.is_function:
                raise RuntimeTypeError("Type mismatch: expected function, got non-function")
            return

    def _type_eq(self, a: Type, b: Type) -> bool:
        ba = a.base_type
        bb = b.base_type
        if type(ba) != type(bb):
            return False
        if isinstance(ba, PrimitiveType) or isinstance(ba, RecordType):
            return ba.name == bb.name
        if isinstance(ba, FunctionType):
            if len(ba.param_types) != len(bb.param_types):
                return False
            for pa, pb in zip(ba.param_types, bb.param_types):
                if not self._type_eq(pa, pb):
                    return False
            return self._type_eq(ba.return_type, bb.return_type)
        return False

    def eval_expression(self, node: Any, frame: Frame) -> RuntimeValue:
        if isinstance(node, PrimitiveLiteral):
            # node.value (int | float | bool)
            rv = RuntimeValue(node.value, static_type=None)
            return rv

        if isinstance(node, StringLiteral):
            rv = RuntimeValue(node.value, static_type=Type(base_type=PrimitiveType("string"), dimension=0))
            return rv

        if isinstance(node, ArrayLiteral):
            items = [self.eval_expression(it, frame).value for it in node.value]

            if NUMPY_ENABLED:
                items = _np.array(items)
            shape = shape_of_array(items)
            if isinstance(shape, tuple):
                dim = len(shape)
            else:
                dim = 0

            if NUMPY_ENABLED:
                if dim > 0:
                    type_ = items.dtype
                else:
                    type_ = None
            else:
                if dim > 0:
                    elem = items[0]
                    for it in range(dim - 1):
                        elem = elem[0]
                    type_ = type(elem)
                else:
                    type_ = None

            if type_ == int:
                base_type = PrimitiveType("int")
            elif type_ == float:
                base_type = PrimitiveType("float")
            elif type_ == bool:
                base_type = PrimitiveType("bool")
            elif type_ is None:
                base_type = PrimitiveType("unit")
            else:
                raise RuntimeTypeError(f"Unsupported type: {type_}")


            rv = RuntimeValue(items, static_type=Type(base_type=base_type,
                                                      dimension=dim),
                                                    shape=shape)
            return rv

        if isinstance(node, VarRef):
            return frame.lookup(node.name)

        if isinstance(node, FieldRef):
            rec_rv = self.eval_expression(node.record, frame)
            rec_val = rec_rv.value
            if not isinstance(rec_val, dict):
                raise RuntimeTypeError("Field access on non-record")
            #check static_type if present
            if rec_rv.static_type and isinstance(rec_rv.static_type.base_type, RecordType):
                rec_name = rec_rv.static_type.base_type.name
                if rec_name in self.type_registry:
                    if node.field_name not in self.type_registry[rec_name]:
                        raise RuntimeTypeError(f"Field '{node.field_name}' not part of record '{rec_name}'")
            if node.field_name not in rec_val:
                raise RuntimeTypeError(f"Field '{node.field_name}' not found in record")
            v = rec_val[node.field_name]
            return RuntimeValue(v, static_type=None)

        if isinstance(node, RecordLiteral):
            # node.type is the name of the record (string)
            rec_name = node.type
            # rec_name = node.type.base_type.name
            if rec_name not in self.type_registry:
                raise RuntimeTypeError(f"Unknown record type '{rec_name}'")
            layout = self.type_registry[rec_name]
            # evaluate provided fields
            rec = {}
            for fname, expr in node.field_values.items():
                if fname not in layout:
                    raise RuntimeTypeError(f"Unknown field '{fname}' for record '{rec_name}'")
                rv = self.eval_expression(expr, frame)
                # check against declared field type
                self._check_type_match(layout[fname].type, rv)
                rec[fname] = rv.value
            # ensure all required fields are present
            for fname in layout:
                if fname not in rec:
                    raise RuntimeTypeError(f"Missing field '{fname}' for record '{rec_name}'")

            # attach record name tag for runtime type checking
            rec["__record_name__"] = node.type

            return RuntimeValue(rec, static_type=Type(base_type=RecordType(rec_name), dimension=0))

        if isinstance(node, LambdaLiteral):
            # capturing current frame
            params = node.params  # list of VarDecl
            return_type = None
            if hasattr(node, 'type') and isinstance(node.type, Type):
                return_type = node.type

            rv = RuntimeValue(value=None, static_type=return_type, is_function=True, func_meta={'params': params,
                                                                                                'return_type': return_type,
                                                                                                'node': node,
                                                                                                'closure': frame})
            return rv

        if isinstance(node, FunctionCall):
            # function is an expression (could be VarRef to function, or LambdaLiteral)
            fn_rv = self.eval_expression(node.function, frame)
            if not fn_rv.is_function:
                raise RuntimeTypeError("Attempt to call non-function")
            # check if this is a builtin function
            fm = fn_rv.func_meta or {}
            if fm.get('builtin', False):
                args = [self.eval_expression(a, frame) for a in node.arguments]
                return fm['pyfunc'](args)

            # now handle user-defined functions: either FunctionDef by name (node.function VarRef) or LambdaLiteral closure

            # FunctionDef case
            if isinstance(node.function, VarRef) and node.function.name in self.functions:
                fn_node = self.functions[node.function.name]

                arg_rvs = []
                arg_vals = []
                shapes = []

                # bind parameters (positional)
                if len(fn_node.params) != len(node.arguments):
                    raise RuntimeTypeError(f"Function '{fn_node.name}' expected {len(fn_node.params)} args, got {len(node.arguments)}")
                for param_decl, arg_expr in zip(fn_node.params, node.arguments):
                    arg_rv = self.eval_expression(arg_expr, frame)
                    # check type
                    self._check_type_match(param_decl.type, arg_rv)
                    arg_rvs.append(arg_rv)
                    arg_val = arg_rv.value
                    arg_vals.append(arg_val)
                    if isinstance(arg_val, _np.ndarray):
                        shapes.append(arg_val.shape)

                if shapes:
                    # vectorized elementwise evaluation
                    bshape = broadcast_shapes(*shapes)
                    result = _np.empty(bshape, dtype=object)

                    for idx in _np.ndindex(bshape):
                        call_args = []
                        for param_decl, val in zip(fn_node.params, arg_vals):
                            if isinstance(val, _np.ndarray):
                                call_args.append(RuntimeValue(val[idx], static_type=param_decl.type))
                            else:
                                call_args.append(RuntimeValue(val, static_type=param_decl.type))
                        # prepare new frame with closure (current `frame`)
                        new_frame = Frame(parent=frame)
                        for param_decl, rv in zip(fn_node.params, call_args):
                            new_frame.define(param_decl.name, rv)
                        res = self.eval_expression(fn_node.body, new_frame)
                        result[idx] = res.value

                    return RuntimeValue(result,
                                        static_type=Type(base_type=RecordType("array"), dimension=result.shape[0]),
                                        shape=result.shape)
                else:
                    # scalar call
                    # prepare new frame with closure (current `frame`)
                    new_frame = Frame(parent=frame)
                    for param_decl, rv in zip(fn_node.params, arg_rvs):
                        new_frame.define(param_decl.name, rv)
                    # evaluate body (body is Expression)
                    ret = self.eval_expression(fn_node.body, new_frame)
                    # check return type
                    if fn_node.return_type is not None:
                        self._check_type_match(fn_node.return_type, ret)
                    return ret

            # Lambda closure case: fn_rv.func_meta has closure and node
            if 'node' in fm and fm['node'] is not None:
                lambda_node = fm['node']
                closure: Frame = fm['closure'] or frame
                params = fm['params']
                if len(params) != len(node.arguments):
                    raise RuntimeTypeError(f"Lambda expected {len(params)} args, got {len(node.arguments)}")
                # create frame with parent=closure to respect lexical scope
                call_frame = Frame(parent=closure)
                for param_decl, arg_expr in zip(params, node.arguments):
                    arg_rv = self.eval_expression(arg_expr, frame)
                    # check type
                    self._check_type_match(param_decl.type, arg_rv)
                    call_frame.define(param_decl.name, arg_rv)
                # evaluate lambda body (body is Expression)
                ret = self.eval_expression(lambda_node.body, call_frame)
                if fm.get('return_type'):
                    self._check_type_match(fm.get('return_type'), ret)
                return ret

            raise RuntimeTypeError("Uncallable function value")

        if isinstance(node, OperatorCall):
            # operator string and operands (list)
            ops = [self.eval_expression(o, frame) for o in node.operands]
            # unary
            if len(ops) == 1:
                a = ops[0].value
                if node.operator == '-':
                    return RuntimeValue(-a, static_type=None)
                if node.operator == 'not':
                    return RuntimeValue(_np.logical_not(a), static_type=None)
                if node.operator == 'sizeof':
                    if NUMPY_ENABLED and isinstance(a, _np.ndarray):
                        dim = a.shape[0] if a.ndim > 0 else 0
                        return RuntimeValue(dim, static_type=None)
                    if isinstance(a, list):
                        return RuntimeValue(len(a), static_type=None)
                    raise RuntimeTypeError("sizeof expects an array")
            # binary
            if len(ops) == 2:
                a = ops[0].value
                b = ops[1].value
                op = node.operator
                # array-aware via numpy if possible
                if NUMPY_ENABLED and (isinstance(a, _np.ndarray) or isinstance(b, _np.ndarray)):
                    try:
                        if op == '+': res = a + b
                        elif op == '-': res = a - b
                        elif op == '*': res = a * b
                        elif op == '/': res = a / b
                        elif op == '%': res = a % b
                        elif op == '@': res = a @ b
                        elif op in ('==','!=','<','>','<=','>='):
                            res = eval(f"a {op} b")
                        elif op in ('&&', 'and'):
                            res = _np.logical_and(a, b)
                        elif op in ('||', 'or'):
                            res = _np.logical_or(a, b)
                        elif op == '++':
                            res = _np.concatenate((a, b), axis=0)
                        elif op == 'index' or op == '[]':
                            try:
                                res = a[b]
                            except Exception as e:
                                raise RuntimeTypeError(f"Indexing error: {e}")
                        else:
                            raise RuntimeTypeError(f"Unsupported operator {op}")
                        return RuntimeValue(res, static_type=None, shape=shape_of_array(res))
                    except Exception as e:
                        raise RuntimeTypeError(f"Array operator error: {e}")
                # Python scalars / lists
                try:
                    if op == '+': res = a + b
                    elif op == '-': res = a - b
                    elif op == '*': res = a * b
                    elif op == '/': res = a / b
                    elif op == '%': res = a % b
                    elif op == '==': res = a == b
                    elif op == '!=': res = a != b
                    elif op == '<': res = a < b
                    elif op == '>': res = a > b
                    elif op == '<=': res = a <= b
                    elif op == '>=': res = a >= b
                    elif op in ('and', '&&'): res = bool(a) and bool(b)
                    elif op in ('or', '||'): res = bool(a) or bool(b)
                    elif op == '++':
                        if isinstance(a, list) and isinstance(b, list):
                            res = a + b
                        else:
                            raise RuntimeTypeError("`++` expects two arrays (lists)")
                    elif op == 'index' or op == '[]':
                        try:
                            res = a[b]
                        except Exception as e:
                            raise RuntimeTypeError(f"Indexing error: {e}")
                    else:
                        raise RuntimeTypeError(f"Unsupported operator {op}")
                    return RuntimeValue(res, static_type=None, shape=shape_of_array(res))
                except TypeError as e:
                    raise RuntimeTypeError(f"Operator error: {e}")
            raise RuntimeTypeError("OperatorCall with wrong arity")

        if isinstance(node, Block):
            # Evaluate sequentially
            local_frame = Frame(parent=frame)
            last_val: Optional[RuntimeValue] = None
            for st in node.statements:
                v = self.exec_statement(st, local_frame)
                # exec_statement returns RuntimeValue for ExprStmt or None
                if isinstance(st, ExprStmt):
                    last_val = v
            return last_val if last_val is not None else RuntimeValue(None, static_type=None)

        if isinstance(node, IfExpr):
            cond = self.eval_expression(node.condition, frame)
            if cond.value:
                return self.eval_expression(node.then_expr, frame)
            else:
                return self.eval_expression(node.else_expr, frame)

        raise RuntimeTypeError(f"Unsupported expression node: {type(node).__name__}")

    def exec_statement(self, node: Any, frame: Frame) -> Optional[RuntimeValue]:
        if isinstance(node, ExprStmt):
            return self.eval_expression(node.expression, frame)

        if isinstance(node, DeclStmt):
            decl = node.declaration

            if isinstance(decl, VarDecl):
                if decl.initializer is None:
                    rv = RuntimeValue(None, static_type=decl.type)
                else:
                    rv = self.eval_expression(decl.initializer, frame)
                    self._check_type_match(decl.type, rv)
                frame.define(decl.name, rv)
                return None

            elif isinstance(decl, FunctionDef):
                # register function in this scope as RuntimeValue (closure)
                meta = {'node': decl, 'closure': frame, 'params_type': [p.type for p in decl.params], 'return_type': decl.return_type}
                rv = RuntimeValue(None, static_type=Type(base_type=FunctionType(param_types=[p.type for p in decl.params], return_type=decl.return_type), dimension=0), is_function=True, func_meta=meta)
                frame.define(decl.name, rv)
                return None
            else:
                raise RuntimeTypeError("Unsupported declaration in DeclStmt")

        if isinstance(node, Assignment):
            # lvalue is PlaceExpression (VarRef or FieldRef)
            r = self.eval_expression(node.rvalue, frame)

            if isinstance(node.lvalue, VarRef):
                # check existence: if var exists in some parent, set there; else set in current frame
                # find the frame that holds the variable
                target = frame
                while target is not None and node.lvalue.name not in target.vars:
                    target = target.parent
                if target is None:
                    # create in current frame
                    frame.define(node.lvalue.name, r)
                else:
                    target.define(node.lvalue.name, r)
                return None

            if isinstance(node.lvalue, FieldRef):
                rec_rv = self.eval_expression(node.lvalue.record, frame)
                if not isinstance(rec_rv.value, dict):
                    raise RuntimeTypeError("Assignment to field on non-record")
                rec_rv.value[node.lvalue.field_name] = r.value
                return None

            raise RuntimeTypeError("Unsupported lvalue in Assignment")

        if isinstance(node, WhileLoop):
            while True:
                cond_rv = self.eval_expression(node.condition, frame)
                if not cond_rv.value:
                    break
                self.exec_statement(node.body, frame)
            return None

        raise RuntimeTypeError(f"Unsupported statement: {type(node).__name__}")

    def run(self):
        # execute top-level declarations stored in program.declarations
        for decl in self.program.declarations:
            if isinstance(decl, FunctionDef):
                # register function wrapper in global frame
                meta = {'node': decl, 'closure': self.global_frame, 'params_type':[p.type for p in decl.params], 'return_type': decl.return_type}
                rv = RuntimeValue(None, static_type=Type(base_type=FunctionType(param_types=[p.type for p in decl.params], return_type=decl.return_type), dimension=0), is_function=True, func_meta=meta)
                self.global_frame.define(decl.name, rv)
                self.functions[decl.name] = decl
            elif isinstance(decl, VarDecl):
                # top-level var already handled in _register_declarations, but double-check
                if decl.name not in self.global_frame.vars:
                    if decl.initializer is None:
                        rv = RuntimeValue(None, static_type=decl.type)
                    else:
                        rv = self.eval_expression(decl.initializer, self.global_frame)
                        self._check_type_match(decl.type, rv)
                    self.global_frame.define(decl.name, rv)
            elif isinstance(decl, RecordTypeDecl):
                continue
            else:
                raise RuntimeTypeError(f"Unsupported declaration: {type(decl).__name__}")

        return self.global_frame
