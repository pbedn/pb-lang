"""
PB Type Checker
===============

This module implements static type checking for PB, a Python-like language that compiles to C.
It validates types at the AST level according to the PB language specification.

Environment:
------------
- `self.env`:        Current scope variable types (name → type)
- `self.functions`:  Function signatures (name → (param_types, return_type))
- `self.classes`:    Class definitions (class_name → field_name → type)
- `self.current_return_type`: Return type currently expected (if inside a function)
- `self.in_loop`:    Loop nesting depth (to validate `break`/`continue`)

Supported Expression Types:
---------------------------
- `Literal`:          int, float, str, bool, None
- `Identifier`:       Variable reference
- `UnaryOp`:          `-`, `not` (numeric/bool)
- `BinOp`:            Arithmetic (`+`, `-`, etc.), logical, and comparison
- `CallExpr`:         Validates function call arguments and return type
- `AttributeExpr`:    `obj.field`, primarily for `self` inside methods
- `IndexExpr`:        Indexing for `list[T]` and `dict[str, T]`
- `ListExpr`:         Homogeneous literal lists (e.g., `[1, 2, 3]`)
- `DictExpr`:         Homogeneous `dict[str, T]` (e.g., `{"a": 1}`)

Supported Statement Types:
--------------------------
- `VarDecl`:           Must have declared type and initializer
- `AssignStmt`:        Reassignment must match original declared type
- `AugAssignStmt`:     In-place ops for numeric vars and `self.field`
- `ReturnStmt`:        Must match function’s declared return type
- `BreakStmt`:         Only allowed inside loops
- `ContinueStmt`:      Only allowed inside loops
- `PassStmt`:          Always valid
- `AssertStmt`:        Assert condition must be bool
- `RaiseStmt`:         Cannot raise None
- `GlobalStmt`:        Only valid inside a function
- `IfStmt`:            Each condition must be bool, bodies checked
- `WhileStmt`:         Condition must be bool; body checked with loop context
- `ForStmt`:           Iterates over `list[T]`; binds loop var to `T`
- `FunctionDef`:       Checks parameters, return type, and body
- `ClassDef`:          Validates base class, fields, and methods
- `TryExceptStmt`:     Checks try-body; each except-block's type (if given) and body

Design Notes:
-------------
- Fully modular checker; expressions and statements checked recursively
- Allows for progressive language expansion (e.g., types, generics, decorators)
- Error messages are minimal but can be extended with position info
- Does not enforce runtime semantics (only static type structure)

Testing:
--------
- `TestTypeCheckerInternals`: Focuses on individual method-level units
- `TestTypeCheckerProgramLevel`: Integration tests with whole-program ASTs
- Test docstrings document the equivalent PB source for clarity

"""

from typing import Dict, Tuple, Optional, List

from lang_ast import (
    ForStmt,
    Stmt,
    Expr,
    Program,
    VarDecl,
    Literal,
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

        # func_name → ([param_types], return_type)
        self.functions: Dict[str, Tuple[List[str], str]] = {}

        self.functions["print"] = (["int"], "None")
        self.functions["print_str"] = (["str"], "None")
        # You can extend this later with polymorphic handling

        # to track the expected return type while checking a function body
        self.current_return_type: Optional[str] = None

        # for validating break and continue
        self.in_loop: int = 0  # loop depth counter

        self.classes: Dict[str, Dict[str, str]] = {}  # class name → field name → type

    def check(self, program: Program):
        """Type-check the entire program."""
        seen_main = False
        for stmt in program.body:
            if isinstance(stmt, FunctionDef) and stmt.name == "main":
                if seen_main:
                    raise TypeError("Multiple 'main' functions are not allowed")
                seen_main = True
            self.check_stmt(stmt)

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
            self.check_expr(stmt.expr)  # validate call, access, etc.

        else:
            raise NotImplementedError(f"Type checking not yet implemented for {type(stmt).__name__}")

    def check_var_decl(self, decl: VarDecl):
        """Type-check a variable declaration.
        
        Ensures that the initializer expression matches the declared type.
        """
        name = decl.name
        declared = decl.declared_type
        actual = self.check_expr(decl.value)

        if declared != actual:
            raise TypeError(f"Type mismatch in variable '{name}': declared {declared}, got {actual}")

        self.env[name] = declared

    def check_expr(self, expr: Expr) -> str:
        """Infer and return the static type of an expression."""
        if isinstance(expr, Literal):
            raw = expr.raw
            if raw == "True" or raw == "False":
                return "bool"
            elif raw == "None":
                return "None"
            elif raw.startswith('"') or raw.startswith("'"):
                return "str"
            elif "." in raw or "e" in raw or "E" in raw:
                return "float"
            else:
                return "int"

        elif isinstance(expr, Identifier):
            name = expr.name
            if name not in self.env:
                raise TypeError(f"Undefined variable '{name}'")
            return self.env[name]

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
                return left_type  # same as operands

            # Comparison
            elif op in {"==", "!=", "<", "<=", ">", ">=", "is", "is not"}:
                if left_type != right_type:
                    raise TypeError(f"Comparison '{op}' between incompatible types: {left_type} and {right_type}")
                return "bool"

            # Logical
            elif op in {"and", "or"}:
                if left_type != "bool" or right_type != "bool":
                    raise TypeError(f"Logical '{op}' requires bool operands")
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
                return operand_type

            elif op == "not":
                if operand_type != "bool":
                    raise TypeError(f"Unary 'not' requires bool operand, got {operand_type}")
                return "bool"

            else:
                raise TypeError(f"Unknown unary operator '{op}'")

        # CallExpr
        # the called expression must be a function
        # its signature must be known (e.g. from a prior FunctionDef)
        # arguments must match the parameter types (in number and type)
        # the expression returns a value of known type
        elif isinstance(expr, CallExpr):
            if not isinstance(expr.func, Identifier):
                raise TypeError("Only direct function calls are supported")

            fname = expr.func.name
            if fname not in self.functions:
                raise TypeError(f"Call to undefined function '{fname}'")

            param_types, return_type = self.functions[fname]
            if len(param_types) != len(expr.args):
                raise TypeError(f"Function '{fname}' expects {len(param_types)} arguments, got {len(expr.args)}")

            for i, (arg, expected_type) in enumerate(zip(expr.args, param_types)):
                actual_type = self.check_expr(arg)
                if actual_type != expected_type:
                    raise TypeError(f"Argument {i+1} to '{fname}' expected {expected_type}, got {actual_type}")

            return return_type
        
        # AttributeExpr
        # Ensure obj is a known variable with a class type
        # Look up the class in self.classes
        # Look up the attribute in the class field list
        elif isinstance(expr, AttributeExpr):
            # Only support obj.attr where obj is Identifier
            if not isinstance(expr.obj, Identifier):
                raise TypeError("Attribute access must be through an identifier")

            obj_name = expr.obj.name
            if obj_name not in self.env:
                raise TypeError(f"Variable '{obj_name}' is not defined")

            obj_type = self.env[obj_name]
            if obj_type not in self.classes:
                raise TypeError(f"'{obj_name}' has type '{obj_type}', which is not a class")

            class_fields = self.classes[obj_type]
            if expr.attr not in class_fields:
                raise TypeError(f"Class '{obj_type}' has no attribute '{expr.attr}'")

            return class_fields[expr.attr]

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
                return base_type[5:-1]  # extract T from list[T]

            elif base_type.startswith("dict[") and base_type.endswith("]"):
                if index_type != "str":
                    raise TypeError(f"Dict key must be str, got {index_type}")
                return base_type[len("dict[str, "):-1]  # extract T from dict[str, T]

            else:
                raise TypeError(f"Cannot index into value of type '{base_type}'")

        # PB supports:
        # ListExpr(elements=[...])        → list[T]
        #
        # A list must be homogeneous: all elements must have the same type
        elif isinstance(expr, ListExpr):
            if not expr.elements:
                raise TypeError("Cannot infer element type from empty list literal")

            elem_types = {self.check_expr(e) for e in expr.elements}
            if len(elem_types) > 1:
                raise TypeError(f"List elements must be the same type, got: {elem_types}")

            elem_type = elem_types.pop()
            return f"list[{elem_type}]"

        # PB supports:
        # DictExpr(entries=[(key, val)])  → dict[str, T]
        #
        # Dict must have string keys (enforced by grammar)
        # all values must have the same type
        elif isinstance(expr, DictExpr):
            if not expr.keys:
                raise TypeError("Cannot infer value type from empty dict literal")

            for key_expr in expr.keys:
                key_type = self.check_expr(key_expr)
                if key_type != "str":
                    raise TypeError(f"Dict keys must be str, got {key_type}")

            val_types = {self.check_expr(v) for v in expr.values}
            if len(val_types) > 1:
                raise TypeError(f"Dict values must be the same type, got: {val_types}")

            val_type = val_types.pop()
            return f"dict[str, {val_type}]"

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
        # if a value is returned: it must match the function’s declared return type
        else:
            actual_type = self.check_expr(stmt.value)
            if actual_type != self.current_return_type:
                raise TypeError(f"Return type mismatch: expected {self.current_return_type}, got {actual_type}")

    def check_function_def(self, fn: FunctionDef):
        """Type-check a function declaration and body."""
        fname = fn.name

        # Check for duplicate parameter names
        seen = set()
        param_types = []
        for param in fn.params:
            if param.name in seen:
                raise TypeError(f"Duplicate parameter name '{param.name}' in function '{fname}'")
            seen.add(param.name)
            if param.type is None:
                raise TypeError(f"Missing type annotation for parameter '{param.name}' in function '{fname}'")
            param_types.append(param.type)

        ret_type = fn.return_type or "None"

        # Register function signature
        self.functions[fname] = (param_types, ret_type)

        # New environment for function scope
        old_env = self.env.copy()
        self.env = old_env.copy()
        # Then add (or shadow) with this function’s parameters
        for p in fn.params:
            self.env[p.name] = p.type
        old_ret = self.current_return_type
        self.current_return_type = ret_type

        has_pass = False
        has_return = False

        # Check body
        for stmt in fn.body:
            self.check_stmt(stmt)
            if isinstance(stmt, PassStmt):
                has_pass = True
            elif isinstance(stmt, ReturnStmt):
                has_return = True

        if has_pass and has_return:
            raise TypeError(f"Function '{fn.name}' cannot contain both 'pass' and 'return'")

        # Restore previous state
        self.env = old_env
        self.current_return_type = old_ret

    def check_assign_stmt(self, stmt: AssignStmt):
        """Type-check a reassignment to an existing variable."""
        if not isinstance(stmt.target, Identifier):
            raise TypeError("Only assignment to identifiers is supported at this stage")

        name = stmt.target.name
        if name not in self.env:
            raise TypeError(f"Cannot assign to undefined variable '{name}'")

        expected_type = self.env[name]
        actual_type = self.check_expr(stmt.value)

        if expected_type != actual_type:
            raise TypeError(f"Assignment to '{name}': expected {expected_type}, got {actual_type}")

    def check_aug_assign_stmt(self, stmt: AugAssignStmt):
        """Check augmented assignment like x += 1."""
        target = stmt.target
        actual_type = self.check_expr(stmt.value)

        if isinstance(target, Identifier):
            name = target.name
            if name not in self.env:
                raise TypeError(f"Variable '{name}' not defined before augmented assignment")
            expected_type = self.env[name]

        elif isinstance(target, AttributeExpr):
            # Must be of form self.field inside method
            if not isinstance(target.obj, Identifier) or target.obj.name != "self":
                raise TypeError("Only 'self.field' assignments are supported in methods")

            if "self" not in self.env:
                raise TypeError("'self' is not defined in current scope")

            self_type = self.env["self"]
            if self_type not in self.classes:
                raise TypeError(f"'self' is of unknown class type '{self_type}'")

            class_fields = self.classes[self_type]
            field_name = target.attr
            if field_name not in class_fields:
                raise TypeError(f"Class '{self_type}' has no field '{field_name}'")

            expected_type = class_fields[field_name]

        else:
            raise TypeError("Unsupported target for augmented assignment")

        if stmt.op not in {"+=", "-=", "*=", "/=", "//=", "%="}:
            raise TypeError(f"Unsupported augmented operator '{stmt.op}'")

        if expected_type != actual_type:
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

        # Extend environment with loop variable
        old_env = self.env.copy()
        self.env[stmt.var_name] = element_type

        self.in_loop += 1
        for s in stmt.body:
            self.check_stmt(s)
        self.in_loop -= 1

        self.env = old_env

    def check_class_def(self, cls: ClassDef):
        """Type-check a class definition with optional base and method checking.
        
        Ensure:
        - Base is either None or already known
        - Fields are all VarDecl with valid types
        - Methods are type-checked like normal functions
        - Maintain correct environments for field/method checking

        """
        name = cls.name
        if cls.base is not None and cls.base not in self.classes:
            raise TypeError(f"Base class '{cls.base}' not defined before '{name}'")

        # Register class early to allow recursive references
        self.classes[name] = {}

        # Validate fields
        field_env: Dict[str, str] = {}
        for field in cls.fields:
            if not isinstance(field, VarDecl):
                raise TypeError(f"Invalid field in class '{name}'")
            self.check_var_decl(field)
            field_env[field.name] = field.declared_type

        # Save field types
        self.classes[name] = field_env

        # Validate methods (methods can use self.<field>)
        for method in cls.methods:
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
            raise TypeError("Cannot raise value of type None")

    def check_global_stmt(self, stmt: GlobalStmt):
        """Ensure global declaration is inside a function body.

        Rule:
        Must be inside a function (self.current_return_type is not None)
        Names declared global do not affect type checking here directly,
         but should be marked valid only in function bodies.
        """
        if self.current_return_type is None:
            raise TypeError(f"'global' declaration is only allowed inside a function")

    def check_try_except_stmt(self, stmt: TryExceptStmt):
        """Type-check try-except blocks."""
        # Check try block
        for s in stmt.try_body:
            self.check_stmt(s)

        # Check except blocks
        for block in stmt.except_blocks:
            # Validate exception type if present
            if block.exc_type is not None:
                if block.exc_type not in self.classes:
                    raise TypeError(f"Unknown exception type '{block.exc_type}' in except block")

            # Add alias to a shallow copy of env if needed
            old_env = self.env.copy()
            if block.alias is not None:
                self.env[block.alias] = block.exc_type or "object"  # fallback to generic object

            for s in block.body:
                self.check_stmt(s)

            self.env = old_env
