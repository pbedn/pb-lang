import re
import os

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
}

def map_c_type(c_type):
    """Map a C type to a PB type."""
    c_type = c_type.replace("const ", "").strip()
    if c_type.endswith("*"):
        # Treat all pointers as int for simplicity, unless it's char*
        if "char" in c_type:
            return "str"
        return "int"
    return TYPE_MAP.get(c_type, c_type)  # For structs: use same name

def parse_functions(header):
    """Parse C functions from header file."""
    func_regex = re.compile(r'RLAPI\s+([a-zA-Z0-9_ *]+?)\s+([a-zA-Z0-9_]+)\s*\(([^)]*)\);')
    functions = []
    for ret, name, params in func_regex.findall(header):
        ret = ret.strip().replace(" *", "*")
        param_list = []
        if params.strip() and params.strip() != "void":
            for p in params.split(","):
                p = p.strip()
                # Split parameter into type and name
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
    """Parse #define, constants and enums as constants, skip all comments (including indented or next-line comments)."""
    # #define MACROS
    define_pattern = re.compile(
        r"#define\s+([A-Z0-9_]+)\s+(.+)"
    )
    constants = []
    for m in define_pattern.finditer(header):
        name, val = m.groups()
        if name.isupper():
            constants.append(f"{name}: int = ...")

    # Parse enums, line-by-line, skipping comments and blank lines
    enums = []
    for enum_match in re.finditer(r"typedef enum\s*{([^}]+)}\s*([a-zA-Z0-9_]+);", header, re.DOTALL):
        enum_body, enum_name = enum_match.groups()
        # Split by lines, not by comma
        for line in enum_body.splitlines():
            line = line.strip()
            if not line or line.startswith("//"):
                continue  # Skip empty lines or pure comments
            # Remove inline comment, if any
            line = line.split("//", 1)[0].strip()
            # Remove trailing commas
            if line.endswith(","):
                line = line[:-1].strip()
            if not line:
                continue
            # Extract name
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
    for struct_match in re.finditer(
        r"typedef struct\s+([a-zA-Z0-9_]+)?\s*{([^}]*)}\s*([a-zA-Z0-9_]+);",
        header, re.DOTALL):
        struct_body = struct_match.group(2)
        struct_name = struct_match.group(3)
        fields = []
        for line in struct_body.splitlines():
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            if "//" in line:
                line = line.split("//", 1)[0].strip()
            line = line.rstrip(";").strip()
            if not line:
                continue
            # Parse type and field list
            m = re.match(r"(.+?)\s+(.+)", line)
            if not m:
                continue
            c_type = m.group(1).replace('const ', '').strip()
            names_str = m.group(2).strip().rstrip(',')
            # Fix C unsigned type notation
            c_type = c_type.replace("unsigned int", "int").replace("unsigned char", "int").replace("unsigned short", "int").replace("unsigned", "int")
            pb_type = map_c_type(c_type.replace('*', '').strip())
            # Split all names by ','
            name_list = [n.strip().rstrip(',') for n in names_str.split(",") if n.strip()]
            for i, raw_name in enumerate(name_list):
                # Remove any pointer or array syntax
                clean_name = re.sub(r'^\*+', '', raw_name)  # Remove *
                clean_name = re.sub(r'\[.*?\]', '', clean_name)  # Remove [N]
                clean_name = clean_name.strip()
                if not clean_name:
                    continue
                fields.append(f"    {clean_name}: {pb_type}")
        if fields:
            struct_def = f"class {struct_name}:\n" + "\n".join(fields)
        else:
            struct_def = f"class {struct_name}:\n    pass"
        structs.append(struct_def)
    return [s + "\n" for s in structs]  # Add blank line between structs

def main():
    with open(HEADER_PATH, encoding="utf-8") as f:
        header = f.read()

    constants = parse_constants(header)
    structs = parse_structs(header)
    functions = parse_functions(header)

    with open(PB_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("# Auto-generated PB bindings for raylib\n\n")
        for c in constants:
            f.write(c + "\n")
        f.write("\n")
        for struct in structs:
            f.write(struct + "\n")
        f.write("\n")
        for fn in functions:
            f.write(fn + "\n")

if __name__ == "__main__":
    main()
