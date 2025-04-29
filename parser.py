class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def advance(self):
        self.pos += 1

    def expect(self, kind):
        tok = self.peek()
        if not tok or tok.kind != kind:
            raise Exception(f"Expected {kind}, got {tok}")
        self.advance()
        return tok

    def parse(self):
        functions = []
        while self.peek():
            functions.append(self.parse_function())
        return functions

    def parse_function(self):
        self.expect("DEF")
        name = self.expect("IDENT").value
        self.expect("LPAREN")
        params = []
        while self.peek().kind != "RPAREN":
            param_name = self.expect("IDENT").value
            self.expect("COLON")
            param_type = self.expect("IDENT").value
            params.append((param_name, param_type))
            if self.peek().kind == "COMMA":
                self.advance()
        self.expect("RPAREN")
        self.expect("ARROW")
        return_type = self.expect("IDENT").value
        self.expect("COLON")
        body = self.parse_body()
        return ("function", name, params, return_type, body)

    def parse_body(self):
        stmts = []
        while self.peek() and self.peek().kind in {"PRINT", "RETURN"}:
            if self.peek().kind == "PRINT":
                stmts.append(self.parse_print())
            elif self.peek().kind == "RETURN":
                stmts.append(self.parse_return())
        return stmts

    def parse_print(self):
        self.expect("PRINT")
        self.expect("LPAREN")
        arg = self.expect("STRING").value
        self.expect("RPAREN")
        return ("print", arg)

    def parse_return(self):
        self.expect("RETURN")
        value = self.expect("NUMBER").value
        return ("return", int(value))

if __name__ == "__main__":
    from lexer import Lexer
    with open("test.pyc") as f:
        code = f.read()
    tokens = Lexer(code).tokenize()
    parser = Parser(tokens)
    tree = parser.parse()
    print(tree)
