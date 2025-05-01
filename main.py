import sys
from lexer import Lexer
from parser import Parser
from codegen import CCodeGenerator
from pprint import pprint

def compile_to_c(source_code: str, output_file: str = "out.c"):
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    pprint(tokens)

    parser = Parser(tokens)
    ast = parser.parse()
    pprint(ast)

    generator = CCodeGenerator()
    c_code = generator.generate(ast)

    with open(output_file, "w") as f:
        f.write(c_code)
    print(f"✅ C code written to {output_file}")
    print(c_code)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python compiler.py file.pb")
        exit()
    filename = sys.argv[1]
    with open(filename) as f:
        src = f.read()
    compile_to_c(src)
