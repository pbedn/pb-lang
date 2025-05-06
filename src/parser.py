from lexer import TokenType
from lang_ast import *

class ParserError(Exception):
    pass

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.in_function_body = False

    def current(self):
        return self.tokens[self.pos]

    def advance(self):
        self.pos += 1

    def check(self, *types):
        return self.current().type in types

    def match(self, *types):
        if self.current().type in types:
            tok = self.current()
            self.advance()
            return tok
        return None

    def expect(self, type_):
        tok = self.match(type_)
        if not tok:
            print(f"[DEBUG] expect failed: expected {type_}, but got {self.current()}")
            raise ParserError(f"Expected {type_} at line {self.current().line}")
        return tok

    def parse(self):
        body = []
        while self.current().type != TokenType.EOF:
            stmt = self.parse_global_stmt()
            body.append(stmt)
        return Program(body)

    def parse_global_stmt(self):
        if self.match(TokenType.DEF):
            return self.parse_function()
        elif self.match(TokenType.CLASS):
                return self.parse_class_def()
        elif self.current().type == TokenType.IDENTIFIER:
            # Peek ahead for VarDecl (Identifier : Type = ...)
            next_type = self.tokens[self.pos + 1].type
            if next_type == TokenType.COLON:
                return self.parse_vardecl()
        raise ParserError(f"Only function definitions and typed variable declarations are allowed at the top level (line {self.current().line})")

    def finish_assignment(self, expr):
        if not isinstance(expr, (Identifier, AttributeExpr, IndexExpr)):
            raise ParserError(f"Invalid assignment target at line {self.current().line}")
        self.expect(TokenType.ASSIGN)
        value = self.parse_expr()
        self.expect(TokenType.NEWLINE)
        return AssignStmt(expr, value)

    def finish_aug_assignment(self, expr):
        if not isinstance(expr, (Identifier, AttributeExpr, IndexExpr)):
            raise ParserError(f"Invalid assignment target at line {self.current().line}")
        op_tok = self.match(
            TokenType.PLUSEQ, TokenType.MINUSEQ, TokenType.STAREQ,
            TokenType.SLASHEQ, TokenType.PERCENTEQ,
        )
        op_map = {
            TokenType.PLUSEQ: "+",
            TokenType.MINUSEQ: "-",
            TokenType.STAREQ: "*",
            TokenType.SLASHEQ: "/",
            TokenType.PERCENTEQ: "%",
        }
        op = op_map[op_tok.type]
        value = self.parse_expr()
        self.expect(TokenType.NEWLINE)
        return AugAssignStmt(expr, op, value)

    def parse_stmt(self):
        if self.match(TokenType.DEF):
            if self.in_function_body:
                raise ParserError(f"Nested function definitions are not allowed (line {self.current().line})")
            return self.parse_function()

        elif self.match(TokenType.CLASS):
            return self.parse_class_def()

        elif self.match(TokenType.RETURN):
            expr = self.parse_expr()
            self.expect(TokenType.NEWLINE)
            return ReturnStmt(expr)

        elif self.match(TokenType.GLOBAL):
            names = []
            while True:
                names.append(self.expect(TokenType.IDENTIFIER).value)
                if not self.match(TokenType.COMMA):
                    break
            self.expect(TokenType.NEWLINE)
            return GlobalStmt(names)

        elif self.match(TokenType.IF):
            return self.parse_if()

        elif self.match(TokenType.WHILE):
            return self.parse_while()

        elif self.match(TokenType.FOR):
            return self.parse_for()

        elif self.match(TokenType.BREAK):
            self.expect(TokenType.NEWLINE)
            return BreakStmt()

        elif self.match(TokenType.CONTINUE):
            self.expect(TokenType.NEWLINE)
            return ContinueStmt()

        if self.match(TokenType.ASSERT):
            return self.parse_assert_stmt()

        elif self.match(TokenType.PASS):
            self.expect(TokenType.NEWLINE)
            return PassStmt()

        elif self.current().type == TokenType.IDENTIFIER:
            if self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].type == TokenType.COLON:
                return self.parse_vardecl()
            expr = self.parse_identifier_or_call()
            if self.check(TokenType.ASSIGN):
                return self.finish_assignment(expr)
            elif self.check(
                TokenType.PLUSEQ, TokenType.MINUSEQ, TokenType.STAREQ,
                TokenType.SLASHEQ, TokenType.PERCENTEQ,
            ):
                return self.finish_aug_assignment(expr)
            else:
                self.expect(TokenType.NEWLINE)
                return expr

        else:
            raise ParserError(f"Unknown statement at line {self.current().line}")

    def parse_vardecl(self):
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.COLON)
        type_tok = self.match(TokenType.IDENTIFIER, TokenType.INT, TokenType.FLOAT, TokenType.BOOL, TokenType.STR)
        if not type_tok:
            raise ParserError(f"Expected type after ':' at line {self.current().line}")
        declared_type = type_tok.value
        if not self.match(TokenType.ASSIGN):
            raise ParserError(f"Global variable declaration must include an initializer (line {self.current().line})")
        value = self.parse_expr()
        self.expect(TokenType.NEWLINE)
        return VarDecl(name, declared_type, value)

    def parse_assignment(self):
        target = self.parse_assignment_target()
        self.expect(TokenType.ASSIGN)
        value = self.parse_expr()
        self.expect(TokenType.NEWLINE)
        return AssignStmt(target, value)


    def parse_aug_assignment(self):
        target = self.parse_assignment_target()
        op_tok = self.match(
            TokenType.PLUSEQ, TokenType.MINUSEQ, TokenType.STAREQ,
            TokenType.SLASHEQ, TokenType.PERCENTEQ,
        )
        if not op_tok:
            raise ParserError(f"Expected augmented assignment operator at line {self.current().line}")
        op_map = {
            TokenType.PLUSEQ: "+",
            TokenType.MINUSEQ: "-",
            TokenType.STAREQ: "*",
            TokenType.SLASHEQ: "/",
            TokenType.PERCENTEQ: "%",
        }
        op = op_map[op_tok.type]
        value = self.parse_expr()
        self.expect(TokenType.NEWLINE)
        return AugAssignStmt(target, op, value)

    def parse_assignment_target(self):
        expr = self.parse_identifier_or_call()
        if isinstance(expr, CallExpr):
            raise ParserError(f"Invalid assignment target at line {self.current().line}")
        # Optionally: enforce valid targets here: Identifier, AttributeExpr, IndexExpr
        if not isinstance(expr, (Identifier, AttributeExpr, IndexExpr)):
            raise ParserError(f"Invalid assignment target at line {self.current().line}")
        return expr

    def parse_function(self):
        print(f"[DEBUG] parse_function: current token before name: {self.current()}")
        name_tok = self.expect(TokenType.IDENTIFIER)
        print(f"[DEBUG] parse_function: got function name: {name_tok.value}")
        self.expect(TokenType.LPAREN)
        params = []
        if self.current().type != TokenType.RPAREN:
            while True:
                param_name = self.expect(TokenType.IDENTIFIER).value
                param_type = "int"  # default type
                if self.match(TokenType.COLON):
                    type_tok = self.match(TokenType.IDENTIFIER, TokenType.INT, TokenType.FLOAT, TokenType.BOOL, TokenType.STR)
                    if not type_tok:
                        raise ParserError(f"Expected type after ':' at line {self.current().line}")
                    param_type = type_tok.value
                params.append((param_name, param_type))
                if not self.match(TokenType.COMMA):
                    break

        self.expect(TokenType.RPAREN)

        return_type = None
        if self.match(TokenType.ARROW):
            return_type_tok = self.match(TokenType.IDENTIFIER, TokenType.INT, TokenType.FLOAT, TokenType.BOOL, TokenType.STR)
            if not return_type_tok:
                raise ParserError(f"Expected return type at line {self.current().line}")
            return_type = return_type_tok.value

        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.expect(TokenType.INDENT)
        body = []
        globals_declared = set()
        self.in_function_body = True
        while not self.match(TokenType.DEDENT):
            stmt = self.parse_stmt()
            if isinstance(stmt, GlobalStmt):
                globals_declared.update(stmt.names)
            body.append(stmt)
        self.in_function_body = False
        return FunctionDef(name_tok.value, params, body, return_type, globals_declared=globals_declared)

    def parse_class_def(self):
        name = self.expect(TokenType.IDENTIFIER).value
        base = None
        if self.match(TokenType.LPAREN):
            base = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.RPAREN)
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.expect(TokenType.INDENT)

        fields = []
        methods = []
        saw_method = False

        while not self.match(TokenType.DEDENT):
            print(f"[DEBUG] parse_class_def: current token at start of loop: {self.current()}")
            if self.match(TokenType.NEWLINE):
                continue

            if self.check(TokenType.PASS):
                if fields or methods:
                    raise ParserError(f"'pass' must be the only statement in class body (line {self.current().line})")
                pass_stmt = self.parse_stmt()
                methods.append(pass_stmt)

                # After pass, nothing else allowed before dedent:
                while not self.match(TokenType.DEDENT):
                    if self.match(TokenType.NEWLINE):
                        continue
                    raise ParserError(f"No statements allowed after 'pass' in class body (line {self.current().line})")
                break  # Exit the class body

            if self.match(TokenType.DEF):
                print(f"[DEBUG] parse_class_def: entering method parsing")
                method = self.parse_function()
                methods.append(method)
                saw_method = True
            elif self.check(TokenType.IDENTIFIER):
                if saw_method:
                    raise ParserError(f"Fields must be declared before methods (line {self.current().line})")
                # Field
                next_type = self.tokens[self.pos + 1].type
                if next_type == TokenType.COLON:
                    field = self.parse_vardecl()
                    fields.append(field)
                else:
                    raise ParserError(f"Unexpected statement in class body at line {self.current().line}")
            else:
                raise ParserError(f"Only methods, fields, or 'pass' allowed in class body (line {self.current().line})")

        return ClassDef(name, base, fields, methods)

    def parse_assert_stmt(self):
        expr = self.parse_expr()
        self.expect(TokenType.NEWLINE)
        return AssertStmt(expr)

    def parse_if(self):
        cond = self.parse_expr()
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.expect(TokenType.INDENT)
        then_body = []
        while not self.match(TokenType.DEDENT):
            then_body.append(self.parse_stmt())

        else_body = None
        if self.match(TokenType.ELIF):
            else_body = [self.parse_if()]  # desugar elif into nested if
        elif self.match(TokenType.ELSE):
            self.expect(TokenType.COLON)
            self.expect(TokenType.NEWLINE)
            self.expect(TokenType.INDENT)
            else_body = []
            while not self.match(TokenType.DEDENT):
                else_body.append(self.parse_stmt())

        return IfStmt(cond, then_body, else_body)


    def parse_while(self):
        cond = self.parse_expr()
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.expect(TokenType.INDENT)
        body = []
        while not self.match(TokenType.DEDENT):
            body.append(self.parse_stmt())
        return WhileStmt(cond, body)

    def parse_for(self):
        var_name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.IN)
        iterable = self.parse_expr()
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.expect(TokenType.INDENT)
        body = []
        while not self.match(TokenType.DEDENT):
            body.append(self.parse_stmt())
        return ForStmt(var_name, iterable, body)

    def parse_expr(self):
        return self.parse_or()

    def parse_or(self):
        expr = self.parse_and()
        while self.match(TokenType.OR):
            right = self.parse_and()
            expr = BinOp(expr, "or", right)
        return expr

    def parse_and(self):
        expr = self.parse_comparison()
        while self.match(TokenType.AND):
            right = self.parse_comparison()
            expr = BinOp(expr, "and", right)
        return expr

    def parse_comparison(self):
        expr = self.parse_add_sub()
        while self.current().type in {
            TokenType.EQ, TokenType.NOTEQ,
            TokenType.LT, TokenType.LTE,
            TokenType.GT, TokenType.GTE,
            TokenType.IS
        }:
            if self.current().type == TokenType.IS:
                self.advance()
                if self.match(TokenType.NOT):
                    op = "is not"
                else:
                    op = "is"
            else:
                op = self.current().value
                self.advance()
            right = self.parse_add_sub()
            expr = BinOp(expr, op, right)
        return expr

    def parse_add_sub(self):
        expr = self.parse_term()
        while self.current().type in (TokenType.PLUS, TokenType.MINUS):
            op = self.current().value
            self.advance()
            right = self.parse_term()
            expr = BinOp(expr, op, right)
        return expr

    def parse_term(self):
        expr = self.parse_factor()
        while self.current().type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self.current().value
            self.advance()
            right = self.parse_factor()
            expr = BinOp(expr, op, right)
        return expr

    def parse_factor(self):
        tok = self.current()
        if tok.type == TokenType.MINUS:
            self.advance()
            return UnaryOp('-', self.parse_factor())
        elif tok.type == TokenType.NOT:
            self.advance()
            return UnaryOp('not', self.parse_factor())
        elif tok.type == TokenType.INT_LIT:
            self.advance()
            return Literal(int(tok.value))
        elif tok.type == TokenType.FLOAT_LIT:
            self.advance()
            return Literal(float(tok.value))
        elif tok.type == TokenType.STRING_LIT:
            self.advance()
            return Literal(tok.value)
        elif tok.type == TokenType.IDENTIFIER:
            return self.parse_identifier_or_call()
        elif tok.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expr()
            self.expect(TokenType.RPAREN)
            return expr
        elif tok.type == TokenType.LBRACKET:
            return self.parse_list()
        elif tok.type == TokenType.LBRACE:
            return self.parse_dict()
        else:
            raise ParserError(f"Unexpected token {tok.type} at line {tok.line}")

    def parse_identifier_or_call(self):
        name = self.expect(TokenType.IDENTIFIER).value
        expr = Identifier(name)
        # Function call
        if self.match(TokenType.LPAREN):
            args = []
            if self.current().type != TokenType.RPAREN:
                while True:
                    args.append(self.parse_expr())
                    if not self.match(TokenType.COMMA):
                        break
            self.expect(TokenType.RPAREN)
            expr = CallExpr(expr, args)

        while True:
            # Handle indexing (mylist[0][1] ...)
            if self.match(TokenType.LBRACKET):
                index = self.parse_expr()
                self.expect(TokenType.RBRACKET)
                expr = IndexExpr(expr, index)
            elif self.match(TokenType.DOT):
                attr = self.expect(TokenType.IDENTIFIER).value
                expr = AttributeExpr(expr, attr)
            else:
                break

        return expr

    def parse_list(self):
        self.expect(TokenType.LBRACKET)
        elements = []
        if self.current().type != TokenType.RBRACKET:
            while True:
                elements.append(self.parse_expr())
                if not self.match(TokenType.COMMA):
                    break
        self.expect(TokenType.RBRACKET)
        return ListExpr(elements)

    def parse_dict(self):
        self.expect(TokenType.LBRACE)
        pairs = []
        if self.current().type != TokenType.RBRACE:
            while True:
                key = self.parse_expr()
                self.expect(TokenType.COLON)
                value = self.parse_expr()
                pairs.append((key, value))
                if not self.match(TokenType.COMMA):
                    break
        self.expect(TokenType.RBRACE)
        return DictExpr(pairs)
