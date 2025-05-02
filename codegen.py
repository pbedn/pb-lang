from lang_ast import *

class CCodeGenerator:
    def __init__(self):
        self.indent_level = 0
        self.output = []
        self.defined_vars = set()

    def indent(self):
        return '    ' * self.indent_level

    def emit(self, line):
        self.output.append(self.indent() + line)

    def generate(self, program: Program) -> str:
        self.emit("#include <stdio.h>")
        self.emit("#include <stdbool.h>")
        self.emit("")
        for stmt in program.body:
            self.gen_stmt(stmt)
        return '\n'.join(self.output)

    def gen_stmt(self, stmt: Stmt):
        if isinstance(stmt, FunctionDef):
            ret_type = stmt.return_type or "void"
            args = ", ".join(
                f"int {p}" if isinstance(p, str) else f"{p[1]} {p[0]}"
                for p in stmt.params
                )
            self.emit(f"{ret_type} {stmt.name}({args}) {{")
            self.indent_level += 1
            self.defined_vars = set()  # reset per function
            for s in stmt.body:
                self.gen_stmt(s)
            self.indent_level -= 1
            self.emit("}")
            self.emit("")

        elif isinstance(stmt, ReturnStmt):
            expr = self.gen_expr(stmt.value)
            self.emit(f"return {expr};")

        elif isinstance(stmt, AssignStmt):
            expr = self.gen_expr(stmt.value)
            if stmt.target in self.defined_vars:
                self.emit(f"{stmt.target} = {expr};")
            else:
                self.emit(f"int {stmt.target} = {expr};")
                self.defined_vars.add(stmt.target)

        elif isinstance(stmt, IfStmt):
            cond = self.gen_expr(stmt.condition)
            self.emit(f"if ({cond}) {{")
            self.indent_level += 1
            for s in stmt.then_body:
                self.gen_stmt(s)
            self.indent_level -= 1
            self.emit("}")
            if stmt.else_body:
                self.emit("else {")
                self.indent_level += 1
                for s in stmt.else_body:
                    self.gen_stmt(s)
                self.indent_level -= 1
                self.emit("}")

        elif isinstance(stmt, WhileStmt):
            cond = self.gen_expr(stmt.condition)
            self.emit(f"while ({cond}) {{")
            self.indent_level += 1
            for s in stmt.body:
                self.gen_stmt(s)
            self.indent_level -= 1
            self.emit("}")

        elif isinstance(stmt, ForStmt):
            if isinstance(stmt.iterable, CallExpr) and isinstance(stmt.iterable.func, Identifier) and stmt.iterable.func.name == "range":
                args = stmt.iterable.args
                if len(args) == 1:
                    start = "0"
                    end = self.gen_expr(args[0])
                elif len(args) == 2:
                    start = self.gen_expr(args[0])
                    end = self.gen_expr(args[1])
                else:
                    raise NotImplementedError("range() with 1 or 2 args only")
                self.emit(f"for (int {stmt.var_name} = {start}; {stmt.var_name} < {end}; {stmt.var_name}++) {{")
                self.indent_level += 1
                for s in stmt.body:
                    self.gen_stmt(s)
                self.indent_level -= 1
                self.emit("}")
            else:
                self.emit(f"// unsupported for-loop iterable: {stmt.iterable}")

        elif isinstance(stmt, BreakStmt):
            self.emit("break;")

        elif isinstance(stmt, ContinueStmt):
            self.emit("continue;")

        elif isinstance(stmt, CallExpr):
            self.gen_expr(stmt)  # side effect like print()

    def gen_expr(self, expr: Expr) -> str:
        if isinstance(expr, BinOp):
            left = self.gen_expr(expr.left)
            right = self.gen_expr(expr.right)
            return f"({left} {expr.op} {right})"

        elif isinstance(expr, UnaryOp):
            operand = self.gen_expr(expr.operand)
            return f"({expr.op}{operand})"

        elif isinstance(expr, Literal):
            if isinstance(expr.value, bool):
                return "true" if expr.value else "false"
            elif isinstance(expr.value, str):
                return f'"{expr.value}"'  # warning: string support in C is basic
            return str(expr.value)

        elif isinstance(expr, Identifier):
            return expr.name

        elif isinstance(expr, CallExpr):
            if isinstance(expr.func, Identifier) and expr.func.name == "print":
                for arg in expr.args:
                    arg_str = self.gen_expr(arg)
                    if isinstance(arg, Literal):
                        if isinstance(arg.value, str):
                            self.emit(f'printf("%s\\n", {arg_str});')
                        elif isinstance(arg.value, int):
                            self.emit(f'printf("%d\\n", {arg_str});')
                        elif isinstance(arg.value, float):
                            self.emit(f'printf("%f\\n", {arg_str});')
                        elif isinstance(arg.value, bool):
                            self.emit(f'printf("%s\\n", {arg_str} ? "true" : "false");')
                    else:
                        self.emit(f'printf("%d\\n", {arg_str});')  # fallback for non-literal
                return "0"
            else:
                args = ", ".join(self.gen_expr(a) for a in expr.args)
                return f"{expr.func.name}({args})"

        elif isinstance(expr, ListExpr):
            elements = ", ".join(self.gen_expr(e) for e in expr.elements)
            return f"{{ {elements} }}"  # user must define array outside

        elif isinstance(expr, DictExpr):
            return "/* dicts not directly supported in C */"

        else:
            raise NotImplementedError(f"Unknown expression type: {type(expr)}")
