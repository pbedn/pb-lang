class Empty:
    pass

class ClassWithUserDefinedAttr:
    uda: Empty = Empty()

e: Empty = Empty()
uda: ClassWithUserDefinedAttr = ClassWithUserDefinedAttr()

# ────────────────────────────────────────────────────────────────
class Player:
    name: str = "P"
    BASE_HP: int = 150

    def __init__(self) -> None:
        self.hp = 150

    def get_hp(self) -> int:
        return self.hp

    def default_hp(self) -> int:
        return Player.BASE_HP

class Mage(Player):
    DEFAULT_MANA: int = 200

    def __init__(self) -> None:
        Player.__init__(self)
        self.mana = 200

    def total_power(self, bonus: int = 10) -> int:
        return self.hp + self.mana + bonus

class ArchMage(Mage):
    # multi-level inheritance to verify look-through depth
    pass

# ────────────────────────────────────────────────────────────────
def main() -> int:
    # print(uda)
    # print(ClassWithUserDefinedAttr.uda)
    # ── base-class instance access ──────────────────────────────
    p: Player = Player()
    print(p.hp)                # 150  (instance field)
    print(p.get_hp())          # 150  (method)
    print(Player.name)         # "P"  (class attr)
    print(Player.BASE_HP)      # 150  (class attr)
    # print(p.name)              # "P"  (class attr via instance)

    # ── derived-class instance access ───────────────────────────
    m: Mage = Mage()           # uses default args
    print(m.hp)                # 150  (INHERITED field → must become m->base.hp)
    print(m.mana)              # 200  (own field)
    print(m.get_hp())          # 150
    # print(m.name)              # "P"  (class attr from base, via instance)
    # print(Mage.name)           # "P"  (class attr from base, via class)
    print(Mage.DEFAULT_MANA)   # 200  (own class attr)

    # ── multi-level instance access ─────────────────────────────
    a: ArchMage = ArchMage()
    print(a.mana)              # 200  (field in level-1 base)
    print(a.hp)                # 150  (field in level-2 base → m->base.base.hp in C)
    print(a.total_power())     # 350

    return 0
