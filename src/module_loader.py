import os
import toml
from lexer import Lexer
from parser import Parser
from lang_ast import ImportStmt, ImportFromStmt, FunctionDef, ClassDef, VarDecl
from type_checker import TypeChecker, ModuleSymbol


root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_std_vendor_paths():
    """
    Returns the absolute paths to stdlib and vendor directories at the repo root.
    """
    stdlib = os.path.join(root, "stdlib")
    vendor = os.path.join(root, "vendor")
    return [stdlib, vendor]


def load_vendor_metadata(module_path: str):
    vendor_dir = os.path.dirname(module_path)
    metadata_path = os.path.join(vendor_dir, "metadata.toml")
    if os.path.isfile(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as f:
            return toml.load(f)
    return None


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
    rel_path2 = os.path.join(*module_name, module_name[-1] + ".pb")
    for base in search_paths:
        candidate = os.path.join(base, rel_path)
        candidate2 = os.path.join(base, rel_path2)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
        if os.path.isfile(candidate2):
            return os.path.abspath(candidate2)
    paths = [os.path.join(base, rel_path) for base in search_paths]
    paths2 = [os.path.join(base, rel_path2) for base in search_paths]
    raise ModuleNotFoundError(
        f"Module {'.'.join(module_name)} not found. "
        f"Paths tried: {', '.join(paths + paths2)}"
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

    base_search_paths = get_std_vendor_paths()
    this_module_dir = os.path.dirname(filepath)
    # Compose new search_paths: stdlib, vendor, this module dir, then rest (no duplicates)
    child_search_paths = []
    for p in base_search_paths + [this_module_dir] + search_paths:
        if p not in child_search_paths:
            child_search_paths.append(p)
    if verbose: print(f"Loading: {module_name} from {search_paths} -> {filepath}")

    # Register imports (recursive)
    for stmt in program.body:
        if isinstance(stmt, ImportStmt):
            alias_name = stmt.alias or ".".join(stmt.module)
            mod_symbol = load_module(stmt.module, child_search_paths, loaded_modules, verbose)
            if verbose:
                print(f"Loaded module: {alias_name}, exports: {mod_symbol.exports}")
            checker.modules[alias_name] = mod_symbol
        elif isinstance(stmt, ImportFromStmt):
            mod_symbol = None
            if stmt.is_wildcard:
                mod_symbol = load_module(stmt.module, child_search_paths, loaded_modules, verbose)
                for name, kind in mod_symbol.exports.items():
                    if kind == "function" and name in mod_symbol.functions:
                        checker.functions[name] = mod_symbol.functions[name]
                    else:
                        checker.env[name] = kind
            else:
                for alias_obj in stmt.names or []:
                    name = alias_obj.name
                    asname = alias_obj.asname or name
                    try:
                        sub_mod = load_module(stmt.module + [name], child_search_paths, loaded_modules, verbose)
                    except ModuleNotFoundError:
                        if mod_symbol is None:
                            mod_symbol = load_module(stmt.module, child_search_paths, loaded_modules, verbose)
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

    checker.check(program)

    # Step 4: Collect exports (functions, classes, globals)
    exports = {}
    functions = {}
    for stmt in program.body:
        if isinstance(stmt, FunctionDef):
            exports[stmt.name] = "function"  # attribute access type
            if stmt.name in checker.functions:
                functions[stmt.name] = checker.functions[stmt.name]
        elif isinstance(stmt, ClassDef):
            exports[stmt.name] = "class"
        elif isinstance(stmt, VarDecl):
            exports[stmt.name] = stmt.declared_type

    vendor_metadata = None
    if "vendor" in filepath.split(os.sep):
        vendor_metadata = load_vendor_metadata(filepath)

    program.module_name = ".".join(module_name)
    mod_symbol = ModuleSymbol(
        name=".".join(module_name),
        program=program,
        path=filepath,
        exports=exports,
        functions=functions,
        vendor_metadata=vendor_metadata,
    )
    loaded_modules[name_tuple] = mod_symbol
    return mod_symbol
