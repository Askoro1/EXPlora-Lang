import unittest
from pathlib import Path

from ..parser.tokenizer import tokenize
from ..parser.parser import Parser
from ..typeinference.type_annotator import type_annotate_program
from ..interpreter.interpreter import Interpreter
from ..ast_nodes import FunctionCall, VarRef, PrimitiveLiteral

HERE = Path(__file__).resolve().parent
CODE_DIR = HERE / "explora_code_files"

def run_function(filename: str, func_name: str, args):
    """
    Load an .exp file, run the basic process (tokenize -> parse -> type-annotate -> interpret),
    then call the given function with the given primitive args and return its value.
    """
    path = CODE_DIR / filename
    code = path.read_text(encoding="utf-8")

    tokens = tokenize(code)
    parser = Parser(tokens)
    ast = parser.parse()
    tast = type_annotate_program(ast)

    interp = Interpreter(tast)
    frame = interp.run()

    arg_nodes = [PrimitiveLiteral(v) for v in args]
    call = FunctionCall(function=VarRef(func_name), arguments=arg_nodes)
    rv = interp.eval_expression(call, frame)
    return rv.value

class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(run_function("add.exp", "add", [1, 2]), 3)
        self.assertEqual(run_function("add.exp", "add", [0, 0]), 0)
        self.assertEqual(run_function("add.exp", "add", [-1, 5]), 4)

class TestMax(unittest.TestCase):
    def test_max(self):
        self.assertEqual(run_function("max.exp", "max", [5, 3]), 5)
        self.assertEqual(run_function("max.exp", "max", [4, 7]), 7)

class TestSquare(unittest.TestCase):
    def test_max(self):
        self.assertEqual(run_function("square.exp", "square", [0]), 0)
        self.assertEqual(run_function("square.exp", "square", [2]), 4)
        self.assertEqual(run_function("square.exp", "square", [3]), 9)
        self.assertEqual(run_function("square.exp", "square", [-2]), 4)

class TestAbsVal(unittest.TestCase):
    def test_max(self):
        self.assertEqual(run_function("absval.exp", "absval", [5]), 5)
        self.assertEqual(run_function("absval.exp", "absval", [-7]), 7)
        self.assertEqual(run_function("absval.exp", "absval", [0]), 0)

class TestMin(unittest.TestCase):
    def test_min(self):
        self.assertEqual(run_function("min.exp", "min", [5, 3]), 3)
        self.assertEqual(run_function("min.exp", "min", [4, 7]), 4)
        self.assertEqual(run_function("min.exp", "min", [-2, 6]), -2)

class TestClampZero(unittest.TestCase):
    def test_clamp_zero(self):
        self.assertEqual(run_function("clamp_zero.exp", "clamp_zero", [-5]), 0)
        self.assertEqual(run_function("clamp_zero.exp", "clamp_zero", [3]), 3)

class TestSignum(unittest.TestCase):
    def test_signum(self):
        self.assertEqual(run_function("signum.exp", "signum", [10]), 1)
        self.assertEqual(run_function("signum.exp", "signum", [-3]), -1)
        self.assertEqual(run_function("signum.exp", "signum", [0]), 0)

class TestIsEven(unittest.TestCase):
    def test_is_even(self):
        self.assertEqual(run_function("is_even.exp", "is_even", [4]), 1)
        self.assertEqual(run_function("is_even.exp", "is_even", [5]), 0)

class TestIsOdd(unittest.TestCase):
    def test_is_odd(self):
        self.assertEqual(run_function("is_odd.exp", "is_odd", [4]), 0)
        self.assertEqual(run_function("is_odd.exp", "is_odd", [5]), 1)

class TestMin3(unittest.TestCase):
    def test_min3(self):
        self.assertEqual(run_function("min3.exp", "min3", [1, 2, 3]), 1)
        self.assertEqual(run_function("min3.exp", "min3", [10, 2, 3]), 2)

class TestMax3(unittest.TestCase):
    def test_max3(self):
        self.assertEqual(run_function("max3.exp", "max3", [1, 2, 3]), 3)
        self.assertEqual(run_function("max3.exp", "max3", [10, 2, 3]), 10)
        self.assertEqual(run_function("max3.exp", "max3", [-1, -5, -3]), -1)

class TestClampRange(unittest.TestCase):
    def test_clamp_range(self):
        self.assertEqual(run_function("clamp_range.exp", "clamp_range", [5, 0, 10]), 5)
        self.assertEqual(run_function("clamp_range.exp", "clamp_range", [-3, 0, 10]), 0)
        self.assertEqual(run_function("clamp_range.exp", "clamp_range", [20, 0, 10]), 10)

class TestIsNonzero(unittest.TestCase):
    def test_is_nonzero(self):
        self.assertEqual(run_function("is_nonzero.exp", "is_nonzero", [0]), 0)
        self.assertEqual(run_function("is_nonzero.exp", "is_nonzero", [7]), 1)
        self.assertEqual(run_function("is_nonzero.exp", "is_nonzero", [-3]), 1)

class TestAdd3(unittest.TestCase):
    def test_add3(self):
        self.assertEqual(run_function("add3.exp", "add3", [1, 2, 3]), 6)

class TestMul3(unittest.TestCase):
    def test_mul3(self):
        self.assertEqual(run_function("mul3.exp", "mul3", [2, 3, 4]), 24)

class TestAverage2(unittest.TestCase):
    def test_average2(self):
        self.assertEqual(run_function("average2.exp", "average2", [3, 5]), 4)
        self.assertEqual(run_function("average2.exp", "average2", [2, 3]), 2.5)

class TestDiff(unittest.TestCase):
    def test_diff(self):
        self.assertEqual(run_function("diff.exp", "diff", [7, 3]), 4)
        self.assertEqual(run_function("diff.exp", "diff", [3, 7]), 4)

class TestIsBetween(unittest.TestCase):
    def test_is_between(self):
        self.assertEqual(run_function("is_between.exp", "is_between", [5, 0, 10]), 1)
        self.assertEqual(run_function("is_between.exp", "is_between", [-1, 0, 10]), 0)
        self.assertEqual(run_function("is_between.exp", "is_between", [11, 0, 10]), 0)

class TestIsPositive(unittest.TestCase):
    def test_is_positive(self):
        self.assertEqual(run_function("is_positive.exp", "is_positive", [5]), 1)
        self.assertEqual(run_function("is_positive.exp", "is_positive", [0]), 0)
        self.assertEqual(run_function("is_positive.exp", "is_positive", [-3]), 0)

class TestSameParity(unittest.TestCase):
    def test_same_parity(self):
        self.assertEqual(run_function("same_parity.exp", "same_parity", [2, 4]), 1)
        self.assertEqual(run_function("same_parity.exp", "same_parity", [2, 3]), 0)
        self.assertEqual(run_function("same_parity.exp", "same_parity", [5, 7]), 1)

if __name__ == "__main__":
    unittest.main()