# test_lexer.py
import unittest

from lexer import Lexer, LexerError

class TestLexer(unittest.TestCase):
    def test_keywords_and_literals(self):
        code = (
            'def main() -> int:\n'
            '    return 42\n'
            '    print("hello")\n'
            '    if x == 1:\n'
            '        pass\n'
            '    else:\n'
            '        pass'
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type.name for t in tokens]
        for expected in [
            "DEF", "RETURN", "INT_LIT",
            "STRING_LIT", "IF", "ELSE", "EQ"
        ]:
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
        tokens = Lexer(code).tokenize()
        types = [t.type.name for t in tokens]
        for aug in ["PLUSEQ", "MINUSEQ", "STAREQ", "SLASHEQ", "PERCENTEQ"]:
            self.assertIn(aug, types)

    def test_global_keyword(self):
        code = 'global x, y'
        types = [t.type.name for t in Lexer(code).tokenize()]
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
        self.assertIn("IDENTIFIER", types)
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

    def test_assert_keyword(self):
        code = (
            "def main() -> int:\n"
            "    assert x > 0\n"
            "    return 0\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type.name for t in tokens]

        self.assertIn("ASSERT", types)

    def test_2d_list_indexing(self):
        code = (
            "grid = [[1, 2], [3, 4]]\n"
            "y = grid[1][0]\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type.name for t in tokens]

        # Check multiple bracket tokens exist
        self.assertGreaterEqual(types.count("LBRACKET"), 4)
        self.assertGreaterEqual(types.count("RBRACKET"), 4)

    def test_function_parameter_type_single_arg(self):
        code = (
            "def apply_twice(f: (int) -> int, x: int) -> int:\n"
            "    return f(f(x))\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type.name for t in tokens]

        self.assertIn("DEF", types)
        self.assertIn("IDENTIFIER", types)
        self.assertIn("LPAREN", types)
        self.assertIn("RPAREN", types)
        self.assertIn("ARROW", types)
        self.assertIn("COLON", types)
        self.assertIn("IDENTIFIER", types)

    def test_function_parameter_type_multi_arg(self):
        code = (
            "def apply_op(f: (int, int) -> int, a: int, b: int) -> int:\n"
            "    return f(a, b)\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type.name for t in tokens]

        self.assertIn("DEF", types)
        self.assertIn("LPAREN", types)
        self.assertIn("COMMA", types)
        self.assertIn("ARROW", types)
        self.assertIn("COLON", types)
        self.assertIn("IDENTIFIER", types)

    def test_class_as_function_parameter(self):
        code = (
            "class Player:\n"
            "    hp: int\n"
            "\n"
            "def heal(target: Player, amount: int):\n"
            "    target.hp += amount\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type.name for t in tokens]

        self.assertIn("CLASS", types)
        self.assertIn("DEF", types)
        self.assertIn("IDENTIFIER", types)
        self.assertIn("COLON", types)
        self.assertIn("IDENTIFIER", types)
        self.assertIn("DOT", types)

    def test_import_keyword(self):
        code = 'import utils\n'
        types = [t.type.name for t in Lexer(code).tokenize()]
        self.assertIn("IMPORT", types)

    def test_boolean_literals(self):
        code = 'x = True\ny = False\n'
        types = [t.type.name for t in Lexer(code).tokenize()]
        self.assertIn("TRUE", types)
        self.assertIn("FALSE", types)

    def test_numeric_literal_underscores(self):
        code = (
            'a = 1_000\n'
            'b = 3.14_15\n'
            'c = 2_5\n'
            'd = 6.022_140e+23\n'
        )
        tokens = Lexer(code).tokenize()
        ints = [t for t in tokens if t.type.name == "INT_LIT"]
        floats = [t for t in tokens if t.type.name == "FLOAT_LIT"]
        self.assertTrue(any(tok.value == '1000' for tok in ints))
        self.assertTrue(any(tok.value == '3.1415' for tok in floats))
        self.assertTrue(any(tok.value == '25' for tok in ints))
        self.assertTrue(any(tok.value.replace('.', '').startswith('6022140') for tok in floats))

    def test_f_string_literal(self):
        code = 'a = f"hello {name}"\n'
        tokens = Lexer(code).tokenize()

        fstr = [t for t in tokens if t.type.name == "FSTRING_LIT"]
        self.assertEqual(len(fstr), 1)

        raw, vars_ = fstr[0].value      # token.value is now a tuple
        self.assertEqual(raw,  "hello {name}")
        self.assertEqual(vars_, ["name"])

    def test_f_string_literal_attr_method_call(self):
        # Test with a class attribute
        code_method = 'b = f"Attribute: {obj.attribute}"\n'
        tokens_method = Lexer(code_method).tokenize()

        fstr_method = [t for t in tokens_method if t.type.name == "FSTRING_LIT"]
        self.assertEqual(len(fstr_method), 1)

        raw_method, vars_method = fstr_method[0].value
        self.assertEqual(raw_method, "Attribute: {obj.attribute}")
        self.assertEqual(vars_method, ["obj.attribute"])

        # Test with a method call
        code_function = 'c = f"Method: {obj.method()}"\n'
        tokens_function = Lexer(code_function).tokenize()

        fstr_function = [t for t in tokens_function if t.type.name == "FSTRING_LIT"]
        self.assertEqual(len(fstr_function), 1)

        raw_function, vars_function = fstr_function[0].value
        self.assertEqual(raw_function, "Method: {obj.method()}")
        self.assertEqual(vars_function, ["obj.method()"])

    def test_hash_inside_string(self):
        code = 's = "#notcomment"\n'
        tokens = Lexer(code).tokenize()
        lits = [t for t in tokens if t.type.name == "STRING_LIT"]
        self.assertEqual(len(lits), 1)
        self.assertEqual(lits[0].value, "#notcomment")

    @unittest.skip("Currently inserting new line is removed from lexer")
    def test_blank_line_generates_NEWLINE(self):
        code = "a=1\n\nb=2\n"
        tokens = Lexer(code).tokenize()
        newlines = [t for t in tokens if t.type.name == "NEWLINE"]
        # a=1, blank line, b=2 all generate NEWLINE, so at least 3
        self.assertGreaterEqual(len(newlines), 3)

    def test_indent_dedent_column(self):
        code = "if True:\n    x=1\n"
        tokens = Lexer(code).tokenize()
        indents = [t for t in tokens if t.type.name == "INDENT"]
        dedents = [t for t in tokens if t.type.name == "DEDENT"]
        self.assertTrue(indents and indents[0].column == 1)
        # the final DEDENT (after EOF) should also carry column 1
        self.assertTrue(dedents and all(d.column == 1 for d in dedents))

    def test_unknown_token_includes_lexeme(self):
        code = "a @ b\n"
        with self.assertRaises(LexerError) as cm:
            Lexer(code).tokenize()
        self.assertIn("@", str(cm.exception))


class TestLexerEdgeCases(unittest.TestCase):
    def lex(self, src: str):
        return Lexer(src).tokenize()

    # indentation ------------------------------------------------------
    def test_mixed_tabs_spaces_error(self):
        src = "def bad():\n\t  pass\n"
        with self.assertRaises(LexerError):
            self.lex(src)

    # strings ----------------------------------------------------------
    def test_unterminated_string(self):
        with self.assertRaises(LexerError):
            self.lex('"oops\n')

    # f-strings --------------------------------------------------------
    def test_invalid_fstring_placeholders(self):
        bad_sources = [
            'f"{x + 1}"\n',   # expression
            'f"{123}"\n',     # numeric
            'f"{x!r}"\n',     # conversion flag
        ]
        for src in bad_sources:
            with self.subTest(src=src):
                with self.assertRaises(LexerError):
                    self.lex(src)

    # numeric literals -------------------------------------------------
    def test_numeric_underscores(self):
        toks = self.lex("a = 1_234_567\nb = 3.14_15\n")
        ints   = [t for t in toks if t.type.name == "INT_LIT"]
        floats = [t for t in toks if t.type.name == "FLOAT_LIT"]

        self.assertEqual(ints[0].value,   "1234567")
        self.assertEqual(floats[0].value, "3.1415")

    def test_large_int_and_float(self):
        toks = self.lex("i = 9223372036854775808\nf = 1e309\n")
        self.assertTrue(any(t.value == "9223372036854775808" for t in toks))
        self.assertTrue(any(t.value == "1e309"               for t in toks))

    # token sequence for  `a is not b`
    def test_token_is_not(self):
        toks  = self.lex("a is not b\n")
        kinds = [t.type.name for t in toks if t.type.name not in ("NEWLINE", "EOF")]
        self.assertEqual(
            kinds,
            ["IDENTIFIER", "IS", "NOT", "IDENTIFIER"],
        )

if __name__ == "__main__":
    unittest.main()
