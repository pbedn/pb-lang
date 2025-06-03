# lang.pb
# This file demonstrates all currently implemented features of the language.
# Each section includes comments describing what is tested.

# NOT SUPPORTED YET
# import utils

# === Global variable declaration ===
counter: int = 100

# === Class definition ===
class Player:
    hp: int = 100
    species: str = "Human"  # class attribute shared by all instances

    def __init__(self, hp: int, mp: int=150) -> None:
        self.hp = hp  # instance attribute with same name as class attribute
        self.mp = mp
        self.score = 0
        self.name = "Hero"

    def heal(self, amount: int) -> None:
        self.hp += amount  # Augmented assignment on attribute

    def get_name(self) -> str:
        return self.name

    def get_species_one(self) -> str:
        return Player.species

    def add_to_counter(self) -> None:
        global counter
        counter += self.hp

# === Class definition: subclass with inheritance ===
class Mage(Player):
    power: str = "fire"

    def __init__(self, hp: int) -> None:
        Player.__init__(self, hp)
        self.mp = 200

    def cast_spell(self, spell_cost: int) -> None:
        if self.mp >= spell_cost:
            print("Spell cast!")
            self.mp -= spell_cost
        else:
            print("Not enough mana")

    def heal(self, amount: int) -> None:
        self.hp += amount
        self.mp += amount // 2

# === Function definition with parameters and return value ===
def add(x: int, y: int) -> int:
    # Local variable assignment and arithmetic expression
    result: int = x + y
    
    # Print statements (strings and integers)
    print("Adding numbers:")
    print(result)
    
    # Return statement
    return result

def divide(x: int, y: int) -> int:
    if y == 0:
        raise RuntimeError("division by zero")
    return x // y

def increment(x: int, step: int = 1) -> int:
    return x + step

# === Function returning a boolean (demonstrates bool literals and if/else) ===
def is_even(n: int) -> bool:
    if n % 2 == 0:
        return True  # Built-in bool literal
    else:
        return False

# === Main function showcasing all features ===
def main() -> int:
    # NOT SUPPORTED YET
    # print("=== Import and Call ===")
    # utils.helper()

    print("=== F-String Interpolation ===")
    value: int = 42
    name: str = "Alice"
    print(f"Value is {value}")
    print(f"Hello, {name}!")

    print("=== Global Variable Before Update ===")
    print(counter)

    global counter
    counter = 200

    print("=== Global Variable After Update ===")
    print(counter)

    # Function call and assignment
    print("=== Function Call ===")
    total: int = add(10, 5)

    print("=== Function with Default Argument ===")
    a: int = increment(5)
    b: int = increment(5, 3)
    print(a)
    print(b)

    print("=== Assert Statement ===")
    abc: int = 10
    efg: int = 10
    assert abc == efg
    print("Assertion passed")

    # Explicit var declaration
    print("=== Handle Float/Double ===")
    threshold: float = 50.0
    print(threshold)
    
    # If/Else statement using a function returning bool
    print("=== If/Else ===")
    if is_even(total):
        print("Total is even")
    else:
        print("Total is odd")
    
    # While loop with condition and local variable update
    print("=== While Loop ===")
    loop_counter: int = 0
    while loop_counter < 3:
        print(loop_counter)
        loop_counter = loop_counter + 1  # Reassignment
    
    # For loop using range(start, end)
    print("=== For Loop with range(0, 3) ===")
    for i in range(0, 3):
        print(i)
    
    # For loop using range(end)
    print("=== For Loop with range(2) ===")
    for j in range(2):
        print(j)
    
    # For loop with break and continue control flow
    print("=== Break and Continue ===")
    for k in range(0, 5):
        if k == 2:
            continue  # Skip current iteration
        if k == 4:
            break  # Exit loop
        print(k)
    
    # List literal and indexing
    print("=== List and Indexing ===")
    numbers: list[int] = [100, 200, 300]  # ListExpr
    first_number: int = numbers[0]  # IndexExpr
    second_number: int = numbers[1]
    print(first_number)
    print(second_number)

    print("=== Dict Literal and Access ===")
    settings: dict[str, int] = {"volume": 10, "brightness": 75}
    print(settings["volume"])
    print(settings["brightness"])

    map_str: dict[str, str] = {"a": "sth here", "b": "and here"}
    print(map_str["a"])
    print(map_str["b"])

    print("=== Try / Except / Raise ===")
    try:
        result: int = divide(10, 0)
        print(result)
    except RuntimeError:
        print("Caught division by zero")
    
    # Boolean literals and logical operators
    print("=== Boolean Literals ===")
    x: bool = True
    y: bool = False
    if x and not y:  # Logical AND and NOT
        print("x is True and y is False")

    # Boolean list and indexing
    print("=== Boolean List and Indexing ===")
    flags: list[bool] = [True, False, True]
    first_flag: bool = flags[0]
    second_flag: bool = flags[1]
    print(first_flag)
    print(second_flag)

    print("=== Empty List ===")
    arr_int: list[int] = []
    arr_str: list[int] = []
    arr_bool: list[bool] = []

    # If/Elif/Else chain
    print("=== If/Elif/Else ===")
    n: int = 5
    if n == 0:
        print("zero")
    elif n == 5:
        print("five")
    else:
        print("other")

    # Pass statement demonstration
    print("=== Pass Statement ===")
    if True:
        pass
    print("Pass block completed")

    # 'is' and 'is not' operators
    print("=== Is / Is Not Operators ===")
    aa: int = 10
    bb: int = 10
    if aa is bb:
        print("a is b")
    if aa is not 20:
        print("a is not 20")

    # Augmented assignment demonstration
    print("=== Augmented Assignment ===")
    m: int = 5
    print(m)
    m += 3
    print(m)
    m -= 2
    print(m)
    m *= 4
    print(m)
    m //= 2
    print(m)
    m %= 3
    print(m)
    mm: float = 5.0
    mm /= 2
    print(mm)

    # NOT SUPPORTED YET
    # print("=== Explicit Type Conversion ===")
    # i: int = 10
    # f: float = float(i)
    # print(f)

    # f2: float = 3.5
    # i2: int = int(f2)
    # print(i2)

    # === Class instantiation and method calls ===
    print("=== Class Instantiation and Methods ===")
    player: Player = Player(110)
    print(player.hp)
    print("Healing player by 50...")
    player.heal(50)
    print(player.hp)

    print("Adding player's hp to global counter...")
    player.add_to_counter()
    print("Updated counter:")
    print(counter)

    print("=== Class vs Instance Variables ===")
    player1: Player = Player(1234)
    player2: Player = Player(5678)
    player1.score = 100
    print("Player1 score:")
    print(player1.score)
    print("Player2 score (should be default):")
    print(player2.score)

    # Access class attribute via class and instances
    print("Player class species:")
    print(Player.species)

    print("Species from player1 (via class attribute):")
    print(player1.get_species_one())

    # Shadow class variable via instance
    player1.hp = 777
    print("Player1.hp (instance attribute):")
    print(player1.hp)

    print("Player2.hp (instance attribute):")
    print(player2.hp)

    print("Player.hp (class attribute):")
    print(Player.hp)

    # === Attribute access and assignment ===
    print("Directly setting player.hp to 999")
    player.hp = 999
    print(player.hp)

    # === Inheritance: Using Mage subclass ===
    print("=== Inheritance: Mage Subclass ===")
    mage: Mage = Mage(120)
    print("Mage name:")
    print(mage.get_name())  # inherited from Player

    print("Mage HP:", mage.hp)
    print("Mage MP:", mage.mp)

    print("Mage casts a spell costing 20 mana...")
    mage.cast_spell(20)
    print("Remaining MP:", mage.mp)

    print("Mage takes damage and heals...")
    mage.hp -= 30
    mage.mp -= 10
    print("HP after damage:", mage.hp)
    print("MP after damage:", mage.mp)

    mage.heal(40)  # uses overridden heal
    print("HP after healing:", mage.hp)
    print("MP after healing:", mage.mp)

    # Return statement to indicate success
    return 0
