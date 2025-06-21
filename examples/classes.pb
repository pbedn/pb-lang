# Class can be empty
class Empty:
    pass

# Can have class attributes
class ClassWithAttr:
    attr1: str = "some attr"
    ATR2: str = "other attr"

class ClassWithUserDefinedAttr:
    uda: Empty = Empty()

class Player:
    name: str = "P"

    def __init__(self) -> None:
        self.hp = 150

    def get_hp(self) -> int:
        return self.hp

class Mage(Player):

    def __init__(self) -> None:
        Player.__init__(self)
        self.mana = 200

def main() -> int:
    p: Player = Player()
    print(p.hp)
    print(p.get_hp())
    print(Player.name)
    m: Mage = Mage()
    print(m.hp)
    print(m.mana)
    print(m.get_hp())
    return 0
