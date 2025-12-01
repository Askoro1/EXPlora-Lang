import sys

from .parser.parser import *
from .parser.pretty_printer import *
from .typeinference.type_annotator import *
from .interpreter.interpreter import *
from .interpreter.builtins_ import *

def main():
    if len(sys.argv) < 2:
        print('Usage: python -m "EXPlora-Lang".pipeline <filename>')
        sys.exit(1)

    filename = sys.argv[1]

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            code_ = f.read()

    except FileNotFoundError:
        print(f"File '{filename}' not found.")
        sys.exit(1)

    while True:
        try:
            print("\n--- Running ---\n")
            # Tokenize
            tokens = tokenize(code_)

            # Parse
            parser = Parser(tokens)
            ast = parser.parse()

            # Infer Types
            tast = type_annotate_program(ast)

            with open('output.txt', 'w', encoding='utf-8') as f:
                pprint(tast, stream=f)

            # Interpret TAST
            interp = Interpreter(tast, code=code_)
            global_frame = interp.run()
            # Call main()
            call = FunctionCall(function=VarRef("main"), arguments=[])
            print(interp.eval_expression(call, global_frame).value)
            sys.exit(0)
        except StopRecursion as upd_code:
            code_ = str(upd_code)
            continue

    #except Exception as e:
    #   print(f"{type(e).__name__}: {e}")
    #   sys.exit(1)

if __name__ == '__main__':
    main()