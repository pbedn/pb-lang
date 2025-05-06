import unittest

from lexer import Lexer, LexerError

class TestLexer(unittest.TestCase):
    def test_keywords_and_literals(self):
        code = 'def main() -> int:\n    return 42\n    print("hello")\n    if x == 1:\n        pass\n    else:\n        pass'
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type.name for t in tokens]
        for expected in ["DEF", "RETURN", "INT_LIT", "STRING_LIT", "IF", "ELSE", "EQ"]:
            self.assertIn(expected, types)

    def test_operators(self):
        code = 'a + b - c * d / e % f and g or not h'
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        ops = [t.value for t in tokens if t.type.name in ["PLUS", "MINUS", "STAR", "SLASH", "PERCENT", "AND", "OR", "NOT"]]
        for op in ['+', '-', '*', '/', '%', 'and', 'or', 'not']:
            self.assertIn(op, ops)

    def test_single_quoted_string(self):
        code = (
            "class Y:\n"
            "    s: str = 'abc'\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type.name for t in tokens]

        self.assertIn("STRING_LIT", types)

    def test_unterminated_string_literal(self):
        code = (
            "def main() -> int:\n"
            "    s = 'unterminated\n"
        )
        lexer = Lexer(code)
        with self.assertRaises(LexerError):
            lexer.tokenize()

    def test_mixed_tabs_and_spaces(self):
        code = (
            "def main() -> int:\n"
            "   \tprint('hello')\n"  # 3 spaces + 1 tab mixed on same line
        )
        lexer = Lexer(code)
        with self.assertRaises(LexerError):
            lexer.tokenize()

    def test_escape_in_single_quoted_string(self):
        code = (
            "def main() -> int:\n"
            "    print('line\\nnext')\n"
            "    return 0\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        values = [t.value for t in tokens if t.type.name == "STRING_LIT"]
        self.assertIn("line\nnext", values)

    def test_augmented_assignment_tokens(self):
        code = (
            "x += 1\n"
            "y -= 2\n"
            "z *= 3\n"
            "w /= 4\n"
            "v %= 5\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type.name for t in tokens]
        self.assertIn("PLUSEQ", types)
        self.assertIn("MINUSEQ", types)
        self.assertIn("STAREQ", types)
        self.assertIn("SLASHEQ", types)
        self.assertIn("PERCENTEQ", types)

    def test_global_keyword(self):
        code = 'global x, y'
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type.name for t in tokens]
        self.assertIn("GLOBAL", types)

    def test_simple_class(self):
        code = (
            "class Animal:\n"
            "    age: int\n"
            "\n"
            "    def speak(self):\n"
            "        print(\"Animal sound\")\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type.name for t in tokens]

        # Check we get CLASS and DEF tokens
        self.assertIn("CLASS", types)
        self.assertIn("DEF", types)
        self.assertIn("IDENTIFIER", types)
        self.assertIn("COLON", types)
        self.assertIn("INT", types)
        self.assertIn("STRING_LIT", types)

    def test_class_inheritance(self):
        code = (
            "class Dog(Animal):\n"
            "    breed: str\n"
            "\n"
            "    def speak(self):\n"
            "        print(\"Woof!\")\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type.name for t in tokens]

        self.assertIn("CLASS", types)
        self.assertIn("LPAREN", types)
        self.assertIn("RPAREN", types)
        self.assertIn("DEF", types)
        self.assertIn("STRING_LIT", types)

    def test_empty_class(self):
        code = (
            "class Empty:\n"
            "    pass\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type.name for t in tokens]

        self.assertIn("CLASS", types)
        self.assertIn("PASS", types)

    def test_class_with_field_initializers(self):
        code = (
            "class ABC:\n"
            "    a: str = 'b'\n"
            "    b: int = 1\n"
            "    c: List[int] = []\n"
            "\n"
            "    def method(ABC: int) -> str:\n"
            "        return 'a'\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type.name for t in tokens]

        self.assertIn("CLASS", types)
        self.assertIn("DEF", types)
        self.assertIn("IDENTIFIER", types)
        self.assertIn("COLON", types)
        self.assertIn("ASSIGN", types)
        self.assertIn("STRING_LIT", types)
        self.assertIn("INT_LIT", types)
        self.assertIn("LBRACKET", types)
        self.assertIn("RBRACKET", types)

    def test_complex_field_types(self):
        code = (
            "class Data:\n"
            "    items: Dict[str, List[int]] = {}\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type.name for t in tokens]
        self.assertIn("CLASS", types)
        self.assertIn("IDENTIFIER", types)
        self.assertIn("COLON", types)
        self.assertIn("ASSIGN", types)
        self.assertIn("LBRACKET", types)
        self.assertIn("RBRACKET", types)
