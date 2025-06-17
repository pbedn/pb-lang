class Player:
    species: str = "Human"

    def __init__(self, hp: int):
        self.hp = hp
        self.name = "Hero"

    def get_name(self) -> str:
        return self.name

def main():
    x: int = 5
    print(f"Simple fstring: x={x}")
    print(f"{x + 1}")
    print(f"Float conversion: {float(2)}")
    print("--------------------------------")
    p: Player = Player(100)
    print(f"player.hp: {p.hp}")
    print(f"player get_name: {p.get_name()}")
    print(f"Player.species: {Player.species}")
