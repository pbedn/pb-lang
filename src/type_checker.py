from lang_ast import *

class LangTypeError(Exception):
    pass

class TypeChecker:
    def __init__(self):
        self.functions = {
            "print": ([("value", "int")], "void"),
            "range": ([("start", "int")], "range"),
        }
        self.classes = {}
        self.builtins = {"True": "bool", "False": "bool", "None": "int"}
        self.env = {}        # local vars (per function/method)
        self.global_env = {} # global vars
        self.current_function_globals = set()
        self.current_function_return_type = None
        self.in_loop = 0

    def check(self, program: Program):
        # First pass: register classes & functions signatures
        for stmt in program.body:
            if isinstance(stmt, ClassDef):
                if stmt.name in self.classes:
                    raise LangTypeError(f"Duplicate class '{stmt.name}'")
                # Register the class early
                field_types = {field.name: field.declared_type for field in stmt.fields}
                self.classes[stmt.name] = {
                    "fields": field_types,
                    "methods": {method.name: method for method in stmt.methods},
                }
            elif isinstance(stmt, FunctionDef):
                self.functions[stmt.name] = (stmt.params, stmt.return_type or "void")

        # Second pass: type check everything
        for stmt in program.body:
            if isinstance(stmt, VarDecl):
                val_type = self.check_expr(stmt.value)
                if val_type != stmt.declared_type:
                    raise LangTypeError(
                        f"Type mismatch: global variable '{stmt.name}' declared as '{stmt.declared_type}' but got '{val_type}'"
                    )
                self.global_env[stmt.name] = stmt.declared_type

            elif isinstance(stmt, FunctionDef):
                self.check_stmt(stmt)

            elif isinstance(stmt, ClassDef):
                # Validate fields
                class_info = self.classes[stmt.name]
                for field in stmt.fields:
                    val_type = self.check_expr(field.value)
                    if val_type != field.declared_type:
                        raise LangTypeError(
                            f"Type mismatch in field '{field.name}' of class '{stmt.name}': expected '{field.declared_type}' but got '{val_type}'"
                        )
                # Validate methods
                for method in stmt.methods:
                    self.check_method(method, stmt.name)

            else:
                raise LangTypeError(f"Invalid statement at top level: {stmt}")

    def check_method(self, method: FunctionDef, class_name: str):
        self.env = {}
        self.current_function_globals = set()
        self.current_function_return_type = method.return_type or "void"

        if not method.params:
            raise LangTypeError(f"Method '{method.name}' in class '{class_name}' must have 'self' as first parameter")
        first_param_name, first_param_type = method.params[0]
        if first_param_type != class_name:
            raise LangTypeError(f"First parameter of method '{method.name}' must be '{class_name}', got '{first_param_type}'")

        # Register method params
        for param in method.params:
            name, typ = param
            self.env[name] = typ

        for s in method.body:
            self.check_stmt(s)

    def check_stmt(self, stmt: Stmt):
        if isinstance(stmt, FunctionDef):
            self.env = {}
            self.current_function_globals = set()
            self.current_function_return_type = stmt.return_type or "void"
            for param in stmt.params:
                name, typ = param
                self.env[name] = typ
            for s in stmt.body:
                self.check_stmt(s)

        elif isinstance(stmt, GlobalStmt):
            for name in stmt.names:
                self.current_function_globals.add(name)
                if name not in self.global_env:
                    raise LangTypeError(f"Global variable '{name}' not defined")

        elif isinstance(stmt, VarDecl):
            val_type = self.check_expr(stmt.value)
            if val_type != stmt.declared_type:
                raise LangTypeError(
                    f"Type mismatch: variable '{stmt.name}' declared as '{stmt.declared_type}' but got '{val_type}'"
                )
            if stmt.name in self.current_function_globals:
                self.global_env[stmt.name] = stmt.declared_type
            else:
                self.env[stmt.name] = stmt.declared_type

        elif isinstance(stmt, AssignStmt):
            val_type = self.check_expr(stmt.value)
            if isinstance(stmt.target, Identifier):
                target_name = stmt.target.name
                if target_name in self.current_function_globals:
                    self.global_env[target_name] = val_type
                elif target_name in self.env:
                    self.env[target_name] = val_type
                else:
                    raise LangTypeError(
                        f"Variable '{target_name}' assigned before declaration"
                    )
            elif isinstance(stmt.target, AttributeExpr):
                self.check_expr(stmt.target)  # Ensures it's a valid attribute
            else:
                raise LangTypeError(f"Invalid assignment target: {stmt.target}")

        elif isinstance(stmt, AugAssignStmt):
            if isinstance(stmt.target, Identifier):
                target_name = stmt.target.name
                if target_name in self.current_function_globals:
                    if target_name not in self.global_env:
                        raise LangTypeError(f"Global variable '{target_name}' not defined before augmented assignment")
                    target_type = self.global_env[target_name]
                elif target_name in self.env:
                    target_type = self.env[target_name]
                else:
                    raise LangTypeError(f"Variable '{target_name}' not declared before augmented assignment")
            elif isinstance(stmt.target, AttributeExpr):
                target_type = self.check_expr(stmt.target)
            else:
                raise LangTypeError(f"Invalid augmented assignment target: {stmt.target}")

            value_type = self.check_expr(stmt.value)
            if target_type != value_type:
                raise LangTypeError(
                    f"Augmented assignment type mismatch: {target_type} {stmt.op}= {value_type}"
                )

        elif isinstance(stmt, ReturnStmt):
            if self.current_function_return_type == "void":
                if stmt.value is not None and not (isinstance(stmt.value, Literal) and stmt.value.value is None):
                    raise LangTypeError(
                        "Cannot return a value from a function declared as void"
                    )
            else:
                val_type = self.check_expr(stmt.value)
                if self.current_function_return_type != val_type:
                    raise LangTypeError(
                        f"Function declared to return '{self.current_function_return_type}' but got '{val_type}'"
                    )

        elif isinstance(stmt, IfStmt):
            cond_type = self.check_expr(stmt.condition)
            if cond_type != "bool":
                raise LangTypeError("Condition must be of type 'bool'")
            for s in stmt.then_body:
                self.check_stmt(s)
            if stmt.else_body:
                for s in stmt.else_body:
                    self.check_stmt(s)

        elif isinstance(stmt, WhileStmt):
            cond_type = self.check_expr(stmt.condition)
            if cond_type != "bool":
                raise LangTypeError("While condition must be of type 'bool'")
            self.in_loop += 1
            for s in stmt.body:
                self.check_stmt(s)
            self.in_loop -= 1

        elif isinstance(stmt, ForStmt):
            iter_type = self.check_expr(stmt.iterable)
            if iter_type != "range":
                raise LangTypeError("Can only iterate over range")
            self.env[stmt.var_name] = "int"
            self.in_loop += 1
            for s in stmt.body:
                self.check_stmt(s)
            self.in_loop -= 1

        elif isinstance(stmt, BreakStmt) or isinstance(stmt, ContinueStmt):
            if self.in_loop == 0:
                raise LangTypeError(f"{type(stmt).__name__} used outside of loop")

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
            if expr.name in self.builtins:
                return self.builtins[expr.name]
            if expr.name in self.env:
                return self.env[expr.name]
            if expr.name in self.global_env:
                return self.global_env[expr.name]
            raise LangTypeError(f"Undefined variable '{expr.name}'")

        elif isinstance(expr, AttributeExpr):
            obj_type = self.check_expr(expr.obj)
            if obj_type not in self.classes:
                raise LangTypeError(f"Cannot access attribute of non-class type '{obj_type}'")
            class_info = self.classes[obj_type]
            fields = class_info["fields"]
            if expr.attr not in fields:
                raise LangTypeError(f"Class '{obj_type}' has no field '{expr.attr}'")
            return fields[expr.attr]

        elif isinstance(expr, BinOp):
            left = self.check_expr(expr.left)
            right = self.check_expr(expr.right)
            if left != right:
                raise LangTypeError("Type mismatch in binary operation")
            if expr.op in ['+', '-', '*', '/', '%']:
                return left
            if expr.op in {"==", "!=", "<", ">", "<=", ">=", "is", "is not"}:
                return "bool"
            if expr.op in ['and', 'or']:
                if left != "bool":
                    raise LangTypeError("Logical operations require 'bool' operands")
                return "bool"

        elif isinstance(expr, UnaryOp):
            t = self.check_expr(expr.operand)
            if expr.op == "-" and t in ["int", "float"]:
                return t
            if expr.op == "not" and t == "bool":
                return "bool"
            raise LangTypeError(f"Invalid unary op '{expr.op}' for type '{t}'")

        elif isinstance(expr, IndexExpr):
            base_type = self.check_expr(expr.base)
            index_type = self.check_expr(expr.index)
            if not base_type.startswith("list"):
                raise LangTypeError("Can only index into lists")
            if index_type != "int":
                raise LangTypeError("List index must be an integer")
            elem_type = base_type[5:-1]
            expr.elem_type = elem_type
            return elem_type

        elif isinstance(expr, CallExpr):
            if not isinstance(expr.func, Identifier):
                raise LangTypeError("Function calls must use identifier as name")
            fname = expr.func.name
            if fname == "print":
                for arg in expr.args:
                    arg_type = self.check_expr(arg)
                    if arg_type.startswith("list["):
                        raise LangTypeError("Cannot print a list directly")
                return "void"

            if fname == "range":
                if not (1 <= len(expr.args) <= 2):
                    raise LangTypeError("range() takes 1 or 2 arguments")
                for arg in expr.args:
                    if self.check_expr(arg) != "int":
                        raise LangTypeError("range() arguments must be integers")
                return "range"

            if fname not in self.functions:
                raise LangTypeError(f"Undefined function '{fname}'")
            params, return_type = self.functions[fname]
            if len(expr.args) != len(params):
                raise LangTypeError(f"Argument count mismatch in call to '{fname}'")
            for arg, param in zip(expr.args, params):
                param_type = param[1] if isinstance(param, tuple) else "int"
                arg_type = self.check_expr(arg)
                if arg_type != param_type:
                    raise LangTypeError(f"Argument type mismatch in call to '{fname}'")
            return return_type

        elif isinstance(expr, ListExpr):
            if not expr.elements:
                raise LangTypeError("Cannot infer type of empty list")
            elem_types = [self.check_expr(e) for e in expr.elements]
            first_type = elem_types[0]
            for t in elem_types:
                if t != first_type:
                    raise LangTypeError("All elements of a list must have the same type")
            expr.elem_type = first_type
            return f"list[{first_type}]"

        elif isinstance(expr, DictExpr):
            for k, v in expr.pairs:
                self.check_expr(k)
                self.check_expr(v)
            return "dict"

        else:
            raise NotImplementedError(f"Unknown expression type: {type(expr)}")
