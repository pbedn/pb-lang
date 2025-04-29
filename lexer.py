class Token:
    def __init__(self, kind, value):
        self.kind = kind
        self.value = value

    def __repr__(self):
        return f"Token({self.kind}, {self.value})"

class Lexer:
    def __init__(self, code):
        self.code = code
        self.pos = 0

    def advance(self):
        self.pos += 1

    def peek(self):
        return self.code[self.pos] if self.pos < len(self.code) else '\0'

    def tokenize(self):
        tokens = []
        while self.pos < len(self.code):
            ch = self.code[self.pos]

            if ch.isspace():
                self.advance()
                continue

            if ch == '-' and self.pos + 1 < len(self.code) and self.code[self.pos + 1] == '>':
                self.advance()
                self.advance()
                tokens.append(Token("ARROW", "->"))
                continue

            if ch == '(':
                tokens.append(Token("LPAREN", ch))
                self.advance()
                continue

            if ch == ')':
                tokens.append(Token("RPAREN", ch))
                self.advance()
                continue

            if ch == ':':
                tokens.append(Token("COLON", ch))
                self.advance()
                continue

            if ch == ',':
                tokens.append(Token("COMMA", ch))
                self.advance()
                continue

            if ch == '"':
                self.advance()
                start = self.pos
                while self.peek() != '"' and self.peek() != '\0':
                    self.advance()
                value = self.code[start:self.pos]
                tokens.append(Token("STRING", value))
                self.advance()  # closing "
                continue

            if ch.isdigit():
                start = self.pos
                while self.peek().isdigit():
                    self.advance()
                tokens.append(Token("NUMBER", self.code[start:self.pos]))
                continue

            if ch.isalpha() or ch == '_':
                start = self.pos
                while self.peek().isalnum() or self.peek() == '_':
                    self.advance()
                word = self.code[start:self.pos]

                if word == "def":
                    tokens.append(Token("DEF", word))
                elif word == "return":
                    tokens.append(Token("RETURN", word))
                elif word == "print":
                    tokens.append(Token("PRINT", word))
                else:
                    tokens.append(Token("IDENT", word))
                continue

            raise Exception(f"Unexpected character: {ch}")

        return tokens

if __name__ == "__main__":
    with open("test.pyc") as f:
        code = f.read()
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    print(tokens)
