# python .\examples\exceptions2.pb
# Caught ValueError: Damage must be non-negative
# Caught RuntimeError: Not enough mana!
# Caught ZeroDivisionError: integer division or modulo by zero
# Caught AttributeError: 'Mage' object has no attribute 'undefined_attr'

# PB -> AttributeError: 'CallExpr' object has no attribute 'name'

class Player:
    name: str = "P"

    def __init__(self) -> None:
        self.hp = 150

    # New helper that can raise an exception
    def hit(self, damage: int) -> None:
        """Decrease HP; raise ValueError on invalid damage."""
        if damage < 0:
            raise ValueError("Damage must be non-negative")
        self.hp -= damage


class Mage(Player):

    def __init__(self) -> None:
        super().__init__()         # clearer than explicit base call
        self.mana = 200

    # New method that over-casts a spell and may raise
    def cast(self, cost: int) -> None:
        """Spend mana; raise RuntimeError if not enough."""
        if cost > self.mana:
            raise RuntimeError("Not enough mana!")
        self.mana -= cost


# ----------------------------------------
# Helper that can raise a built-in exception
def safe_div(a: int, b: int) -> int:
    """Integer divide, re-raising ZeroDivisionError for b == 0."""
    return a // b                 # ⟵ will raise automatically when b == 0


# ----------------------------------------
# Entry point: exercise normal paths and exceptions
def main():
    # Normal use-cases
    p: Player = Player()
    m: Mage = Mage()

    # ------------------------------------------------------------
    # Exception tests (each in its own try/except so the program
    # continues and you see every message on one run)
    # ------------------------------------------------------------

    # 1) Custom ValueError from Player.hit
    try:
        p.hit(-10)
    except ValueError as exc:
        print("Caught ValueError:", exc)

    # 2) Custom RuntimeError from Mage.cast
    try:
        m.cast(999)
    except RuntimeError as exc:
        print("Caught RuntimeError:", exc)

    # 3) Built-in ZeroDivisionError
    try:
        safe_div(42, 0)
    except ZeroDivisionError as exc:
        print("Caught ZeroDivisionError:", exc)

    # 4) AttributeError (accessing undefined attribute)
    try:
        print(m.undefined_attr)
    except AttributeError as exc:
        print("Caught AttributeError:", exc)

if __name__ == "__main__":
    main()
