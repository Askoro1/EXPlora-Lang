import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import List


# ------------------------
# Token Types
# ------------------------
class TokenType(Enum):
    # Keywords
    KW = auto()
    # Identifiers
    ID = auto()
    # Literals
    NUMBER = auto()
    CHAR = auto()
    STRING = auto()
    # Operators
    OP = auto()
    # End of file
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: str
    pos: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, pos={self.pos})"


# ------------------------
# Token patterns
# ------------------------
TOKEN_SPEC = [
    ("WHITESPACE", r"[ \t\n\r]+"),

    ("CHAR", r"'(\\.|[^\\'])'"),
    ("STRING", r"\"(\\.|[^\"])*\""),

    ("COMMENT", r"//[^\n]*"),
    ("MCOMMENT", r"/\*.*\*/"),

    ("NUMBER", r"\d+(\.\d+)?([eE][+-]?\d+)?"),
    ("ID", r"[A-Za-z_][A-Za-z0-9_]*"),
    # Multi-char operators
    ("OP", r"==|!=|<=|>=|\+\+|--|\+=|-=|\*=|/=|&&|\|\||<<|>>|->|=>"),
    # Single-character operators & punctuation
    ("SINGLE", r"[+\-*/%<>=!&|^~\[\]\(\)\{\},;.:]"),
]

MASTER_RE = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC), re.S)

# ------------------------
# Keywords
# ------------------------
KEYWORDS = {
    "int", "float", "char", "bool", "unit", "auto", "string",
    "if", "else", "while", "for", "return",
    "true", "false", "sizeof",
    "Record"
}


def strip_comments(code: str) -> str:
    result = []
    i = 0
    n = len(code)
    in_string = False
    in_char = False

    while i < n:
        c = code[i]

        # --- STRING ---
        if not in_char and c == '"' and (i == 0 or code[i - 1] != '\\'):
            in_string = not in_string
            result.append(c)
            i += 1
            continue

        # --- CHAR ---
        if not in_string and c == "'" and (i == 0 or code[i - 1] != '\\'):
            in_char = not in_char
            result.append(c)
            i += 1
            continue

        # --- LINE COMMENT: // ---
        if not in_string and not in_char and c == '/' and i + 1 < n and code[i + 1] == '/':
            i += 2
            while i < n and code[i] != '\n':
                i += 1
            continue

        # --- BLOCK COMMENT: /* ... */ ---
        if not in_string and not in_char and c == '/' and i + 1 < n and code[i + 1] == '*':
            i += 2
            while i + 1 < n and not (code[i] == '*' and code[i + 1] == '/'):
                i += 1
            i += 2
            continue

        # normal char
        result.append(c)
        i += 1

    return "".join(result)


# ------------------------
# Tokenizer
# ------------------------
def tokenize(code: str) -> List[Token]:
    code = strip_comments(code)
    tokens: List[Token] = []

    for m in MASTER_RE.finditer(code):
        kind = m.lastgroup
        value = m.group()
        pos = m.start()

        # Skip whitespace and comments
        if kind in {"WHITESPACE", "COMMENT", "MCOMMENT"}:
            continue

        # Keywords vs identifiers
        elif kind == "ID":
            if value in KEYWORDS:
                tokens.append(Token(TokenType.KW, value, pos))
            else:
                tokens.append(Token(TokenType.ID, value, pos))

        # Literals
        elif kind == "NUMBER":
            tokens.append(Token(TokenType.NUMBER, value, pos))
        elif kind == "CHAR":
            tokens.append(Token(TokenType.CHAR, value, pos))
        elif kind == "STRING":
            tokens.append(Token(TokenType.STRING, value, pos))

        # Operators
        elif kind in {"OP", "SINGLE"}:
            tokens.append(Token(TokenType.OP, value, pos))

        else:
            raise SyntaxError(f"Unknown token kind {kind} at position {pos}")

    tokens.append(Token(TokenType.EOF, "", len(code)))
    return tokens


# ------------------------
# Example usage
# ------------------------
if __name__ == "__main__":
    code = r"""
    int main() {
        int x = 42;
        float y = 3.14;
        char c = 'a'; // this is a comment
        string s = "Hello, world!"; // this is another comment
        
        string s1 = "this is not // a comment";
        string t1 = "this /* is also not */ a comment";

        Record Point { x, y } 
        Point p = Point(1, 2);

        auto f = [](int x, int y) -> int {
            /* This is a
               multi-line
               comment */
            return x + y;
        };

        Point p = Point { x: 1, y: 2 };

        int arr[2][2] = {{1, 2}, {3, 4}};

        if (x < y) {
            x = x + 1;
        } else {
            x = x - 1;
        }
        return x;
    }
    """
    tokens = tokenize(code)
    for t in tokens:
        print(t)
