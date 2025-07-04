from dataclasses import dataclass
from typing import Generic, List, Type, Optional
from lexer import Token, TokenType
from lang_ast import (
    Program,
    Identifier,
    Literal,
    Stmt,
    StringLiteral,
    FStringLiteral,
    FStringText,
    FStringExpr,
    UnaryOp,
    Expr,
    BinOp,
    ExprStmt,
    ReturnStmt,
    VarDecl,
    AssignStmt,
    AugAssignStmt,
    IfBranch,
    IfStmt,
    WhileStmt,
    ForStmt,
    BreakStmt,
    ContinueStmt,
    PassStmt,
    Parameter,
    FunctionDef,
    ClassDef,
    GlobalStmt,
    AssertStmt,
    RaiseStmt,
    TryExceptStmt,
    ExceptBlock,
    CallExpr,
    AttributeExpr,
    IndexExpr,
    ListExpr,
    SetExpr,
    DictExpr,
    EllipsisLiteral,
    ImportStmt,
    ImportFromStmt,
    ImportAlias,
)


@dataclass
class Comment:
    text: str
    line: int
    column: int
    kind: str = "inline"


class ParserError(Exception):
    pass


class Parser:
    def __init__(self, tokens: List[Token]):
        self.comments: List[Comment] = [
            Comment(t.value, t.line, t.column)
            for t in tokens
            if t.type == TokenType.COMMENT
        ]
        self.tokens: List[Token] = [
            t for t in tokens if t.type not in (TokenType.COMMENT, TokenType.NL)
        ]
        self.pos: int = 0
        self.loop_depth: int = 0      # > 0 → inside while/for
        self.fn_depth:   int = 0      # > 0 → inside def

    # ───────────────────────── low‑level helpers ─────────────────────────
    def current(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> None:
        if not self.at_end():
            self.pos += 1

    def check(self, *types) -> bool:
        return self.current().type in types

    def match(self, *types: TokenType) -> bool:
        if self.current().type in types:
            self.advance()
            return True
        return False

    def peek(self, offset=1) -> Token:
        index = self.pos + offset
        if index < len(self.tokens):
            return self.tokens[index]
        return self.tokens[-1]

    def peek_debug(self, offset=0) -> Token:
        tok = self.peek(offset)
        print(f"[DEBUG] peek({offset}) = {tok}")
        return tok

    def expect(self, type_: TokenType) -> Token:
        tok = self.current()
        if tok.type != type_:
            raise ParserError(f"Expected `{type_.name}`, got `{tok.type.name}` at line: {tok.line}, col: {tok.column}, token: `{tok.value}`")
        self.advance()
        return tok

    def at_end(self) -> bool:
        return self.current().type == TokenType.EOF

    # ───────────────────────── entry‑point ─────────────────────────

    def parse(self) -> Program:
        """Parse a complete program

        This is the top-level entry point.
        
        Grammar fragment:
        Program ::= { Statement } EOF
        AST target: Program(body)
        """
        body: list[Stmt] = []

        while not self.at_end():
            if self.check(TokenType.NEWLINE):
                self.advance()
                continue
            # print(f"[DEBUG]: Peek next token: {self.peek()}")

            stmt = self.parse_statement()
            if isinstance(stmt, ExprStmt):
                raise ParserError(
                    f"Function call `{stmt.expr.func.name}` not allowed in global scope."
                )

            if isinstance(
                stmt,
                (WhileStmt, ForStmt, TryExceptStmt, RaiseStmt, AssertStmt, PassStmt),
            ):
                raise ParserError(
                    f"Statement `{stmt.__class__.__name__[:-4]}` not allowed in global scope."
                )

            if isinstance(stmt, IfStmt):
                if (
                    len(stmt.branches) == 1
                    and isinstance(stmt.branches[0].condition, BinOp)
                    and stmt.branches[0].condition.op == "=="
                    and isinstance(stmt.branches[0].condition.left, Identifier)
                    and stmt.branches[0].condition.left.name == "__name__"
                    and isinstance(stmt.branches[0].condition.right, StringLiteral)
                    and stmt.branches[0].condition.right.value == "__main__"
                ):
                    # Ignore this Python-style entry point guard.
                    continue
                raise ParserError(
                    f"Statement `{stmt.__class__.__name__[:-4]}` not allowed in global scope."
                )

            body.append(stmt)
        return Program(body)

    # ───────────────────────── expressions ─────────────────────────

    def parse_identifier(self) -> Expr:
        """Parse a single identifier like: x, foo, my_var
        
        Grammar fragment: Identifier ::= <IDENTIFIER>
        AST target: Identifier(name)
        """
        tok = self.expect(TokenType.IDENTIFIER)
        return Identifier(name=tok.value)

    def parse_literal(self) -> Expr:
        """Parse raw literals like: 123, 3.14, "hello"
        
        Grammar fragment: Literal ::= INT_LIT | FLOAT_LIT | STRING_LIT
        AST target: Literal(raw), StringLiteral(value, is_fstring)
        """
        tok = self.current()
        if tok.type in (TokenType.INT_LIT, TokenType.FLOAT_LIT):
            self.advance()
            return Literal(raw=tok.value)
        if tok.type in (TokenType.TRUE, TokenType.FALSE, TokenType.NONE):
            self.advance()
            return Literal(raw=tok.value)
        if tok.type == TokenType.STRING_LIT:
            self.advance()
            return StringLiteral(value=tok.value)
        if tok.type == TokenType.FSTRING_START:
            return self.parse_fstring_literal()
        raise ParserError(f"Expected literal, got {tok.type.name} at {tok.line},{tok.column}")

    def parse_fstring_literal(self) -> FStringLiteral:
        """Parse an f-string with parts like:
        - f"static text"
        - f"prefix {expr}"
        - f"value: {score:.2f}"
        Supports literal chunks and embedded expressions with optional format spec.
        """
        self.expect(TokenType.FSTRING_START)
        parts: list[FStringText | FStringExpr] = []

        while not self.check(TokenType.FSTRING_END):
            if self.match(TokenType.FSTRING_MIDDLE):
                tok = self.tokens[self.pos - 1]
                parts.append(FStringText(text=tok.value))

            elif self.match(TokenType.LBRACE):
                expr = self.parse_expr()
                fmt = None

                if self.match(TokenType.COLON):
                    if self.check(TokenType.STRING_LIT, TokenType.FLOAT_LIT):
                        fmt_token = self.current()
                        self.advance()
                        fmt = fmt_token.value
                    else:
                        tok = self.current()
                        raise ParserError(f"Expected format specifier after ':', got {tok.type.name} at {tok.line},{tok.column}")

                self.expect(TokenType.RBRACE)
                parts.append(FStringExpr(expr=expr, format_spec=fmt))

            else:
                tok = self.current()
                raise ParserError(f"Unexpected token `{tok.type.name}` inside f-string at line {tok.line}, col {tok.column}")

        self.expect(TokenType.FSTRING_END)
        return FStringLiteral(parts=parts)

    def parse_unary(self) -> Expr:
        """Handle unary operators like: -x, not x

        Grammar: UnaryExpr ::= ("-" | "not") UnaryExpr | Primary
        This is recursive: unary ops apply to another unary or primary expression.
        AST: UnaryOp(op, operand)
        """
        if self.match(TokenType.MINUS):
            operand = self.parse_unary()
            return UnaryOp("-", operand)
        elif self.match(TokenType.NOT):
            operand = self.parse_unary()
            return UnaryOp("not", operand)

        return self.parse_postfix_expr()

    def parse_postfix_expr(self) -> Expr:
        """Parse a primary expression with optional postfix operators

        Grammar fragment:
        PostfixExpr ::= Primary { "(" [Expr { "," Expr}] ")" }
        
        This supports function calls like:
            - foo()
            - foo(x, y + 1)
            - (a + b)(c)

        Returns:
            CallExpr, Identifier, Literal, etc.
        """
        expr = self.parse_primary()
        return self.parse_postfix(expr)

    def parse_postfix(self, expr: Expr) -> Expr:
        """Parse any postfix operations after a primary expression:
        - Function calls: expr(...)
        - Attribute access: expr.attr
          AttributeExpr ::= Expr "." Identifier
        - Indexing: expr[expr]
          IndexExpr ::= Expr "[" Expr "]"
        """
        while True:
            if self.match(TokenType.LPAREN):
                args = []
                if not self.check(TokenType.RPAREN):
                    args.append(self.parse_expr())
                    while self.match(TokenType.COMMA):
                        args.append(self.parse_expr())
                self.expect(TokenType.RPAREN)
                expr = CallExpr(func=expr, args=args)

            elif self.match(TokenType.DOT):
                attr_token = self.expect(TokenType.IDENTIFIER)
                expr = AttributeExpr(obj=expr, attr=attr_token.value)

            elif self.match(TokenType.LBRACKET):
                index = self.parse_expr()
                self.expect(TokenType.RBRACKET)
                expr = IndexExpr(base=expr, index=index)

            else:
                break

        return expr

    def parse_primary(self) -> Expr:
        """Handle the simplest atomic expressions and post‑fix calls:
        Identifiers: foo
        Literals: 123, 3.14, 'hello'
        Grouped expressions: (x + 1)
        Function calls: foo(), bar(x), obj.method(x)

        Grammar: Primary ::= Atom { "(" [Args] ")" }
        AST: Identifier, Literal, StringLiteral, CallExpr
        """
        tok = self.current()

        if tok.type == TokenType.IDENTIFIER:
            return self.parse_identifier()
        elif tok.type == TokenType.ELLIPSIS:
            self.advance()
            return EllipsisLiteral()
        elif tok.type in (TokenType.INT_LIT, TokenType.FLOAT_LIT, TokenType.STRING_LIT, TokenType.FSTRING_START, TokenType.TRUE, TokenType.FALSE, TokenType.NONE):
            return self.parse_literal()
        elif tok.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expr()
            self.expect(TokenType.RPAREN)
        elif tok.type == TokenType.LBRACKET:
            self.advance()
            elements = []
            if not self.check(TokenType.RBRACKET):
                elements.append(self.parse_expr())
                while self.match(TokenType.COMMA):
                    elements.append(self.parse_expr())
            self.expect(TokenType.RBRACKET)
            return ListExpr(elements)
        elif tok.type == TokenType.LBRACE:
            self.advance()
            if self.check(TokenType.RBRACE):
                self.advance()
                return DictExpr(keys=[], values=[])

            first = self.parse_expr()
            if self.match(TokenType.COLON):
                # dict literal
                keys = [first]
                values = [self.parse_expr()]
                while self.match(TokenType.COMMA):
                    if self.check(TokenType.RBRACE):
                        break  # allow trailing comma
                    key = self.parse_expr()
                    self.expect(TokenType.COLON)
                    value = self.parse_expr()
                    keys.append(key)
                    values.append(value)
                self.expect(TokenType.RBRACE)
                return DictExpr(keys, values)
            else:
                # set literal
                elements = [first]
                while self.match(TokenType.COMMA):
                    if self.check(TokenType.RBRACE):
                        break
                    elements.append(self.parse_expr())
                self.expect(TokenType.RBRACE)
                return SetExpr(elements)
        else:
            raise ParserError(f"Expected primary expression, got {tok.type.name} at {tok.line},{tok.column}")

        # Handle chained function calls: foo(), bar(x, y)
        while self.match(TokenType.LPAREN):
            args = []
            if not self.check(TokenType.RPAREN):
                args.append(self.parse_expr())
                while self.match(TokenType.COMMA):
                    args.append(self.parse_expr())
            self.expect(TokenType.RPAREN)
            expr = CallExpr(func=expr, args=args)

        return expr

    def parse_term(self) -> Expr:
        """Handle multiplicative expressions

        Builds the full left-associative expression tree in-place as it goes.

        a * b
        a / b
        a // b
        a % b
        Grammar fragment: Term ::= UnaryExpr { ("*" | "/" | "//" | "%") UnaryExpr }
        AST target: BinOp(left, op, right)
        """
        left = self.parse_unary()

        while self.current().type in (
            TokenType.STAR,
            TokenType.SLASH,
            TokenType.FLOORDIV,
            TokenType.PERCENT,
        ):
            op_token = self.current()
            self.advance()
            right = self.parse_unary()
            left = BinOp(left, op_token.value, right)

        return left

    def parse_arith_expr(self) -> Expr:
        """Handle additive expressions

        Builds the full left-associative expression tree in-place.

        a + b
        a - b
        a + b - c

        Grammar fragment: ArithExpr ::= Term { ("+" | "-") Term }
        AST target: BinOp(left, op, right)
        """
        left = self.parse_term()

        while self.current().type in (TokenType.PLUS, TokenType.MINUS):
            op_token = self.current()
            self.advance()
            right = self.parse_term()
            left = BinOp(left, op_token.value, right)

        return left

    def parse_comparison(self) -> Expr:
        """Handle comparison expressions, including chaining.

        Examples::

            a == b
            a != b
            a < b
            a is b
            1 < x < 10

        Grammar fragment::

            Comparison ::= ArithExpr ( ("==" | "!=" | "<" | "<=" | ">" | ">=" | "is" | "is not") ArithExpr )*

        AST target: nested ``BinOp`` expressions combined with ``and`` for chained comparisons.
        """
        left = self.parse_arith_expr()

        ops: list[str] = []
        comparators: list[Expr] = [left]

        while True:
            if self.current().type == TokenType.IS and self.peek().type == TokenType.NOT:
                self.advance()  # 'is'
                self.advance()  # 'not'
                ops.append("is not")
            elif self.current().type in (
                TokenType.EQ,
                TokenType.NOTEQ,
                TokenType.LT,
                TokenType.LTE,
                TokenType.GT,
                TokenType.GTE,
                TokenType.IS,
            ):
                op_token = self.current()
                self.advance()
                ops.append(op_token.value)
            else:
                break

            comparators.append(self.parse_arith_expr())

        if not ops:
            return left

        expr = BinOp(comparators[0], ops[0], comparators[1])
        for i in range(1, len(ops)):
            expr = BinOp(expr, "and", BinOp(comparators[i], ops[i], comparators[i + 1]))

        return expr

    def parse_not_expr(self) -> Expr:
        """Handle logical negation

        Recursive rule:
        not x
        not x == y → not (x == y)

        Grammar fragment:
        NotExpr ::= "not" NotExpr | Comparison
        AST target: UnaryOp(op="not", operand=...)
        """
        if self.match(TokenType.NOT):
            operand = self.parse_not_expr()
            return UnaryOp("not", operand)

        return self.parse_comparison()

    def parse_and_expr(self) -> Expr:
        """Handle logical conjunction

        Builds left-associative binary trees.

        a and b
        a and b and c

        Grammar fragment:
        AndExpr ::= NotExpr { "and" NotExpr }
        AST target: BinOp(left, op, right)
        """
        left = self.parse_not_expr()

        while self.match(TokenType.AND):
            right = self.parse_not_expr()
            left = BinOp(left, "and", right)

        return left

    def parse_or_expr(self) -> Expr:
        """Handle logical disjunction

        Builds left-associative binary trees.

        a or b
        a or b or c

        Grammar fragment:
        OrExpr ::= AndExpr { "or" AndExpr }
        AST target: BinOp(left, op, right)
        """
        left = self.parse_and_expr()

        while self.match(TokenType.OR):
            right = self.parse_and_expr()
            left = BinOp(left, "or", right)

        return left

    def parse_expr(self) -> Expr:
        """Top-level entry point for parsing expressions

        This simply delegates to the highest-precedence rule: OrExpr.

        Grammar fragment:
        Expr ::= OrExpr
        AST target: same as returned by OrExpr (e.g., BinOp, Identifier, Literal)
        """
        return self.parse_or_expr()

    # ───────────────────────── statements ─────────────────────────

    def parse_statement(self) -> Stmt:
        """Top-level dispatcher for parsing a single statement

        Determines the appropriate statement rule based on the current token.
        """

        while self.match(TokenType.NEWLINE):
            pass

        tok = self.current()

        if tok.type in (TokenType.IMPORT, TokenType.FROM):
            return self.parse_import_stmt()

        if tok.type == TokenType.CLASS:
            return self.parse_class_def()

        if tok.type == TokenType.DEF:
            return self.parse_function_def()

        if tok.type == TokenType.GLOBAL:
            return self.parse_global_stmt()

        if tok.type == TokenType.RETURN:
            return self.parse_return_stmt()

        if tok.type == TokenType.ASSERT:
            return self.parse_assert_stmt()

        if tok.type == TokenType.RAISE:
            return self.parse_raise_stmt()

        if tok.type == TokenType.TRY:
            return self.parse_try_except_stmt()

        if tok.type == TokenType.IF:
            return self.parse_if_stmt()

        if tok.type == TokenType.WHILE:
            return self.parse_while_stmt()

        if tok.type == TokenType.FOR:
            return self.parse_for_stmt()

        if tok.type == TokenType.IDENTIFIER:
            # Handle variable declaration
            if self.peek().type == TokenType.COLON:
                return self.parse_var_decl()

            # Start by parsing the expression (could be variable, call, attribute, etc.)
            expr = self.parse_expr()

            # Assignment
            if self.check(TokenType.ASSIGN):
                self.advance()
                value = self.parse_expr()
                self.expect(TokenType.NEWLINE)
                return AssignStmt(expr, value)

            # Augmented assignment
            if self.check(TokenType.PLUSEQ, TokenType.MINUSEQ, TokenType.STAREQ,
                          TokenType.SLASHEQ, TokenType.FLOORDIVEQ, TokenType.PERCENTEQ):
                op = self.current().value
                self.advance()
                value = self.parse_expr()
                self.expect(TokenType.NEWLINE)
                return AugAssignStmt(expr, op, value)

            # Fallback: plain expression statement
            self.expect(TokenType.NEWLINE)
            return ExprStmt(expr)

        if tok.type == TokenType.BREAK:
            return self.parse_break_stmt()

        if tok.type == TokenType.CONTINUE:
            return self.parse_continue_stmt()

        if tok.type == TokenType.PASS:
            return self.parse_pass_stmt()

        # Fallback: treat as expression statement
        return self.parse_expr_stmt()

    def parse_expr_stmt(self) -> ExprStmt:
        """Parse an expression used as a statement

        This is the fallback form of a statement in PB:
        any expression followed by a newline.

        Grammar fragment:
        ExprStmt ::= Expr NEWLINE
        AST target: ExprStmt(expr)
        """
        expr = self.parse_expr()
        self.expect(TokenType.NEWLINE)
        return ExprStmt(expr)

    def parse_return_stmt(self) -> ReturnStmt:
        """Parse a return statement

        Handles both `return` and `return <expr>`

        Grammar fragment:
        ReturnStmt ::= "return" [Expr] NEWLINE
        AST target: ReturnStmt(value)
        """
        if self.fn_depth == 0:
            raise ParserError("'return' outside function "
                              f"at {self.current().line},{self.current().column}")
        self.expect(TokenType.RETURN)

        if self.check(TokenType.NEWLINE):
            self.expect(TokenType.NEWLINE)
            return ReturnStmt(None)

        value = self.parse_expr()
        self.expect(TokenType.NEWLINE)
        return ReturnStmt(value)
    
    def parse_var_decl(self) -> VarDecl:
        """Parse a typed variable declaration, optionally with an initializer

        Grammar fragment:
        VarDecl ::= Identifier ":" Type ["=" Expr] NEWLINE
        AST target: VarDecl(name, declared_type, value)
        """
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.COLON)
        declared_type = self.parse_type()
        value: Optional[Expr] = None
        if self.match(TokenType.ASSIGN):
            value = self.parse_expr()
        self.expect(TokenType.NEWLINE)
        return VarDecl(name, declared_type, value)

    def parse_assign_stmt(self) -> AssignStmt:
        """Parse an assignment statement

        Supports assignment to variables or attributes.
        Example: x = 42

        Grammar fragment:
        Assignment ::= Expr \"=\" Expr NEWLINE
        AST target: AssignStmt(target, value)
        """
        target = self.parse_expr()
        self.expect(TokenType.ASSIGN)
        value = self.parse_expr()
        self.expect(TokenType.NEWLINE)
        return AssignStmt(target, value)

    def parse_aug_assign_stmt(self) -> AugAssignStmt:
        """Parse an augmented assignment statement

        Supports operators like +=, -=, *=, etc.

        Grammar fragment:
        AugAssignment ::= Expr AugOp Expr NEWLINE
        AST target: AugAssignStmt(target, op, value)
        """
        target = self.parse_expr()
        op_token = self.current()

        if op_token.type not in (
            TokenType.PLUSEQ,
            TokenType.MINUSEQ,
            TokenType.STAREQ,
            TokenType.SLASHEQ,
            TokenType.FLOORDIVEQ,
            TokenType.PERCENTEQ,
        ):
            raise ParserError(f"Expected augmented assignment operator, got {op_token.type.name} at {op_token.line},{op_token.column}")

        self.advance()
        value = self.parse_expr()
        self.expect(TokenType.NEWLINE)
        return AugAssignStmt(target, op_token.value, value)

    def parse_if_stmt(self) -> IfStmt:
        """Parse an if/elif/else statement

        Grammar fragment:
        IfStmt ::= \"if\" Expr \":\" NEWLINE INDENT { Statement } DEDENT
                   { \"elif\" Expr \":\" NEWLINE INDENT { Statement } DEDENT }
                   [ \"else\" \":\" NEWLINE INDENT { Statement } DEDENT ]

        AST target: IfStmt(branches=[IfBranch(condition, body)])
        """
        branches = []

        def parse_branch(with_condition: bool) -> IfBranch:
            cond = self.parse_expr() if with_condition else None
            self.expect(TokenType.COLON)
            self.expect(TokenType.NEWLINE)
            while self.match(TokenType.NEWLINE):
                pass
            self.expect(TokenType.INDENT)

            body = []
            while True:
                if self.match(TokenType.DEDENT):
                    break
                if self.check(TokenType.NEWLINE):
                    self.advance()
                    continue
                stmt = self.parse_statement()
                body.append(stmt)

            return IfBranch(cond, body)

        self.expect(TokenType.IF)
        branches.append(parse_branch(with_condition=True))

        while self.match(TokenType.ELIF):
            branches.append(parse_branch(with_condition=True))

        if self.match(TokenType.ELSE):
            branches.append(parse_branch(with_condition=False))

        return IfStmt(branches)

    def parse_while_stmt(self) -> WhileStmt:
        """Parse a while loop

        Grammar fragment:
        WhileStmt ::= \"while\" Expression \":\" NEWLINE INDENT { Statement } DEDENT
        AST target: WhileStmt(condition, body)
        """
        self.expect(TokenType.WHILE)
        condition = self.parse_expr()
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        while self.match(TokenType.NEWLINE):
            pass
        self.expect(TokenType.INDENT)

        body: List[Stmt] = []
        self.loop_depth += 1
        while True:
            if self.match(TokenType.DEDENT):
                break
            if self.check(TokenType.NEWLINE):
                self.advance()
                continue
            body.append(self.parse_statement())
        self.loop_depth -= 1

        return WhileStmt(condition, body)

    def parse_for_stmt(self) -> ForStmt:
        """Parse a for-in loop

        Grammar fragment:
        ForStmt ::= \"for\" Identifier \"in\" Expression \":\" NEWLINE INDENT { Statement } DEDENT
        AST target: ForStmt(var, iterable, body)
        """
        self.expect(TokenType.FOR)
        var = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.IN)
        iterable = self.parse_expr()
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        while self.match(TokenType.NEWLINE):
            pass
        self.expect(TokenType.INDENT)

        body: List[Stmt] = []
        self.loop_depth += 1
        while True:
            if self.match(TokenType.DEDENT):
                break
            if self.check(TokenType.NEWLINE):
                self.advance()
                continue
            body.append(self.parse_statement())
        self.loop_depth -= 1

        return ForStmt(var, iterable, body)

    def parse_break_stmt(self) -> BreakStmt:
        """Parse a break statement

        Grammar: BreakStmt ::= "break" NEWLINE
        AST: BreakStmt()
        """
        if self.loop_depth == 0:
            raise ParserError("'break' outside loop "
                              f"at {self.current().line},{self.current().column}")
        self.expect(TokenType.BREAK)
        self.expect(TokenType.NEWLINE)
        return BreakStmt()

    def parse_continue_stmt(self) -> ContinueStmt:
        """Parse a continue statement

        Grammar: ContinueStmt ::= "continue" NEWLINE
        AST: ContinueStmt()
        """
        if self.loop_depth == 0:
            raise ParserError("'continue' outside loop "
                              f"at {self.current().line},{self.current().column}")
        self.expect(TokenType.CONTINUE)
        self.expect(TokenType.NEWLINE)
        return ContinueStmt()

    def parse_pass_stmt(self) -> PassStmt:
        """Parse a pass statement

        Grammar: PassStmt ::= "pass" NEWLINE
        AST: PassStmt()
        """
        self.expect(TokenType.PASS)
        self.expect(TokenType.NEWLINE)
        return PassStmt()


    def parse_function_def(self) -> FunctionDef:
        """Parse a function definition

        Grammar:
        FunctionDef ::= "def" Identifier "(" [ Parameters ] ")" "->" Type ":" NEWLINE INDENT { Statement } DEDENT
        AST: FunctionDef(name, params, body, return_type)
        """
        self.expect(TokenType.DEF)
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LPAREN)

        params: List[Parameter] = []
        if not self.check(TokenType.RPAREN):
            params.append(self.parse_parameter())
            while self.match(TokenType.COMMA):
                params.append(self.parse_parameter())

        # Duplicate parameter names are an error
        names_seen = set()
        for p in params:
            if p.name in names_seen:
                raise ParserError(f"duplicate parameter '{p.name}' "
                                  f"in function '{name}'")
            names_seen.add(p.name)

        self.expect(TokenType.RPAREN)

        # If type not specified, it defaults to None
        return_type = "None"
        if self.match(TokenType.ARROW):
            if self.check(TokenType.COLON):
                raise ParserError("Return type annotation must not be followed by ':' "
                                  f"at line: {self.current().line}, col: {self.current().column}")
            return_type = self.expect_type_name()

        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        while self.match(TokenType.NEWLINE):
            pass
        self.expect(TokenType.INDENT)

        body: List[Stmt] = []
        self.fn_depth += 1
        while not self.match(TokenType.DEDENT):
            if self.check(TokenType.NEWLINE):
                self.advance()
                continue
            stmt = self.parse_statement()
            body.append(stmt)

        if len(body) > 1 and PassStmt() in body:
            raise ParserError("Function body must be empty when using `pass` statement")

        self.fn_depth -= 1

        if not body:
            raise ParserError("Function body cannot be empty "
                              f"(see {self.current().line},{self.current().column})")

        return FunctionDef(name, params, body, return_type)

    def parse_parameter(self) -> Parameter:
        name = self.expect(TokenType.IDENTIFIER).value
        type_name = None
        default = None
        if self.match(TokenType.COLON):
            type_name = self.expect_type_name()
        if self.match(TokenType.ASSIGN):      # "=" sign
            default = self.parse_expr()
        return Parameter(name, type_name, default)

    def expect_type_name(self) -> str:
        return self.parse_type()

    def parse_type(self) -> str:
        """Parse a (possibly generic) type annotation.

        Handles:
            int
            list[int]
            dict[str, int]
            list[dict[str, float]]
        Returns the fully spelled-out type as a plain string.
        """
        tok = self.current()
        if tok.type not in (
            TokenType.IDENTIFIER, TokenType.NONE
        ):
            raise ParserError(
                f"Expected type name, got {tok.type.name} "
                f"at {tok.line},{tok.column}"
            )

        # consume the base identifier / builtin name
        type_str = tok.value
        self.advance()

        # Optional generic arguments, e.g. "[" Type {"," Type} "]"
        if self.match(TokenType.LBRACKET):
            args = [self.parse_type()]           # first arg
            while self.match(TokenType.COMMA):
                args.append(self.parse_type())   # additional args
            self.expect(TokenType.RBRACKET)
            type_str += "[" + ", ".join(args) + "]"

        # Optional union with None using "|" syntax
        while self.match(TokenType.PIPE):
            rhs = self.parse_type()
            type_str += " | " + rhs

        return type_str

    def parse_class_def(self) -> ClassDef:
        """Parse a class definition with optional single inheritance

        Grammar:
        ClassDef ::= "class" Identifier [ "(" Identifier ")" ] ":" NEWLINE INDENT { Statement } DEDENT

        AST: ClassDef(name, base, fields, methods)
        """
        self.expect(TokenType.CLASS)
        name = self.expect(TokenType.IDENTIFIER).value

        base: Optional[str] = None
        if self.match(TokenType.LPAREN):
            base = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.RPAREN)

        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        while self.match(TokenType.NEWLINE):
            pass
        self.expect(TokenType.INDENT)

        fields: List[VarDecl] = []
        methods: List[FunctionDef] = []

        is_empty_with_pass = False

        while True:
            if self.match(TokenType.DEDENT):
                break
            if self.check(TokenType.NEWLINE):
                self.advance()
                continue
            stmt = self.parse_statement()
            if isinstance(stmt, VarDecl):
                fields.append(stmt)
            elif isinstance(stmt, FunctionDef):
                methods.append(stmt)
            elif isinstance(stmt, PassStmt):
                # empty body with pass is allowed
                is_empty_with_pass = True
                continue
            else:
                raise ParserError(f"Only variable declarations and methods allowed in class body at line {self.current().line}")

        if not (fields or methods or is_empty_with_pass):
            raise ParserError(f"class '{name}' has no body (line {self.current().line})")

        return ClassDef(name, base, fields, methods)

    def parse_global_stmt(self) -> GlobalStmt:
        """Parse a global declaration statement

        Grammar:
        GlobalStmt ::= "global" Identifier { "," Identifier } NEWLINE
        AST: GlobalStmt(names)
        """
        if self.fn_depth == 0:
            raise ParserError("'global' only allowed inside a function "
                              f"at {self.current().line},{self.current().column}")

        self.expect(TokenType.GLOBAL)
        names = [self.expect(TokenType.IDENTIFIER).value]

        while self.match(TokenType.COMMA):
            names.append(self.expect(TokenType.IDENTIFIER).value)

        self.expect(TokenType.NEWLINE)
        return GlobalStmt(names)

    def parse_assert_stmt(self) -> AssertStmt:
        """Parse an assert statement

        Grammar:
        AssertStmt ::= "assert" Expr NEWLINE
        AST: AssertStmt(condition)
        """
        self.expect(TokenType.ASSERT)
        condition = self.parse_expr()
        self.expect(TokenType.NEWLINE)
        return AssertStmt(condition)

    def parse_raise_stmt(self) -> RaiseStmt:
        """Parse a raise statement

        Grammar:
        RaiseStmt ::= "raise" [Expr] NEWLINE
        AST: RaiseStmt(exception_or_none)
        """
        self.expect(TokenType.RAISE)
        expr = None
        if not self.check(TokenType.NEWLINE):
            expr = self.parse_expr()
        self.expect(TokenType.NEWLINE)
        return RaiseStmt(expr)

    def parse_try_except_stmt(self) -> TryExceptStmt:
        """Parse a try/except statement

        Grammar:
        TryExceptStmt ::= "try" ":" NEWLINE INDENT { Statement } DEDENT
                          { "except" [Identifier] [ "as" Identifier ] ":" NEWLINE INDENT { Statement } DEDENT }
                          [ "finally" ":" NEWLINE INDENT { Statement } DEDENT ]
        AST: TryExceptStmt(try_body, except_blocks, finally_body?)
        """
        self.expect(TokenType.TRY)
        self.expect(TokenType.COLON)
        self.expect(TokenType.NEWLINE)
        self.expect(TokenType.INDENT)

        try_body: List[Stmt] = []
        while True:
            if self.match(TokenType.DEDENT):
                break
            if self.check(TokenType.NEWLINE):
                self.advance()
                continue
            try_body.append(self.parse_statement())

        except_blocks: List[ExceptBlock] = []

        while self.match(TokenType.EXCEPT):
            # Optional type
            if self.check(TokenType.IDENTIFIER):
                exc_type = self.expect(TokenType.IDENTIFIER).value
            else:
                exc_type = None

            # Optional alias
            alias = None
            if self.match(TokenType.AS):
                alias = self.expect(TokenType.IDENTIFIER).value

            self.expect(TokenType.COLON)
            self.expect(TokenType.NEWLINE)
            while self.match(TokenType.NEWLINE):
                pass
            self.expect(TokenType.INDENT)

            body: List[Stmt] = []
            while True:
                if self.match(TokenType.DEDENT):
                    break
                if self.check(TokenType.NEWLINE):
                    self.advance()
                    continue
                body.append(self.parse_statement())

            except_blocks.append(ExceptBlock(exc_type, alias, body))

        finally_body: Optional[List[Stmt]] = None

        if self.match(TokenType.FINALLY):
            self.expect(TokenType.COLON)
            self.expect(TokenType.NEWLINE)
            self.expect(TokenType.INDENT)
            finally_body = []
            while not self.match(TokenType.DEDENT):
                finally_body.append(self.parse_statement())

        return TryExceptStmt(try_body, except_blocks, finally_body)

    def parse_import_stmt(self) -> Stmt:
        """Parse an import or from-import statement.

        Grammar:
        ImportStmt      ::= "import" Identifier { "." Identifier } [ "as" Identifier ] NEWLINE
        ImportFromStmt  ::= "from" Identifier { "." Identifier } "import" (Identifier | "*") [ "as" Identifier ] {"," Identifier ["as" Identifier]} NEWLINE
        """
        if self.match(TokenType.FROM):
            module = [self.expect(TokenType.IDENTIFIER).value]
            while self.match(TokenType.DOT):
                module.append(self.expect(TokenType.IDENTIFIER).value)
            self.expect(TokenType.IMPORT)

            if self.match(TokenType.STAR):
                self.expect(TokenType.NEWLINE)
                loc = (self.tokens[self.pos-1].line, self.tokens[self.pos-1].column)
                return ImportFromStmt(module=module, names=None, is_wildcard=True, loc=loc)

            names: list[ImportAlias] = []

            name = self.expect(TokenType.IDENTIFIER).value
            asname = None
            if self.match(TokenType.AS):
                asname = self.expect(TokenType.IDENTIFIER).value
            names.append(ImportAlias(name, asname))

            while self.match(TokenType.COMMA):
                name = self.expect(TokenType.IDENTIFIER).value
                asname = None
                if self.match(TokenType.AS):
                    asname = self.expect(TokenType.IDENTIFIER).value
                names.append(ImportAlias(name, asname))

            self.expect(TokenType.NEWLINE)
            loc = (self.tokens[self.pos-1].line, self.tokens[self.pos-1].column)

            return ImportFromStmt(module=module, names=names, is_wildcard=False, loc=loc)

        self.expect(TokenType.IMPORT)
        module = [self.expect(TokenType.IDENTIFIER).value]

        while self.match(TokenType.DOT):
            module.append(self.expect(TokenType.IDENTIFIER).value)

        alias = None
        if self.match(TokenType.AS):
            alias = self.expect(TokenType.IDENTIFIER).value

        self.expect(TokenType.NEWLINE)

        loc = (self.tokens[self.pos-1].line, self.tokens[self.pos-1].column)
        return ImportStmt(module=module, alias=alias, loc=loc)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python script.py <code> [method]")
        print("Example: python script.py foo identifier")
        sys.exit(1)

    source = sys.argv[1]
    method = sys.argv[2]

    if method == "file":
        try:
            with open(f"{sys.argv[1]}", 'r') as fin:
                source = fin.read()
        except (FileExistsError, FileNotFoundError) as e:
            print(e)
            exit(1)

    from lexer import Lexer
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    import pprint
    pprint.pprint(tokens)
    parser = Parser(tokens)

    node = parser.parse()
    print(node)
