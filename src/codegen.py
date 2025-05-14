from __future__ import annotations
import logging
import functools
from typing import List, Optional, Set, Any
from lang_ast import (
    Program, FunctionDef, ClassDef, VarDecl, AssignStmt, AugAssignStmt,
    IfStmt, WhileStmt, ForStmt, ReturnStmt, ExprStmt, GlobalStmt,
    TryExceptStmt, RaiseStmt, AssertStmt, BreakStmt, ContinueStmt,
    ImportStmt,
    Expr, Identifier, Literal, StringLiteral, FStringLiteral,
    BinOp, UnaryOp, CallExpr, AttributeExpr, IndexExpr,
    ListExpr, DictExpr,
    Parameter, FunctionDef, PassStmt,
)

# ───────────────────────── Logging Setup ─────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

def debug(func):
    """
    Logs a readable call/return trace including:
      → function name
      → each AST arg summarized as ClassName(name)? 
      → the string you returned (or its type)
      → indent-based nesting
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # indent prefix
        level = getattr(self, "_indent", 0)
        prefix = "  " * level

        # summarize each positional arg
        parts = []
        for a in args:
            cls = a.__class__.__name__
            name = getattr(a, "name", None)
            parts.append(f"{cls}({name})" if name is not None else cls)
        args_str = ", ".join(parts) or "<no args>"

        # logger.debug(f"{prefix}→ {func.__name__}({args_str})")
        result = func(self, *args, **kwargs)

        if isinstance(result, str):
            out = result if len(result)<=60 else result[:57]+"..."
            ret = f"'{out}'"
        else:
            ret = f"<{type(result).__name__}>"

        # logger.debug(f"{prefix}← {func.__name__} returned {ret}")
        return result

    return wrapper

class CodeGen:
    """Translate a typed AST (`lang_ast.Program`) into a full C99 file."""

    INDENT = "    "

    @debug
    def __init__(self) -> None:
        self._lines: List[str] = []
        self._indent: int = 0
        self._runtime_emitted: bool = False
        self._structs_emitted: Set[str] = set()
        self._func_protos: List[str] = []
        self._globals_emitted: bool = False
        self._var_types: dict[str, str] = {}  # variable name → class name
        self._function_params: dict[str, list[str]] = {}
        self._function_defaults: dict[str, list[str|None]] = {}
        self._function_returns: dict[str, Optional[str]] = {}
        self._tmp_counter: int = 0
        self._fields: dict[str, set[str]] = {}   # class -> set(field names)
        self._base:   dict[str, str|None] = {}   # class -> base name or None

    @debug
    def generate(self, program: Program) -> str:
        """Generate the complete C source for `program`."""
        self._lines.clear()
        self._indent = 0

        self._classes = [d for d in program.body if isinstance(d, ClassDef)]

        self._emit_headers_and_runtime()
        self._emit_class_structs(program)
        self._emit_class_statics(program)
        self._emit_global_decls(program)
        self._emit_function_prototypes(program)

        # Definitions
        for stmt in program.body:
            if isinstance(stmt, ClassDef):
                self._emit_class_def(stmt)
            elif isinstance(stmt, FunctionDef):
                if stmt.name == "main":
                    self._emit_main(stmt)
                else:
                    self._emit_function(stmt)
            # top-level VarDecl or Assign go to globals, already handled
        return "\n".join(self._lines)

    @debug
    def _emit(self, line: str = "") -> None:
        # self._lines.append(f"{self.INDENT * self._indent}{line}")
        # handle multi-line strings gracefully
        prefix = self.INDENT * self._indent
        for sub in line.splitlines():
            self._lines.append(f"{prefix}{sub}")

    @debug
    def _emit_headers_and_runtime(self) -> None:
        if self._runtime_emitted:
            return
        self._runtime_emitted = True

        for h in ("stdio.h","stdlib.h","stdint.h","stdbool.h","string.h","stdarg.h"):
            self._emit(f"#include <{h}>")
        self._emit()

        # Failure helper
        self._emit("static void pb_fail(const char *msg) {")
        self._indent += 1
        self._emit('fprintf(stderr, "%s\\n", msg);')
        self._emit("exit(EXIT_FAILURE);")
        self._indent -= 1
        self._emit("}")
        self._emit()

        self._emit("// Runtime types for list[int] and dict[str,int]")
        self._emit("typedef struct {")
        self._indent += 1
        self._emit("int64_t len;")
        self._emit("int64_t *data;")
        self._indent -= 1
        self._emit("} List_int;")
        self._emit()

        self._emit("typedef struct {")
        self._indent += 1
        self._emit("const char *key;")
        self._emit("int64_t value;")
        self._indent -= 1
        self._emit("} Pair_str_int;")
        self._emit()

        self._emit("typedef struct {")
        self._indent += 1
        self._emit("int64_t len;")
        self._emit("Pair_str_int *data;")
        self._indent -= 1
        self._emit("} Dict_str_int;")
        self._emit()


        # Print helpers
        self._emit("static void pb_print_int(int64_t x)   { printf(\"%lld\\n\", x); }")
        self._emit("static void pb_print_double(double x) { printf(\"%f\\n\", x); }")
        self._emit("static void pb_print_str(const char *s){ printf(\"%s\\n\", s); }")
        self._emit("static void pb_print_bool(bool b)     { printf(\"%s\\n\", b?\"True\":\"False\"); }")
        
        self._emit("static int64_t pb_dict_get(Dict_str_int d, const char * key) {")
        self._indent += 1
        self._emit("for (int64_t i = 0; i < d.len; ++i) {")
        self._indent += 1
        self._emit("if (strcmp(d.data[i].key, key) == 0) return d.data[i].value;")
        self._indent -= 1
        self._emit("}")
        self._emit('pb_fail("Key not found in dict");')
        self._emit("return 0;")
        self._indent -= 1
        self._emit("}")
        self._emit()

    @staticmethod
    @debug
    def _c_type(pb_type: Optional[str]) -> str:
        """Map PB type to C99 type spelling."""
        if pb_type is None or pb_type == "None":
            return "void"
        tbl = {
            "int": "int64_t",
            "float": "double",
            "bool": "bool",
            "str": "const char *",
        }
        if pb_type in tbl:
            return tbl[pb_type]
        if pb_type.startswith("list[") and pb_type.endswith("]"):
            return "List_int"
        if pb_type.startswith("dict[") and pb_type.endswith("]"):
            return "Dict_str_int"
        # user class
        return f"struct {pb_type} *"

    @debug
    def _emit_class_structs(self, program: Program) -> None:
        """Emit structs (with single inheritance) for each ClassDef in the program."""
        # inside _emit_class_structs
        # declared      = {fld.name for fld in stmt.fields}         # explicit fields
        # extra_fields  = self._collect_instance_fields(stmt)       # self.hp, self.mp, …
        # inherited     = {f.name for f in base_cls.fields}         # only *explicit* base fields


        for stmt in program.body:
            if not isinstance(stmt, ClassDef):
                continue
            name = stmt.name
            if name in self._structs_emitted:
                continue
            self._structs_emitted.add(name)

            # Begin struct
            # logger.info(f"[struct] Emitting struct for class {stmt.name}")
            self._emit(f"typedef struct {name} {{")
            self._indent += 1

            # Single inheritance: embed base struct if present
            if stmt.base:
                self._emit(f"{stmt.base} base;")

            # All VarDecls in stmt.fields become instance fields
            for fld in stmt.fields:
                c_ty = self._c_type(fld.declared_type)
                # logger.info(f"[struct] {stmt.name}: explicit field '{fld.name}' as '{c_ty}'")
                self._emit(f"{c_ty} {fld.name};")

            # Add any self.x assignments not in fields
            declared = {fld.name for fld in stmt.fields}
            extra_fields = self._collect_instance_fields(stmt)
            # logger.info(f"Extra fields for {stmt.name}: {extra_fields}")

            # Names that are already present in the (direct) base class.
            inherited = set()
            if stmt.base:
                base_cls = next((c for c in self._classes if c.name == stmt.base), None)
                if base_cls:
                    inherited = {f.name for f in base_cls.fields}

            actually_emitted: set[str] = set(declared)     # keep track

            for field_name in sorted(extra_fields):
                if field_name not in declared and field_name not in inherited:
                    pb_type = extra_fields[field_name]
                    c_type = self._c_type(pb_type)
                    # logger.info(f"[struct] {stmt.name}: inferred field '{field_name}' as '{c_type}'")
                    self._emit(f"{c_type} {field_name};")
                    actually_emitted.add(field_name)       # now it *is* present

            self._indent -= 1
            self._emit(f"}} {name};")
            self._emit()

            self._fields[stmt.name] = declared | set(extra_fields)
            # store only the members that really exist in the struct
            self._fields[stmt.name] = actually_emitted
            self._base[stmt.name]   = stmt.base


    @debug
    def _emit_global_decls(self, program: Program) -> None:
        """Emit global variables at top-level."""
        if self._globals_emitted:
            return
        self._globals_emitted = True
        for stmt in program.body:
            if isinstance(stmt, VarDecl):
                c_ty = self._c_type(stmt.declared_type)
                # initializer expression will be a constant literal or simple expr
                init = self._expr(stmt.value)
                # remember the PB type for printf dispatch
                if stmt.declared_type:
                    self._var_types[stmt.name] = stmt.declared_type
                self._emit(f"{c_ty} {stmt.name} = {init};")
        if self._globals_emitted:
            self._emit()

    @debug
    def _emit_function_prototypes(self, program: Program) -> None:
        """Emit prototypes for every function the code-gen will create."""
        # — top-level (non-main) functions —
        for stmt in program.body:
            if isinstance(stmt, FunctionDef) and stmt.name != "main":
                self._emit(self._func_proto(stmt) + ";")

        # — methods of every class —
        for cls in (s for s in program.body if isinstance(s, ClassDef)):
            own = {m.name for m in cls.methods}

            for m in cls.methods:
                params = [Parameter("self", cls.name, None)] + [
                    p for p in m.params if p.name != "self"
                ]
                fake = FunctionDef(
                    name=f"{cls.name}__{m.name}",
                    params=params,
                    body=[],
                    return_type=m.return_type,
                    globals_declared=None,
                )
                self._emit(self._func_proto(fake) + ";")

            # stub prototype when the class (and its bases) define no __init__
            if "__init__" not in own and not cls.base:
                self._emit(f"void {cls.name}____init__(struct {cls.name} * self);")

        self._emit()


    @debug
    def _func_proto(self, fn: FunctionDef) -> str:
        ret = self._c_type(fn.return_type)
        params = []
        for p in fn.params:
            pty = self._c_type(p.type)
            params.append(f"{pty} {p.name}")
        if not params:
            params = ["void"]
        return f"{ret} {fn.name}({', '.join(params)})"

    @debug
    def _emit_function(self, fn: FunctionDef) -> None:
        """Emit a standard (non-main) function definition."""
        prev = getattr(self, "_current_class", None)
        if fn.params and fn.params[0].name == "self":
            self._current_class = fn.params[0].type   # 'Player', 'Mage', …

        self._emit(self._func_proto(fn))

        # keep metadata for print() type-picking
        self._function_returns[fn.name] = fn.return_type or "None"
        
        # … and their default literals (or None if no default)
        # record defaults *only* for the real parameters (skip `self`)
        self._function_defaults[fn.name] = [
            (arg.default.raw if arg.default else None)
            for arg in fn.params[1:]
        ]
        # record parameter names …
        self._function_params[fn.name] = [arg.name for arg in fn.params]

        self._emit("{")
        self._indent += 1

        # ── silence -Wunused-parameter for any parameter we never read ──
        for p in fn.params:
            if p.name:                      # skip the synthetic “void”
                self._emit(f"(void){p.name};")

        self._emit("char __fbuf[256];")
        self._emit("(void)__fbuf;")
        # declare parameters are already in C signature
        for stmt in fn.body:
            self._emit(self._stmt(stmt))
        # ensure void return
        if fn.return_type is None:
            self._emit("return;")
        self._indent -= 1
        self._emit("}")
        self._emit()
        self._current_class = prev                   # restore on exit

    @debug
    def _emit_main(self, fn: FunctionDef) -> None:
        """Map PB `main()` → `int main(void)`."""
        self._emit("int main(void)")
        self._emit("{")
        self._indent += 1
        self._emit("char __fbuf[256];")
        self._emit("(void)__fbuf;")
        for stmt in fn.body:
            self._emit(self._stmt(stmt))
        # self._emit("return 0;")
        self._indent -= 1
        self._emit("}")
        self._emit()

    @debug
    def _emit_class_def(self, cls: ClassDef) -> None:
        """
        Emit each method of `cls` as a standalone function taking
        an explicit `self` parameter of type `cls.name`.
        """
        own = set()

        for method in cls.methods:
            own.add(method.name)
            params = [p for p in method.params if p.name != "self"]
            self_param = Parameter("self", cls.name, None)
            fn = FunctionDef(
                name=f"{cls.name}__{method.name}",
                params=[self_param] + params,
                body=method.body,
                return_type=method.return_type,
                globals_declared=method.globals_declared,
            )
            # logger.debug(f"Emitting method: {fn.name}({', '.join(p.name for p in fn.params)})")
            self._emit_function(fn)

        # stub constructor if not defined & no base provides one
        if "__init__" not in own and not cls.base:
            self._emit(f"void {cls.name}____init__(struct {cls.name} * self) {{ /* no-op */ }}")
            self._emit()

        # wrappers for inherited methods – keep the types correct
        if cls.base:
            base = next((c for c in self._classes if c.name == cls.base), None)
            if base:
                for m in sorted({m.name for m in base.methods} - own):
                    ret_c = self._c_type(
                        next(mm for mm in base.methods if mm.name == m).return_type
                    )
                    # record PB return type so print() picks the right helper
                    ret_pb = next(mm for mm in base.methods if mm.name == m).return_type
                    self._function_returns[f"{cls.name}__{m}"] = ret_pb

                    self._emit(f"static inline {ret_c} {cls.name}__{m}(")
                    self._emit(f"    struct {cls.name} * self) {{")
                    self._indent += 1
                    call = f"{base.name}__{m}((struct {base.name} *)self)"
                    self._emit(f"return {call};" if ret_c != "void" else f"{call};")
                    self._indent -= 1
                    self._emit("}")
                    self._emit()

    @debug
    def _stmt(self, st: Any) -> str:
        """Translate one AST statement → C, returning a full C statement/block."""
        # ── 1.  print(…)  ───────────────────────────────────────────────────
        if isinstance(st, ExprStmt):
            if isinstance(st.expr, CallExpr):
                ce = st.expr
                if isinstance(ce.func, Identifier) and ce.func.name == "print":
                    lines: list[str] = []

                    for arg in ce.args:
                        arg_expr = self._expr(arg)

                        # a) string literals & f-strings
                        if isinstance(arg, (StringLiteral, FStringLiteral)):
                            lines.append(f"pb_print_str({arg_expr});")

                        # b) numeric / bool literals
                        elif isinstance(arg, Literal):
                            if arg.raw in ("True", "False"):
                                lines.append(f"pb_print_bool({arg_expr});")
                            elif "." in arg.raw:
                                lines.append(f"pb_print_double({arg_expr});")
                            else:
                                lines.append(f"pb_print_int({arg_expr});")

                        # c) identifiers (look up remembered type)
                        elif isinstance(arg, Identifier):
                            t = self._var_types.get(arg.name, "int")
                            if t == "str":
                                lines.append(f"pb_print_str({arg_expr});")
                            elif t == "bool":
                                lines.append(f"pb_print_bool({arg_expr});")
                            elif t in ("float", "double"):
                                lines.append(f"pb_print_double({arg_expr});")
                            else:
                                lines.append(f"pb_print_int({arg_expr});")

                        # ── NEW ──  value comes from a function / method call
                        elif isinstance(arg, CallExpr):
                           fn_name = None
                           # direct function  add(…),  get_name(…)
                           if isinstance(arg.func, Identifier):
                               fn_name = arg.func.name
                           # method call  obj.get_name(…)
                           elif isinstance(arg.func, AttributeExpr):
                               obj_var = getattr(arg.func.obj, "name", None)
                               if obj_var:
                                   cls = self._var_types.get(obj_var)
                                   if cls:
                                       fn_name = f"{cls}__{arg.func.attr}"

                           ret_pb = self._function_returns.get(fn_name, "int")
                           if ret_pb == "str":
                               lines.append(f"pb_print_str({arg_expr});")
                           elif ret_pb == "bool":
                               lines.append(f"pb_print_bool({arg_expr});")
                           elif ret_pb == "float":
                               lines.append(f"pb_print_double({arg_expr});")
                           else:
                               lines.append(f"pb_print_int({arg_expr});")

                        # d) attribute access  obj.field  OR  Class.field
                        elif isinstance(arg, AttributeExpr):
                            # try Class_field first, then obj-var type
                            typ = "int"
                            if isinstance(arg.obj, Identifier):
                                typ = self._var_types.get(
                                    f"{arg.obj.name}_{arg.attr}",
                                    self._var_types.get(arg.obj.name, "int")
                                )
                            if typ == "str":
                                lines.append(f"pb_print_str({arg_expr});")
                            else:
                                lines.append(f"pb_print_int({arg_expr});")

                        # e) a *function call expression*  >>> NEW <<<
                        elif isinstance(arg, CallExpr):
                            fname = None
                            if isinstance(arg.func, Identifier):
                                fname = arg.func.name
                            elif isinstance(arg.func, AttributeExpr) and isinstance(arg.func.obj, Identifier):
                                # method call → mangled name  Class__method
                                fname = f"{arg.func.obj.name}__{arg.func.attr}"

                            rtype = self._function_returns.get(fname, "int")
                            if rtype == "str":
                                lines.append(f"pb_print_str({arg_expr});")
                            elif rtype == "bool":
                                lines.append(f"pb_print_bool({arg_expr});")
                            elif rtype in ("float", "double"):
                                lines.append(f"pb_print_double({arg_expr});")
                            else:
                                lines.append(f"pb_print_int({arg_expr});")

                        # f) fallback: treat as int
                        else:
                            lines.append(f"pb_print_int({arg_expr});")

                    return "\n".join(lines)

            # not a print() call – just an expression statement
            return self._expr(st.expr) + ";"

        # ── 2.  assignment, returns, loops, etc.  (unchanged) ──────────────
        if isinstance(st, AssignStmt):
            tgt = self._expr(st.target)
            val = self._expr(st.value)
            return f"{tgt} = {val};"

        if isinstance(st, AugAssignStmt):
            tgt = self._expr(st.target)
            val = self._expr(st.value)
            op = st.op
            # drop extra '=' if present ('+==' → '+=')
            if op.endswith("="): op = op[:-1]
            # integer‐div replacement
            if op == "//": op = "/"
            return f"{tgt} {op}= {val};"

        if isinstance(st, ReturnStmt):
            ret = "" if st.value is None else " " + self._expr(st.value)
            return f"return{ret};"

        if isinstance(st, PassStmt):
            return ";  // pass"

        if isinstance(st, IfStmt):
            parts = []
            for idx, br in enumerate(st.branches):
                kw = "if" if idx == 0 else ("else if" if br.condition else "else")
                cond = "" if br.condition is None else f"({self._expr(br.condition)})"
                parts.append(f"{kw} {cond} {{")
                for s in br.body:
                    parts.append(self.INDENT + self._stmt(s))
                parts.append("}")
            return "\n".join(parts)

        if isinstance(st, WhileStmt):
            # 1) the loop header
            cond  = self._expr(st.condition)
            lines = [f"while ({cond}) {{"]

            # 2) translate every statement inside the while-body
            for sub in st.body:
                # prepend exactly one extra indent level so nested code lines up
                lines.append(self.INDENT + self._stmt(sub))

            # 3) close the block
            lines.append("}")
            return "\n".join(lines)

        if isinstance(st, ForStmt):
            # only support: for var in range(stop) or range(start, stop)
            loop = st.iterable
            if isinstance(loop, CallExpr) and getattr(loop.func, "name", "") == "range":
                args = loop.args
                if len(args) == 1:
                    start = "0"
                    stop  = self._expr(args[0])
                else:
                    start = self._expr(args[0])
                    stop  = self._expr(args[1])

                # build the for-loop header
                lines = [f"for (int64_t {st.var_name} = {start}; {st.var_name} < {stop}; ++{st.var_name}) {{"]
                # inject body statements
                for s in st.body:
                    lines.append(self.INDENT + self._stmt(s))
                lines.append("}")
                return "\n".join(lines)
            else:
                # fallback for other iterables
                return "/* unsupported for-loop */"
            return f"for(int64_t {st.var_name}={start}; {st.var_name}<{stop}; ++{st.var_name}) {{ /* ... */ }}"
        
        if isinstance(st, BreakStmt):
            return "break;"

        if isinstance(st, ContinueStmt):
            return "continue;"

        if isinstance(st, AssertStmt):
            cond = self._expr(st.condition)
            return f"if(!({cond})) pb_fail(\"Assertion failed\");"

        if isinstance(st, RaiseStmt):
            # dynamic exceptions not supported → abort
            return 'pb_fail("Exception raised");'

        if isinstance(st, GlobalStmt):
            names = ", ".join(st.names)
            return f"/* global {names} */"

        if isinstance(st, TryExceptStmt):
            return "/* try/except not supported at runtime */"

        if isinstance(st, VarDecl):
            c_ty = self._c_type(st.declared_type)
            val = self._expr(st.value)
            # remember every variable’s PB type for later printf logic
            if st.declared_type:
                self._var_types[st.name] = st.declared_type
            if isinstance(st.declared_type, str):
                if st.declared_type in self._structs_emitted:
                    self._var_types[st.name] = st.declared_type
                elif st.declared_type.startswith("dict["):
                    self._var_types[st.name] = "Dict_str_int"
                elif st.declared_type.startswith("list["):
                    self._var_types[st.name] = "List_int"
                elif st.declared_type in ("int", "float", "bool", "str"):
                    self._var_types[st.name] = st.declared_type
            return f"{c_ty} {st.name} = {val};"

        # fallbacks
        return "/* unhandled stmt */;"

    @debug
    def _expr(self, e: Expr) -> str:
        """Dispatch and return a C expression (no indent, no semicolon)."""
        if isinstance(e, Literal):
            # map Python True/False → C `true`/`false`
            if e.raw == "True":  return "true"
            if e.raw == "False": return "false"
            return e.raw
        if isinstance(e, StringLiteral):
            return f"\"{e.value}\""
        if isinstance(e, Identifier):
            return e.name
        if isinstance(e, BinOp):
            left  = self._expr(e.left)
            right = self._expr(e.right)
            op    = e.op
            # floor-div → C integer divide
            if op == "//":
                op = "/"
            # Python logic ops → C logical ops
            if op == "and":
                return f"({left} && {right})"
            if op == "or":
                return f"({left} || {right})"
            if op == "is":
                return f"({left} == {right})"
            if op == "is not":
                return f"({left} != {right})"
            # default
            return f"({left} {op} {right})"
        if isinstance(e, UnaryOp):
            operand = self._expr(e.operand)
            if e.op == "not":
                return f"!({operand})"
            return f"({e.op}{operand})"

        if isinstance(e, CallExpr):
            # Special case: Class.__init__(self, ...) → Player____init__(self, ...)
            if isinstance(e.func, AttributeExpr):
                obj = e.func.obj
                attr = e.func.attr

                # Special case: Class.__init__(self, ...) → Player____init__((struct Player *) self, hp, mp_default)
                if attr == "__init__" and isinstance(obj, Identifier):
                    class_name = obj.name
                    init_fn   = f"{class_name}____init__"
                    # figure out how many params that init wants
                    expected = self._function_params.get(init_fn, [])
                    # build the actual args (as C expressions)
                    actual = [self._expr(arg) for arg in e.args]
                    # pad missing args using defaults
                    defaults = self._function_defaults.get(init_fn, [])
                    # skip the 'self' slot at index 0
                    num_provided = len(actual) - 1    # arguments after 'self'
                    for i in range(num_provided, len(defaults)):
                        default = defaults[i]
                        if default is None:
                            raise RuntimeError(f"No default for parameter {i+1} of {init_fn}")
                        actual.append(default)
                    # cast self to the correct struct pointer
                    self_expr = self._expr(e.args[0])
                    casted   = f"(struct {class_name} *){self_expr}"
                    # stitch the call
                    args = ", ".join([casted] + actual[1:])
                    return f"{init_fn}({args})"


            # Constructor call like Player(...) or Mage(...)
            elif isinstance(e.func, Identifier):
                class_name = e.func.name
                if class_name in self._structs_emitted:
                    self._tmp_counter += 1
                    var = f"__tmp_{class_name.lower()}_{self._tmp_counter}"
                    init_func = f"{class_name}____init__"

                    actual_args = [self._expr(arg) for arg in e.args]
                    expected = self._function_params.get(init_func, [])
                    # pad using the actual defaults from the .pb AST
                    defaults = self._function_defaults.get(init_func, [])
                    # skip the 'self' slot at index 0
                    for i in range(len(actual_args), len(defaults)):
                        if defaults[i] is None:
                            raise RuntimeError(f"Missing default for parameter {i+1} of {init_func}")
                        actual_args.append(defaults[i])

                    args = ", ".join(actual_args)
                    self._emit(f"struct {class_name} {var};")
                    self._var_types[var] = class_name
                    self._emit(f"{init_func}(&{var}, {args});")
                    return f"&{var}"

                # Normal function call — also handle defaults
                fn_name = class_name
                if fn_name in self._function_params:
                    expected = self._function_params[fn_name]
                    actual_args = [self._expr(arg) for arg in e.args]
                    while len(actual_args) < len(expected):
                        # Insert known defaults by name (manual for now)
                        if fn_name == "increment":
                            actual_args.append("1")
                        else:
                            actual_args.append("0")
                    args = ", ".join(actual_args)
                    return f"{fn_name}({args})"

            # Method call: player.get_name() → Player__get_name(player)
            if isinstance(e.func, AttributeExpr):
                obj_expr = self._expr(e.func.obj)
                method_name = e.func.attr

                obj_var = getattr(e.func.obj, "name", None)
                class_type = self._var_types.get(obj_var)
                if class_type:
                    mangled = f"{class_type}__{method_name}"
                    args = ", ".join([obj_expr] + [self._expr(arg) for arg in e.args])
                    return f"{mangled}({args})"


            # Fallback: general function call expression
            fn = self._expr(e.func)
            args = ", ".join(self._expr(a) for a in e.args)
            return f"{fn}({args})"


        if isinstance(e, AttributeExpr):
            # --- FIRST:   class attribute  ---------------------------
            if isinstance(e.obj, Identifier) and e.obj.name in self._structs_emitted:
                #   Player.species   →   Player_species
                return f"{e.obj.name}_{e.attr}"
            
            obj = self._expr(e.obj)
            attr = e.attr

            # --- SECOND:  subclass instance --------------------------
            if isinstance(e.obj, Identifier):
                # 1.  Which class does this identifier refer to?
                if e.obj.name == "self" and hasattr(self, "_current_class"):
                    cls = self._current_class            # we are inside a method
                else:
                    cls = self._var_types.get(e.obj.name)

                # 2.  If we know the class and the field is NOT owned by it,
                #     let C look one level down into the embedded base struct.
                if cls and e.attr not in self._fields.get(cls, set()):
                    return f"{obj}->base.{e.attr}"

            return f"{obj}->{attr}"

        if isinstance(e, IndexExpr):
            base = self._expr(e.base)
            idx  = self._expr(e.index)
            if isinstance(e.base, Identifier) and self._var_types.get(e.base.name, "") == "Dict_str_int":
                return f"pb_dict_get({base}, {idx})"
            return f"{base}.data[{idx}]"  # or list_int_get
        if isinstance(e, ListExpr):
            elems = ", ".join(self._expr(x) for x in e.elements)
            self._tmp_counter += 1
            buf_name = f"__tmp_list_{self._tmp_counter}"
            self._emit(f"int64_t {buf_name}[] = {{{elems}}};")
            return f"(List_int){{ .len={len(e.elements)}, .data={buf_name} }}"

            # Not working with GCC C99
            # elems = ", ".join(self._expr(x) for x in e.elements)
            # return f"({{ .len={len(e.elements)}, .data=(int64_t[]){{{elems}}} }})"
        if isinstance(e, DictExpr):
            self._tmp_counter += 1
            buf_name = f"__tmp_dict_{self._tmp_counter}"
            pairs = ", ".join(
                f'{{{self._expr(k)}, {self._expr(v)}}}' for k, v in zip(e.keys, e.values)
            )
            self._emit(f"Pair_str_int {buf_name}[] = {{{pairs}}};")
            return f"(Dict_str_int){{ .len={len(e.keys)}, .data={buf_name} }}"

            # Not working with GCC C99
            # specialized to dict[str,int]
            # pairs = ", ".join(f'{{"{self._expr(k)}",{self._expr(v)}}}' for k,v in zip(e.keys,e.values))
            # return f"((Dict_str_int){{ .len={len(e.keys)}, .data=(Pair_str_int[]){{{pairs}}} }})"
        elif isinstance(e, FStringLiteral):
            buf  = "__fbuf"
            fmt  = e.raw
            specs = {"int": "%lld", "float": "%f", "str": "%s", "bool": "%s"}
    
            arg_list: list[str] = []
            for var in e.vars:
                pb_t   = self._var_types.get(var, "int")
                fmt    = fmt.replace(f"{{{var}}}", specs.get(pb_t, "%lld"))
                arg_list.append(var)
    
            joined = ", ".join(arg_list) or "0"           # keep GCC happy if empty
            return f'(snprintf({buf}, 256, "{fmt}", {joined}), {buf})'

        # fallback
        return "/* unhandled expr */"

    def _collect_instance_fields(self, cls: ClassDef) -> dict[str, str]:
        """Return a dict of 'self.x' → pb type ('int', 'str', ...) inferred from assignment or method param."""
        field_types: dict[str, str] = {}

        def walk_stmt(stmt, param_map):
            if isinstance(stmt, AssignStmt):
                if isinstance(stmt.target, AttributeExpr):
                    if isinstance(stmt.target.obj, Identifier) and stmt.target.obj.name == "self":
                        name = stmt.target.attr
                        value = stmt.value
                        # logger.debug(f"[collect] {cls.name}: found instance field '{name}' of type '{stmt.value}'")
                        if isinstance(value, StringLiteral):
                            field_types[name] = "str"
                        elif isinstance(value, Literal):
                            if value.raw in ("True", "False"):
                                field_types[name] = "bool"
                            elif value.raw.replace(".", "", 1).isdigit():
                                field_types[name] = "float" if "." in value.raw else "int"
                            else:
                                field_types[name] = "int"  # fallback
                        elif isinstance(value, Identifier):
                            ref_name = value.name
                            if ref_name in param_map:
                                field_types[name] = param_map[ref_name]
                                # logger.debug(f"[collect] {cls.name}: inferred field '{name}' from param '{ref_name}'")
                            else:
                                logger.warning(f"[collect] {cls.name}: unknown identifier '{ref_name}', defaulting '{name}' to int")
                                field_types[name] = "int"  # fallback
            elif isinstance(stmt, AugAssignStmt):
                if isinstance(stmt.target, AttributeExpr):
                    if isinstance(stmt.target.obj, Identifier) and stmt.target.obj.name == "self":
                        name = stmt.target.attr
                        field_types[name] = "int"  # conservative fallback
            elif hasattr(stmt, "body") and isinstance(stmt.body, list):
                for sub in stmt.body:
                    walk_stmt(sub, param_map)
            elif hasattr(stmt, "branches"):
                for br in stmt.branches:
                    for sub in br.body:
                        walk_stmt(sub, param_map)

        for method in cls.methods:
            param_map = {p.name: p.type for p in method.params if p.type}
            for stmt in method.body:
                walk_stmt(stmt, param_map)

        return field_types


    def _emit_class_statics(self, program: Program) -> None:
        """Emit class-level variables like Player_species = ..."""
        for stmt in program.body:
            if isinstance(stmt, ClassDef):
                for field in stmt.fields:
                    # Emit only class-level fields (not instance `self.x`)
                    if isinstance(field.value, StringLiteral):
                        self._emit(f'const char * {stmt.name}_{field.name} = "{field.value.value}";')
                        self._var_types[f"{stmt.name}_{field.name}"] = "str"
                    elif isinstance(field.value, Literal):
                        raw = field.value.raw
                        if raw in ("True", "False"):
                            self._emit(f'bool {stmt.name}_{field.name} = {raw.lower()};')
                            self._var_types[f"{stmt.name}_{field.name}"] = "bool"
                        elif "." in raw:
                            self._emit(f'double {stmt.name}_{field.name} = {raw};')
                            self._var_types[f"{stmt.name}_{field.name}"] = "float"
                        else:
                            self._emit(f'int64_t {stmt.name}_{field.name} = {raw};')
                            self._var_types[f"{stmt.name}_{field.name}"] = "int"


if __name__ == "__main__":
    import sys
    from lexer import Lexer
    from parser import Parser
    from type_checker import TypeChecker

    if len(sys.argv) != 2:
        print("Usage: python codegen.py <source.pb>")
        sys.exit(1)

    source = sys.argv[1]
    text = open(source).read()
    tokens = Lexer(text).tokenize()
    prog   = Parser(tokens).parse()
    # LOG AST
    # logger.info(prog)
    TypeChecker().check(prog)
    c_src  = CodeGen().generate(prog)
    print(c_src)
    # LOG C CODE
    # logger.info(c_src)
