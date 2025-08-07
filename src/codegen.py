from __future__ import annotations
import logging
import functools
from typing import List, Optional, Set, Any
from lang_ast import (
    Program, FunctionDef, ClassDef, VarDecl, AssignStmt, AugAssignStmt,
    IfStmt, WhileStmt, ForStmt, ReturnStmt, ExprStmt, GlobalStmt,
    TryExceptStmt, RaiseStmt, AssertStmt, BreakStmt, ContinueStmt,
    ImportStmt,
    ImportFromStmt,
    Expr, Identifier, Literal, StringLiteral, FStringLiteral, FStringText, FStringExpr,
    BinOp, UnaryOp, CallExpr, AttributeExpr, IndexExpr,
    ListExpr, SetExpr, DictExpr, EllipsisLiteral,
    Parameter, FunctionDef, PassStmt, EnumDef,
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

        logger.debug(f"{prefix}← {func.__name__} returned {ret}")
        return result

    return wrapper

class CodeGen:
    """Translate a typed AST (`lang_ast.Program`) into a full C99 file."""

    INDENT = "    "

    def __init__(self) -> None:
        self._lines: List[str] = []
        self._indent: int = 0
        self._runtime_emitted: bool = False
        self._structs_emitted: Set[str] = set()
        self._func_protos: List[str] = []
        self._globals_emitted: bool = False
        self._function_params: dict[str, list[str]] = {}
        self._function_defaults: dict[str, list[str|None]] = {}
        self._function_returns: dict[str, Optional[str]] = {}
        self._tmp_counter: int = 0
        self._tmp_list_counter: int = 0
        self._tmp_dict_counter: int = 0
        self._tmp_set_counter: int = 0

        # Track generic container instantiations
        self._needed_list_types: set[tuple[str, str]] = set()
        self._needed_dict_types: set[tuple[str, str]] = set()
        self._needed_set_types: set[tuple[str, str]] = set()

        # Instance field information from the type checker
        self._instance_fields: dict[str, dict[str, str]] = {}
        self._class_bases: dict[str, Optional[str]] = {}
        self._direct_fields: dict[str, set[str]] = {}

        # Map class name to ClassDef for attribute lookups
        self._class_map: dict[str, ClassDef] = {}

        self._modules: dict[str, str] = {}  # alias -> real module name

        # Lines that should execute before main to initialize globals
        self._global_init_lines: list[str] = []

        self._enums: dict[str, list[tuple[str, int]]] = {}

        # Names of all classes in the current program
        self._class_names: set[str] = set()

        # Track which imported functions originate from native modules
        self._native_functions: dict[str, bool] = {}

    def _attr_full_name(self, expr: Expr) -> str | None:
        if isinstance(expr, Identifier):
            return expr.name
        if isinstance(expr, AttributeExpr):
            base = self._attr_full_name(expr.obj)
            if base is None:
                return None
            return f"{base}.{expr.attr}"
        return None

    def _find_class_attr_origin(self, class_name: str, attr: str) -> Optional[str]:
        """Return the class that defines ``attr`` by walking bases."""
        c = class_name
        while c:
            cls_def = self._class_map.get(c)
            if cls_def and any(f.name == attr for f in cls_def.fields):
                return c
            c = self._class_bases.get(c)
        return None

    def generate(self, program: Program) -> str:
        """Generate the complete C source for ``program``."""
        self._program = program
        self._modules = getattr(program, "import_aliases", {}).copy()
        self._native_modules = getattr(program, "native_modules", {})
        self._native_functions = getattr(program, "native_functions", {})
        self._lines.clear()
        self._indent = 0
        self._runtime_emitted = False
        self._needed_list_types.clear()
        self._needed_dict_types.clear()
        self._needed_set_types.clear()
        self._global_init_lines.clear()
        self._enums = {name: members for name, members in getattr(program, "enums", {}).items()}

        self._classes = [d for d in program.body if isinstance(d, ClassDef)]
        self._instance_fields = getattr(program, "inferred_instance_fields", {})
        self._class_bases = {cls.name: cls.base for cls in self._classes}
        self._class_names = {cls.name for cls in self._classes}
        self._class_map = {cls.name: cls for cls in self._classes}
        self._direct_fields = {}
        for cls in self._classes:
            base_fields = set(self._instance_fields.get(cls.base, {})) if cls.base else set()
            declared = {f.name for f in cls.fields}
            assigned_here = self._assigned_fields_in_class(cls)
            direct = set()
            for field in self._instance_fields.get(cls.name, {}):
                if field not in base_fields or field in assigned_here or field in declared:
                    direct.add(field)
            self._direct_fields[cls.name] = direct

        self._emit_headers_and_runtime(False, include_self=True, include_runtime=False)
        self._emit_enum_defs(program)
        self._emit_global_decls(program)
        self._emit_class_statics(program)
        self._emit_global_init_func()

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

    def generate_header(self, program: Program) -> str:
        """Generate a C header file (.h) for a given PB module AST."""
        self._program = program
        self._modules = getattr(program, "import_aliases", {}).copy()
        self._native_modules = getattr(program, "native_modules", {})
        self._native_functions = getattr(program, "native_functions", {})
        self._lines.clear()
        self._indent = 0
        self._runtime_emitted = False
        self._needed_list_types.clear()
        self._needed_dict_types.clear()
        self._needed_set_types.clear()
        self._structs_emitted.clear()
        self._enums = {name: members for name, members in getattr(program, "enums", {}).items()}

        self._lines.append("#pragma once")

        self._classes = [d for d in program.body if isinstance(d, ClassDef)]
        self._instance_fields = getattr(program, "inferred_instance_fields", {})
        self._class_bases = {cls.name: cls.base for cls in self._classes}
        self._class_names = {cls.name for cls in self._classes}
        self._class_map = {cls.name: cls for cls in self._classes}
        self._direct_fields = {}
        for cls in self._classes:
            base_fields = set(self._instance_fields.get(cls.base, {})) if cls.base else set()
            declared = {f.name for f in cls.fields}
            assigned_here = self._assigned_fields_in_class(cls)
            direct = set()
            for field in self._instance_fields.get(cls.name, {}):
                if field not in base_fields or field in assigned_here or field in declared:
                    direct.add(field)
            self._direct_fields[cls.name] = direct

        self._emit_headers_and_runtime(True, include_self=False, include_runtime=True)
        self._emit_enum_defs(program)
        self._emit_global_externs(program)
        self._emit_class_structs(program)
        self._emit_function_prototypes(program)

        return "\n".join(self._lines)

    def _emit_global_externs(self, program: Program) -> None:
        """Emit extern declarations for global variables."""
        for stmt in program.body:
            if isinstance(stmt, VarDecl):
                c_ty = self._c_type(stmt.declared_type)
                name = self._mangle_global_name(stmt.name)
                self._emit(f"extern {c_ty} {name};")
                if name != stmt.name:
                    self._emit(f"#define {stmt.name} {name}")
        if any(isinstance(stmt, VarDecl) for stmt in program.body):
            self._emit()

    def _get_module_name(self) -> str:
        name = getattr(self._program, "module_name", None)
        return name or "main"

    def _mangle_function_name(self, name: str) -> str:
        if name == "main" or "__" in name:
            return name
        module = self._get_module_name().replace('.', '_')
        return f"{module}_{name}"

    def _mangle_global_name(self, name: str) -> str:
        module = self._get_module_name()
        if module == "main" or "." not in module:
            return name
        module = module.replace('.', '_')
        return f"{module}_{name}"

    def _emit(self, line: str = "") -> None:
        prefix = self.INDENT * self._indent
        for sub in line.splitlines():
            self._lines.append(f"{prefix}{sub}")

    def _emit_headers_and_runtime(self, is_header: bool = False, include_self: bool = False, include_runtime: bool = True) -> None:
        """Emit required #include directives for runtime and imports."""
        seen_includes: set[str] = set()
        seen_aliases: set[str] = set()

        def emit_include(path: str) -> None:
            if path not in seen_includes:
                self._emit(f'#include "{path}"')
                seen_includes.add(path)

        if not is_header:
            emit_include(f"{self._get_module_name()}.h")
            self._emit()
            return

        emit_include("pb_runtime.h")

        for stmt in self._program.body:
            if isinstance(stmt, ImportStmt):
                mod_name = ".".join(stmt.module)
                emit_include(f"{mod_name}.h")

                alias = stmt.alias or mod_name
                self._modules[alias] = getattr(self._program, "import_aliases", {}).get(alias, mod_name)
                if alias != mod_name and alias not in seen_aliases:
                    self._emit(f"#define {alias} {mod_name}")
                    seen_aliases.add(alias)
            elif isinstance(stmt, ImportFromStmt):
                mod_name = ".".join(stmt.module)
                emit_include(f"{mod_name}.h")
                if not stmt.is_wildcard:
                    for alias_obj in stmt.names or []:
                        name = alias_obj.name
                        alias = alias_obj.asname or name
                        if alias != name and alias not in seen_aliases:
                            self._emit(f"#define {alias} {name}")
                            seen_aliases.add(alias)

        self._emit()

    def _sanitize(self, name: str) -> str:
        """Sanitize a PB type name for C identifiers."""
        out = name.replace(" ", "_")
        for ch in "[],*":
            out = out.replace(ch, "_")
        while "__" in out:
            out = out.replace("__", "_")
        return out

    def _c_type(self, pb_type: Optional[str]) -> str:
        """Map PB type to C99 type spelling and collect generics."""
        if pb_type is None or pb_type == "None":
            return "void"

        if "|" in pb_type:
            parts = [p.strip() for p in pb_type.split("|") if p.strip() != "None"]
            if len(parts) == 1:
                pb_type = parts[0]
            else:
                raise NotImplementedError(f"C codegen does not support union type '{pb_type}'")
        tbl = {
            "int": "int64_t",
            "float": "double",
            "bool": "bool",
            "str": "const char *",
            "file": "PbFile",
        }
        if pb_type in tbl:
            return tbl[pb_type]
        if pb_type.startswith("list[") and pb_type.endswith("]"):
            mapping = {
                'list[int]': 'List_int',
                'list[float]': 'List_float',
                'list[bool]': 'List_bool',
                'list[str]': 'List_str',
            }
            if pb_type in mapping:
                return mapping[pb_type]
            elem = pb_type[5:-1].strip()
            c_elem = self._c_type(elem)
            name = self._sanitize(elem)
            self._needed_list_types.add((name, c_elem))
            return f"List_{name}"
        if pb_type.startswith("set[") and pb_type.endswith("]"):
            mapping = {
                'set[int]': 'Set_int',
                'set[float]': 'Set_float',
                'set[bool]': 'Set_bool',
                'set[str]': 'Set_str',
            }
            if pb_type in mapping:
                return mapping[pb_type]
            elem = pb_type[4:-1].strip()
            c_elem = self._c_type(elem)
            name = self._sanitize(elem)
            self._needed_set_types.add((name, c_elem))
            return f"Set_{name}"
        if pb_type.startswith("dict[str,") and pb_type.endswith("]"):
            mapping = {
                'dict[str, int]': 'Dict_str_int',
                'dict[str, float]': 'Dict_str_float',
                'dict[str, bool]': 'Dict_str_bool',
                'dict[str, str]': 'Dict_str_str',
            }
            if pb_type in mapping:
                return mapping[pb_type]
            val = pb_type[len("dict[str,"):-1].strip()
            c_val = self._c_type(val)
            name = self._sanitize(val)
            self._needed_dict_types.add((name, c_val))
            return f"Dict_str_{name}"
        if pb_type in self._enums:
            return pb_type
        # user class
        return f"struct {pb_type} *"

    def _emit_class_structs(self, program: Program) -> None:
        """Emit structs (with single inheritance) for each ClassDef in the program."""
        # inside _emit_class_structs
        # declared  = {fld.name for fld in stmt.fields}         # explicit fields
        # inherited = fields from base classes (handled via _instance_fields)


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

            declared = {fld.name for fld in stmt.fields}
            instance_fields = self._instance_fields.get(stmt.name, {})
            base_fields = set()
            if stmt.base:
                base_fields = set(self._instance_fields.get(stmt.base, {}))
            assigned_here = self._assigned_fields_in_class(stmt)

            actually_emitted: set[str] = set(declared)

            for field_name in instance_fields:
                pb_type = instance_fields[field_name]
                if field_name in base_fields and field_name not in assigned_here:
                    continue
                if field_name in declared:
                    continue
                c_type = self._c_type(pb_type)
                self._emit(f"{c_type} {field_name};")
                actually_emitted.add(field_name)

            self._indent -= 1
            self._emit(f"}} {name};")
            self._emit()

            self._direct_fields[name] = actually_emitted
            self._class_bases[name] = stmt.base

    def _emit_enum_defs(self, program: Program) -> None:
        for stmt in program.body:
            if not isinstance(stmt, EnumDef):
                continue
            self._emit(f"typedef enum {{")
            self._indent += 1
            for name, val in stmt.members:
                self._emit(f"{stmt.name}_{name} = {val},")
            self._indent -= 1
            self._emit(f"}} {stmt.name};")
            self._emit()


    def _emit_global_decls(self, program: Program) -> None:
        """Emit global variables at top-level."""
        if self._globals_emitted:
            return
        self._globals_emitted = True
        for stmt in program.body:
            if isinstance(stmt, VarDecl):
                c_ty = self._c_type(stmt.declared_type)
                name = self._mangle_global_name(stmt.name)
                if isinstance(stmt.value, CallExpr) and isinstance(stmt.value.func, Identifier) and stmt.value.func.name in self._class_names:
                    class_name = stmt.value.func.name
                    self._tmp_counter += 1
                    tmp = f"__tmp_{class_name.lower()}_{self._tmp_counter}"
                    self._emit(f"struct {class_name} {tmp};")
                    self._emit(f"{c_ty} {name};")
                    args = [self._expr(a) for a in stmt.value.args]
                    call = f"{class_name}____init__(&{tmp}{', ' if args else ''}{', '.join(args)})";
                    self._global_init_lines.append(f"{call};")
                    self._global_init_lines.append(f"{name} = &{tmp};")
                else:
                    init = self._expr(stmt.value)
                    self._emit(f"{c_ty} {name} = {init};")
        if self._globals_emitted:
            self._emit()

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

            if "__init__" not in own:
                if cls.base:
                    base_cls, base_init = self._find_base_init(cls)
                    if base_init:
                        params = [p for p in base_init.params if p.name != "self"]
                        params_code = ", ".join(f"{self._c_type(p.type)} {p.name}" for p in params)
                        self._emit(f"void {cls.name}____init__(struct {cls.name} * self{', ' if params_code else ''}{params_code});")
                    else:
                        self._emit(f"void {cls.name}____init__(struct {cls.name} * self);")
                else:
                    self._emit(f"void {cls.name}____init__(struct {cls.name} * self);")

        self._emit()


    def _func_proto(self, fn: FunctionDef) -> str:
        ret = self._c_type(fn.return_type)
        params = []
        for p in fn.params:
            pty = self._c_type(p.type)
            params.append(f"{pty} {p.name}")
        if not params:
            params = ["void"]
        
        # add module prefix if not main or class method
        name = fn.name
        if not name.startswith("main") and "__" not in name:
            name = f"{self._get_module_name()}_{name}"

        return f"{ret} {name}({', '.join(params)})"

    def _emit_function(self, fn: FunctionDef) -> None:
        """Emit a standard (non-main) function definition."""
        mangled_name = self._mangle_function_name(fn.name)

        self._emit(self._func_proto(fn))

        # keep metadata for print() type-picking
        self._function_returns[mangled_name] = fn.return_type or "None"
        
        # … and their default literals (or None if no default)
        # record defaults *only* for the real parameters (skip `self`)
        self._function_defaults[mangled_name] = [
            (arg.default.raw if arg.default else None)
            for arg in fn.params
        ]
        # record parameter names …
        self._function_params[mangled_name] = [arg.name for arg in fn.params]

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

    def _emit_main(self, fn: FunctionDef) -> None:
        """Map PB `main()` → `int main(void)`."""
        self._emit("int main(void)")
        self._emit("{")
        self._indent += 1
        self._emit("char __fbuf[256];")
        self._emit("(void)__fbuf;")
        for stmt in fn.body:
            self._emit(self._stmt(stmt))
        self._indent -= 1
        self._emit("}")
        self._emit()

    def _find_base_init(self, cls: ClassDef):
        """
        Search the inheritance chain for the nearest __init__ method.
        Returns (base_class, init_method) or (None, None) if not found.
        """
        base_name = cls.base
        while base_name:
            base_cls = next((c for c in self._classes if c.name == base_name), None)
            if base_cls is None:
                return None, None
            for m in base_cls.methods:
                if m.name == "__init__":
                    return base_cls, m
            base_name = base_cls.base
        return None, None

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

        if "__init__" not in own:
            # If the class has a base, look for an inherited __init__
            if cls.base:
                base_cls, base_init = self._find_base_init(cls)
                if base_init:
                    # Signature: same parameters as base __init__, except for self
                    params = [p for p in base_init.params if p.name != "self"]
                    params_code = ", ".join(f"{self._c_type(p.type)} {p.name}" for p in params)
                    self._emit(f"void {cls.name}____init__(struct {cls.name} * self{', ' if params_code else ''}{params_code}) {{")
                    self._indent += 1
                    args_code = ", ".join(p.name for p in params)
                    # Call the base class constructor, passing all arguments
                    self._emit(f"{base_cls.name}____init__((struct {base_cls.name} *)self{', ' if args_code else ''}{args_code});")
                    self._indent -= 1
                    self._emit("}")
                    self._emit()
                else:
                    # If base does not have __init__, emit a no-op constructor
                    self._emit(f"void {cls.name}____init__(struct {cls.name} * self) {{ /* no-op */ }}")
                    self._emit()
            else:
                # No base class: emit a no-op constructor
                self._emit(f"void {cls.name}____init__(struct {cls.name} * self) {{ /* no-op */ }}")
                self._emit()

        # wrappers for inherited methods – keep the types correct
        if cls.base:
            base = next((c for c in self._classes if c.name == cls.base), None)
            if base:
                for m in sorted({m.name for m in base.methods} - own):
                    if m == "__init__":
                        continue  # skip generating a wrapper for inherited __init__
                    method = next(mm for mm in base.methods if mm.name == m)
                    ret_c = self._c_type(method.return_type)
                    ret_pb = method.return_type
                    self._function_returns[f"{cls.name}__{m}"] = ret_pb

                    params = [p for p in method.params if p.name != "self"]
                    params_code = ", ".join(f"{self._c_type(p.type)} {p.name}" for p in params)

                    mangled = f"{cls.name}__{m}"
                    self._function_defaults[mangled] = [
                        (p.default.raw if p.default else None) for p in method.params
                    ]
                    self._function_params[mangled] = [p.name for p in method.params]
                    self._emit(
                        f"static inline {ret_c} {cls.name}__{m}(")
                    self._emit(
                        f"    struct {cls.name} * self{', ' if params_code else ''}{params_code}) {{")
                    self._indent += 1
                    call_args = ", ".join([f"(struct {base.name} *)self"] + [p.name for p in params])
                    call = f"{base.name}__{m}({call_args})"
                    self._emit(f"return {call};" if ret_c != "void" else f"{call};")
                    self._indent -= 1
                    self._emit("}")
                    self._emit()

    def _stmt(self, st: Any) -> str:
        """Translate one AST statement → C, returning a full C statement/block."""
        # Dispatch to specific generator methods based on node type
        if isinstance(st, ExprStmt): return self._generate_ExprStmt(st.expr)
        if isinstance(st, AssignStmt): return self._generate_AssignStmt(st)
        if isinstance(st, AugAssignStmt): return self._generate_AugAssignStmt(st)
        if isinstance(st, ReturnStmt): return self._generate_ReturnStmt(st)
        if isinstance(st, PassStmt): return self._generate_PassStmt(st)
        if isinstance(st, IfStmt): return self._generate_IfStmt(st)
        if isinstance(st, WhileStmt): return self._generate_WhileStmt(st)
        if isinstance(st, ForStmt): return self._generate_ForStmt(st)
        if isinstance(st, BreakStmt): return self._generate_BreakStmt(st)
        if isinstance(st, ContinueStmt): return self._generate_ContinueStmt(st)
        if isinstance(st, AssertStmt): return self._generate_AssertStmt(st)
        if isinstance(st, RaiseStmt): return self._generate_RaiseStmt(st)
        if isinstance(st, GlobalStmt): return self._generate_GlobalStmt(st)
        if isinstance(st, TryExceptStmt): return self._generate_TryExceptStmt(st)
        if isinstance(st, VarDecl): return self._generate_VarDecl(st)
        # ImportStmt is usually handled at a higher level or ignored if not supported
        if isinstance(st, ImportStmt): return "/* import (not directly translated to C stmt) */"

        logger.warning(f"Unhandled statement type: {type(st).__name__}")
        return f"/* unhandled_stmt: {type(st).__name__} */;"

    # --- Specific Statement Generators ---
    def _generate_ExprStmt(self, expr: Expr) -> str:
        if isinstance(expr, CallExpr) and \
           isinstance(expr.func, Identifier) and expr.func.name == "print":
            return self._generate_print_call(expr)
        return self._expr(expr) + ";"

    def _get_expr_type(self, expr: Expr) -> Optional[str]:
        return getattr(expr, "inferred_type", None)

    def _generate_print_call(self, ce: CallExpr) -> str:

        def _print_function_for_type(t: str) -> str:
            return {
                "str": "pb_print_str",
                "bool": "pb_print_bool",
                "float": "pb_print_double",
                "list[int]": "list_int_print",
                "list[float]": "list_float_print",
                "list[bool]": "list_bool_print",
                "list[str]": "list_str_print",
                "set[int]": "set_int_print",
                "set[float]": "set_float_print",
                "set[bool]": "set_bool_print",
                "set[str]": "set_str_print",
            }.get(t, "pb_print_int")  # default to int

        def _extract_dict_value_type(type_str: str) -> str:
            # Assumes type_str starts with "dict["
            try:
                key_type, val_type = map(str.strip, type_str[5:-1].split(",", 1))
                if key_type != "str":
                    raise RuntimeError("Only dicts with string keys are supported")
                return val_type
            except Exception:
                RuntimeError(f"Invalid dict type: {type_str}")
                return "int"

        lines: list[str] = []

        for arg in ce.args:
            arg_expr = self._expr(arg)
            print_arg = arg_expr
            t = self._get_expr_type(arg)

            # Always prefer explicit string forms for string literals and f-strings
            if isinstance(arg, (StringLiteral, FStringLiteral)):
                lines.append(f"pb_print_str({arg_expr});")
                continue

            # Determine type by inference or fallback
            # - numeric / bool literals
            # - Identifiers
            # - AttributeExpr   self.hp, obj.name
            # - IndexExpr       arr[0], d["x"]
            # - CallExpr        get_name()
            if isinstance(arg, Identifier):
                if t and (t.startswith("list[") or t.startswith("set[")):
                    print_arg = f"&{print_arg}"

            if isinstance(arg, IndexExpr):
                base_type = self._get_expr_type(arg.base)
                if base_type and base_type.startswith("dict["):
                    value_type = _extract_dict_value_type(base_type)
                    func = f"pb_dict_get_str_{value_type}"
                    key = self._expr(arg.index)
                    base = self._expr(arg.base)
                    print_arg = f"{func}({base}, {key})"
                    t = value_type
                elif base_type and base_type.startswith("list["):
                    t = arg.elem_type

            if not t:
                raise RuntimeError(f"No inferred type for: {arg}")

            print_func = _print_function_for_type(t)
            lines.append(f"{print_func}({print_arg});")

        return "\n".join(lines)

    def _generate_AssignStmt(self, st: AssignStmt) -> str:
        if not isinstance(st.target, (Identifier, AttributeExpr, IndexExpr)):
            raise RuntimeError(f"Unsupported assignment target: {type(st.target).__name__}")

        tgt = self._expr(st.target)
        val = self._expr(st.value)

        # target is list
        # x = [1]
        if isinstance(st.target, IndexExpr):
            list_type = st.inferred_type
            base_name = st.target.base.name
            index_val = self._expr(st.target.index)

            if list_type == "list[int]":
                return f"list_int_set(&{base_name}, {index_val}, {val});"
            if list_type == "list[str]":
                return f"list_str_set(&{base_name}, {index_val}, {val});"
            if list_type == "list[float]":
                return f"list_float_set(&{base_name}, {index_val}, {val});"
            if list_type == "list[bool]":
                return f"list_bool_set(&{base_name}, {index_val}, {val});"

        return f"{tgt} = {val};"

    def _generate_AugAssignStmt(self, st: AugAssignStmt) -> str:
        tgt = self._expr(st.target)
        val = self._expr(st.value)
        op = st.op
        # drop extra '=' if present ('+==' → '+=')
        if op.endswith("="): op = op[:-1]
        # integer‐div replacement
        if op == "//": op = "/"
        return f"{tgt} {op}= {val};"

    def _generate_ReturnStmt(self, st: ReturnStmt) -> str:
        ret = "" if st.value is None else " " + self._expr(st.value)
        return f"return{ret};"

    def _generate_PassStmt(self, st: PassStmt) -> str:
        return ";  // pass"

    def _generate_IfStmt(self, st: IfStmt) -> str:
        parts = []
        for idx, br in enumerate(st.branches):
            kw = "if" if idx == 0 else ("else if" if br.condition else "else")
            cond = "" if br.condition is None else f"({self._expr(br.condition)})"
            parts.append(f"{kw} {cond} {{")
            for s in br.body:
                parts.append(self.INDENT + self._stmt(s))
            parts.append("}")
        return "\n".join(parts)

    def _generate_WhileStmt(self, st: WhileStmt) -> str:
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

    def _generate_ForStmt(self, st: ForStmt) -> str:
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
    
    def _generate_BreakStmt(self, st: BreakStmt) -> str:
        return "break;"

    def _generate_ContinueStmt(self, st: ContinueStmt) -> str:
        return "continue;"

    def _generate_AssertStmt(self, st: AssertStmt) -> str:
        cond = self._expr(st.condition)
        return f"if(!({cond})) pb_fail(\"Assertion failed\");"

    def _generate_RaiseStmt(self, st: RaiseStmt) -> str:
        if st.exception is None:
            return "pb_reraise();"

        exc = st.exception
        if isinstance(exc, CallExpr) and isinstance(exc.func, Identifier):
            name = exc.func.name

            # Exception *instance* → pb_raise_obj
            if name in self._structs_emitted:
                val = self._expr(exc)
                etype = exc.inferred_type or name
                return f'pb_raise_obj("{etype}", {val});'

            # `raise ValueError("msg")`-style → pb_raise_msg
            elif len(exc.args) == 1:
                msg = self._expr(exc.args[0])
                return f'pb_raise_msg("{name}", {msg});'

        val = self._expr(exc)
        etype = exc.inferred_type or "Exception"
        if etype == "str":
            return f'pb_raise_msg("{etype}", {val});'
        return f'pb_raise_obj("{etype}", {val});'

    def _generate_GlobalStmt(self, st: GlobalStmt) -> str:
        names = ", ".join(st.names)
        return f"/* global {names} */"

    def _generate_TryExceptStmt(self, st: TryExceptStmt) -> str:
        self._tmp_counter += 1
        ctx = f"__exc_ctx_{self._tmp_counter}"
        flag = f"__exc_flag_{self._tmp_counter}"
        handled = f"__exc_handled_{self._tmp_counter}"

        lines = [
            f"PbTryContext {ctx};",
            f"pb_push_try(&{ctx});",
            f"int {flag} = setjmp({ctx}.env);",
            f"bool {handled} = false;",
            f"if ({flag} == 0) {{",
        ]
        for s in st.try_body:
            lines.append(self.INDENT + self._stmt(s))
        lines.append(f"pb_pop_try();")
        lines.append("} else {")

        first = True
        for block in st.except_blocks:
            cond = "1"
            if block.exc_type:
                cond = f'strcmp(pb_current_exc.type, \"{block.exc_type}\") == 0'
            prefix = "if" if first else "else if"
            lines.append(self.INDENT + f"{prefix} ({cond}) {{")
            if block.alias:
                cty = block.exc_type or "Exception"
                lines.append(self.INDENT*2 + f"struct {cty} * {block.alias} = (struct {cty} *)pb_current_exc.value;")
            for s in block.body:
                lines.append(self.INDENT*2 + self._stmt(s))
            lines.append(self.INDENT*2 + "pb_clear_exc();")
            lines.append(self.INDENT*2 + f"{handled} = true;")
            lines.append(self.INDENT + "}")
            first = False
        if st.except_blocks:
            lines.append(self.INDENT + "else {")
            lines.append(self.INDENT*2 + "pb_reraise();")
            lines.append(self.INDENT + "}")
        else:
            lines.append(self.INDENT + "pb_reraise();")
        lines.append("}")

        if st.finally_body:
            for s in st.finally_body:
                lines.append(self._stmt(s))

        lines.append(f"if ({flag} && !{handled}) pb_reraise();")
        return "\n".join(lines)

    def _generate_VarDecl(self, st: VarDecl) -> str:
        c_ty = self._c_type(st.declared_type)
        if st.value is None:
            return f"{c_ty} {st.name};"
    
        val = self._expr(st.value)
        return f"{c_ty} {st.name} = {val};"

    def _expr(self, e: Expr) -> str:
        """Dispatch and return a C expression (no indent, no semicolon)."""
        if isinstance(e, Literal): return self._generate_Literal(e)
        if isinstance(e, StringLiteral): return self._generate_StringLiteral(e)
        if isinstance(e, FStringLiteral): return self._generate_FStringLiteral(e)
        if isinstance(e, Identifier): return self._generate_Identifier(e)
        if isinstance(e, EllipsisLiteral): return "0"
        if isinstance(e, BinOp): return self._generate_BinOp(e)
        if isinstance(e, UnaryOp): return self._generate_UnaryOp(e)
        if isinstance(e, CallExpr): return self._generate_CallExpr(e)
        if isinstance(e, AttributeExpr): return self._generate_AttributeExpr(e)
        if isinstance(e, IndexExpr): return self._generate_IndexExpr(e)
        if isinstance(e, ListExpr): return self._generate_ListExpr(e)
        if isinstance(e, SetExpr): return self._generate_SetExpr(e)
        if isinstance(e, DictExpr): return self._generate_DictExpr(e)

        # fallback
        return "/* unhandled expr */"

    # --- Specific Expression Generators ---
    def _generate_Literal(self, e: Literal) -> str:
        if e.raw == "True": return "true"
        if e.raw == "False": return "false"
        raw = e.raw
        if raw and raw[0].isdigit():
            raw = raw.replace("_", "")
        return raw

    def _c_escape(self, text: str) -> str:
        """Escape a Python string for inclusion in C source."""
        return (
            text.replace('\\', '\\\\')
                .replace('"', '\\"')
                .replace('\n', '\\n')
        )

    def _generate_StringLiteral(self, e: StringLiteral) -> str:
        return f'"{self._c_escape(e.value)}"'

    def _generate_FStringLiteral(self, e: FStringLiteral) -> str:
        """
        Generate C code for an f-string using snprintf and a shared buffer.
        It builds a format string and argument list based on inferred types.
        """
        buf = "__fbuf"
        fmt_parts = []
        args = []

        specs = {
            "int": "%lld",
            "str": "%s",
            "bool": "%s"
        }

        for part in e.parts:
            if isinstance(part, FStringText):
                escaped = self._c_escape(part.text).replace("%", "%%")
                fmt_parts.append(escaped)
            elif isinstance(part, FStringExpr):
                inner = self._expr(part.expr)
                ty = self._get_expr_type(part.expr)

                if ty == "bool":
                    fmt_parts.append(specs["bool"])
                    args.append(f"(({inner}) ? \"True\" : \"False\")")
                elif ty == "float":
                    fmt_parts.append("%s")
                    args.append(f"pb_format_double({inner})")
                elif ty in specs:
                    fmt_parts.append(specs[ty])
                    args.append(inner)
                else:
                    fmt_parts.append("<?>")
                    args.append("/* unsupported */")

        fmt = "".join(fmt_parts)
        fmt_str = f'"{fmt}"'
        arg_str = ", ".join(args) or "0"

        return f'(snprintf({buf}, 256, {fmt_str}, {arg_str}), {buf})'

    def _generate_Identifier(self, e: Identifier) -> str:
        return e.name

    def _generate_BinOp(self, e: BinOp) -> str:
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

    def _generate_UnaryOp(self, e: UnaryOp) -> str:
        operand = self._expr(e.operand)
        if e.op == "not":
            return f"!({operand})"
        return f"({e.op}{operand})"

    def _generate_CallExpr(self, e: CallExpr) -> str:
        """Generate C code for a function/method/constructor call expression."""

        # --- AttributeExpr: module function, method, or class static method ---
        # Special case: Class.__init__(self, ...) → Player____init__(self, ...)
        if isinstance(e.func, AttributeExpr):
            obj = e.func.obj
            attr = e.func.attr
            obj_expr = self._expr(obj)

            obj_full = self._attr_full_name(obj)

            if obj_full and obj_full in self._modules:
                real = self._modules[obj_full]
                if self._native_modules.get(real, False):
                    mangled = attr
                else:
                    mangled = f"{real.replace('.', '_')}_{attr}"
                passed_args = [self._expr(arg) for arg in e.args]
                if mangled in self._function_params:
                    all_args = self._apply_defaults(mangled, passed_args)
                    args = ", ".join(all_args)
                    return f"{mangled}({args})"
                else:
                    args = ", ".join(passed_args)
                    return f"{mangled}({args})"

            obj_type = self._get_expr_type(obj)
            if obj_type and obj_type.startswith("list[") and obj_type.endswith("]"):
                elem = obj_type[5:-1]
                if attr == "append":
                    func = {
                        'int': 'list_int_append',
                        'float': 'list_float_append',
                        'bool': 'list_bool_append',
                        'str': 'list_str_append',
                    }[elem]
                    arg = self._expr(e.args[0])
                    return f"{func}(&{obj_expr}, {arg})"
                if attr == "pop":
                    func = {
                        'int': 'list_int_pop',
                        'float': 'list_float_pop',
                        'bool': 'list_bool_pop',
                        'str': 'list_str_pop',
                    }[elem]
                    return f"{func}(&{obj_expr})"
                if attr == "remove":
                    func = {
                        'int': 'list_int_remove',
                        'float': 'list_float_remove',
                        'bool': 'list_bool_remove',
                        'str': 'list_str_remove',
                    }[elem]
                    arg = self._expr(e.args[0])
                    return f"{func}(&{obj_expr}, {arg})"

            # Special case: Class.__init__ → Class____init__
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
                for i in range(len(actual), len(defaults)):
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
                for i in range(len(actual_args) + 1, len(defaults)):
                    if defaults[i] is None:
                        raise RuntimeError(f"Missing default for parameter {i+1} of {init_func}")
                    actual_args.append(defaults[i])

                args = ", ".join(actual_args)
                self._emit(f"struct {class_name} {var};")
                if args:
                    self._emit(f"{init_func}(&{var}, {args});")
                else:
                    self._emit(f"{init_func}(&{var});")
                return f"&{var}"

            # Normal function call — also handle defaults
            fn_name = e.func.name
            mangled = self._mangle_function_name(fn_name)

            # Try to detect imported functions
            imported_from = None
            for stmt in getattr(self._program, "body", []):
                if isinstance(stmt, ImportFromStmt):
                    mod_prefix = "_".join(stmt.module)
                    for alias_obj in stmt.names or []:
                        alias_name = alias_obj.asname or alias_obj.name
                        if fn_name == alias_name:
                            imported_from = mod_prefix
                            break
            if imported_from:
                mod_name = imported_from.replace("_", ".")
                if self._native_modules.get(mod_name, False) or self._native_functions.get(fn_name, False):
                    mangled = fn_name
                else:
                    mangled = f"{imported_from}_{fn_name}"

            if mangled in self._function_params:
                passed_args = [self._expr(arg) for arg in e.args]
                all_args = self._apply_defaults(mangled, passed_args)
                args = ", ".join(all_args)
                return f"{mangled}({args})"
            elif imported_from:
                args = ", ".join(self._expr(arg) for arg in e.args)
                return f"{mangled}({args})"

            if fn_name == "open":
                arg0 = self._expr(e.args[0])
                arg1 = self._expr(e.args[1])
                return f"pb_open({arg0}, {arg1})"

            if fn_name == "len":
                arg = self._expr(e.args[0])
                arg_type = e.args[0].inferred_type
                if arg_type == "str":
                    return f"(int64_t)strlen({arg})"
                if arg_type.startswith("list[") or arg_type.startswith("set[") or arg_type.startswith("dict["):
                    return f"{arg}.len"
                raise RuntimeError(f"len() not supported for {arg_type}")

            # --- Built-int type conversions ---
            if fn_name == "int":
                if e.args[0].inferred_type == "float":
                    return f"(int64_t)({self._expr(e.args[0])})"
                elif e.args[0].inferred_type == "str":
                    return f"(strtoll)({self._expr(e.args[0])}, NULL, 10)"
                else:
                    raise RuntimeError(f"`{fn_name}` conversion to `{e.args[0].inferred_type}` not supported yet!")
            if fn_name == "float":
                if e.args[0].inferred_type == "int":
                    return f"(double)({self._expr(e.args[0])})"
                elif e.args[0].inferred_type == "str":
                    return f"(strtod)({self._expr(e.args[0])}, NULL)"
                else:
                    raise RuntimeError(f"`{fn_name}` conversion to `{e.args[0].inferred_type}` not supported yet!")
            if fn_name == "bool":
                if e.args[0].inferred_type == "int":
                    return f"({self._expr(e.args[0])} != 0)"
                elif e.args[0].inferred_type == "float":
                    return f"({self._expr(e.args[0])} != 0.0)"
                else:
                    raise RuntimeError(f"`{fn_name}` conversion to `{e.args[0].inferred_type}` not supported yet!")
            if fn_name == "str":
                if e.args[0].inferred_type == "int":
                    return f"pb_format_int({self._expr(e.args[0])})"
                elif e.args[0].inferred_type == "float":
                    return f"pb_format_double({self._expr(e.args[0])})"
                elif e.args[0].inferred_type == "str":
                    return f"{self._expr(e.args[0])}"
                else:
                    raise RuntimeError(f"`{fn_name}` conversion to `{e.args[0].inferred_type}` not supported yet!")
            if fn_name == "hex":
                if e.args[0].inferred_type == "int":
                    return f"pb_format_hex({self._expr(e.args[0])})"
                else:
                    raise RuntimeError(f"`{fn_name}` conversion to `{e.args[0].inferred_type}` not supported yet!")

        # Method call: player.get_name() → Player__get_name(player)
        if isinstance(e.func, AttributeExpr):
            obj_expr = self._expr(e.func.obj)
            method_name = e.func.attr

            obj_type = self._get_expr_type(e.func.obj)
            if obj_type == "file":
                if method_name == "read":
                    return f"pb_file_read({obj_expr})"
                if method_name == "write":
                    arg = self._expr(e.args[0]) if e.args else "\"\""
                    return f"pb_file_write({obj_expr}, {arg})"
                if method_name == "close":
                    return f"pb_file_close({obj_expr})"

            class_type = self._get_expr_type(e.func.obj)
            if class_type:
                mangled = f"{class_type}__{method_name}"
                passed_args = [obj_expr] + [self._expr(arg) for arg in e.args]
                if mangled in self._function_params:
                    all_args = self._apply_defaults(mangled, passed_args)
                else:
                    all_args = passed_args
                args = ", ".join(all_args)
                return f"{mangled}({args})"

        # Fallback: general function call expression
        fn = self._expr(e.func)
        args = ", ".join(self._expr(a) for a in e.args)
        return f"{fn}({args})"

    def _generate_AttributeExpr(self, e: AttributeExpr) -> str:
        if isinstance(e.obj, Identifier) and e.obj.name in self._class_map:
            origin = self._find_class_attr_origin(e.obj.name, e.attr)
            if origin:
                return f"{origin}_{e.attr}"

        obj = self._expr(e.obj)
        attr = e.attr

        obj_full = self._attr_full_name(e.obj)
        if obj_full and obj_full in self._modules:
            return attr

        if isinstance(e.obj, Identifier):
            if e.obj.name in self._modules:
                return attr

            cls = self._get_expr_type(e.obj)
            if cls:
                depth = 0
                c = cls
                while c:
                    if attr in self._direct_fields.get(c, set()):
                        if depth == 0:
                            return f"{obj}->{attr}"
                        prefix = obj + "->base"
                        for i in range(1, depth):
                            prefix += ".base"
                        return f"{prefix}.{attr}"
                    c = self._class_bases.get(c)
                    depth += 1

                origin = self._find_class_attr_origin(cls, attr)
                if origin:
                    return f"{origin}_{attr}"

        return f"{obj}->{attr}"

    def _generate_IndexExpr(self, e: IndexExpr) -> str:
        base = self._expr(e.base)
        idx  = self._expr(e.index)

        t = self._get_expr_type(e)
        if t and t.startswith("list[") and t.endswith("]"):
            etype = e.elem_type or t[5:-1]
            func = {
                'int': 'list_int_get',
                'float': 'list_float_get',
                'bool': 'list_bool_get',
                'str': 'list_str_get',
            }.get(etype)
            if func:
                return f"{func}(&{base}, {idx})"
            return f"{base}.data[{idx}]"

        return f"{base}.data[{idx}]"
    
    def _generate_ListExpr(self, e: ListExpr) -> str:
        self._tmp_list_counter += 1
        buf_name = f"__tmp_list_{self._tmp_list_counter}"

        elem_c_type = self._c_type(e.elem_type)
        list_c_type = self._c_type(e.inferred_type)

        if not e.elements:
            self._emit(f"{list_c_type} {buf_name};")
            self._emit(f"list_{e.elem_type}_init(&{buf_name});")
            return buf_name
        else:
            elems = ", ".join(self._expr(x) for x in e.elements)
            self._emit(f"{elem_c_type} {buf_name}[] = {{{elems}}};")
            return f"({list_c_type}){{ .len={len(e.elements)}, .data={buf_name} }}"

    def _generate_SetExpr(self, e: SetExpr) -> str:
        self._tmp_set_counter += 1
        buf_name = f"__tmp_set_{self._tmp_set_counter}"

        elem_c_type = self._c_type(e.elem_type)
        set_c_type = self._c_type(e.inferred_type)

        if not e.elements:
            self._emit(f"{elem_c_type} {buf_name}[1] = {{0}};")
            return f"({set_c_type}){{ .len=0, .data={buf_name} }}"
        else:
            unique_codes = []
            seen = set()
            for el in e.elements:
                code = self._expr(el)
                if code not in seen:
                    seen.add(code)
                    unique_codes.append(code)

            elems = ", ".join(unique_codes)
            self._emit(f"{elem_c_type} {buf_name}[] = {{{elems}}};")
            return f"({set_c_type}){{ .len={len(unique_codes)}, .data={buf_name} }}"

    def _generate_DictExpr(self, e: DictExpr) -> str:
        self._tmp_dict_counter += 1
        buf_name = f"__tmp_dict_{self._tmp_dict_counter}"

        dict_c_type = self._c_type(e.inferred_type)

        pairs = ", ".join(
            f'{{{self._expr(k)}, {self._expr(v)}}}' for k, v in zip(e.keys, e.values)
        )
        if not pairs:
            self._emit(f"Pair_str_{e.elem_type} {buf_name}[1] = {{0}};")
            return f"({dict_c_type}){{ .len=0, .data={buf_name} }}" 

        self._emit(f"Pair_str_{e.elem_type} {buf_name}[] = {{{pairs}}};")
        return f"({dict_c_type}){{ .len={len(e.keys)}, .data={buf_name} }}"

        # Not working with GCC C99
        # specialized to dict[str,int]
        # pairs = ", ".join(f'{{"{self._expr(k)}",{self._expr(v)}}}' for k,v in zip(e.keys,e.values))
        # return f"((Dict_str_int){{ .len={len(e.keys)}, .data=(Pair_str_int[]){{{pairs}}} }})"


    # --- Helper Methods ---

    def _assigned_fields_in_class(self, cls: ClassDef) -> set[str]:
        fields: set[str] = set()

        def walk(stmt):
            if isinstance(stmt, AssignStmt):
                if isinstance(stmt.target, AttributeExpr):
                    if isinstance(stmt.target.obj, Identifier) and stmt.target.obj.name == "self":
                        fields.add(stmt.target.attr)
            elif hasattr(stmt, "body") and isinstance(stmt.body, list):
                for s in stmt.body:
                    walk(s)
            elif hasattr(stmt, "branches"):
                for br in stmt.branches:
                    for s in br.body:
                        walk(s)

        for m in cls.methods:
            for st in m.body:
                walk(st)
        return fields

    def _emit_class_statics(self, program: Program) -> None:
        """Emit class-level variables like Player_species = ..."""
        for stmt in program.body:
            if isinstance(stmt, ClassDef):
                for field in stmt.fields:
                    # Emit only class-level fields (not instance `self.x`)
                    if isinstance(field.value, StringLiteral):
                        self._emit(f'const char * {stmt.name}_{field.name} = "{field.value.value}";')
                    elif isinstance(field.value, Literal):
                        raw = field.value.raw
                        if raw in ("True", "False"):
                            self._emit(f'bool {stmt.name}_{field.name} = {raw.lower()};')
                        elif "." in raw:
                            self._emit(f'double {stmt.name}_{field.name} = {raw};')
                        else:
                            self._emit(f'int64_t {stmt.name}_{field.name} = {raw};')
                    elif isinstance(field.value, CallExpr) and isinstance(field.value.func, Identifier) and field.value.func.name in self._class_names:
                        class_name = field.value.func.name
                        self._tmp_counter += 1
                        tmp = f"__tmp_{class_name.lower()}_{self._tmp_counter}"
                        self._emit(f"struct {class_name} {tmp};")
                        self._emit(f"struct {class_name} * {stmt.name}_{field.name};")
                        args = [self._expr(a) for a in field.value.args]
                        call = f"{class_name}____init__(&{tmp}{', ' if args else ''}{', '.join(args)})";
                        self._global_init_lines.append(f"{call};")
                        self._global_init_lines.append(f"{stmt.name}_{field.name} = &{tmp};")

    def _emit_global_init_func(self) -> None:
        if not self._global_init_lines:
            return
        func_name = f"{self._get_module_name()}__init_globals"
        self._emit(f"__attribute__((constructor)) static void {func_name}(void)")
        self._emit("{")
        self._indent += 1
        for line in self._global_init_lines:
            self._emit(line)
        self._indent -= 1
        self._emit("}")
        self._emit()

    def _apply_defaults(self, mangled_name: str, passed_args: list[str]) -> list[str]:
        """
        Given a mangled function name and a list of already generated argument expressions (as strings),
        return the final list of arguments to use for codegen, padding with defaults as needed.
        Raise if required arguments are missing.
        """
        expected_params = self._function_params[mangled_name]
        defaults = self._function_defaults[mangled_name]
        args = list(passed_args)
        for i in range(len(args), len(expected_params)):
            default = defaults[i]
            if default is None:
                raise RuntimeError(
                    f"Missing argument for parameter '{expected_params[i]}' in '{mangled_name}', and no default provided."
                )
            args.append(default)
        return args

    # ------------------------------------------------------------------
    def generate_types_header(self) -> str:
        """Generate type specialization declarations for pb_gen_types.h."""
        lines: list[str] = []
        for name, c_ty in sorted(self._needed_list_types):
            lines.append(f"PB_DECLARE_LIST({name}, {c_ty})")
        for name, c_ty in sorted(self._needed_set_types):
            lines.append(f"PB_DECLARE_SET({name}, {c_ty})")
        for name, c_ty in sorted(self._needed_dict_types):
            lines.append(f"PB_DECLARE_DICT({name}, {c_ty})")
        return "\n".join(lines) + ("\n" if lines else "")


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
