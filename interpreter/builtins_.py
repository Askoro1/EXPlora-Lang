from typing import Any, Dict, List, Tuple
from dataclasses import dataclass
from ..ast_nodes import *
from .utils import (_np, NUMPY_ENABLED, RuntimeTypeError, RuntimeValue, shape_of_array, build)

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

# size returns the length of the outermost dimension of an array
def _builtin_size(args: List[RuntimeValue]) -> RuntimeValue:
    """Return the size of the first dimension of an array.

    This built-in function expects exactly one argument, which must be
    an array (numpy ndarray or nested Python list).  It returns the
    length of the outermost dimension as an integer.  Scalars and
    empty arrays return 0.  Passing anything other than an array
    results in a RuntimeTypeError.
    """
    if len(args) != 1:
        raise RuntimeTypeError("`size` expects exactly one argument")
    val = args[0].value
    # numpy array case
    if NUMPY_ENABLED and isinstance(val, _np.ndarray):
        try:
            dim = val.shape[0] if val.ndim > 0 else 0
        except Exception as e:
            raise RuntimeTypeError(f"`size` error: {e}")
        return RuntimeValue(dim, static_type=Type(base_type=PrimitiveType("int"), dimension=0))
    # nested list case
    if isinstance(val, list):
        return RuntimeValue(len(val), static_type=Type(base_type=PrimitiveType("int"), dimension=0))
    raise RuntimeTypeError("`size` expects an array argument")

#
# Additional built-in functions for character I/O
#
def _builtin_read_char(args: List[RuntimeValue]) -> RuntimeValue:
    """Read a single character from standard input and return its integer code.

    The function takes no arguments.  It reads exactly one character
    from the standard input stream and returns its Unicode code point
    as a Python int wrapped in a RuntimeValue.  If no input is
    available or more than one argument is provided, a
    RuntimeTypeError is raised.
    """
    if len(args) != 0:
        raise RuntimeTypeError("`read_char` expects no arguments")
    try:
        import sys
        # read exactly one character from stdin without waiting for a newline
        ch = sys.stdin.read(1)
        if ch == "":
            raise RuntimeError("EOF reached when reading character")
    except Exception as e:
        raise RuntimeTypeError(f"`read_char` failed to read a character: {e}")
    return RuntimeValue(ord(ch), static_type=Type(base_type=PrimitiveType("int"), dimension=0))


def _builtin_write_char(args: List[RuntimeValue]) -> RuntimeValue:
    """Write a character given its integer code.

    Expects exactly one argument of type int.  Converts the integer
    argument into a Unicode character using chr() and writes it to
    standard output without adding a newline.  Returns a unit value
    (None) wrapped in a RuntimeValue.  If the argument is not an
    integer or conversion fails, a RuntimeTypeError is raised.
    """
    if len(args) != 1:
        raise RuntimeTypeError("`write_char` expects exactly one argument: an integer code point")
    val = args[0].value
    if not isinstance(val, int):
        raise RuntimeTypeError("`write_char` argument must be an integer")
    try:
        ch = chr(val)
    except Exception as e:
        raise RuntimeTypeError(f"`write_char` received invalid code point: {e}")
    # print character without newline
    print(ch, end="")
    return RuntimeValue(None, static_type=Type(base_type=PrimitiveType("unit"), dimension=0))

BUILTINS = {
    'print': _builtin_print,
    'zeros': _builtin_zeros,
    'ones' : _builtin_ones,
    'shape': _builtin_shape,
    'size':  _builtin_size,
    'read_char': _builtin_read_char,
    'write_char': _builtin_write_char,
}
