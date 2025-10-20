from typing import Any, Dict, List, Tuple
from dataclasses import dataclass
from ast_nodes import *
from utils import (_np, NUMPY_ENABLED, RuntimeTypeError, RuntimeValue, shape_of_array, build)

# ----- Builtins -----

def _builtin_print(args: List[RuntimeValue]) -> RuntimeValue:
    # `print` function
    print(*[a.value for a in args])
    return RuntimeValue(value=None, static_type=None)

def _builtin_zeros(args: List[RuntimeValue]) -> RuntimeValue:
    if len(args) not in (1, 2):
        raise RuntimeTypeError("`zeros` expects at most two arguments: shape, type")
    shape_val = args[0].value
    if not isinstance(shape_val, (tuple, list)):
        if isinstance(shape_val, _np.ndarray):
            shape_val = shape_val.tolist()
        else:
            raise RuntimeTypeError("`zeros`: arg0 must be array of dims")
    if len(args) == 2:
        init_type = args[1].value
        if not init_type in (float, int):
            raise RuntimeTypeError("`zeros`: arg1 must be float or int")
    else:
        init_type = float
    if NUMPY_ENABLED:
        arr = _np.zeros(tuple(shape_val), dtype=init_type)
        return RuntimeValue(arr, static_type=Type(base_type=RecordType("array"), dimension=len(shape_val)), shape=shape_of_array(arr))
    else:
        # nested lists, if numpy is disabled
        arr = build(tuple(shape_val), init_val=0, init_type=init_type)
        return RuntimeValue(arr, static_type=Type(base_type=RecordType("array"), dimension=len(shape_val)), shape=shape_of_array(arr))

def _builtin_ones(args: List[RuntimeValue]) -> RuntimeValue:
    if len(args) not in (1, 2):
        raise RuntimeTypeError("`ones` expects at most two arguments: shape, type")
    shape_val = args[0].value
    if not isinstance(shape_val, (tuple, list)):
        if isinstance(shape_val, _np.ndarray):
            shape_val = shape_val.tolist()
        else:
            raise RuntimeTypeError("`ones`: arg0 must be array of dims")
    if len(args) == 2:
        init_type = args[1].value
        if not init_type in (float, int):
            raise RuntimeTypeError("`ones`: arg1 must be float or int")
    else:
        init_type = float
    if NUMPY_ENABLED:
        arr = _np.ones(tuple(shape_val), dtype=init_type)
        return RuntimeValue(arr, static_type=Type(base_type=RecordType("array"), dimension=len(shape_val)), shape=shape_of_array(arr))
    else:
        # nested lists, if numpy is disabled
        arr = build(tuple(shape_val), init_val=1, init_type=init_type)
        return RuntimeValue(arr, static_type=Type(base_type=RecordType("array"), dimension=len(shape_val)), shape=shape_of_array(arr))

def _builtin_shape(args: List[RuntimeValue]) -> RuntimeValue:
    if len(args) != 1:
        raise RuntimeTypeError("shape expects 1 argument")
    return RuntimeValue(shape_of_array(args[0].value), static_type=Type(base_type=PrimitiveType("array"), dimension=1))

BUILTINS = {
    'print': _builtin_print,
    'zeros': _builtin_zeros,
    'ones' : _builtin_ones,
    'shape': _builtin_shape,
}