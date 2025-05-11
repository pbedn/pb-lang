from lang_ast import *

class CodeGen:
    """
    Generates C99-compatible code from a PB Program AST.

    This class walks the AST and emits C code using a simple indentation-based emitter.
    The output is designed to be readable, idiomatic C, using PB-specific type mappings
    (e.g., `int` → `int64_t`, `str` → `pb_string`). The output is buffered in `self.output`.
    """

    def __init__(self):
        self.output = []  # lines of C code
        self.indent_level = 0

    # ───────────────────────── helpers ─────────────────────────
    def map_type(self, pb_type: str) -> str:
        """
        Map a PB type name to a C type name.

        Example:
            "int" → "int64_t", "str" → "pb_string"

        Falls back to pointer to struct for user-defined classes.

        Parameters:
            pb_type (str): A PB type name.

        Returns:
            str: Corresponding C type.
        """
        return {
            "int": "int64_t",
            "float": "double",
            "bool": "bool",
            "str": "pb_string",
            "None": "void",
        }.get(pb_type, f"struct {pb_type}*")  # fallback for class types

    def gen_expr(self, expr: Expr) -> str:
        """
        Generate C code for an expression.

        Currently supports:
            - Literal values (int, float, str, etc.)

        Parameters:
            expr (Expr): The PB expression AST node.

        Returns:
            str: C expression as string.
        """
        if isinstance(expr, Literal):
            return expr.raw
        elif isinstance(expr, Identifier):
            return expr.name
        elif isinstance(expr, CallExpr):
            func_code = self.gen_expr(expr.func)
            arg_codes = ", ".join(self.gen_expr(arg) for arg in expr.args)
            return f"{func_code}({arg_codes})"
        elif isinstance(expr, AttributeExpr):
            obj_code = self.gen_expr(expr.obj)
            return f"{obj_code}->{expr.attr}"
        elif isinstance(expr, IndexExpr):
            base = self.gen_expr(expr.base)
            index = self.gen_expr(expr.index)
            return f"{base}[{index}]"



        raise NotImplementedError(f"Code generation not implemented for {type(expr).__name__}")

    # ───────────────────────── entry‑point ─────────────────────────

    def emit(self, line: str = ""):
        """Emit a single line of code with the current indentation level."""
        self.output.append("    " * self.indent_level + line)

    def generate(self, program: Program) -> str:
        """
        Entry point: generate C code from a complete PB program.

        Parameters:
            program (Program): The root AST node of a parsed and type-checked PB program.

        Returns:
            str: Full C source code as a single string.
        """
        self.output = []
        self.emit("// generated C code from PB")
        for stmt in program.body:
            self.gen_stmt(stmt)
        return "\n".join(self.output)

    # ───────────────────────── expressions ─────────────────────────


    # ───────────────────────── statements ─────────────────────────

    def gen_stmt(self, stmt: Stmt):
        """
        Dispatch method for top-level statements.
        
        Each statement type is handled by a dedicated generator function.
        """
        if isinstance(stmt, VarDecl):
            self.gen_var_decl(stmt)
        elif isinstance(stmt, AssignStmt):
            self.gen_assign_stmt(stmt)
        elif isinstance(stmt, AugAssignStmt):
            self.gen_aug_assign_stmt(stmt)
        elif isinstance(stmt, ReturnStmt):
            self.gen_return_stmt(stmt)
        elif isinstance(stmt, ExprStmt):
            self.gen_expr_stmt(stmt)
        elif isinstance(stmt, PassStmt):
            self.emit(";  // pass")
        elif isinstance(stmt, BreakStmt):
            self.emit("break;")
        elif isinstance(stmt, ContinueStmt):
            self.emit("continue;")
        elif isinstance(stmt, IfStmt):
            self.gen_if_stmt(stmt)
        elif isinstance(stmt, WhileStmt):
            self.gen_while_stmt(stmt)
        elif isinstance(stmt, ForStmt):
            self.gen_for_stmt(stmt)
        elif isinstance(stmt, FunctionDef):
            self.gen_function_def(stmt)


        else:
            raise NotImplementedError(f"Code generation not implemented for {type(stmt).__name__}")

    def gen_var_decl(self, decl: VarDecl):
        """
        Generate a C variable declaration from a PB VarDecl node.

        Supports literals for now. Declared PB types are mapped to C types using `map_type`.

        Example:
            PB:    x: int = 42
            C:     int64_t x = 42;

        Parameters:
            decl (VarDecl): A variable declaration AST node.
        """
        c_type = self.map_type(decl.declared_type)
        expr_code = self.gen_expr(decl.value)
        self.emit(f"{c_type} {decl.name} = {expr_code};")

    def gen_assign_stmt(self, stmt: AssignStmt):
        """
        Generate C code for a PB assignment statement.

        Example:
            PB:    x = 10
            C:     x = 10;

        Parameters:
            stmt (AssignStmt): The assignment AST node.
        """
        target = self.gen_expr(stmt.target)
        value = self.gen_expr(stmt.value)
        self.emit(f"{target} = {value};")

    def gen_aug_assign_stmt(self, stmt: AugAssignStmt):
        """
        Generate C code for an augmented assignment statement.

        Example:
            PB:    x += 1
            C:     x += 1;

        Parameters:
            stmt (AugAssignStmt): AST node representing augmented assignment.
        """
        target_code = self.gen_expr(stmt.target)
        value_code = self.gen_expr(stmt.value)
        self.emit(f"{target_code} {stmt.op} {value_code};")

    def gen_return_stmt(self, stmt: ReturnStmt):
        """
        Generate C return statement.

        Handles both `return x` and `return` (as `return;` for void).
        """
        if stmt.value is None:
            self.emit("return;")
        else:
            value_code = self.gen_expr(stmt.value)
            self.emit(f"return {value_code};")

    def gen_expr_stmt(self, stmt: ExprStmt):
        """
        Generate expression statement (e.g., function call).

        Emits the expression with a semicolon.
        """
        expr_code = self.gen_expr(stmt.expr)
        self.emit(f"{expr_code};")

    def gen_if_stmt(self, stmt: IfStmt):
        """
        Generate an if-elif-else statement.

        Each branch is emitted as either `if (...)`, `else if (...)`, or `else`.
        """
        for i, branch in enumerate(stmt.branches):
            if branch.condition:
                cond = self.gen_expr(branch.condition)
                self.emit(f"{'if' if i == 0 else 'else if'} ({cond}) " + "{")
            else:
                self.emit("else {")
            self.indent_level += 1
            for s in branch.body:
                self.gen_stmt(s)
            self.indent_level -= 1
            self.emit("}")

    def gen_while_stmt(self, stmt: WhileStmt):
        """
        Generate a while loop.
        """
        cond = self.gen_expr(stmt.condition)
        self.emit(f"while ({cond}) {{")
        self.indent_level += 1
        for s in stmt.body:
            self.gen_stmt(s)
        self.indent_level -= 1
        self.emit("}")

    def gen_for_stmt(self, stmt: ForStmt):
        """
        Generate a for loop over a list. Assumes list iteration with index.

        PB:     for x in items:
        C:      for (int i = 0; i < items.len; i++) {
                    T x = items.data[i];
        """
        iter_code = self.gen_expr(stmt.iterable)
        iter_var = f"__i_{stmt.var_name}"
        self.emit(f"for (int {iter_var} = 0; {iter_var} < {iter_code}.len; {iter_var}++) {{")
        self.indent_level += 1
        self.emit(f"{self.map_type('int')} {stmt.var_name} = {iter_code}.data[{iter_var}];")
        for s in stmt.body:
            self.gen_stmt(s)
        self.indent_level -= 1
        self.emit("}")

    def gen_function_def(self, fn: FunctionDef):
        """
        Generate a full C function from a PB FunctionDef.
        """
        c_ret = self.map_type(fn.return_type)
        args = ", ".join(f"{self.map_type(p.type)} {p.name}" for p in fn.params)
        self.emit(f"{c_ret} {fn.name}({args}) {{")
        self.indent_level += 1
        for stmt in fn.body:
            self.gen_stmt(stmt)
        self.indent_level -= 1
        self.emit("}")
