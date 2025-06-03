"""
PB Type Checker
===============

This module implements static type checking for PB, a statically typed, Python-like language that compiles to C.
It validates types over the AST, enforcing static constraints at compile time based on the PB language rules.

Environment:
------------
- `self.env`:             Current variable environment (name → type)
- `self.functions`:       Top-level function signatures (name → (param_types, return_type, num_required))
- `self.methods`:         Per-class method tables (class_name → method_name → signature)
- `self.class_attrs`:     Static (class-level) fields per class (class_name → field_name → type)
- `self.instance_fields`: Instance fields per class (class_name → field_name → type); includes inherited fields
- `self.class_bases`:     Single inheritance graph (subclass → base class)
- `self.known_classes`:   Set of all declared class names
- `self.current_return_type`: Return type expected in the current function
- `self.current_function_name`: Name of current function or method
- `self.in_loop`:         Tracks whether inside a loop (for `break` / `continue` validation)

Supported Expression Types:
---------------------------
- `Literal`:          int, float, str, bool, None
- `Identifier`:       Variable reference (must be declared)
- `UnaryOp`:          Supports `-`, `not`; type depends on operand
- `BinOp`:            Arithmetic, logical, comparison, identity (`is`, `is not`)
- `CallExpr`:         Top-level or static method calls (`ClassName.method(...)`)
                      - Default arguments supported
                      - Subclass argument types are allowed where base is expected
                      - Special-case: `print(...)` handles any non-list types
- `AttributeExpr`:    Supports `self.field` and `ClassName.attr`
                      - Validates fields based on class or instance context
- `IndexExpr`:        Supports `list[T]` and `dict[str, T]` indexing
- `ListExpr`:         Homogeneous list literals (type inferred or declared)
- `DictExpr`:         Homogeneous `dict[str, T]` literals
- `FStringLiteral`:   Formatted string literals with variable interpolation

Supported Statement Types:
--------------------------
- `VarDecl`:           Requires declared type and initializer of matching type
- `AssignStmt`:        Updates existing variables (or `self.field`) with matching type
- `AugAssignStmt`:     In-place ops on int/float fields or instance attributes
- `ReturnStmt`:        Must match current function’s declared return type
- `BreakStmt`:         Only valid within loop body
- `ContinueStmt`:      Only valid within loop body
- `PassStmt`:          Always valid; checked for consistency
- `AssertStmt`:        Expression must be boolean
- `RaiseStmt`:         Only known exception types may be raised; value must be valid expression
- `GlobalStmt`:        Declares intention to assign to top-level variable
- `IfStmt`:            All conditions must be bool; checked per branch
- `WhileStmt`:         Condition must be bool; body checked with loop context
- `ForStmt`:           Iterates over `list[T]`; loop var declared with element type `T`
- `FunctionDef`:       Parameters must be typed; default values checked; return statements validated
- `ClassDef`:          Fields and methods validated; base class resolved and fields inherited
- `TryExceptStmt`:     Validates try body and each except-block separately

Design Notes:
-------------
- Per-class method registry prevents method name collisions across classes
- Instance fields are inherited from base classes; no need to redeclare them
- Static method dispatch is supported via `ClassName.method(...)`; dynamic `self.method()` not yet supported
- Subclass types are accepted where a base class is expected
- All methods must have `self` typed as the class or a known subclass (validated)
- Class fields are split between static (`class_attrs`) and instance (`instance_fields`)
- `super()` is not supported; use `BaseClass.method(self, ...)` instead
- Built-in exceptions (`RuntimeError`, `ValueError`, etc.) are always allowed
- Print statements disallow printing lists directly
- Full support for default arguments and named parameters

Testing:
--------
- `TestTypeCheckerInternals`: Unit tests for specific AST forms and edge cases
- `TestTypeCheckerProgramLevel`: Integration tests over full ASTs representing PB source files
- All test functions include Python-style docstrings showing the PB source they model
"""


from typing import Dict, Tuple, Optional, List, Set

from lang_ast import (
    ForStmt,
    Stmt,
    Expr,
    Program,
    VarDecl,
    Literal,
    StringLiteral,
    FStringLiteral,
    Identifier,
    BinOp,
    UnaryOp,
    CallExpr,
    ReturnStmt,
    Parameter,
    FunctionDef,
    AssignStmt,
    AugAssignStmt,
    IfStmt,
    WhileStmt,
    ForStmt,
    BreakStmt,
    ContinueStmt,
    PassStmt,
    ClassDef,
    AttributeExpr,
    IndexExpr,
    ListExpr,
    DictExpr,
    AssertStmt,
    RaiseStmt,
    GlobalStmt,
    TryExceptStmt,
    ExceptBlock,
    ExprStmt,
)


class TypeError(Exception):
    """Raised when a type mismatch or type-related error occurs during type checking."""
    pass


class TypeChecker:
    """Performs static type checking on a PB AST.
    
    Usage:
        checker = TypeChecker()
        checker.check(program)  # where `program` is a Program node
    """
    def __init__(self):
        # Symbol table: variable/function names → declared type
        self.env: Dict[str, str] = {}

        self.global_env: Dict[str, str] = {}

        # func_name → ([param_types], return_type)
        self.functions: Dict[str, Tuple[List[str], str, int]] = {} # param_types, return_type, num_required

        # for range(start, stop) in future:
        self.functions["range"] = (["int", "int"], "list[int]", 1)
        self.functions["range"] = (["int", "int"], "list[int]", 1)

        # to track the expected return type while checking a function body
        self.current_return_type: Optional[str] = None

        # for validating break and continue
        self.in_loop: int = 0  # loop depth counter

        self.inside_method: bool = False

        self.known_classes: Set[str] = set()
        self.class_attrs: Dict[str, Dict[str, str]] = {}
        self.instance_fields: Dict[str, Dict[str, str]] = {}
        self.class_bases: Dict[str, str] = {}  # child class → base class

        # class-scoped method registry
        # class_name → method_name → (param_types, return_type, num_required)
        self.methods: Dict[str, Dict[str, Tuple[List[str], str, int]]] = {} 

        # Register built-in exceptions as class names
        for exc in ["RuntimeError", "ValueError", "IndexError", "TypeError"]:
            self.known_classes.add(exc)
            self.functions[exc] = (["str"], exc, 1)

    # TODO
    # def assert_all_exprs_typed(node: Node):
    #     for child in walk_ast(node):
    #         if isinstance(child, (Expr,)):
    #             assert getattr(child, "inferred_type", None) is not None, f"Missing type: {child}"


    def check(self, program: Program):
        """Type-check the entire program."""
        seen_main = False
        for stmt in program.body:
            if isinstance(stmt, FunctionDef) and stmt.name == "main":
                if seen_main:
                    raise TypeError("Multiple 'main' functions are not allowed")
                seen_main = True
            self.check_stmt(stmt)

        program.inferred_instance_fields = dict(self.instance_fields)
        return program

    def check_stmt(self, stmt: Stmt):
        """Type-check a single statement."""
        if isinstance(stmt, VarDecl):
            self.check_var_decl(stmt)
        elif isinstance(stmt, AssignStmt):
            self.check_assign_stmt(stmt)
        elif isinstance(stmt, AugAssignStmt):
            self.check_aug_assign_stmt(stmt)
        elif isinstance(stmt, ClassDef):
            self.check_class_def(stmt)
        elif isinstance(stmt, FunctionDef):
            self.check_function_def(stmt)
        elif isinstance(stmt, ReturnStmt):
            self.check_return_stmt(stmt)
        elif isinstance(stmt, IfStmt):
            self.check_if_stmt(stmt)
        elif isinstance(stmt, WhileStmt):
            self.check_while_stmt(stmt)
        elif isinstance(stmt, ForStmt):
            self.check_for_stmt(stmt)
        elif isinstance(stmt, AssertStmt):
            self.check_assert_stmt(stmt)
        elif isinstance(stmt, RaiseStmt):
            self.check_raise_stmt(stmt)
        elif isinstance(stmt, GlobalStmt):
            self.check_global_stmt(stmt)
        elif isinstance(stmt, TryExceptStmt):
            self.check_try_except_stmt(stmt)
        elif isinstance(stmt, PassStmt):
            pass  # nothing to check
        elif isinstance(stmt, BreakStmt):
            if self.in_loop == 0:
                raise TypeError("'break' outside of loop")

        elif isinstance(stmt, ContinueStmt):
            if self.in_loop == 0:
                raise TypeError("'continue' outside of loop")

        elif isinstance(stmt, ExprStmt):
            stmt.inferred_type = self.check_expr(stmt.expr)  # validate call, access, etc.

        else:
            raise NotImplementedError(f"Type checking not yet implemented for {type(stmt).__name__}")

    def check_var_decl(self, decl: VarDecl):
        """Type-check a variable declaration.
        
        Ensures that the initializer expression matches the declared type.
        """
        name = decl.name
        declared = decl.declared_type
        actual = self.check_expr(decl.value, expected_type=declared)

        if declared != actual:
            raise TypeError(f"Type mismatch in variable '{name}': declared {declared}, got {actual}")

        self.env[name] = declared
        if self.current_return_type is None:
            self.global_env[name] = declared

        decl.inferred_type = actual

    def check_expr(self, expr: Expr, expected_type: Optional[str] = None) -> str:
        """
        Type-checks an expression node and returns its type as a string.

        Covers:
        - Literals: int, float, str, bool, None
        - Unary and binary operations with type enforcement
        - Variable and attribute access:
            - Instance attributes via `self`
            - Static/class attributes via class name
        - Indexing into lists and dicts
        - List and dict literal expressions with type uniformity
        - Function and static method calls:
            - Top-level functions are stored in `self.functions`
            - Class-scoped static methods are looked up in `self.methods[class][method]`
            - Arguments are type-checked, with support for default arguments
            - Subclass arguments are allowed when a base type is expected

        Notes:
        - Method calls like `Player.method(...)` are supported (static dispatch)
        - Instance method calls like `self.method(...)` are not yet supported (planned)
        - Lambdas, higher-order functions, and closures are not supported
        - Printing lists is explicitly disallowed (`print([1, 2])` → TypeError)

        Returns:
            A string representing the inferred or declared type of the expression.

        Raises:
            TypeError if the expression is invalid in structure or type.
        """
        if isinstance(expr, Literal):
            raw = expr.raw
            if raw == "True" or raw == "False":
                expr.inferred_type = "bool"
                return "bool"
            elif raw == "None":
                expr.inferred_type = "None"
                return "None"
            elif raw.startswith('"') or raw.startswith("'"):
                expr.inferred_type = "str"
                return "str"
            elif "." in raw or "e" in raw or "E" in raw:
                expr.inferred_type = "float"
                return "float"
            else:
                expr.inferred_type = "int"
                return "int"

        elif isinstance(expr, StringLiteral):
            expr.inferred_type = "str"
            return "str"

        elif isinstance(expr, FStringLiteral):
            expr.inferred_type = "str"
            return "str"

        elif isinstance(expr, Identifier):
            name = expr.name
            if name in self.env:
                expr.inferred_type = self.env[name]
                return self.env[name]
            raise TypeError(f"Undefined variable or function '{name}'")

        # Both sides must be of compatible types for the operator.
        elif isinstance(expr, BinOp):
            left_type = self.check_expr(expr.left)
            right_type = self.check_expr(expr.right)
            op = expr.op

            # Arithmetic
            if op in {"+", "-", "*", "/", "//", "%"}:
                if left_type != right_type:
                    raise TypeError(f"Type mismatch in {op}: {left_type} vs {right_type}")
                if left_type not in {"int", "float"}:
                    raise TypeError(f"Operator {op} not supported for type '{left_type}'")
                expr.inferred_type = left_type
                return left_type  # same as operands

            # Comparison
            elif op in {"==", "!=", "<", "<=", ">", ">=", "is", "is not"}:
                if left_type != right_type:
                    raise TypeError(f"Comparison '{op}' between incompatible types: {left_type} and {right_type}")
                expr.inferred_type = "bool"
                return "bool"

            # Logical
            elif op in {"and", "or"}:
                if left_type != "bool" or right_type != "bool":
                    raise TypeError(f"Logical '{op}' requires bool operands")
                expr.inferred_type = "bool"
                return "bool"

            else:
                raise TypeError(f"Unknown binary operator '{op}'")

        # UnaryOp
        # - (negation): works for int or float
        # not (logical negation): works for bool
        elif isinstance(expr, UnaryOp):
            operand_type = self.check_expr(expr.operand)
            op = expr.op

            if op == "-":
                if operand_type not in {"int", "float"}:
                    raise TypeError(f"Unary '-' requires numeric operand, got {operand_type}")
                expr.inferred_type = operand_type
                return operand_type

            elif op == "not":
                if operand_type != "bool":
                    raise TypeError(f"Unary 'not' requires bool operand, got {operand_type}")
                expr.inferred_type = "bool"
                return "bool"

            else:
                raise TypeError(f"Unknown unary operator '{op}'")

        # CallExpr
        # --------------------------
        # The called expression must be a function:
        # - either a direct name (Identifier), like print(x)
        # - or a static class method access (AttributeExpr), like Player.__init__(...)

        elif isinstance(expr, CallExpr):
            if isinstance(expr.func, Identifier):
                # Top-level function call (not a method)
                fname = expr.func.name

                # Class instantiation: Player(...)
                if fname in self.methods and "__init__" in self.methods[fname]:
                    init_sig = self.methods[fname]["__init__"]
                    param_types, return_type, num_required = init_sig

                    # Strip off first param (self)
                    param_types = param_types[1:]
                    num_required = max(0, num_required - 1)

                    if not (num_required <= len(expr.args) <= len(param_types)):
                        raise TypeError(f"Constructor for class '{fname}' expects between {num_required} and {len(param_types)} arguments, got {len(expr.args)}")

                    for i, (arg, expected) in enumerate(zip(expr.args, param_types)):
                        actual = self.check_expr(arg)
                        if actual != expected:
                            if expected in self.known_classes and actual in self.known_classes:
                                if not self.is_subclass(actual, expected):
                                    raise TypeError(f"Argument {i+1} to '{fname}' expected {expected}, got {actual}")
                            else:
                                raise TypeError(f"Argument {i+1} to '{fname}' expected {expected}, got {actual}")

                    expr.inferred_type = fname
                    return fname  # The constructed class becomes the expression's type

                if fname == "print":
                    for arg in expr.args:
                        t = self.check_expr(arg)
                        if t.startswith("list["):
                            raise TypeError("Cannot print a list directly")
                    expr.inferred_type = "function"
                    return "None"
                if fname not in self.functions:
                    raise TypeError(f"Call to undefined function '{fname}'")
                param_types, return_type, num_required = self.functions[fname]

            elif isinstance(expr.func, AttributeExpr):
                # determine if this is an instance call (e.g. obj.method())
                obj = expr.func.obj
                if isinstance(obj, Identifier) and obj.name in self.env:
                    class_name = self.env[obj.name]
                    strip_self = True
                else:
                    class_name = obj.name
                    strip_self = False

                # if it’s a static call on a class that doesn’t exist, error out early
                if not strip_self and class_name not in self.class_attrs:
                    raise TypeError(f"Class '{class_name}' is not defined")

                method_name = expr.func.attr

                # walk up the inheritance chain to find the method
                sig = None
                c = class_name
                while c:
                    if c in self.methods and method_name in self.methods[c]:
                        sig = self.methods[c][method_name]
                        break
                    c = self.class_bases.get(c)
                if sig is None:
                    raise TypeError(f"Class '{class_name}' has no method '{method_name}'")

                param_types, return_type, num_required = sig

                # drop the implicit 'self' argument for instance calls
                if strip_self:
                    param_types = param_types[1:]
                    num_required = max(0, num_required - 1)

                # now run your existing arity check:
                if not (num_required <= len(expr.args) <= len(param_types)):
                    raise TypeError(
                        f"Function '{method_name}' expects between {num_required} and {len(param_types)} arguments, got {len(expr.args)}"
                    )

                # and your existing per-arg type loop (with subclass logic)
                for i, (arg, expected) in enumerate(zip(expr.args, param_types)):
                    actual = self.check_expr(arg)
                    if actual != expected:
                        if expected in self.known_classes and actual in self.known_classes:
                            if not self.is_subclass(actual, expected):
                                raise TypeError(
                                    f"Argument {i+1} to '{method_name}' expected {expected}, got {actual}"
                                )
                        else:
                            raise TypeError(
                                f"Argument {i+1} to '{method_name}' expected {expected}, got {actual}"
                            )

                expr.inferred_type = return_type
                return return_type


            else:
                raise TypeError("Only direct or static method calls are supported")

            # Check argument count
            if not (num_required <= len(expr.args) <= len(param_types)):
                raise TypeError(f"Function '{method_name if isinstance(expr.func, AttributeExpr) else fname}' expects between {num_required} and {len(param_types)} arguments, got {len(expr.args)}")

            for i, (arg, expected_type) in enumerate(zip(expr.args, param_types)):
                actual_type = self.check_expr(arg)
                if actual_type != expected_type:
                    # Allow subclassing
                    if expected_type in self.known_classes and actual_type in self.known_classes:
                        if not self.is_subclass(actual_type, expected_type):
                            raise TypeError(f"Argument {i+1} expected {expected_type}, got {actual_type}")
                    else:
                        raise TypeError(f"Argument {i+1} expected {expected_type}, got {actual_type}")

            expr.inferred_type = return_type
            return return_type

        
        # AttributeExpr
        # --------------------------
        # Supports attribute access in three forms:
        # 1. self.field → instance attribute access (requires 'self' to have a known class type)
        # 2. var.field → access via a variable whose type is a class
        # 3. ClassName.field → static access via class name (class attribute)
        #
        # Resolution steps:
        # - If obj is 'self', use instance_fields for obj_type
        # - If obj is a variable name, get its type from env and lookup in class_attrs
        # - If obj is a class name (not in env), directly lookup in class_attrs
        #
        # Raises:
        # - TypeError if the object is not an identifier
        # - TypeError if the object or class is not defined or the attribute is missing

        elif isinstance(expr, AttributeExpr):
            # only allow obj.attr when obj is a simple identifier
            if not isinstance(expr.obj, Identifier):
                raise TypeError("Attribute access must be through an identifier")

            obj_name = expr.obj.name

            # --- instance-field on any variable (including self) ---
            if obj_name in self.env:
                class_type = self.env[obj_name]
                if class_type not in self.instance_fields:
                    raise TypeError(f"'{obj_name}' has unknown type '{class_type}'")
                fields = self.instance_fields[class_type]
                if expr.attr not in fields:
                    raise TypeError(f"Instance `{obj_name}` for class '{class_type}' has no attribute '{expr.attr}'")

                # Todo: think if allowing setting from class attrs here make sense, if yes then propagate that in other places
                #     if expr.attr not in self.class_attrs[class_type]:
                #         raise TypeError(f"Instance `{obj_name}` for class '{class_type}' has no attribute '{expr.attr}'")
                #     else:
                #         expr.inferred_type = self.class_attrs[class_type][expr.attr]
                # else:
                #     expr.inferred_type = fields[expr.attr]
                expr.inferred_type = fields[expr.attr]
                return expr.inferred_type

            # --- static class-attribute (e.g. Player.species) ---
            if obj_name in self.class_attrs:
                fields = self.class_attrs[obj_name]
                if expr.attr not in fields:
                    raise TypeError(f"Class '{obj_name}' has no class attribute '{expr.attr}'")
                expr.inferred_type = fields[expr.attr]
                return expr.inferred_type

            # neither a variable nor a class
            raise TypeError(f"Variable or class '{obj_name}' is not defined")


        # In PB, only two patterns are valid:
        # list[T][int] → T
        # dict[str, T][str] → T
        # type-check both base and index
        # verify that the base is a list[...] or dict[...]
        # return the element type
        elif isinstance(expr, IndexExpr):
            base_type = self.check_expr(expr.base)
            index_type = self.check_expr(expr.index)

            if base_type.startswith("list[") and base_type.endswith("]"):
                if index_type != "int":
                    raise TypeError(f"List index must be int, got {index_type}")
                elem = base_type[5:-1]
                expr.elem_type = elem
                expr.inferred_type = base_type
                return elem

            elif base_type.startswith("dict[") and base_type.endswith("]"):
                if index_type != "str":
                    raise TypeError(f"Dict key must be str, got {index_type}")
                elem = base_type[len("dict[str, "):-1]
                expr.elem_type = elem
                expr.inferred_type = base_type
                return elem

            else:
                raise TypeError(f"Cannot index into value of type '{base_type}'")

        # PB supports:
        # ListExpr(elements=[...])        → list[T]
        #
        # A list must be homogeneous: all elements must have the same type
        elif isinstance(expr, ListExpr):
            if not expr.elements:
                if expected_type and expected_type.startswith("list["):
                    elem_type = expected_type[5:-1]
                    expr.elem_type = elem_type
                    expr.inferred_type = expected_type
                    return expected_type
                else:
                    raise TypeError("Cannot infer element type from empty list literal, add a variable type annotation.")

            elem_types = {self.check_expr(e) for e in expr.elements}
            if len(elem_types) > 1:
                raise TypeError(f"List elements must be the same type, got: {elem_types}")

            elem_type = elem_types.pop()
            expr.elem_type = elem_type
            expr.inferred_type = f"list[{elem_type}]"
            return expr.inferred_type

        # PB supports:
        # DictExpr(entries=[(key, val)])  → dict[str, T]
        #
        # Dict must have string keys (enforced by grammar)
        # all values must have the same type
        elif isinstance(expr, DictExpr):
            if not expr.keys:
                if expected_type and expected_type.startswith("dict[str,"):
                    val_type = expected_type.split(",")[1][:-1].strip()
                    expr.elem_type = val_type
                    expr.inferred_type = expected_type
                    return expected_type
                else:
                    raise TypeError("Cannot infer value type from empty dict literal")

            for key_expr in expr.keys:
                key_type = self.check_expr(key_expr)
                if key_type != "str":
                    raise TypeError(f"Dict keys must be str, got {key_type}")
                if not isinstance(key_expr, (StringLiteral, Literal)):  # Only allow literals
                    raise TypeError("Dict keys must be string literals, not expressions")

            val_types = {self.check_expr(v) for v in expr.values}
            if len(val_types) > 1:
                raise TypeError(f"Dict values must be the same type, got: {val_types}")

            val_type = val_types.pop()
            expr.elem_type = val_type
            expr.inferred_type = f"dict[str, {val_type}]"
            return expr.inferred_type

        raise NotImplementedError(f"Type inference not implemented for {type(expr).__name__}")

    def check_return_stmt(self, stmt: ReturnStmt):
        """Ensure return value matches expected function return type."""
        # return is only allowed inside functions
        if self.current_return_type is None:
            raise TypeError("Return statement outside of function")

        # if no value is returned: the return type must be None
        if stmt.value is None:
            if self.current_return_type != "None":
                raise TypeError(f"Expected return type '{self.current_return_type}', got None")
            stmt.inferred_type = "None"
        # if a value is returned: it must match the function’s declared return type
        else:
            actual_type = self.check_expr(stmt.value)
            if actual_type != self.current_return_type:
                raise TypeError(f"Return type mismatch: expected {self.current_return_type}, got {actual_type}")
            stmt.inferred_type = actual_type

    def check_function_def(self, fn: FunctionDef):
        """
        Type-checks a function or method body.

        Assumes:
        - Function has already been registered in either `self.functions` (top-level)
          or `self.methods[class_name]` (method inside class)
        - Parameter types and return type are declared and parsed

        Checks:
        - That parameter names are unique
        - That all required parameters come before defaulted ones
        - That statements in the body are valid and respect declared types
        - That return statements match the declared return type
        - That instance attributes in methods use `self` and match declared or inherited fields

        Special Behavior:
        - Tracks `self.current_function_name` to assist `AssignStmt` validation
        - Supports mixing `return` and `pass`, but not both in the same function
        - For methods, the `self` parameter is treated as an instance of the class or subclass

        Raises:
            TypeError for any invalid statements, type mismatches, or signature issues.
        """
        is_method = any(p.name == "self" for p in fn.params)
        self.inside_method = is_method

        fname = fn.name
        self.current_function_name = fname  # Track for context (used in assign stmt)

        seen = set()
        param_types = []
        num_required = 0
        saw_default = False

        for param in fn.params:
            if param.name in seen:
                raise TypeError(f"Duplicate parameter name '{param.name}' in function '{fname}'")
            seen.add(param.name)

            if param.type is None:
                raise TypeError(f"Missing type annotation for parameter '{param.name}' in function '{fname}'")

            param_types.append(param.type)
            param.inferred_type = param.type

            if param.default is None:
                if saw_default:
                    raise TypeError(f"Required parameter '{param.name}' cannot follow defaulted ones in function '{fname}'")
                num_required += 1
            else:
                saw_default = True

        ret_type = fn.return_type or "None"
        fn.inferred_return_type = ret_type
        self.functions[fname] = (param_types, ret_type, num_required)

        old_env = self.env.copy()
        self.env = old_env.copy()
        for p in fn.params:
            self.env[p.name] = p.type

        old_ret = self.current_return_type
        self.current_return_type = ret_type

        has_pass = False
        has_return = False
        for stmt in fn.body:
            self.check_stmt(stmt)
            if isinstance(stmt, PassStmt):
                has_pass = True
            elif isinstance(stmt, ReturnStmt):
                has_return = True
        if has_pass and has_return:
            raise TypeError(f"Function '{fn.name}' cannot contain both 'pass' and 'return'")
        if fn.return_type != "None":
            def contains_return(stmts):
                for s in stmts:
                    if isinstance(s, ReturnStmt):
                        return True
                    if isinstance(s, IfStmt):
                        # only count it if _all_ branches return
                        if all(contains_return(branch.body) for branch in s.branches):
                            return True
                    if isinstance(s, TryExceptStmt):
                        if contains_return(s.try_body) or any(contains_return(b.body) for b in s.except_blocks):
                            return True
                    # you can ignore loops for now
                return False

            if not contains_return(fn.body):
                raise TypeError(
                    f"Function '{fn.name}' declared to return {fn.return_type} but no return statement found"
                )

        self.env = old_env
        self.current_return_type = old_ret
        self.current_function_name = None  # Clear context
        self.inside_method = False

    def check_assign_stmt(self, stmt: AssignStmt):
        """Type-check a regular assignment.

        Supports:
        - Variable assignment: x = ...
        - Attribute assignment: self.x = ...
            - Allows instance attributes to be defined dynamically in __init__
            - Enforces consistent types across assignments
        """
        if isinstance(stmt.target, Identifier):
            name = stmt.target.name
            if name not in self.env:
                raise TypeError(f"Variable '{name}' not defined before assignment")
            expected_type = self.env[name]
            actual_type = self.check_expr(stmt.value)
            if expected_type != actual_type:
                raise TypeError(f"Type mismatch: cannot assign {actual_type} to {expected_type}")
            stmt.inferred_type = actual_type
            return

        elif isinstance(stmt.target, AttributeExpr):
            # extract object and field
            obj = stmt.target.obj
            field_name = stmt.target.attr

            # figure out what class this instance is
            if isinstance(obj, Identifier) and obj.name in self.env:
                class_type = self.env[obj.name]
            else:
                raise TypeError(f"Cannot assign attribute '{field_name}' on non-instance '{getattr(obj, 'name', obj)}'")

            # make sure we've seen that class's fields
            if class_type not in self.instance_fields:
                raise TypeError(f"'{obj.name}' has unknown type '{class_type}'")

            instance_fields = self.instance_fields[class_type]
            value_type = self.check_expr(stmt.value)

            if field_name not in instance_fields:
                if obj.name == "self" and self.current_function_name == "__init__":
                    # Dynamically add the new instance attribute
                    instance_fields[field_name] = value_type
                else:
                    raise TypeError(f"Attribute '{field_name}' not defined on '{class_type}'"
                        f"Class '{class_type}' has no instance attribute '{field_name}'")
            else:
                expected = instance_fields[field_name]
                if expected != value_type:
                    raise TypeError(f"Type mismatch for instance attribute '{field_name}': expected {expected}, got {value_type}")

            stmt.inferred_type = value_type
            return

        else:
            raise TypeError("Unsupported assignment target")

    def check_aug_assign_stmt(self, stmt: AugAssignStmt):
        """Check augmented assignment like x += 1.

        Allows safe type promotion:
        - float += int
        - float /= int
        """
        target = stmt.target
        actual_type = self.check_expr(stmt.value)
        # print("AUG ASSIGN target =", stmt.target)
        # print("  TYPE =", type(stmt.target).__name__)

        if isinstance(target, Identifier):
            name = target.name
            if name not in self.env:
                raise TypeError(f"Variable '{name}' not defined before augmented assignment")
            expected_type = self.env[name]

        elif isinstance(target, AttributeExpr):
            if isinstance(target.obj, Identifier) and target.obj.name == "self":
                # self.field → valid only if inside method
                if not self.inside_method:
                    raise TypeError("'self' is not valid outside of method")

                if "self" not in self.env:
                    raise TypeError("'self' is not defined in current scope")

                self_type = self.env["self"]
                if self_type not in self.instance_fields:
                    raise TypeError(f"'self' is of unknown class type '{self_type}'")

                fields = self.instance_fields[self_type]

                field_name = target.attr
                if field_name not in fields:
                    raise TypeError(f"Class '{self_type}' has no field '{field_name}'")

                expected_type = fields[field_name]
            else:
                # allow any other obj.field (e.g. mage.hp) — outside methods only
                # expected_type = "int"  # <- this is a placeholder, ideally you'd resolve it

                """
                In code like:

                mage.hp -= 30
                We are not:

                checking whether mage is of a known class,

                checking if hp is a valid field on that class,

                checking whether the value assigned matches the declared type.

                That means bugs like these would go undetected:

                mage.hp += "oops"              # string into int
                mage.unknown_field += 10       # nonexistent field
                some_random += 1               # invalid variable
                """
                return

        else:
            raise TypeError("Unsupported target for augmented assignment")

        if stmt.op not in {"+=", "-=", "*=", "/=", "//=", "%="}:
            raise TypeError(f"Unsupported augmented operator '{stmt.op}'")

        # Allow int → float promotion
        if expected_type == actual_type:
            return
        elif expected_type == "float" and actual_type == "int":
            return  # allow widening
        raise TypeError(f"AugAssign type mismatch: expected {expected_type}, got {actual_type}")


    def check_if_stmt(self, stmt: IfStmt):
        """Type-check if / elif / else branches.

        For each branch:
        If condition is not None, it must be of type bool
        Body is a list of statements to be type-checked in the current scope
        """
        for branch in stmt.branches:
            # condition is None for the 'else' branch
            if branch.condition is not None:
                cond_type = self.check_expr(branch.condition)
                if cond_type != "bool":
                    raise TypeError(f"If condition must be bool, got {cond_type}")

            for sub_stmt in branch.body:
                self.check_stmt(sub_stmt)

    def check_while_stmt(self, stmt: WhileStmt):
        """Type-check a while loop.

        Condition is of type bool
        The loop body type-checks in the current environment
        Track loop context (self.in_loop) for validating break and continue
        """
        cond_type = self.check_expr(stmt.condition)
        if cond_type != "bool":
            raise TypeError(f"While loop condition must be bool, got {cond_type}")

        self.in_loop += 1
        for s in stmt.body:
            self.check_stmt(s)
        self.in_loop -= 1

    def check_for_stmt(self, stmt: ForStmt):
        """Type-check a for loop over list[T].

        Type-checking requirements:
        - Iterable must be a list[T]
        - var_name is assigned elements of type T
        - Body type-checks with var_name bound to T
        - Must track loop context for break / continue
        """
        iterable_type = self.check_expr(stmt.iterable)

        if not iterable_type.startswith("list[") or not iterable_type.endswith("]"):
            raise TypeError(f"For loop requires iterable of type list[T], got {iterable_type}")

        element_type = iterable_type[5:-1]  # extract T from 'list[T]'
        stmt.elem_type = element_type

        # Extend environment with loop variable
        old_env = self.env.copy()
        self.env[stmt.var_name] = element_type

        self.in_loop += 1
        for s in stmt.body:
            self.check_stmt(s)
        self.in_loop -= 1

        self.env = old_env

    def is_subclass(self, sub: str, sup: str) -> bool:
        """
        Determines whether `sub` is the same as or a subclass of `sup`.

        Walks up the inheritance chain using `self.class_bases`.

        Examples:
            is_subclass("Mage", "Player")  → True
            is_subclass("Player", "Mage")  → False
            is_subclass("Player", "Player") → True

        Used in:
        - Method parameter validation (e.g., type of 'self')
        - Argument compatibility in function/method calls

        Returns:
            True if `sub` is a subclass of `sup`, or the same class.
        """
        while sub in self.class_bases:
            if sub == sup:
                return True
            sub = self.class_bases[sub]
        return sub == sup

    def check_class_def(self, cls: ClassDef):
        """
        Type-check a class definition with optional base class, fields, and methods.

        Validates:
        - Base class (if any) must be declared earlier.
        - Class name is registered early to allow forward references.
        - Fields must be valid `VarDecl` nodes with proper declared types.
        - Instance fields declared in base classes are inherited.
        - Class attributes (static fields) are tracked separately from instance fields.

        Method handling:
        - Each method is registered in `self.methods[class_name][method_name]`
          with its parameter types, return type, and number of required arguments.
        - If the first parameter is named 'self' and untyped, its type is injected
          as the current class name.
        - If 'self' is explicitly typed, it must match the current class or a known subclass.
        - Duplicate method names in the same class raise an error.

        Inheritance:
        - Instance fields from base classes are inherited by subclasses.
        - Method inheritance (e.g., calling self.base_method() from a subclass)
          is not yet implemented but planned.

        Example:
            class Player:
                def __init__(self, hp: int):
                    self.hp = hp

            class Mage(Player):
                def heal(self, amount: int):
                    self.hp += amount  # OK: 'hp' inherited from Player
        """
        name = cls.name
        if cls.base:
            if cls.base not in self.known_classes:
                raise TypeError(f"Base class '{cls.base}' not defined before '{name}'")
            self.class_bases[cls.name] = cls.base

        # Register class early
        self.known_classes.add(name)
        self.instance_fields[name] = {}
        self.class_attrs[name] = {}
        self.methods[name] = {}

        # Validate fields
        for field in cls.fields:
            if not isinstance(field, VarDecl):
                raise TypeError(f"Invalid field in class '{name}'")
            self.check_var_decl(field)
            # Assume all top-level fields are class attributes
            self.class_attrs[name][field.name] = field.declared_type

        # Inherit instance fields from base class
        if cls.base:
            if cls.base not in self.instance_fields:
                raise TypeError(f"Base class '{cls.base}' has no instance fields")
            # Copy base class fields into subclass
            for k, v in self.instance_fields[cls.base].items():
                self.instance_fields[name][k] = v

            for field in cls.fields:
                if field.name in self.instance_fields[name]:  # Check for field redefinition
                    if self.instance_fields[name][field.name] != field.declared_type:
                        raise TypeError(
                            f"Field '{field.name}' conflicts with base class: "
                            f"redefined as {field.declared_type} (was {self.instance_fields[name][field.name]})"
                        )

        # Validate methods (methods can use self.<field>)
        for method in cls.methods:
            if method.params:
                first_param = method.params[0]
                if first_param.name == "self" and first_param.type is None:
                    first_param.type = name  # Inject class name
                elif first_param.name == "self" and first_param.type != name:
                    # Allow self to be a subclass of the current class
                    actual = first_param.type
                    if not (
                        actual in self.known_classes
                        and name in self.known_classes
                        and self.is_subclass(actual, name)
                    ):
                        raise TypeError(f"In method '{method.name}', 'self' must be of type '{name}' or a subclass (got '{actual}')")


            # Register method in per-class method table
            param_types = []
            required = 0
            for param in method.params:
                if param.type is None:
                    raise TypeError(f"Parameter '{param.name}' in method '{method.name}' missing type")
                param_types.append(param.type)
                if param.default is None:
                    required += 1

            if method.name in self.methods[name]:
                raise TypeError(f"Duplicate method '{method.name}' in class '{name}'")
            self.methods[name][method.name] = (param_types, method.return_type, required)

            # Type-check the method body
            self.check_function_def(method)

    def check_assert_stmt(self, stmt: AssertStmt):
        """Check that the asserted expression is of type bool."""
        cond_type = self.check_expr(stmt.condition)
        if cond_type != "bool":
            raise TypeError(f"Assert expression must be bool, got {cond_type}")

    def check_raise_stmt(self, stmt: RaiseStmt):
        """Check that raise expression is not None.

        For now, accept any non-None value, and reject None
        """
        exc_type = self.check_expr(stmt.exception)
        if exc_type == "None":
            raise TypeError(f"Cannot raise value of type None — expression was: {stmt.exception}")

    def check_global_stmt(self, stmt: GlobalStmt):
        """Ensure global declaration is inside a function body.

        Rule:
        Must be inside a function (self.current_return_type is not None)
        Names declared global do not affect type checking here directly,
         but should be marked valid only in function bodies.
        """
        if self.current_return_type is None:
            raise TypeError(f"'global' declaration is only allowed inside a function")

        for name in stmt.names:
            if name not in self.global_env:
                raise TypeError(f"Global variable '{name}' used before declaration")
            self.env[name] = self.global_env[name]

    def check_try_except_stmt(self, stmt: TryExceptStmt):
        """Type-check try-except blocks."""
        # Check try block
        for s in stmt.try_body:
            self.check_stmt(s)

        # Check except blocks
        for block in stmt.except_blocks:
            # Validate exception type if present
            if block.exc_type is not None:
                if block.exc_type not in self.known_classes:
                    raise TypeError(f"Unknown exception type '{block.exc_type}' in except block")

            # Add alias to a shallow copy of env if needed
            old_env = self.env.copy()
            if block.alias is not None:
                self.env[block.alias] = block.exc_type or "object"  # fallback to generic object

            for s in block.body:
                self.check_stmt(s)

            self.env = old_env

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
    # pprint.pprint(tokens)
    print(tokens)
    from parser import Parser
    parser = Parser(tokens)
    node = parser.parse()
    # pprint.pprint(node)
    print(node)
    checker = TypeChecker().check(node)
