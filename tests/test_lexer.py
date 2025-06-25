# test_lexer.py
import unittest

from lexer import Lexer, LexerError, TokenType

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

    def test_from_keyword(self):
        code = 'from utils import helper\n'
        types = [t.type.name for t in Lexer(code).tokenize()]
        self.assertIn("FROM", types)

    def test_as_keyword(self):
        code = 'from utils import helper as h\n'
        types = [t.type.name for t in Lexer(code).tokenize()]
        self.assertIn("AS", types)

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
        types = [t.type.name for t in tokens]

        self.assertIn("FSTRING_START", types)
        self.assertIn("FSTRING_MIDDLE", types)
        self.assertIn("FSTRING_END", types)
        self.assertIn("IDENTIFIER", types)

        name_tokens = [t for t in tokens if t.type.name == "IDENTIFIER" and t.value == "name"]
        self.assertEqual(len(name_tokens), 1)

        parts = [(t.type.name, t.value) for t in tokens if t.type.name.startswith("FSTRING")]
        expected = [
            ("FSTRING_START", 'f"'),
            ("FSTRING_MIDDLE", 'hello '),
            ("FSTRING_END", '"'),
        ]
        self.assertEqual(parts, expected)

    def test_hash_inside_string(self):
        code = 's = "#notcomment"\n'
        tokens = Lexer(code).tokenize()
        lits = [t for t in tokens if t.type.name == "STRING_LIT"]
        self.assertEqual(len(lits), 1)
        self.assertEqual(lits[0].value, "#notcomment")

    def test_raw_string_literal(self):
        code = 's = r"line\\nnext"\n'
        tokens = Lexer(code).tokenize()
        vals = [t.value for t in tokens if t.type == TokenType.STRING_LIT]
        self.assertIn("line\\nnext", vals)

    def test_multiline_string_literal(self):
        code = (
            's = """hello\nworld"""\n'
        )
        tokens = Lexer(code).tokenize()
        vals = [t.value for t in tokens if t.type == TokenType.STRING_LIT]
        self.assertEqual(vals, ["hello\nworld"])

    def test_pipe_token(self):
        tokens = Lexer('x: int | None\n').tokenize()
        self.assertTrue(any(t.type == TokenType.PIPE for t in tokens))

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
    # def test_invalid_fstring_placeholders(self):
    #     bad_sources = [
    #         'f"{x + 1}"\n',   # expression
    #         'f"{123}"\n',     # numeric
    #         'f"{x!r}"\n',     # conversion flag
    #     ]
    #     for src in bad_sources:
    #         with self.subTest(src=src):
    #             with self.assertRaises(LexerError):
    #                 self.lex(src)

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

class TestFStringLexing(unittest.TestCase):

    def assertTokenSequence(self, tokens, expected):
        actual = [(t.type.name, t.value) for t in tokens if t.type.name in {e[0] for e in expected}]
        for expected_type, expected_val in expected:
            self.assertIn((expected_type, expected_val), actual)

    def test_basic_f_string(self):
        code = 'a = f"Hello {name}"\n'
        tokens = Lexer(code).tokenize()
        types = [t.type.name for t in tokens]

        self.assertIn("FSTRING_START", types)
        self.assertIn("FSTRING_MIDDLE", types)
        self.assertIn("FSTRING_END", types)
        self.assertIn("IDENTIFIER", types)

        self.assertTokenSequence(tokens, [
            ("FSTRING_START", 'f"'),
            ("FSTRING_MIDDLE", "Hello "),
            ("IDENTIFIER", "name"),
            ("FSTRING_END", '"')
        ])

    def test_f_string_with_attribute(self):
        code = 'b = f"{user.name}"\n'
        tokens = Lexer(code).tokenize()

        self.assertTokenSequence(tokens, [
            ("FSTRING_START", 'f"'),
            ("IDENTIFIER", "user"),
            ("DOT", "."),
            ("IDENTIFIER", "name"),
            ("FSTRING_END", '"')
        ])

    def test_f_string_with_method_call(self):
        code = 'f = f"{obj.method()}"\n'
        tokens = Lexer(code).tokenize()

        self.assertTokenSequence(tokens, [
            ("FSTRING_START", 'f"'),
            ("IDENTIFIER", "obj"),
            ("DOT", "."),
            ("IDENTIFIER", "method"),
            ("LPAREN", "("),
            ("RPAREN", ")"),
            ("FSTRING_END", '"')
        ])

    # NOT SUPPORTED YET
    # def test_f_string_with_conversion(self):
    #     code = 'g = f"{value!r}"\n'
    #     tokens = Lexer(code).tokenize()

    #     self.assertTokenSequence(tokens, [
    #         ("FSTRING_START", 'f"'),
    #         ("IDENTIFIER", "value"),
    #         ("EXCLAMATION", "!"),
    #         ("IDENTIFIER", "r"),
    #         ("FSTRING_END", '"')
    #     ])

    # def test_f_string_with_format_spec(self):
    #     code = 'h = f"{price:.2f}"\n'
    #     tokens = Lexer(code).tokenize()

    #     self.assertTokenSequence(tokens, [
    #         ("FSTRING_START", 'f"'),
    #         ("IDENTIFIER", "price"),
    #         ("COLON", ":"),
    #         ("FLOAT_LIT", ".2f"),
    #         ("FSTRING_END", '"')
    #     ])

    # def test_f_string_with_conversion_and_format_spec(self):
    #     code = 'i = f"{value!s:.2f}"\n'
    #     tokens = Lexer(code).tokenize()

    #     self.assertTokenSequence(tokens, [
    #         ("FSTRING_START", 'f"'),
    #         ("IDENTIFIER", "value"),
    #         ("EXCLAMATION", "!"),
    #         ("IDENTIFIER", "s"),
    #         ("COLON", ":"),
    #         ("FLOAT_LIT", ".2f"),
    #         ("FSTRING_END", '"')
    #     ])

    def test_f_string_with_escaped_braces(self):
        code = 'j = f"{{escaped}} {var}}}"\n'
        tokens = Lexer(code).tokenize()

        # Should produce a middle literal with '{escaped}'
        self.assertTokenSequence(tokens, [
            ("FSTRING_START", 'f"'),
            ("FSTRING_MIDDLE", "{escaped} "),
            ("IDENTIFIER", "var"),
            ("FSTRING_END", '"')
        ])

    def test_f_string_with_multiple_expressions(self):
        code = 'k = f"{a} + {b} = {a + b}"\n'
        tokens = Lexer(code).tokenize()

        self.assertIn("PLUS", [t.type.name for t in tokens])
        self.assertTokenSequence(tokens, [
            ("FSTRING_START", 'f"'),
            ("IDENTIFIER", "a"),
            ("FSTRING_MIDDLE", " + "),
            ("IDENTIFIER", "b"),
            ("FSTRING_MIDDLE", " = "),
            ("IDENTIFIER", "a"),
            ("PLUS", "+"),
            ("IDENTIFIER", "b"),
            ("FSTRING_END", '"')
        ])

    def test_nl_tokens_for_multiline_expr(self):
        code = (
            "total = (\n"
            "    1 +\n"
            "    2\n"
            ")\n"
        )
        tokens = Lexer(code).tokenize()
        nls = [t.type.name for t in tokens if t.type in (TokenType.NEWLINE, TokenType.NL)]
        self.assertEqual(nls, ["NL", "NL", "NL", "NEWLINE"])

    def test_comment_token_emitted(self):
        code = 'x = 1  # important\n'
        tokens = Lexer(code).tokenize()
        comments = [t for t in tokens if t.type == TokenType.COMMENT]
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].value, "# important")

if __name__ == "__main__":
    unittest.main()
