#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdarg.h>
static void pb_fail(const char *msg) {
    fprintf(stderr, "%s\n", msg);
    exit(EXIT_FAILURE);
}
// Runtime types for list[int] and dict[str,int]
typedef struct {
    int64_t len;
    int64_t *data;
} List_int;
typedef struct {
    const char *key;
    int64_t value;
} Pair_str_int;
typedef struct {
    int64_t len;
    Pair_str_int *data;
} Dict_str_int;
static void pb_print_int(int64_t x)   { printf("%lld\n", x); }
static void pb_print_double(double x) { printf("%f\n", x); }
static void pb_print_str(const char *s){ printf("%s\n", s); }
static void pb_print_bool(bool b)     { printf("%s\n", b?"True":"False"); }
static int64_t pb_dict_get(Dict_str_int d, const char * key) {
    for (int64_t i = 0; i < d.len; ++i) {
        if (strcmp(d.data[i].key, key) == 0) return d.data[i].value;
    }
    pb_fail("Key not found in dict");
    return 0;
}
typedef struct Player {
    int64_t hp;
    const char * species;
    int64_t mp;
    const char * name;
    int64_t score;
} Player;
typedef struct Mage {
    Player base;
    const char * power;
    int64_t mp;
} Mage;
int64_t Player_hp = 100;
const char * Player_species = "Human";
const char * Mage_power = "fire";
int64_t counter = 100;
int64_t add(int64_t x, int64_t y);
int64_t divide(int64_t x, int64_t y);
int64_t increment(int64_t x, int64_t step);
bool is_even(int64_t n);
void Player____init__(struct Player * self, int64_t hp, int64_t mp);
void Player__heal(struct Player * self, int64_t amount);
const char * Player__get_name(struct Player * self);
const char * Player__get_species_one(struct Player * self);
void Player__add_to_counter(struct Player * self);
void Mage____init__(struct Mage * self, int64_t hp);
void Mage__cast_spell(struct Mage * self, int64_t spell_cost);
void Mage__heal(struct Mage * self, int64_t amount);
void Player____init__(struct Player * self, int64_t hp, int64_t mp)
{
    (void)self;
    (void)hp;
    (void)mp;
    char __fbuf[256];
    (void)__fbuf;
    self->hp = hp;
    self->mp = mp;
    self->score = 0;
    self->name = "Hero";
}
void Player__heal(struct Player * self, int64_t amount)
{
    (void)self;
    (void)amount;
    char __fbuf[256];
    (void)__fbuf;
    self->hp += amount;
}
const char * Player__get_name(struct Player * self)
{
    (void)self;
    char __fbuf[256];
    (void)__fbuf;
    return self->name;
}
const char * Player__get_species_one(struct Player * self)
{
    (void)self;
    char __fbuf[256];
    (void)__fbuf;
    return Player_species;
}
void Player__add_to_counter(struct Player * self)
{
    (void)self;
    char __fbuf[256];
    (void)__fbuf;
    /* global counter */
    counter += self->hp;
}
void Mage____init__(struct Mage * self, int64_t hp)
{
    (void)self;
    (void)hp;
    char __fbuf[256];
    (void)__fbuf;
    Player____init__((struct Player *)self, hp, 150);
    self->mp = 200;
}
void Mage__cast_spell(struct Mage * self, int64_t spell_cost)
{
    (void)self;
    (void)spell_cost;
    char __fbuf[256];
    (void)__fbuf;
    if ((self->mp >= spell_cost)) {
        pb_print_str("Spell cast!");
        self->mp -= spell_cost;
    }
    else  {
        pb_print_str("Not enough mana");
    }
}
void Mage__heal(struct Mage * self, int64_t amount)
{
    (void)self;
    (void)amount;
    char __fbuf[256];
    (void)__fbuf;
    self->base.hp += amount;
    self->mp += (amount / 2);
}
static inline void Mage__add_to_counter(
    struct Mage * self) {
    Player__add_to_counter((struct Player *)self);
}
static inline const char * Mage__get_name(
    struct Mage * self) {
    return Player__get_name((struct Player *)self);
}
static inline const char * Mage__get_species_one(
    struct Mage * self) {
    return Player__get_species_one((struct Player *)self);
}
int64_t add(int64_t x, int64_t y)
{
    (void)x;
    (void)y;
    char __fbuf[256];
    (void)__fbuf;
    int64_t result = (x + y);
    pb_print_str("Adding numbers:");
    pb_print_int(result);
    return result;
}
int64_t divide(int64_t x, int64_t y)
{
    (void)x;
    (void)y;
    char __fbuf[256];
    (void)__fbuf;
    if ((y == 0)) {
        pb_fail("Exception raised");
    }
    return (x / y);
}
int64_t increment(int64_t x, int64_t step)
{
    (void)x;
    (void)step;
    char __fbuf[256];
    (void)__fbuf;
    return (x + step);
}
bool is_even(int64_t n)
{
    (void)n;
    char __fbuf[256];
    (void)__fbuf;
    if (((n % 2) == 0)) {
        return true;
    }
    else  {
        return false;
    }
}
int main(void)
{
    char __fbuf[256];
    (void)__fbuf;
    pb_print_str("=== F-String Interpolation ===");
    int64_t value = 42;
    const char * name = "Alice";
    pb_print_str((snprintf(__fbuf, 256, "Value is %lld", value), __fbuf));
    pb_print_str((snprintf(__fbuf, 256, "Hello, %s!", name), __fbuf));
    pb_print_str("=== Global Variable Before Update ===");
    pb_print_int(counter);
    /* global counter */
    counter = 200;
    pb_print_str("=== Global Variable After Update ===");
    pb_print_int(counter);
    pb_print_str("=== Function Call ===");
    int64_t total = add(10, 5);
    pb_print_str("=== Function with Default Argument ===");
    int64_t a = increment(5, 1);
    int64_t b = increment(5, 3);
    pb_print_int(a);
    pb_print_int(b);
    pb_print_str("=== Assert Statement ===");
    int64_t abc = 10;
    int64_t efg = 10;
    if(!((abc == efg))) pb_fail("Assertion failed");
    pb_print_str("Assertion passed");
    pb_print_str("=== Handle Float/Double ===");
    double threshold = 50.0;
    pb_print_double(threshold);
    pb_print_str("=== If/Else ===");
    if (is_even(total)) {
        pb_print_str("Total is even");
    }
    else  {
        pb_print_str("Total is odd");
    }
    pb_print_str("=== While Loop ===");
    int64_t loop_counter = 0;
    while ((loop_counter < 3)) {
        pb_print_int(loop_counter);
        loop_counter = (loop_counter + 1);
    }
    pb_print_str("=== For Loop with range(0, 3) ===");
    for (int64_t i = 0; i < 3; ++i) {
        pb_print_int(i);
    }
    pb_print_str("=== For Loop with range(2) ===");
    for (int64_t j = 0; j < 2; ++j) {
        pb_print_int(j);
    }
    pb_print_str("=== Break and Continue ===");
    for (int64_t k = 0; k < 5; ++k) {
        if ((k == 2)) {
        continue;
    }
        if ((k == 4)) {
        break;
    }
        pb_print_int(k);
    }
    pb_print_str("=== List and Indexing ===");
    int64_t __tmp_list_1[] = {100, 200, 300};
    List_int numbers = (List_int){ .len=3, .data=__tmp_list_1 };
    int64_t first_number = numbers.data[0];
    int64_t second_number = numbers.data[1];
    pb_print_int(first_number);
    pb_print_int(second_number);
    pb_print_str("=== Dict Literal and Access ===");
    Pair_str_int __tmp_dict_2[] = {{"volume", 10}, {"brightness", 75}};
    Dict_str_int settings = (Dict_str_int){ .len=2, .data=__tmp_dict_2 };
    pb_print_int(pb_dict_get(settings, "volume"));
    pb_print_int(pb_dict_get(settings, "brightness"));
    pb_print_str("=== Try / Except / Raise ===");
    /* try/except not supported at runtime */
    pb_print_str("=== Boolean Literals ===");
    bool x = true;
    bool y = false;
    if ((x && !(y))) {
        pb_print_str("x is True and y is False");
    }
    pb_print_str("=== Boolean List and Indexing ===");
    int64_t __tmp_list_3[] = {true, false, true};
    List_int flags = (List_int){ .len=3, .data=__tmp_list_3 };
    bool first_flag = flags.data[0];
    bool second_flag = flags.data[1];
    pb_print_bool(first_flag);
    pb_print_bool(second_flag);
    pb_print_str("=== If/Elif/Else ===");
    int64_t n = 5;
    if ((n == 0)) {
        pb_print_str("zero");
    }
    else if ((n == 5)) {
        pb_print_str("five");
    }
    else  {
        pb_print_str("other");
    }
    pb_print_str("=== Pass Statement ===");
    if (true) {
        ;  // pass
    }
    pb_print_str("Pass block completed");
    pb_print_str("=== Is / Is Not Operators ===");
    int64_t aa = 10;
    int64_t bb = 10;
    if ((aa == bb)) {
        pb_print_str("a is b");
    }
    if ((aa != 20)) {
        pb_print_str("a is not 20");
    }
    pb_print_str("=== Augmented Assignment ===");
    int64_t m = 5;
    pb_print_int(m);
    m += 3;
    pb_print_int(m);
    m -= 2;
    pb_print_int(m);
    m *= 4;
    pb_print_int(m);
    m /= 2;
    pb_print_int(m);
    m %= 3;
    pb_print_int(m);
    double mm = 5.0;
    mm /= 2;
    pb_print_double(mm);
    pb_print_str("=== Class Instantiation and Methods ===");
    struct Player __tmp_player_4;
    Player____init__(&__tmp_player_4, 110, 150);
    struct Player * player = &__tmp_player_4;
    pb_print_int(player->hp);
    pb_print_str("Healing player by 50...");
    Player__heal(player, 50);
    pb_print_int(player->hp);
    pb_print_str("Adding player's hp to global counter...");
    Player__add_to_counter(player);
    pb_print_str("Updated counter:");
    pb_print_int(counter);
    pb_print_str("=== Class vs Instance Variables ===");
    struct Player __tmp_player_5;
    Player____init__(&__tmp_player_5, 1234, 150);
    struct Player * player1 = &__tmp_player_5;
    struct Player __tmp_player_6;
    Player____init__(&__tmp_player_6, 5678, 150);
    struct Player * player2 = &__tmp_player_6;
    player1->score = 100;
    pb_print_str("Player1 score:");
    pb_print_int(player1->score);
    pb_print_str("Player2 score (should be default):");
    pb_print_int(player2->score);
    pb_print_str("Player class species:");
    pb_print_str(Player_species);
    pb_print_str("Species from player1 (via class attribute):");
    pb_print_str(Player__get_species_one(player1));
    player1->hp = 777;
    pb_print_str("Player1.hp (instance attribute):");
    pb_print_int(player1->hp);
    pb_print_str("Player2.hp (instance attribute):");
    pb_print_int(player2->hp);
    pb_print_str("Player.hp (class attribute):");
    pb_print_int(Player_hp);
    pb_print_str("Directly setting player.hp to 999");
    player->hp = 999;
    pb_print_int(player->hp);
    pb_print_str("=== Inheritance: Mage Subclass ===");
    struct Mage __tmp_mage_7;
    Mage____init__(&__tmp_mage_7, 120);
    struct Mage * mage = &__tmp_mage_7;
    pb_print_str("Mage name:");
    pb_print_str(Mage__get_name(mage));
    pb_print_str("Mage HP:");
    pb_print_int(mage->base.hp);
    pb_print_str("Mage MP:");
    pb_print_int(mage->mp);
    pb_print_str("Mage casts a spell costing 20 mana...");
    Mage__cast_spell(mage, 20);
    pb_print_str("Remaining MP:");
    pb_print_int(mage->mp);
    pb_print_str("Mage takes damage and heals...");
    mage->base.hp -= 30;
    mage->mp -= 10;
    pb_print_str("HP after damage:");
    pb_print_int(mage->base.hp);
    pb_print_str("MP after damage:");
    pb_print_int(mage->mp);
    Mage__heal(mage, 40);
    pb_print_str("HP after healing:");
    pb_print_int(mage->base.hp);
    pb_print_str("MP after healing:");
    pb_print_int(mage->mp);
    return 0;
}
