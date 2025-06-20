import os
from lexer import Lexer
from parser import Parser
from lang_ast import ImportStmt, FunctionDef, ClassDef, VarDecl
from type_checker import TypeChecker, ModuleSymbol


class ModuleNotFoundError(Exception):
    """Raised when a PB module cannot be found in any search path."""
    pass

def resolve_module(module_name: list[str], search_paths: list[str] = None) -> str:
    """
    Resolve a PB module name to an absolute file path.

    Args:
        module_name: List of identifiers, e.g. ['foo', 'bar'] for 'import foo.bar'.
        search_paths: List of base directories to search. Defaults to [os.getcwd()].

    Returns:
        The absolute path to the module file.

    Raises:
        ModuleNotFoundError: If the module file is not found in any of the search paths.
    """
    if search_paths is None:
        search_paths = [os.getcwd()]
    rel_path = os.path.join(*module_name) + ".pb"
    for base in search_paths:
        candidate = os.path.join(base, rel_path)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
    raise ModuleNotFoundError(
        f"Module {'.'.join(module_name)} not found. "
        f"Paths tried: {', '.join(os.path.join(base, rel_path) for base in search_paths)}"
    )


def load_module(module_name: list[str], search_paths: list[str], loaded_modules: dict, verbose: bool = False) -> ModuleSymbol:
    """
    Loads, parses, and type-checks a PB module, recursively resolving its imports.
    Caches loaded modules in loaded_modules to avoid redundant work and handle import cycles.

    Args:
        module_name: List of identifiers for the module (e.g., ["foo", "bar"]).
        search_paths: Directories to search for the .pb file.
        loaded_modules: Dict[module_name_tuple, ModuleSymbol] for already loaded modules.

    Returns:
        ModuleSymbol populated with exports.
    """
    name_tuple = tuple(module_name)
    if name_tuple in loaded_modules:
        return loaded_modules[name_tuple]

    # Step 1: Resolve to file path
    try:
        filepath = resolve_module(module_name, search_paths)
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(f"While importing {'.'.join(module_name)}: {e}")

    # Step 2: Parse file
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()

    # Step 3: Type check, including imports
    checker = TypeChecker()

    # For recursive imports, always put *this* module's directory first in the search_paths
    this_module_dir = os.path.dirname(filepath)
    # Compose new search_paths: this module's directory first, then the rest (no duplicates)
    child_search_paths = [this_module_dir] + [p for p in search_paths if p != this_module_dir]
    if verbose: print(f"Loading: {module_name} from {search_paths} -> {filepath}")

    # Register imports (recursive)
    for stmt in program.body:
        if isinstance(stmt, ImportStmt):
            # Recursively load imported module
            imported_name = stmt.module
            alias = stmt.alias if stmt.alias else imported_name[0]
            mod_symbol = load_module(imported_name, child_search_paths, loaded_modules)
            if verbose: print(f"Loaded module: {alias}, exports: {mod_symbol.exports}")
            checker.modules[alias] = mod_symbol

    checker.check(program)

    # Step 4: Collect exports (functions, classes, globals)
    exports = {}
    for stmt in program.body:
        if isinstance(stmt, FunctionDef):
            exports[stmt.name] = "function"  # Optionally: store signature string
        elif isinstance(stmt, ClassDef):
            exports[stmt.name] = "class"
        elif isinstance(stmt, VarDecl):
            exports[stmt.name] = stmt.declared_type

    mod_symbol = ModuleSymbol(name=".".join(module_name), path=filepath, exports=exports)
    loaded_modules[name_tuple] = mod_symbol
    return mod_symbol
