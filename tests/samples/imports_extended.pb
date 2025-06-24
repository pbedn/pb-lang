import mathlib
import mathlib as m1
import test_import.mathlib2
from test_import import mathlib2
from test_import import mathlib2 as m2
from test_import.mathlib2 import PI
from test_import.mathlib2 import PI as pi2


import utils

def main():
    mathlib.add(5, 4)
    print(mathlib.add(5, 4))
    x: int = mathlib.add(5, 4)
    print(x)

    print(f"import mathlib: {mathlib.PI}")
    print(f"import mathlib as m1: {mathlib.PI}")

    print(f"import test_import.mathlib2: {test_import.mathlib2.PI}")
    print(f"from test_import import mathlib2: {mathlib2.PI}")
    print(f"from test_import import mathlib2: {m2.PI}")
    print(f"from test_import.mathlib2 import PI: {PI}")
    print(f"from test_import.mathlib2 import PI as pi: {pi2}")

    utils.helper()
