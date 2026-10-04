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
    Parameter, FunctionDef, PassStmt, EnumDef, EnumMember,
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

        # Names of all classes in the current program
        self._class_names: set[str] = set()

        # Enum definitions by name
        self._enums: dict[str, EnumDef] = {}

        # Track which imported functions originate from native modules
        self._native_functions: dict[str, bool] = {}
        self._exception_aliases = {}
        self._try_frames = []
        self._loop_depth = 0
        self._volatile_names = set()

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

    def _classes_with_builtins(self, program):
        classes = [stmt for stmt in program.body if isinstance(stmt, ClassDef)]
        declared = {cls.name for cls in classes}
        needed = set()
        def walk(value):
            if isinstance(value, TryExceptStmt):
                needed.update(block.exc_type for block in value.except_blocks if block.exc_type)
            if isinstance(value, ClassDef) and value.base:
                needed.add(value.base)
            if isinstance(value, CallExpr) and isinstance(value.func, Identifier):
                if value.func.name in {"BaseException", "Exception", "RuntimeError", "ValueError", "IndexError", "KeyError", "TypeError"}:
                    needed.add(value.func.name)
            if hasattr(value, "__dict__"):
                for field in vars(value).values():
                    if isinstance(field, list):
                        for item in field: walk(item)
                    elif hasattr(field, "__dict__"): walk(field)
        walk(program)
        parents = {"BaseException": None, "Exception": "BaseException", "RuntimeError": "Exception", "ValueError": "Exception", "IndexError": "Exception", "KeyError": "Exception", "TypeError": "Exception"}
        synthesized = []
        def add(name):
            if name in declared or name not in parents:
                return
            base = parents[name]
            if base: add(base)
            fields, methods = [], []
            if name == "BaseException":
                fields = [VarDecl("msg", "str")]
                methods = [FunctionDef("__init__", [Parameter("self", name), Parameter("msg", "str")], [AssignStmt(AttributeExpr(Identifier("self", inferred_type=name), "msg"), Identifier("msg", inferred_type="str"))], "None")]
            builtin = ClassDef(name, base, fields, methods)
            builtin.builtin_exception = True
            synthesized.append(builtin)
            declared.add(name)
        for name in sorted(needed): add(name)
        return synthesized + classes

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

        self._classes = self._classes_with_builtins(program)
        self._enums = getattr(program, "enum_c_names", {}).copy()
        self._instance_fields = getattr(program, "inferred_instance_fields", {})
        self._class_bases = getattr(program, "class_bases", {}).copy()
        self._class_bases.update({cls.name: cls.base for cls in self._classes})
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
        self._enums = getattr(program, "enum_c_names", {}).copy()

        self._lines.append("#pragma once")

        self._classes = self._classes_with_builtins(program)
        self._instance_fields = getattr(program, "inferred_instance_fields", {})
        self._class_bases = getattr(program, "class_bases", {}).copy()
        self._class_bases.update({cls.name: cls.base for cls in self._classes})
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
            return self._enums[pb_type]
        # user class
        return f"struct {pb_type} *"

    def _emit_enum_defs(self, program: Program) -> None:
        for stmt in program.body:
            if not isinstance(stmt, EnumDef):
                continue
            name = getattr(stmt, "c_name", stmt.name)
            values = getattr(program, "enums", {}).get(stmt.name, {})
            members = ", ".join(f"{name}_{member.name} = {values.get(member.name, self._expr(member.value))}" for member in stmt.members)
            if not members:
                members = f"{name}__empty = 0"
            self._emit(f"typedef enum {{ {members} }} {name};")
            self._emit(f"static inline const char *{name}_name({name} value) {{")
            for member in stmt.members:
                self._emit(f'    if (value == {name}_{member.name}) return "{stmt.name}.{member.name}";')
            self._emit('    return "<invalid enum>";')
            self._emit("}")
            self._emit()

    def _emit_class_structs(self, program: Program) -> None:
        """Emit structs (with single inheritance) for each ClassDef in the program."""
        # inside _emit_class_structs
        # declared  = {fld.name for fld in stmt.fields}         # explicit fields
        # inherited = fields from base classes (handled via _instance_fields)


        for stmt in self._classes:
            name = stmt.name
            if name in self._structs_emitted:
                continue
            self._structs_emitted.add(name)

            builtin = getattr(stmt, "builtin_exception", False)
            if builtin:
                self._emit(f"#ifndef PB_BUILTIN_{name}_DEFINED")
                self._emit(f"#define PB_BUILTIN_{name}_DEFINED")
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
            if builtin:
                self._emit(f"static inline void {name}____init__(struct {name} *self, const char *msg) {{ *(const char **)self = msg; }}")
                self._emit("#endif")
            self._emit()

            self._direct_fields[name] = actually_emitted
            self._class_bases[name] = stmt.base


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
        for cls in self._classes:
            if getattr(cls, "builtin_exception", False):
                continue
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


    def _exception_modified_names(self, fn):
        """C requires modified automatic variables to survive longjmp via volatile."""
        modified = set()
        def walk(node, protected=False):
            if isinstance(node, TryExceptStmt):
                protected = True
            if protected and isinstance(node, (AssignStmt, AugAssignStmt)) and isinstance(node.target, Identifier):
                modified.add(node.target.name)
            if hasattr(node, "__dict__"):
                for field in vars(node).values():
                    if isinstance(field, list):
                        for child in field:
                            walk(child, protected)
                    elif hasattr(field, "__dict__"):
                        walk(field, protected)
        walk(fn)
        return modified

    def _func_proto(self, fn: FunctionDef) -> str:
        ret = self._c_type(fn.return_type)
        protected = self._exception_modified_names(fn)
        params = []
        for p in fn.params:
            pty = self._c_type(p.type)
            if p.name in protected:
                pty += " volatile"
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
        self._volatile_names = self._exception_modified_names(fn)

        self._emit(self._func_proto(fn))

        self._try_frames = []
        self._loop_depth = 0
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
        for cls in self._classes:
            if cls.base:
                self._emit(f'pb_register_exception("{cls.name}", "{cls.base}");')
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
        self._try_frames = []
        self._loop_depth = 0
        self._volatile_names = self._exception_modified_names(fn)
        self._emit("int main(void)")
        self._emit("{")
        self._indent += 1
        self._emit("char __fbuf[256];")
        self._emit("(void)__fbuf;")
        for cls in self._classes:
            if cls.base:
                self._emit(f'pb_register_exception("{cls.name}", "{cls.base}");')
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
        # Expression temporaries belong to this statement's C scope, including
        # statements nested in branches and exception handlers.
        previous_lines, previous_indent = self._lines, self._indent
        self._lines, self._indent = [], 0
        try:
            statement = self._dispatch_stmt(st)
            return "\n".join(self._lines + [statement])
        finally:
            self._lines, self._indent = previous_lines, previous_indent

    def _dispatch_stmt(self, st: Any) -> str:
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
        if len(ce.args) != 1:
            arguments = []
            for arg in ce.args:
                typ = self._get_expr_type(arg)
                value = self._expr(arg)
                if isinstance(arg, IndexExpr):
                    typ = arg.elem_type
                if isinstance(arg, Identifier) and arg.name in self._exception_aliases:
                    typ, value = "str", self._exception_aliases[arg.name]
                if typ == "str":
                    value = f"pb_string_copy({value})"
                self._tmp_counter += 1
                name = f"__print_arg_{self._tmp_counter}"
                self._emit(f"{self._c_type(typ)} {name} = {value};")
                arguments.append(Identifier(name, inferred_type=typ))
            lines = ["pb_print_begin();"]
            for arg in arguments:
                lines.append(self._generate_print_call(CallExpr(Identifier("print"), [arg])))
            return "\n".join(lines + ["pb_print_end();"])

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
                "dict[str, int]": "dict_str_int_print",
                "dict[str, float]": "dict_str_float_print",
                "dict[str, bool]": "dict_str_bool_print",
                "dict[str, str]": "dict_str_str_print",
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

            if isinstance(arg, Identifier) and arg.name in self._exception_aliases:
                lines.append(f"pb_print_str({self._exception_aliases[arg.name]});")
                continue

            if t in self._enums:
                lines.append(f"pb_print_str({self._enums[t]}_name({arg_expr}));")
                continue

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
                if t and t.startswith(("list[", "set[", "dict[")):
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

        if len(ce.args) != 1:
            lines = ["pb_print_begin();"] + lines + ["pb_print_end();"]
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
            base_name = self._expr(st.target.base)
            index_val = self._expr(st.target.index)

            if list_type.startswith("dict[str,"):
                return f"pb_dict_set_str_{list_type[9:-1].strip()}({base_name}, {index_val}, {val});"

            if list_type == "list[int]":
                return f"list_int_set(&{base_name}, {index_val}, {val});"
            if list_type == "list[str]":
                return f"list_str_set(&{base_name}, {index_val}, {val});"
            if list_type == "list[float]":
                return f"list_float_set(&{base_name}, {index_val}, {val});"
            if list_type == "list[bool]":
                return f"list_bool_set(&{base_name}, {index_val}, {val});"

        if isinstance(st.target, AttributeExpr):
            val = self._owned_value(val, st.inferred_type)
        return f"{tgt} = {val};"

    def _generate_AugAssignStmt(self, st: AugAssignStmt) -> str:
        tgt = self._expr(st.target)
        val = self._expr(st.value)
        if st.op == "+=" and self._get_expr_type(st.target) == "str":
            return f"{tgt} = pb_str_concat({tgt}, {val});"
        op = st.op
        # drop extra '=' if present ('+==' → '+=')
        if op.endswith("="): op = op[:-1]
        # integer‐div replacement
        if op == "//": op = "/"
        return f"{tgt} {op}= {val};"

    def _owned_value(self, value, typ):
        if typ == "str":
            return f"pb_string_copy({value})"
        if typ and typ.startswith(("list[", "set[")):
            kind, elem = typ.split("[", 1)
            return f"{kind}_{elem[:-1]}_copy({value})"
        if typ and typ.startswith("dict[str,"):
            return f"dict_str_{typ[9:-1].strip()}_copy({value})"
        return value

    def _generate_ReturnStmt(self, st: ReturnStmt) -> str:
        if st.value is None:
            return "\n".join(self._unwind() + ["return;"])
        value = self._expr(st.value)
        typ = st.inferred_type or self._get_expr_type(st.value)
        value = self._owned_value(value, typ)
        if self._try_frames:
            self._tmp_counter += 1
            name = f"__return_{self._tmp_counter}"
            return "\n".join([f"{self._c_type(typ)} {name} = {value};"] + self._unwind() + [f"return {name};"])
        return f"return {value};"

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
        self._loop_depth += 1
        for sub in st.body:
            # prepend exactly one extra indent level so nested code lines up
            lines.append(self.INDENT + self._stmt(sub))

        self._loop_depth -= 1
        # 3) close the block
        lines.append("}")
        return "\n".join(lines)

    def _generate_ForStmt(self, st: ForStmt) -> str:
        loop = st.iterable
        self._tmp_counter += 1
        suffix = self._tmp_counter
        if isinstance(loop, CallExpr) and getattr(loop.func, "name", "") == "range":
            args = loop.args
            start = "0" if len(args) == 1 else self._expr(args[0])
            stop = self._expr(args[0] if len(args) == 1 else args[1])
            end = f"__range_end_{suffix}"
            lines = ["{", f"int64_t {end} = {stop};", f"for (int64_t {st.var_name} = {start}; {st.var_name} < {end}; ++{st.var_name}) {{"]
        else:
            value = self._expr(loop)
            typ = self._get_expr_type(loop)
            if not typ or not (typ == "str" or typ.startswith(("list[", "set[", "dict["))):
                raise RuntimeError(f"Unsupported for-loop iterable: {typ}")
            tmp, idx = f"__iter_{suffix}", f"__index_{suffix}"
            length = f"pb_string_length({tmp})" if typ == "str" else f"{tmp}.len"
            item = f"pb_string_char({tmp}, {idx})" if typ == "str" else f"{tmp}.data[{idx}]"
            if typ.startswith("dict["):
                item += ".key"
            lines = ["{", f"{self._c_type(typ)} {tmp} = {value};", f"for (int64_t {idx} = 0; {idx} < {length}; ++{idx}) {{", self.INDENT + f"{self._c_type(st.elem_type)} {st.var_name} = {item};"]
        self._loop_depth += 1
        for stmt in st.body:
            lines.append(self.INDENT + self._stmt(stmt))
        self._loop_depth -= 1
        lines.extend(["}", "}"])
        return "\n".join(lines)

    def _generate_BreakStmt(self, st: BreakStmt) -> str:
        return "\n".join(self._unwind(self._loop_depth) + ["break;"])

    def _generate_ContinueStmt(self, st: ContinueStmt) -> str:
        return "\n".join(self._unwind(self._loop_depth) + ["continue;"])

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

    def _unwind(self, minimum_loop=None):
        lines = []
        frames = self._try_frames[:]
        for index in range(len(frames) - 1, -1, -1):
            frame = frames[index]
            if minimum_loop is not None and frame["loop"] < minimum_loop:
                continue
            if frame.get("pop"):
                lines.append("pb_pop_try();")
            if frame.get("restore"):
                lines.append(f"pb_current_exc = {frame['restore']};")
            self._try_frames = frames[:index]
            for stmt in frame.get("finally", []):
                lines.append(self._stmt(stmt))
        self._try_frames = frames
        return lines

    def _generate_TryExceptStmt(self, st: TryExceptStmt) -> str:
        self._tmp_counter += 1
        n = self._tmp_counter
        ctx, flag, saved = f"__exc_ctx_{n}", f"__exc_flag_{n}", f"__exc_saved_{n}"
        lines = ["{", f"PbException {saved} = pb_current_exc;"]
        guard = f"__finally_ctx_{n}"
        pending = f"__finally_flag_{n}"
        if st.finally_body:
            lines += [f"PbTryContext {guard};", f"pb_push_try(&{guard});", f"int {pending} = pb_setjmp({guard}.env);", f"if ({pending} == 0) {{"]
            self._try_frames.append({"pop": True, "finally": st.finally_body, "loop": self._loop_depth})
        lines += [f"PbTryContext {ctx};", f"pb_push_try(&{ctx});", f"int {flag} = pb_setjmp({ctx}.env);", f"if ({flag} == 0) {{"]
        self._try_frames.append({"pop": True, "loop": self._loop_depth})
        for stmt in st.try_body:
            lines.append(self.INDENT + self._stmt(stmt))
        self._try_frames.pop()
        lines += ["pb_pop_try();", "} else {"]
        for index, block in enumerate(st.except_blocks):
            condition = f'pb_exception_matches("{block.exc_type}")' if block.exc_type else "true"
            prefix = "if" if index == 0 else "else if"
            lines.append(f"{prefix} ({condition}) {{")
            previous = self._exception_aliases.copy()
            if block.alias:
                typ = block.exc_type or "Exception"
                lines.append(f"struct {typ} *{block.alias} = (struct {typ} *)pb_current_exc.value;")
                lines.append(f"(void){block.alias};")
                self._exception_aliases[block.alias] = "pb_exception_message()"
            self._try_frames.append({"restore": saved, "loop": self._loop_depth})
            for stmt in block.body:
                lines.append(self.INDENT + self._stmt(stmt))
            self._try_frames.pop()
            self._exception_aliases = previous
            lines += [f"pb_current_exc = {saved};", "}"]
        if st.except_blocks:
            lines.append("else { pb_reraise(); }")
        else:
            lines.append("pb_reraise();")
        lines.append("}")
        if st.finally_body:
            self._try_frames.pop()
            lines += ["pb_pop_try();", "}"]
            self._try_frames.append({"restore": saved, "loop": self._loop_depth})
            for stmt in st.finally_body:
                lines.append(self._stmt(stmt))
            self._try_frames.pop()
            lines.append(f"if ({pending}) pb_reraise();")
        lines.append("}")
        return "\n".join(lines)

    def _generate_VarDecl(self, st: VarDecl) -> str:
        c_ty = self._c_type(st.declared_type)
        if st.name in self._volatile_names:
            c_ty += " volatile"
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
        if op == "+" and self._get_expr_type(e.left) == self._get_expr_type(e.right) == "str":
            return f"pb_str_concat({left}, {right})"
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
                self._emit(f"struct {class_name} *{var} = pb_alloc(sizeof(*{var}));")
                if args:
                    self._emit(f"{init_func}({var}, {args});")
                else:
                    self._emit(f"{init_func}({var});")
                return var

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
                    return f"pb_string_length({arg})"
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
                    return f"pb_string_copy(pb_format_int({self._expr(e.args[0])}))"
                elif e.args[0].inferred_type == "float":
                    return f"pb_string_copy(pb_format_double({self._expr(e.args[0])}))"
                elif e.args[0].inferred_type == "str":
                    return f"{self._expr(e.args[0])}"
                elif e.args[0].inferred_type == "bool":
                    return f'({self._expr(e.args[0])} ? "True" : "False")'
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
        if isinstance(e.obj, Identifier) and e.obj.name in self._exception_aliases and e.attr == "msg":
            return self._exception_aliases[e.obj.name]
        if getattr(e, "enum_c_name", None):
            return e.enum_c_name
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

        if t and t.startswith("dict[str,"):
            return f"pb_dict_get_str_{t[9:-1].strip()}({base}, {idx})"
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
