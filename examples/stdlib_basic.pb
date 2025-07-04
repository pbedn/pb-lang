import random as r
from random import randint, random


def main():
    r.seed(1)
    
    # test var decl
    x: int = randint(1, 10)
    print(f"randint: {x}")
    
    # test call from fstrings
    print(f"random: {random()}")

    # test import alias
    print(f"uniform: {r.uniform(0.25, 0.75)}")

if __name__ == "__main__":
    main()
