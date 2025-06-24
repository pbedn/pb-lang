from __future__ import annotations

import re
from enum import Enum, auto
from typing import List, NamedTuple


# ───────────────────────── token object ─────────────────────────
class TokenType(Enum):
    # Keywords
    DEF = auto(); RETURN = auto(); IF = auto(); ELSE = auto(); ELIF = auto()
    WHILE = auto(); FOR = auto(); IN = auto(); IS = auto(); NOT = auto()
    AND = auto(); OR = auto(); BREAK = auto(); CONTINUE = auto(); PASS = auto()
    GLOBAL = auto(); IMPORT = auto(); FROM = auto(); CLASS = auto(); ASSERT = auto()
    TRUE = auto(); FALSE = auto(); NONE = auto()
    TRY = auto(); EXCEPT = auto(); FINALLY = auto(); RAISE = auto(); AS = auto()

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
    NEWLINE = auto(); NL = auto(); INDENT = auto(); DEDENT = auto(); EOF = auto(); COMMENT = auto()

    # Literals & Identifiers
    IDENTIFIER = auto(); INT_LIT = auto(); FLOAT_LIT = auto()
    STRING_LIT = auto();
    FSTRING_START = auto(); FSTRING_MIDDLE = auto(); FSTRING_END   = auto()


# ───────────────────────── token object ─────────────────────────
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
        text = self.value if isinstance(self.value, str) else str(self.value)
        lines = text.splitlines()
        if len(lines) == 1:
            return self.line, self.column + len(lines[0])
        else:
            return self.line + len(lines) - 1, len(lines[-1])


# ───────────────────────── misc helpers ─────────────────────────
class LexerError(Exception):
    def __init__(self, message, line, column):
        super().__init__(f"Lexer error at line {line}, column {column}: {message}")

# ───────────────────────── keywords ──────────────────────────
KEYWORDS = {
    "def": TokenType.DEF,
    "class": TokenType.CLASS,
    "return": TokenType.RETURN,
    "global": TokenType.GLOBAL,
    "import": TokenType.IMPORT,
    "from": TokenType.FROM,
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
    "not": TokenType.NOT,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "try": TokenType.TRY,
    "except": TokenType.EXCEPT,
    "finally": TokenType.FINALLY,
    "as": TokenType.AS,
    "raise": TokenType.RAISE,
    "True": TokenType.TRUE,
    "False": TokenType.FALSE,
    "None": TokenType.NONE,
}

# ───────────────────────── regex table ──────────────────────────
TOKEN_REGEX = [
    # two-char operators first
    (re.compile(r'=='), TokenType.EQ),
    (re.compile(r'!='), TokenType.NOTEQ),
    (re.compile(r'<='), TokenType.LTE),
    (re.compile(r'>='), TokenType.GTE),
    (re.compile(r'->'), TokenType.ARROW),
    (re.compile(r'\+='), TokenType.PLUSEQ),
    (re.compile(r'-='), TokenType.MINUSEQ),
    (re.compile(r'\*='), TokenType.STAREQ),
    (re.compile(r'//='), TokenType.FLOORDIVEQ),
    (re.compile(r'/='), TokenType.SLASHEQ),
    (re.compile(r'%='), TokenType.PERCENTEQ),
    (re.compile(r'//'), TokenType.FLOORDIV),
    
    # single-char punctuation
    (re.compile(r'\('), TokenType.LPAREN),
    (re.compile(r'\)'), TokenType.RPAREN),
    (re.compile(r'\['), TokenType.LBRACKET),
    (re.compile(r'\]'), TokenType.RBRACKET),
    (re.compile(r'\{'), TokenType.LBRACE),
    (re.compile(r'\}'), TokenType.RBRACE),
    (re.compile(r':'), TokenType.COLON),
    (re.compile(r';'), TokenType.SEMICOLON),
    (re.compile(r','), TokenType.COMMA),
    (re.compile(r'='), TokenType.ASSIGN),
    (re.compile(r'\+'), TokenType.PLUS),
    (re.compile(r'-'), TokenType.MINUS),
    (re.compile(r'\*'), TokenType.STAR),
    (re.compile(r'/'), TokenType.SLASH),
    (re.compile(r'%'), TokenType.PERCENT),
    (re.compile(r'<'), TokenType.LT),
    (re.compile(r'>'), TokenType.GT),
    (re.compile(r'\.'), TokenType.DOT),
    
    # numeric literals (underscore allowed)
    (re.compile(r'\d[\d_]*\.\d[\d_]*[eE][+-]?\d[\d_]*'), TokenType.FLOAT_LIT),  # Fraction + Exponent; 12.34e5, 6.02_2e+23
    (re.compile(r'\d[\d_]*[eE][+-]?\d[\d_]*'), TokenType.FLOAT_LIT),            # Integer + Exponent; 10e-3, 1_6e2
    (re.compile(r'\d[\d_]*\.\d[\d_]*'), TokenType.FLOAT_LIT),                   # Simple Fraction (no exponent); 3.1415, 0.5, 2_5.0
    (re.compile(r'\d[\d_]*'), TokenType.INT_LIT),
    
    # plain string literals
    (re.compile(r'"(?:\\.|[^"\\])*"'), TokenType.STRING_LIT),
    (re.compile(r"'(?:\\.|[^'\\])*'"), TokenType.STRING_LIT),

    # identifiers
    (re.compile(r'[A-Za-z_][A-Za-z0-9_]*'), TokenType.IDENTIFIER),
]

WHITESPACE = re.compile(r'[ \t]*')

def split_comment(line: str) -> tuple[str, str | None, int | None]:
    """Return code portion and comment from a line.

    If a ``#`` is encountered outside quotes, returns the code before the
    comment, the comment text (including ``#``), and the 1-based column where
    the comment starts. If no comment is present, returns the line and ``None``
    values.
    """
    result = []
    in_string = False
    string_char = ''
    escape = False
    for idx, c in enumerate(line):
        if escape:
            result.append(c)
            escape = False
        elif c == '\\':
            result.append(c)
            escape = True
        elif in_string:
            result.append(c)
            if c == string_char:
                in_string = False
        else:
            if c in ('"', "'"):
                in_string = True
                string_char = c
                result.append(c)
            elif c == '#':
                return ''.join(result), line[idx:], idx + 1
            else:
                result.append(c)
    return ''.join(result), None, None


# ───────────────────────── lexer proper ─────────────────────────
class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.tokens: List[Token] = []
        self.lines = source.splitlines(keepends=False)
        self.indents = [0]
        self.line_num = 0
        self.bracket_depth = 0

    # public API --------------------------------------------------
    def tokenize(self) -> List[Token]:
        while self.line_num < len(self.lines):
            self._tokenize_line()
        # DEDENT to level 0
        while len(self.indents) > 1:
            self.indents.pop()
            self.tokens.append(Token(TokenType.DEDENT, "", self.line_num + 1, 1))
        self.tokens.append(Token(TokenType.EOF, "", self.line_num + 1, 1))
        return self.tokens

    # single line -------------------------------------------------
    def _tokenize_line(self):
        raw = self.lines[self.line_num]; self.line_num += 1
        code, comment, comment_col = split_comment(raw)
        line = code.rstrip()

        indent_width = 0
        if line.strip():
            indent_str   = WHITESPACE.match(line).group(0)
            if " " in indent_str and "\t" in indent_str:
                raise LexerError("Mixed tabs and spaces in indentation", self.line_num, 1)
            indent_width = len(indent_str.replace("\t", "    "))
            self._emit_indentation(indent_width)

        # scan the rest of the line
        pos, length = indent_width, len(line)
        while pos < length:
            ch = line[pos]

            if ch in " \t":
                pos += 1; continue

            if (ch in 'fF') and pos + 1 < length and line[pos+1] in ('"', "'"):
                    pos = self._scan_fstring(line, pos)
                    continue

            for regex, ttype in TOKEN_REGEX:
                m = regex.match(line, pos)
                if not m:
                    continue

                text, value = m.group(0), m.group(0)

                # promote keywords
                if ttype == TokenType.IDENTIFIER and value in KEYWORDS:
                    ttype = KEYWORDS[value]

                # numeric literals – strip underscores
                elif ttype in (TokenType.INT_LIT, TokenType.FLOAT_LIT):
                    value = value.replace("_", "")

                # plain strings – decode escapes
                elif ttype == TokenType.STRING_LIT:
                    inner = value[1:-1]
                    value = bytes(inner, "utf-8").decode("unicode_escape")

                # emit
                self.tokens.append(Token(ttype, value, self.line_num, pos + 1))

                if ttype in (TokenType.LPAREN, TokenType.LBRACKET, TokenType.LBRACE):
                    self.bracket_depth += 1
                elif ttype in (TokenType.RPAREN, TokenType.RBRACKET, TokenType.RBRACE):
                    if self.bracket_depth > 0:
                        self.bracket_depth -= 1
                pos = m.end()
                break
            else:
                snippet = line[pos:pos + 10]
                raise LexerError(f"Unknown token {snippet!r}", self.line_num, pos + 1)

        if comment is not None:
            self.tokens.append(Token(TokenType.COMMENT, comment, self.line_num, comment_col))

        nl_type = TokenType.NEWLINE if self.bracket_depth == 0 else TokenType.NL
        self.tokens.append(Token(nl_type, "", self.line_num, len(raw)))

    def _tokenize_expr(self, expr: str, base_line: int, base_col: int) -> None:
        """
        Tokenize the expression string inside f-string braces as normal code.
        base_line and base_col specify where this expression starts in the source for accurate token positions.
        """
        pos = 0
        length = len(expr)

        while pos < length:
            ch = expr[pos]

            if ch in ' \t\r\n':
                pos += 1
                continue

            for regex, ttype in TOKEN_REGEX:
                m = regex.match(expr, pos)
                if not m:
                    continue
                text = m.group(0)
                value = text
                # promote keywords
                if ttype == TokenType.IDENTIFIER and value in KEYWORDS:
                    ttype = KEYWORDS[value]
                elif ttype in (TokenType.INT_LIT, TokenType.FLOAT_LIT):
                    value = value.replace("_", "")
                elif ttype == TokenType.STRING_LIT:
                    inner = value[1:-1]
                    value = bytes(inner, "utf-8").decode("unicode_escape")

                self.tokens.append(Token(ttype, value, base_line, base_col + pos + 1))
                pos = m.end()
                if ttype in (TokenType.LPAREN, TokenType.LBRACKET, TokenType.LBRACE):
                    self.bracket_depth += 1
                elif ttype in (TokenType.RPAREN, TokenType.RBRACKET, TokenType.RBRACE):
                    if self.bracket_depth > 0:
                        self.bracket_depth -= 1
                break
            else:
                snippet = expr[pos:pos + 10]
                raise LexerError(f"Unknown token in f-string expression: {snippet!r}", base_line, base_col + pos + 1)

    # helpers -----------------------------------------------------
    def _emit_indentation(self, width: int):
        cur = self.indents[-1]
        if width > cur:
            self.indents.append(width)
            self.tokens.append(Token(TokenType.INDENT, "", self.line_num, 1))
        elif width < cur:
            while width < self.indents[-1]:
                self.indents.pop()
                self.tokens.append(Token(TokenType.DEDENT, "", self.line_num, 1))
            if width != self.indents[-1]:
                raise LexerError("Inconsistent indentation", self.line_num, 1)

    def _scan_fstring(self, line: str, start_pos: int) -> int:
        """Scan an f-string from the starting quote. Returns the position after closing quote."""
        prefix = line[start_pos]           # 'f' or 'F'
        quote_char = line[start_pos + 1]   # '"' or "'"
        delim = prefix + quote_char
        pos = start_pos + 2                # skip f and the quote
        col = start_pos + 1

        self._emit_token(TokenType.FSTRING_START, delim, col)

        buf: list[str] = []
        while pos < len(line):
            ch = line[pos]

            # handle escaped braces {{ or }}
            if ch == '{' and self._peek(line, pos+1) == '{':
                buf.append('{')
                pos += 2; continue
            if ch == '}' and self._peek(line, pos+1) == '}':
                buf.append('}')
                pos += 2; continue

            # enter expression
            if ch == '{':
                if buf:
                    self._emit_literal(buf, col)
                expr_end, expr = self._extract_braced_expression(line, pos)
                # Tokenize expr inside braces normally with _tokenize_expr
                self._emit_token(TokenType.LBRACE, '{', pos + 1)  # emit opening brace as operator
                self._tokenize_expr(expr, self.line_num, pos + 2)
                self._emit_token(TokenType.RBRACE, '}', expr_end)  # emit closing brace as operator
                pos = expr_end
                col = pos + 1
                continue

            # closing quote?
            if ch == quote_char:
                if buf:
                    self._emit_literal(buf, col)
                self._emit_token(TokenType.FSTRING_END, quote_char, pos + 1)
                return pos + 1

            buf.append(ch)
            pos += 1

        raise self._syntax_error("Unterminated f-string", pos)


    def _emit_literal(self, buf: list[str], col: int) -> None:
        """Emit FSTRING_MIDDLE token from accumulated literal text."""
        text = ''.join(buf)
        self._emit_token(TokenType.FSTRING_MIDDLE, text, col)
        buf.clear()

    def _extract_braced_expression(self, line: str, start_pos: int) -> tuple[int, str]:
        """Extract a balanced {expression}, return (end_pos, expr_text)."""
        pos = start_pos + 1  # Skip initial '{'
        depth = 1
        expr_start = pos
        while pos < len(line):
            ch = line[pos]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return pos + 1, line[expr_start:pos]
            pos += 1
        raise self._syntax_error("Unterminated expression in f-string", start_pos + 1)

    def _peek(self, line: str, pos: int) -> str:
        """Return character at pos if in bounds, else empty string."""
        return line[pos] if pos < len(line) else ''

    def _emit_token(self, kind: TokenType, text: str, col: int) -> None:
        self.tokens.append(Token(kind, text, self.line_num, col))

    def _syntax_error(self, msg: str, col: int) -> SyntaxError:
        return SyntaxError(f"{msg} at line {self.line_num}, column {col}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Provide sample code")
        exit(1)
    source = ''
    try:
        with open(sys.argv[1], 'r') as fin:
            source = fin.read()
    except (FileExistsError, FileNotFoundError):
        source = sys.argv[1]
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    for token in tokens:
        print(token)
