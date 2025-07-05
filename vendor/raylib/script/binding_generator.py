import re
import os
from collections import defaultdict, deque

HEADER_PATH = os.path.join(os.path.dirname(__file__), "../include/raylib.h")
PB_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "../raylib.pb")

TYPE_MAP = {
    "void": "None",
    "int": "int",
    "float": "float",
    "double": "float",
    "unsigned int": "int",
    "unsigned short": "int",
    "unsigned char": "int",
    "char": "int",
    "const char *": "str",
    "char *": "str",
    "bool": "bool",
    "long": "int",
    "unsigned long": "int",
    "long long": "int",
    "unsigned long long": "int",
}

IMMEDIATE_ALIASES = {
    "Vector4": ["Quaternion"],
    "Texture": ["Texture2D", "TextureCubemap"],
    "RenderTexture": ["RenderTexture2D"],
    "Camera3D": ["Camera"],
}

IMMEDIATE_ALIAS_SET = set(alias for aliases in IMMEDIATE_ALIASES.values() for alias in aliases)

def map_c_type(c_type):
    """Map a C type to a PB type."""
    c_type = c_type.replace("const ", "").strip()
    # Normalize all unsigned variants
    c_type = re.sub(r'\bunsigned\s+int\b', 'int', c_type)
    c_type = re.sub(r'\bunsigned\s+char\b', 'int', c_type)
    c_type = re.sub(r'\bunsigned\s+short\b', 'int', c_type)
    c_type = re.sub(r'\bunsigned\b', 'int', c_type)
    c_type = re.sub(r'\bsigned\s+int\b', 'int', c_type)
    c_type = re.sub(r'\bsigned\b', '', c_type)
    if c_type.endswith("*"):
        return "int"
    if c_type.endswith("*"):
        if "char" in c_type:
            return "str"
        return "int"
    return TYPE_MAP.get(c_type, c_type)

def parse_function_pointer_aliases(header):
    """
    Finds typedef function pointer types and returns
    a list of (alias, argtypes, returntype, paramnames)
    Skips any function pointer with ... (variable args).
    """
    result = []
    # Example: typedef void (*AudioCallback)(void *bufferData, unsigned int frames);
    pattern = re.compile(
        r"typedef\s+([a-zA-Z0-9_ *]+)\s*\(\s*\*\s*([a-zA-Z0-9_]+)\s*\)\s*\(([^)]*)\)\s*;"
    )

    for ret, alias, params in pattern.findall(header):
        ret = map_c_type(ret.strip())
        paramtypes = []
        paramnames = []
        params = params.strip()
        if params and params != "void":
            for param in params.split(","):
                param = param.strip()
                if "va_list" in param or "..." in param:
                    continue  # skip this parameter but NOT the typedef!
                if "*" in param:
                    t, n = param.rsplit("*", 1)
                    t = t.strip() + "*"
                elif " " in param:
                    t, n = param.rsplit(" ", 1)
                    t = t.strip()
                else:
                    t, n = param, ""
                pb_type = map_c_type(t)
                paramtypes.append(pb_type)
                paramnames.append(n.strip())
        result.append((alias, paramtypes, ret, paramnames))
    return result

def parse_opaque_structs(header):
    """
    Finds typedef struct forward declarations like
    'typedef struct rAudioBuffer rAudioBuffer;'
    Returns a list of such struct names.
    """
    result = []
    pattern = re.compile(r"typedef\s+struct\s+([a-zA-Z0-9_]+)\s+\1\s*;")
    for m in pattern.finditer(header):
        name = m.group(1)
        result.append(name)
    return result

def parse_type_aliases(header):
    """Return a list of (alias, orig), e.g. [('Texture2D', 'Texture'), ...]"""
    aliases = []
    # skip function pointer typedefs
    funcptr_names = set()
    pattern_fp = re.compile(
        r"typedef\s+([a-zA-Z0-9_ ]+)\s*\(\s*\*\s*([a-zA-Z0-9_]+)\s*\)\s*\(([^)]*)\)\s*;"
    )
    for _, alias, _ in pattern_fp.findall(header):
        funcptr_names.add(alias)
    for m in re.finditer(r"typedef\s+(?:struct\s+|enum\s+)?([a-zA-Z0-9_]+)\s+([a-zA-Z0-9_]+)\s*;", header):
        orig, alias = m.groups()
        if orig == alias or alias in funcptr_names:
            continue
        aliases.append((alias, orig))
    return aliases

def parse_functions(header):
    func_regex = re.compile(r'RLAPI\s+([a-zA-Z0-9_ *]+?)\s+([a-zA-Z0-9_]+)\s*\(([^)]*)\);')
    functions = []
    for ret, name, params in func_regex.findall(header):
        if "..." in params:
            if params.strip().endswith(", ..."):
                params = params.rsplit(",", 1)[0].strip()
            else:
                continue

        ret = ret.strip().replace(" *", "*")
        param_list = []
        if params.strip() and params.strip() != "void":
            for p in params.split(","):
                p = p.strip()
                if "*" in p:
                    t, n = p.rsplit("*", 1)
                    t = t.strip() + "*"
                elif " " in p:
                    t, n = p.rsplit(" ", 1)
                    t = t.strip()
                else:
                    t, n = p, ""
                pb_type = map_c_type(t)
                n = n.replace("[", "").replace("]", "")
                if n == "":
                    n = f"param{len(param_list)+1}"
                param_list.append(f"{n.strip()}: {pb_type}")
        sig = f"def {name}({', '.join(param_list)}) -> {map_c_type(ret)}: ..."
        functions.append(sig)
    return functions

def parse_constants(header):
    define_pattern = re.compile(r"#define\s+([A-Z0-9_]+)\s+(.+)")
    constants = []
    for m in define_pattern.finditer(header):
        name, val = m.groups()
        if name.isupper():
            constants.append(f"{name}: int = ...")

    enums = []
    for enum_match in re.finditer(r"typedef enum\s*{([^}]+)}\s*([a-zA-Z0-9_]+);", header, re.DOTALL):
        enum_body, enum_name = enum_match.groups()
        for line in enum_body.splitlines():
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            line = line.split("//", 1)[0].strip()
            if line.endswith(","):
                line = line[:-1].strip()
            if not line:
                continue
            if "=" in line:
                name = line.split("=")[0].strip()
            else:
                name = line.strip()
            if name:
                enums.append(f"{name}: int = ...")
    return constants + enums

def parse_structs(header):
    """Parse typedef structs as PB classes, group fields per line, strip comments, remove pointers/arrays and C type prefix in names."""
    structs = []
    struct_names = []
    struct_fields_types = []
    for struct_match in re.finditer(
        r"typedef struct\s+([a-zA-Z0-9_]+)?\s*{([^}]*)}\s*([a-zA-Z0-9_]+);",
        header, re.DOTALL):
        struct_body = struct_match.group(2)
        struct_name = struct_match.group(3)
        fields = []
        field_types = set()
        for line in struct_body.splitlines():
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            if "//" in line:
                line = line.split("//", 1)[0].strip()
            line = line.rstrip(";").strip()
            if not line:
                continue

            if ";" in line:
                line = line[:line.index(";")]
            type_and_names = line.strip()
            if not type_and_names:
                continue
            m = re.match(r"(.+?)\s+([^\s][^;]*)$", type_and_names)
            if not m:
                continue
            c_type = m.group(1).replace('const ', '').strip()
            names_str = m.group(2).strip().rstrip(',')
            names_str = re.sub(r"^(char|int|float|double|bool|short|long|struct)\b\s*", "", names_str)
            pb_type = map_c_type(c_type.replace('*', '').strip())
            name_list = [n.strip().rstrip(',') for n in names_str.split(",") if n.strip()]
            for raw_name in name_list:
                clean_name = re.sub(r'^\*+', '', raw_name)
                clean_name = re.sub(r'\[.*?\]', '', clean_name)
                clean_name = clean_name.strip()
                if not clean_name:
                    continue
                fields.append(f"    {clean_name}: {pb_type}")
                field_types.add(pb_type)
        if fields:
            struct_def = f"class {struct_name}:\n" + "\n".join(fields)
        else:
            struct_def = f"class {struct_name}:\n    pass"
        structs.append(struct_def)
        struct_names.append(struct_name)
        struct_fields_types.append((struct_name, field_types))
    return structs, struct_names, struct_fields_types

def main():
    with open(HEADER_PATH, encoding="utf-8") as f:
        header = f.read()

    constants = parse_constants(header)
    opaque_structs = parse_opaque_structs(header)
    structs, struct_names, struct_fields_types = parse_structs(header)
    aliases = parse_type_aliases(header)
    funcptr_aliases = parse_function_pointer_aliases(header)
    # Remove opaque names that are actually fully defined
    opaque_structs = [s for s in opaque_structs if s not in struct_names]
    alias_map = dict(aliases)

    # Determine if Callable import is needed
    needs_callable = bool(funcptr_aliases)

    with open(PB_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("# Auto-generated PB bindings for raylib\n\n")
        f.write("# pyright: reportAssignmentType=none\n\n")
        if needs_callable:
            f.write("from typing import Callable\n\n")

        # 1. Emit constants/enums
        for c in constants:
            f.write(c + "\n")
        f.write("\n")

        # 2. Emit opaque structs as empty classes
        for s in opaque_structs:
            f.write(f"class {s}:\n    \"\"\"Opaque struct; actual fields are not visible from binding.\"\"\"\n    pass\n\n")

        # 3. Emit regular structs
        for struct in structs:
            f.write(struct + "\n\n")
            # Parse class name from struct definition
            m = re.match(r"class\s+([a-zA-Z0-9_]+):", struct)
            if m:
                class_name = m.group(1)
                if class_name in IMMEDIATE_ALIASES:
                    for alias in IMMEDIATE_ALIASES[class_name]:
                        f.write(f"{alias} = {class_name}\n")
                    f.write("\n")

        # 4. Emit all type aliases
        for alias, orig in aliases:
            if alias not in IMMEDIATE_ALIAS_SET:
                f.write(f"{alias} = {orig}\n")
        f.write("\n")

        # 5. Emit all function pointer typedefs
        for alias, paramtypes, ret, paramnames in funcptr_aliases:
            arg_str = ", ".join(f"{n}: {t}" for n, t in zip(paramnames, paramtypes))
            comment = f"# {alias}({arg_str}) -> {ret}"
            typestr = f"Callable[[{', '.join(paramtypes)}], {ret}]"
            f.write(f"{comment}\n{alias} = {typestr}\n")
        f.write("\n")

        # 6. Emit functions
        functions = parse_functions(header)
        for fn in functions:
            f.write(fn + "\n")


if __name__ == "__main__":
    main()
