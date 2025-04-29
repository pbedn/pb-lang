from parser import Parser
from lexer import Lexer

def emit_c(ast):
    lines = ['#include <stdio.h>', '']
    for node in ast:
        if node[0] == "function":
            name = node[1]
            ret_type = node[3]
            body = node[4]

            header = f"{ret_type} {name}()" if name != "main" else "int main()"
            lines.append(f"{header} {{")

            for stmt in body:
                if stmt[0] == "print":
                    lines.append(f'    printf("{stmt[1]}\\n");')
                elif stmt[0] == "return":
                    lines.append(f'    return {stmt[1]};')
    lines.append('}')
    return "\n".join(lines)

if __name__ == "__main__":
    with open("test.pyc") as f:
        code = f.read()

    tokens = Lexer(code).tokenize()
    tree = Parser(tokens).parse()
    c_code = emit_c(tree)

    with open("out.c", "w") as f:
        f.write(c_code)

    print("Generated C code:")
    print(c_code)
