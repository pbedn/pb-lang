# lexer.py
import re
from pprint import pprint
from enum import Enum, auto
from typing import List, NamedTuple


class TokenType(Enum):
    # Keywords
    DEF = auto(); RETURN = auto(); IF = auto(); ELSE = auto(); ELIF = auto()
    WHILE = auto(); FOR = auto(); IN = auto(); IS = auto()
    INT = auto(); FLOAT = auto(); BOOL = auto(); STR = auto(); NOT = auto()
    AND = auto(); OR = auto(); BREAK = auto(); CONTINUE = auto(); PASS = auto()
    GLOBAL = auto(); IMPORT = auto(); CLASS = auto(); ASSERT = auto()
    TRUE = auto(); FALSE = auto()
    TRY = auto(); EXCEPT = auto(); RAISE = auto()

    # Symbols
    COLON = auto(); COMMA = auto(); LPAREN = auto(); RPAREN = auto()
    LBRACKET = auto(); RBRACKET = auto(); LBRACE = auto(); RBRACE = auto()
    ASSIGN = auto(); PLUS = auto(); MINUS = auto(); STAR = auto(); SLASH = auto()
    PERCENT = auto(); FLOORDIV = auto(); DOT = auto(); SEMICOLON = auto()

    ## augmented assignment
    PLUSEQ = auto(); MINUSEQ = auto(); STAREQ = auto(); SLASHEQ = auto()
    PERCENTEQ = auto(); FLOORDIVEQ = auto()

    EQ = auto(); NOTEQ = auto(); LT = auto(); LTE = auto(); GT = auto(); GTE = auto()
    ARROW = auto()

    # Structure
    NEWLINE = auto(); INDENT = auto(); DEDENT = auto(); EOF = auto()

    # Literals & Identifiers
    IDENTIFIER = auto(); INT_LIT = auto(); FLOAT_LIT = auto()
    STRING_LIT = auto(); FSTRING_LIT = auto()

class Token(NamedTuple):
    type: TokenType
    value: str
    line: int
    column: int

    def __repr__(self):
        start_line, start_col = self.line, self.column
        end_line, end_col = self._compute_end_position()

        # Format layout: line,col-line,col: TOKEN_TYPE_PADDED 'value'
        position = f"{start_line},{start_col}-{end_line},{end_col}:"
        type_name = f"{self.type.name:<16}"  # Right-align in 16-character field
        value_repr = f"{repr(self.value)}"
        return f"{position:<16} {type_name} {value_repr}"  # Position left-aligned, type right-aligned

    def _compute_end_position(self):
        if not self.value:
            return self.line, self.column
        lines = self.value.splitlines()
        if len(lines) == 1:
            return self.line, self.column + len(lines[0])
        else:
            return self.line + len(lines) - 1, len(lines[-1])


class LexerError(Exception):
    def __init__(self, message, line, column):
        super().__init__(f"LexerError at line {line}, column {column}: {message}")


KEYWORDS = {
    "def": TokenType.DEF,
    "class": TokenType.CLASS,
    "return": TokenType.RETURN,
    "global": TokenType.GLOBAL,
    "import": TokenType.IMPORT,
    "assert": TokenType.ASSERT,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "elif": TokenType.ELIF,
    "while": TokenType.WHILE,
    "for": TokenType.FOR,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "pass": TokenType.PASS,
    "in": TokenType.IN,
    "is": TokenType.IS,
    "int": TokenType.INT,
    "float": TokenType.FLOAT,
    "bool": TokenType.BOOL,
    "str": TokenType.STR,
    "not": TokenType.NOT,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "try": TokenType.TRY,
    "except": TokenType.EXCEPT,
    "raise": TokenType.RAISE,
    "True": TokenType.TRUE,
    "False": TokenType.FALSE,
}

TOKEN_REGEX = [
    (r'==', TokenType.EQ),
    (r'!=', TokenType.NOTEQ),
    (r'<=', TokenType.LTE),
    (r'>=', TokenType.GTE),
    (r'->', TokenType.ARROW),
    (r'\+=', TokenType.PLUSEQ),
    (r'-=', TokenType.MINUSEQ),
    (r'\*=', TokenType.STAREQ),
    (r'//=', TokenType.FLOORDIVEQ),
    (r'/=', TokenType.SLASHEQ),
    (r'%=', TokenType.PERCENTEQ),
    (r'//', TokenType.FLOORDIV),
    (r'\(', TokenType.LPAREN),
    (r'\)', TokenType.RPAREN),
    (r'\[', TokenType.LBRACKET),
    (r'\]', TokenType.RBRACKET),
    (r'\{', TokenType.LBRACE),
    (r'\}', TokenType.RBRACE),
    (r':', TokenType.COLON),
    (r';', TokenType.SEMICOLON),
    (r',', TokenType.COMMA),
    (r'=', TokenType.ASSIGN),
    (r'\+', TokenType.PLUS),
    (r'-', TokenType.MINUS),
    (r'\*', TokenType.STAR),
    (r'/', TokenType.SLASH),
    (r'%', TokenType.PERCENT),
    (r'<', TokenType.LT),
    (r'>', TokenType.GT),
    (r'\.', TokenType.DOT),
    
    # F-string patterns must precede regular string patterns
    (r'f"(?:\\.|[^"\\])*"', TokenType.FSTRING_LIT),
    (r"f'(?:\\.|[^'\\])*'", TokenType.FSTRING_LIT),
    # Numeric literals with optional underscores
    (r'\d[\d_]*\.\d[\d_]*[eE][+-]?\d[\d_]*', TokenType.FLOAT_LIT), # Fraction + Exponent; 12.34e5, 6.02_2e+23
    (r'\d[\d_]*[eE][+-]?\d[\d_]*', TokenType.FLOAT_LIT),           # Integer + Exponent; 10e-3, 1_6e2
    (r'\d[\d_]*\.\d[\d_]*', TokenType.FLOAT_LIT),                  # Simple Fraction (no exponent); 3.1415, 0.5, 2_5.0
    (r'\d[\d_]*', TokenType.INT_LIT),
    (r'"(?:\\.|[^"\\])*"', TokenType.STRING_LIT),
    (r"'(?:\\.|[^'\\])*'", TokenType.STRING_LIT),
    (r'[A-Za-z_][A-Za-z0-9_]*', TokenType.IDENTIFIER),
]


WHITESPACE = re.compile(r'[ \t]*')


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.tokens: List[Token] = []
        self.lines = source.splitlines()
        self.indents = [0]
        self.line_num = 0

    def tokenize(self) -> List[Token]:
        while self.line_num < len(self.lines):
            self._tokenize_line()
        while len(self.indents) > 1:
            self.tokens.append(Token(TokenType.DEDENT, "", self.line_num + 1, 0))
            self.indents.pop()
        self.tokens.append(Token(TokenType.EOF, "", self.line_num + 1, 0))
        return self.tokens

    def _tokenize_line(self):
        raw_line = self.lines[self.line_num]
        self.line_num += 1
        line = raw_line.rstrip()

        # Handle comments
        comment_start = line.find('#')
        if comment_start != -1:
            line = line[:comment_start]

        if not line.strip():
            return  # skip empty or comment-only line

        if '\t' in line and ' ' in line:
            raise LexerError("Mixed tabs and spaces in indentation", self.line_num, 0)
        line = line.replace('\t', '    ')

        indent_match = WHITESPACE.match(line)
        indent = len(indent_match.group(0)) if indent_match else 0
        pos = indent

        # Indentation handling
        if indent > self.indents[-1]:
            self.indents.append(indent)
            self.tokens.append(Token(TokenType.INDENT, "", self.line_num, 0))
        elif indent < self.indents[-1]:
            while indent < self.indents[-1]:
                self.indents.pop()
                self.tokens.append(Token(TokenType.DEDENT, "", self.line_num, 0))
            if indent != self.indents[-1]:
                raise LexerError("Inconsistent indentation", self.line_num, 0)

        while pos < len(line):
            char = line[pos]
            if char in ' \t':
                pos += 1
                continue

            matched = False
            for pattern, ttype in TOKEN_REGEX:
                regex = re.compile(pattern)
                match = regex.match(line, pos)
                if match:
                    text = match.group(0)
                    value = text

                    if ttype == TokenType.IDENTIFIER and text in KEYWORDS:
                        ttype = KEYWORDS[text]
                    elif ttype in [TokenType.INT_LIT, TokenType.FLOAT_LIT]:
                        value = text.replace('_', '')
                    elif ttype in [TokenType.STRING_LIT, TokenType.FSTRING_LIT]:
                        try:
                            value = bytes(text[1:-1], "utf-8").decode("unicode_escape")
                        except Exception:
                            raise LexerError("Invalid string escape sequence", self.line_num, pos + 1)

                    self.tokens.append(Token(ttype, value, self.line_num, pos + 1))
                    pos = match.end()
                    matched = True
                    break
            if not matched:
                raise LexerError("Unknown token", self.line_num, pos + 1)

        self.tokens.append(Token(TokenType.NEWLINE, "", self.line_num, len(line)))

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Provide sample code")
        exit(1)

    source = sys.argv[1]
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    for token in tokens:
        print(token)
