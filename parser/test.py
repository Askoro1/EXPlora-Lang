from tokenizer import tokenize
from parser import Parser
from pretty_printer import PrettyPrinter

if __name__ == "__main__":
    source = r'''
    int max(int a, int b) {
        if (a > b) return a;
        else return b;
    }

    int main() {
        int x = 10;
        int y = 20;
        int z;
        z = max(x + 2*3, y - 1);
        while (z > 0) {
            z = z - 1;
        }
        return 0;
    }
    '''
    print("SOURCE:")
    print(source)
    tokens = tokenize(source)

    p = Parser(tokens)
    ast = p.parse()

    print(ast)

    printer = PrettyPrinter()
    pretty_ast = printer.pprint(ast)

    print("\nAST (pretty):\n")
    print(pretty_ast)