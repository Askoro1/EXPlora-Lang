import sys

from .parser.parser import *
from .parser.pretty_printer import *
from .typeinference.type_annotator import *
from .interpreter.interpreter import *
from .interpreter.builtins_ import *

def main():
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <filename>")
        sys.exit(1)

    filename = sys.argv[1]

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            code_ = f.read()

    except FileNotFoundError:
        print(f"File '{filename}' not found.")
        sys.exit(1)

    # Tokenize
    tokens = tokenize(code_)

    # Parse
    parser = Parser(tokens)
    ast = parser.parse()

    # for debug
    with open('output.txt', 'w', encoding='utf-8') as f:
        pprint(ast, stream=f)
        # printer = PrettyPrinter()
        # pretty_code = printer.pprint(ast)
        # print(pretty_code, file=f)

    # Infer Types
    #tast = type_annotate_program(ast)

    # Interpret TAST
    interp = Interpreter(ast)
    global_frame = interp.run()

    # Call main()
    call = FunctionCall(function=VarRef("main"), arguments=[])
    interp.eval_expression(call, global_frame)

    sys.exit(0)
    # except Exception as e:
    #     print(f"{type(e).__name__}: {e}")
    #     sys.exit(1)

if __name__ == '__main__':
    main()