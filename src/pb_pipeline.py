import os

from lexer import Lexer, LexerError
from parser import Parser, ParserError
from type_checker import TypeChecker, TypeError
from codegen import CodeGen
from lang_ast import ImportStmt, ImportFromStmt, ImportAlias, Program, Stmt
from module_loader import load_module, ModuleNotFoundError
from module_loader import get_std_vendor_paths, is_native_binding


def process_imports(ast: Program, pb_path: str, verbose: bool = False):
    """
    Resolves import statements in the AST and returns:
        - a TypeChecker with registered modules
        - a loaded_modules dict
    """
    loaded_modules = {}
    checker = TypeChecker()
    entry_dir = os.path.dirname(os.path.abspath(pb_path))
    search_paths = get_std_vendor_paths() + [entry_dir]
    expanded: list[Stmt] = []

    for stmt in getattr(ast, "body", []):
        if isinstance(stmt, ImportFromStmt) and not stmt.is_wildcard:
            for alias_obj in stmt.names or []:
                try:
                    load_module(stmt.module + [alias_obj.name], search_paths, loaded_modules, verbose)
                except ModuleNotFoundError:
                    expanded.append(ImportFromStmt(module=stmt.module[:], names=[alias_obj], is_wildcard=False, loc=stmt.loc))
                else:
                    alias = alias_obj.asname or alias_obj.name
                    expanded.append(ImportStmt(module=stmt.module + [alias_obj.name], alias=alias, loc=stmt.loc))
        else:
            expanded.append(stmt)
    ast.body = expanded

    for stmt in getattr(ast, "body", []):
        if isinstance(stmt, ImportStmt):
            alias = stmt.alias or ".".join(stmt.module)
            mod_symbol = load_module(stmt.module, search_paths, loaded_modules, verbose)
            if verbose:
                print(f"Registering module '{alias}' with exports: {mod_symbol.exports}")
            checker.modules[alias] = mod_symbol
        elif isinstance(stmt, ImportFromStmt):
            mod_symbol = None
            if stmt.is_wildcard:
                mod_symbol = load_module(stmt.module, search_paths, loaded_modules, verbose)
                for name, kind in mod_symbol.exports.items():
                    if kind == "function" and name in mod_symbol.functions:
                        checker.functions[name] = mod_symbol.functions[name]
                    else:
                        checker.env[name] = kind
                stmt.names = [ImportAlias(n) for n in mod_symbol.exports.keys()]
            else:
                for alias_obj in stmt.names or []:
                    name = alias_obj.name
                    asname = alias_obj.asname or name
                    try:
                        sub_mod = load_module(stmt.module + [name], search_paths, loaded_modules, verbose)
                    except ModuleNotFoundError:
                        if mod_symbol is None:
                            mod_symbol = load_module(stmt.module, search_paths, loaded_modules, verbose)
                        if name not in mod_symbol.exports:
                            raise ModuleNotFoundError(
                                f"Module '{'.'.join(stmt.module)}' has no export '{name}'"
                            )
                        kind = mod_symbol.exports[name]
                        if kind == "function" and name in mod_symbol.functions:
                            checker.functions[asname] = mod_symbol.functions[name]
                        else:
                            checker.env[asname] = kind
                    else:
                        checker.modules[asname] = sub_mod

    return checker, loaded_modules


def compile_code_to_ast(
    source_code: str, 
    module_name: str = "main", 
    debug: bool = False, 
    verbose: bool = False, 
    pretty_print_code=None, 
    pprint=None,
    import_support: bool = True,
    pb_path: str | None= None
) -> tuple[Program | None, dict]:
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    if debug and pprint:
        print("TOKENS:\n"); pprint(tokens); print(f"{'-'*80}\n")

    parser = Parser(tokens)
    ast = parser.parse()
    if debug and pprint:
        print("PARSER AST:\n"); pprint(ast); print(f"{'-'*80}\n")

    checker = TypeChecker()
    loaded_modules = {}

    if import_support and pb_path is not None:
        checker, loaded_modules = process_imports(ast, pb_path, verbose=verbose)
    else:
        checker = TypeChecker()
        loaded_modules = {}

    checker.check(ast)
    if debug and pprint:
        print("TYPED ENRICHED AST:\n"); pprint(ast); print(f"{'-'*80}\n")

    ast.module_name = module_name
    return ast, loaded_modules

def compile_code_to_c_and_h(
    source_code: str,
    module_name: str = "main",
    debug: bool = False,
    verbose: bool = False,
    pretty_print_code=None,
    pprint=None,
    import_support: bool = True,
    pb_path: str | None = None
) -> tuple[str | None, str | None, Program | None, dict]:
    ast, loaded_modules = compile_code_to_ast(
        source_code, module_name, debug, verbose, pretty_print_code, pprint, import_support, pb_path
    )
    if ast is None:
        return None, None, None, loaded_modules
    if pb_path and is_native_binding(pb_path):
        # Skip code generation for native bindings
        return None, None, ast, loaded_modules
    codegen = CodeGen()
    h_code = codegen.generate_header(ast)
    c_code = codegen.generate(ast)
    if debug and pretty_print_code:
        print("PB CODE:\n"); pretty_print_code(source_code, "py"); print(f"{'-'*80}\n")
        print(f"H CODE: {module_name}.h\n"); pretty_print_code(h_code, "c"); print(f"{'-'*80}\n")
        print(f"C CODE: {module_name}.c\n"); pretty_print_code(c_code, "c"); print(f"{'-'*80}\n")
    return h_code, c_code, ast, loaded_modules
