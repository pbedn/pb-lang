from lang_ast import *

class TypeError(Exception):
    pass

class TypeChecker:
    def __init__(self):
        self.functions = {}  # name -> (params: [(name, type)], return_type)
        self.env = {}        # variable -> type
        self.current_function_return_type = None

    def check(self, program: Program):
        for stmt in program.body:
            if isinstance(stmt, FunctionDef):
                self.functions[stmt.name] = (stmt.params, stmt.return_type or "void")

        for stmt in program.body:
            self.check_stmt(stmt)

    def check_stmt(self, stmt: Stmt):
        if isinstance(stmt, FunctionDef):
            self.env = {}
            self.current_function_return_type = stmt.return_type or "void"
            for param in stmt.params:
                if isinstance(param, tuple):
                    name, typ = param
                else:
                    name, typ = param, "int"  # default type
                self.env[name] = typ

            for s in stmt.body:
                self.check_stmt(s)

        elif isinstance(stmt, AssignStmt):
            val_type = self.check_expr(stmt.value)
            self.env[stmt.target] = val_type

        elif isinstance(stmt, ReturnStmt):
            val_type = self.check_expr(stmt.value)
            if self.current_function_return_type != val_type:
                raise TypeError(
                    f"Function declared to return '{self.current_function_return_type}' but got '{val_type}'"
                )

        elif isinstance(stmt, IfStmt):
            cond_type = self.check_expr(stmt.condition)
            if cond_type != "bool":
                raise TypeError("Condition must be of type 'bool'")
            for s in stmt.then_body:
                self.check_stmt(s)
            if stmt.else_body:
                for s in stmt.else_body:
                    self.check_stmt(s)

        elif isinstance(stmt, WhileStmt):
            cond_type = self.check_expr(stmt.condition)
            if cond_type != "bool":
                raise TypeError("While condition must be of type 'bool'")
            for s in stmt.body:
                self.check_stmt(s)

        elif isinstance(stmt, ForStmt):
            self.env[stmt.var_name] = "int"
            self.check_expr(stmt.iterable)
            for s in stmt.body:
                self.check_stmt(s)

        elif isinstance(stmt, CallExpr):
            self.check_expr(stmt)

    def check_expr(self, expr: Expr) -> str:
        if isinstance(expr, Literal):
            if isinstance(expr.value, int):
                return "int"
            elif isinstance(expr.value, float):
                return "float"
            elif isinstance(expr.value, str):
                return "str"
            elif isinstance(expr.value, bool):
                return "bool"

        elif isinstance(expr, Identifier):
            if expr.name not in self.env:
                raise TypeError(f"Undeclared variable '{expr.name}'")
            return self.env[expr.name]

        elif isinstance(expr, BinOp):
            left = self.check_expr(expr.left)
            right = self.check_expr(expr.right)
            if left != right:
                raise TypeError("Type mismatch in binary operation")
            if expr.op in ['+', '-', '*', '/', '%']:
                return left
            if expr.op in ['==', '!=', '<', '<=', '>', '>=']:
                return "bool"
            if expr.op in ['and', 'or']:
                if left != "bool":
                    raise TypeError("Logical operations require 'bool' operands")
                return "bool"

        elif isinstance(expr, UnaryOp):
            t = self.check_expr(expr.operand)
            if expr.op == "-" and t in ["int", "float"]:
                return t
            if expr.op == "not" and t == "bool":
                return "bool"
            raise TypeError(f"Invalid unary op '{expr.op}' for type '{t}'")

        elif isinstance(expr, CallExpr):
            if not isinstance(expr.func, Identifier):
                raise TypeError("Function calls must use identifier as name")
            fname = expr.func.name
            if fname == "print":
                for arg in expr.args:
                    self.check_expr(arg)
                return "void"
            if fname not in self.functions:
                raise TypeError(f"Undefined function '{fname}'")
            params, return_type = self.functions[fname]
            if len(expr.args) != len(params):
                raise TypeError(f"Argument count mismatch in call to '{fname}'")
            for arg, param in zip(expr.args, params):
                param_type = param[1] if isinstance(param, tuple) else "int"
                arg_type = self.check_expr(arg)
                if arg_type != param_type:
                    raise TypeError(f"Argument type mismatch in call to '{fname}'")
            return return_type

        elif isinstance(expr, ListExpr):
            for e in expr.elements:
                self.check_expr(e)  # not enforcing homogeneity yet
            return "list"

        elif isinstance(expr, DictExpr):
            for k, v in expr.pairs:
                self.check_expr(k)
                self.check_expr(v)
            return "dict"

        else:
            raise NotImplementedError(f"Unknown expression type: {type(expr)}")
