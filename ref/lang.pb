# lang.pb
# This file demonstrates all currently implemented features of the language.
# Each section includes comments describing what is tested.

# === Global variable declaration ===
counter: int = 100

# === Class definition ===
class Player:
    hp: int = 100
    species: str = "Human"  # class attribute shared by all instances

    def __init__(self, hp: int, mp: int=150):
        self.hp = hp  # instance attribute with same name as class attribute
        self.mp = mp
        self.score = 0
        self.name = "Hero"

    def heal(self, amount: int):
        self.hp += amount  # Augmented assignment on attribute

    def get_name(self) -> str:
        return self.name

    def get_species_one(self) -> str:
        return Player.species

    def add_to_counter(self):
        global counter
        counter += self.hp

# === Class definition: subclass with inheritance ===
class Mage(Player):
    power: str = "fire"

    def __init__(self, hp: int):
        Player.__init__(self, hp)
        self.mp = 200

    def cast_spell(self, spell_cost: int):
        if self.mp >= spell_cost:
            print("Spell cast!")
            self.mp -= spell_cost
        else:
            print("Not enough mana")

    def heal(self, amount: int):
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
    print("=== F-String Interpolation ===")
    value: int = 42
    name: str = "Alice"
    print(f"Value is {value}")
    print(f"Hello, {name}!")

    print("=== Global Variable===")
    global counter
    print(f"Before Update: {counter}")
    counter = 200
    print(f"After Update: {counter}")

    # Function call and assignment
    print("=== Function Call ===")
    total: int = add(10, 5)
    divided: int = divide(10, 5)

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
    # List must not be empty current limitation for indexing set operation
    print("=== List and Indexing ===")
    numbers: list[int] = [100, 200, 300]
    first_number: int = numbers[0]
    print(first_number)
    print(numbers[0])
    print(numbers)

    # Init empty list
    arr_int_empty: list[int] = []
    arr_str_empty: list[str] = []
    arr_bool_empty: list[bool] = []

    # other list types
    arr_float_init: list[float] = [1.1, 2.2, 3.3]
    arr_str_init: list[str] = ["abc", "def"]
    arr_bool_init: list[bool] = [True, False]
    print(arr_float_init[0])
    print(arr_float_init)
    print(arr_str_init[0])
    print(arr_str_init)
    print(arr_bool_init[0])
    print(arr_bool_init)

    # Can modify list using indexing
    arr_float_init[0] = 100.101
    arr_str_init[0] = "some string"
    arr_bool_init[0] = False
    print(arr_float_init)
    print(arr_str_init)
    print(arr_bool_init)

    print("=== List Operations ===")
    # append
    # remove ?
    # pop
    # insert
    # sort
    # ..

    print("=== Dict Literal and Access ===")
    settings: dict[str, int] = {"volume": 10, "brightness": 75}
    print(settings["volume"])
    print(settings["brightness"])

    map_str: dict[str, str] = {"a": "sth here", "b": "and here"}
    print(map_str["a"])
    print(map_str["b"])

    # Not supported yet - Currently it just skips try except
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

    print("=== Explicit Type Conversion ===")
    i: int = 10
    f: float = float(i)
    print(f"i: {i}, f: {f}")

    f2: float = 3.5
    i2: int = int(f2)
    print(f"f2: {f2}, i2: {i2}")

    # === Class instantiation and method calls ===
    print("=== Class Instantiation and Methods ===")
    player: Player = Player(110)
    print(f"player.hp: {player.hp}")
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
    print(f"Player1 score: {player1.score}")
    print(f"Player2 score (should be default): {player2.score}")

    # Access class attribute via class and instances
    print(f"Player class species: {Player.species}")

    print(f"Species from player1 (via class attribute): {player1.get_species_one()}")

    # Shadow class variable via instance
    player1.hp = 777
    print(f"Player1.hp (instance attribute): {player1.hp}")

    print(f"Player2.hp (instance attribute): {player2.hp}")

    print(f"Player.hp (class attribute): {Player.hp}")

    # === Attribute access and assignment ===
    print("Directly setting player.hp to 999")
    player.hp = 999
    print(player.hp)

    # === Inheritance: Using Mage subclass ===
    print("=== Inheritance: Mage Subclass ===")
    mage: Mage = Mage(120)
    print(f"Mage name: {mage.get_name()}")  # inherited from Player

    print(f"Mage HP: {mage.hp}")
    print(f"Mage MP: {mage.mp}")

    print("Mage casts a spell costing 20 mana...")
    mage.cast_spell(20)
    print(f"Remaining MP: {mage.mp}")

    print("Mage takes damage and heals...")
    mage.hp -= 30
    mage.mp -= 10
    print(f"HP after damage: {mage.hp}")
    print(f"MP after damage: {mage.mp}")

    mage.heal(40)  # uses overridden heal
    print(f"HP after healing: {mage.hp}")
    print(f"MP after healing: {mage.mp}")

    # Return statement to indicate success
    return 0
