import sys
from lexer import Lexer
from parser import Parser
from codegen import CCodeGenerator
from type_checker import TypeChecker, TypeError

from pprint import pprint

def compile_to_c(source_code: str, output_file: str = "out.c"):
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    pprint(tokens)
    ast = parser.parse()
    pprint(ast)

    # ✅ Run type checker
    try:
        checker = TypeChecker()
        checker.check(ast)
    except TypeError as e:
        print(f"❌ Type Error: {e}")
        return

    # ✅ Generate C code if type check passes
    codegen = CCodeGenerator()
    c_code = codegen.generate(ast)

    with open(output_file, "w") as f:
        f.write(c_code)
    print(f"✅ C code written to {output_file}")



if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python compiler.py file.pb")
        exit()
    filename = sys.argv[1]
    with open(filename) as f:
        src = f.read()
    compile_to_c(src)
