from typing import Any, Dict, List, Tuple
from dataclasses import dataclass
from ast_nodes import *


# if numpy is available we use numpy under the hood for effective array ops
try:
    import numpy as _np
    NUMPY_ENABLED = True
except Exception:
    _np = None
    NUMPY_ENABLED = False


class RuntimeErrorWithNode(Exception):
    pass


class RuntimeTypeError(RuntimeErrorWithNode):
    pass


@dataclass
class RuntimeValue:
    """Wrapper which contains the value itself, static type of the variable (Type/None) and additional metadata"""
    value: Any
    static_type: Optional[Type] = None
    shape: Optional[Tuple[int, ...]] = None
    # if THIS is a function/lambda-function, then it contains callable and function info
    is_function: bool = False
    func_meta: Optional[dict] = None  # {'params': [...], 'return_type': Type, 'node': ASTnode, 'closure': Frame}

    def __repr__(self):
        t = self.static_type
        return f"RuntimeValue(value={self.value!r}, static_type={t}, shape={self.shape}, is_fn={self.is_function}, func_meta={self.func_meta})"


# helper functions
def shape_of_array(val):
    if NUMPY_ENABLED and isinstance(val, _np.ndarray):
        return tuple(val.shape)
    elif isinstance(val, list):
        dims = []
        curr = val
        while isinstance(curr, list):
            dims.append(len(curr))
            if len(curr) == 0:
                break
            curr = curr[0]
        return tuple(dims)
    else:
        return 0


def build(dims, init_val=0, init_type=float):
    if len(dims) == 0:
        return init_type(init_val)
    return [build(dims[1:]) for _ in range(dims[0])]